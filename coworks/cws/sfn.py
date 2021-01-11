import json
import os
import pathlib
from abc import ABC, abstractmethod

import click
import yaml

from .writer import CwsWriter, CwsWriterError

INITIAL_STATE_NAME = "Init"
LAMBDA_ERROR_FALLBACK = "MicroServiceErrorFallback"


class CwsSFNTranslater(CwsWriter):

    def __init__(self, app=None, name='translate-sfn', extension='yml'):
        super().__init__(app, name=name)
        self.extension = extension

    @property
    def options(self):
        return [
            *super().options,
            click.option('--account_number', default=None),
        ]

    def _export_header(self, **options):
        ...

    def _export_content(self, *, project_dir, module, **options):
        module_path = module.split('.')
        step_functions = {}
        sfn_name = self.app.sfn_name
        filename = pathlib.Path(project_dir, *module_path[:-1]) / f"{sfn_name}.{self.extension}"

        options.pop('output')
        options.pop('error')
        sfn = StepFunction(sfn_name, filename, **options)
        step_functions[sfn_name] = sfn.generate()
        for idx, (sfn_name, sfn) in enumerate(step_functions.items()):
            if idx > 0:
                print("---", file=self.output)
            print(json.dumps(sfn, indent=2), file=self.output)


class StepFunction:

    def __init__(self, sfn_name, filepath, **options):
        self.name = sfn_name
        self.options = options
        self.all_states = []
        try:
            with filepath.open() as file:
                self.data = yaml.load(file, Loader=yaml.SafeLoader)
                if not self.data:
                    raise CwsWriterError(f"The content of the {sfn_name} microservice seems to be empty.")
        except FileNotFoundError:
            path = pathlib.Path(filepath)
            if not path.is_absolute():
                path = pathlib.Path(f"{os.getcwd()}/{filepath}")
            raise CwsWriterError(f"The source for the {sfn_name} microservice should be found in {path}.")
        except Exception as e:
            raise CwsWriterError(str(e))

        self.global_catch = 'catch' in self.data

    def generate(self):
        first = PassState(self, {'name': INITIAL_STATE_NAME})

        self.all_states.append(first)
        states = State.get_or_raise(self.data, 'states')
        self.add_actions(self.all_states, states)

        first.add_next_or_end('Next', self.all_states[1].name)

        # global catch state (no automatic catch in corresponding ations)
        if self.global_catch:
            error_fallback = PassState(self, {'name': LAMBDA_ERROR_FALLBACK})
            self.all_states.append(error_fallback)
            self.add_actions(self.all_states, self.data['catch'], no_catch=True)

        return {
            "Version": "1.0",
            "Comment": self.data.get('comment', self.name),
            "StartAt": "Init",
            "States": {state.name: state.state for state in self.all_states}
        }

    def add_actions(self, states, actions, no_catch=False):
        if not actions:
            raise CwsWriterError("Actions list cannot be empty.")

        previous_state = states[-1] if len(states) > 0 else None
        for action in actions:
            state = self.new_state(action, previous_state, no_catch=no_catch)
            states.append(state)
            previous_state = state

            if action == actions[-1] and 'Next' not in state.state:
                state.add_next_or_end('End', True)

            states.extend(state.catch_states)

    def new_state(self, action, previous_state, no_catch=False):
        def add_next_to_previous_state():
            if isinstance(previous_state, ChoiceState):
                if 'Default' not in previous_state.state:
                    previous_state.state['Default'] = state.name
            else:
                if 'Next' not in previous_state.state and 'End' not in previous_state.state:
                    previous_state.state['Next'] = state.name

        if 'choices' in action:
            state = ChoiceState(self, action)
        elif 'fail' in action:
            state = FailState(self, action)
        elif 'pass' in action:
            state = PassState(self, action)
        elif 'success' in action:
            state = SuccessState(self, action)
        elif 'tech' in action:
            state = TechState(self, action, no_catch=no_catch, **self.options)
        elif 'wait' in action:
            state = WaitState(self, action)
        else:
            raise CwsWriterError(f"Undefined type of action for {action}")

        if previous_state is not None:
            add_next_to_previous_state()

        return state

    def __repr__(self):
        return f"{self.name} : {self.all_states}"


class State(ABC):

    def __init__(self, sfn, action, **kwargs):
        self.sfn = sfn
        self.action = action or {}
        self.state = {**kwargs}
        self.catch_states = []

    @property
    def name(self):
        return self.action.get('name', f'The action {self.action} has no name')

    @property
    def slug(self):
        return "_".join(self.name.split()).lower()

    @staticmethod
    def get_or_raise(action, key):
        """Get the value at key or raise an error if the key doesn't exist."""
        try:
            return action[key]
        except (KeyError, TypeError):
            raise CwsWriterError(f"The key {key} is missing for {action}")

    @staticmethod
    def get_goto(action_or_choice):
        goto = action_or_choice.get('goto')
        if goto == "End":
            return "End", True
        elif goto is not None:
            return "Next", goto
        return None

    def add_goto(self, action):
        entry = self.get_goto(action)
        if entry:
            key, value = entry
            self.add_next_or_end(key, value)

    def __repr__(self):
        return f"{self.name} : {json.dumps(self.state, indent=2)}"

    @abstractmethod
    def add_next_or_end(self, key, value):
        """Do nothing by default."""


class SuccessState(State):
    def __init__(self, sfn, action=None, **kwargs):
        kwargs.update({
            "Type": "Succeed",
        })
        super().__init__(sfn, action, **kwargs)

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class FailState(State):
    def __init__(self, sfn, action, **kwargs):
        super().__init__(sfn, action, Type="Fail", **kwargs)
        self.state['Cause'] = action.get('cause', "Undefined reason")
        self.state['Error'] = action.get('error', "Undefined error")

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class ChoiceState(State):

    def __init__(self, sfn, action, **kwargs):
        super().__init__(sfn, action, Type="Choice", **kwargs)

        choices = self.get_or_raise(action, 'choices')
        if not choices:
            raise CwsWriterError(f"The list of choices may not be empty {action}")

        self.state['Choices'] = self.create_choices_sequence(choices)

        if 'default' in action:
            self.state['Default'] = action.get('default')

    def create_choices_sequence(self, choices):

        def create_condition(data):
            var = self.get_or_raise(data, 'var')
            oper = self.get_or_raise(data, 'oper')
            val = self.get_or_raise(data, 'value')
            return {
                'Variable': var,
                oper: val,
            }

        switch = []
        for choice in choices:
            entry = self.get_goto(choice)
            if entry is None:
                raise KeyError(f"The key goto is missing for {choice}")

            key, value = entry
            if 'not' in choice:
                switch.append({"Not": create_condition(choice['not']), key: value})
            elif 'or' in choice:
                switch.append({"Or": create_condition(choice['or']), key: value})
            elif 'and' in choice:
                switch.append({"And": create_condition(choice['and']), key: value})
            else:
                switch.append({**create_condition(choice), key: value})
        return switch

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class PassState(State):
    def __init__(self, sfn, action, **kwargs):
        kwargs.setdefault("Type", "Pass")
        super().__init__(sfn, action, **kwargs)

    def add_next_or_end(self, key, value):
        self.state[key] = value


class EndState(PassState):
    def __init__(self, sfn, action, **kwargs):
        super().__init__(sfn, action, **kwargs)
        self.state['End'] = True

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class WaitState(PassState):
    def __init__(self, sfn, action, **kwargs):
        super().__init__(sfn, action, Type="Wait", **kwargs)
        self.state['Seconds'] = action['wait']
        self.add_goto(action)


class TechState(PassState):
    def __init__(self, sfn, action, *, workspace, **kwargs):
        self.no_catch = kwargs.pop('no_catch', False)
        super().__init__(sfn, action, Type="Task", **kwargs)

        tech_data = self.get_or_raise(action, 'tech')
        if not tech_data:
            raise CwsWriterError(f"The content of tech action is empty")

        try:
            res = self.get_or_raise(tech_data, 'service')
            if kwargs.get('customer'):
                self.state[
                    'Resource'] = f"arn:aws:lambda:eu-west-1:{kwargs['account_number']}:function:{res}-{kwargs.get('customer')}-{workspace}"
            else:
                self.state[
                    'Resource'] = f"arn:aws:lambda:eu-west-1:{kwargs['account_number']}:function:{res}-{workspace}"
            self.state["InputPath"] = f"$"
            result_path = tech_data.get('result_path')
            self.state["ResultPath"] = result_path if result_path else f"$.{self.slug}.result"
            output_path = tech_data.get('output_path')
            self.state["OutputPath"] = output_path if output_path else "$"
            self.state["Parameters"] = self.get_call_data(action, tech_data)

            if 'catch' not in action:
                if self.sfn.global_catch and not self.no_catch:
                    self.state["Catch"] = [{
                        "ErrorEquals": ["BadRequestError"],
                        "Next": LAMBDA_ERROR_FALLBACK
                    }]
            else:
                self.sfn.add_actions(self.catch_states, action['catch'])
                self.state["Catch"] = [{
                    "ErrorEquals": ["BadRequestError"],
                    "Next": self.catch_states[0].name
                }]
                if self.sfn.global_catch and "States.TaskFailed" not in [c["ErrorEquals"] for c in self.state["Catch"]]:
                    self.state["Catch"].append({
                        "ErrorEquals": ["States.TaskFailed"],
                        "Next": LAMBDA_ERROR_FALLBACK
                    })

        except KeyError as e:
            raise CwsWriterError(f"The key {e} is missing for {action}")

        self.add_goto(action)

        # complementary informations
        timeout = tech_data.get('timeout')
        if timeout is not None:
            self.state["TimeoutSeconds"] = timeout

    @staticmethod
    def get_call_data(action, tech_data):

        # get route and method
        route = method = None
        has_get = 'get' in tech_data
        has_post = 'post' in tech_data
        has_put = 'put' in tech_data
        if has_get + has_post + has_put > 1:
            raise CwsWriterError(f"Too many methods defined for {action}")
        if has_get:
            route = tech_data['get']
            method = 'GET'
        if has_post:
            route = tech_data['post']
            method = 'POST'
        if has_put:
            route = tech_data['put']
            method = 'PUT'
        if route is None:
            raise CwsWriterError(f"No route defined for {action}")

        # get call parameters
        uri_params = tech_data.get('uri_params')
        query_params = tech_data.get('query_params')
        body = tech_data.get('body')
        form_data = tech_data.get('form-data')
        content_type = "application/json" if form_data is None else "multipart/form-data"

        return {
            "type": "CWS_SFN",
            "resource": route,
            "path": route,
            "requestContext": {
                "resourcePath": route,
                'httpMethod': method,
            },
            "multiValueQueryStringParameters": query_params,
            "pathParameters": uri_params,
            "headers": {
                "Accept-Encoding": "gzip,deflate",
                "Content-Type": content_type
            },
            "body": body if body else None,
            "form-data": TechState.validate_form_data(form_data) if form_data else None,
            "stageVariables": None,
        }

    @staticmethod
    def validate_form_data(form_data):
        return form_data
