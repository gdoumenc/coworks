import json
import os
import pathlib
from abc import ABC, abstractmethod

import yaml

from coworks.cli.writer import Writer, WriterError

INITIAL_STATE_NAME = "Init"
LAMBDA_ERROR_FALLBACK = "MicroServiceErrorFallback"


class StepFunctionWriter(Writer):

    def __init__(self, app=None, name='sfn', extension='yml'):
        super().__init__(app, name)
        self.extension = extension

    def _export_content(self, module_name='app', handler_name='biz', project_dir='.', **kwargs):

        # checks at least one microservices is defined
        if not self.app.services:
            print(f"No bizz service defined for {self.app.app_name}", file=self.error)

        module_path = module_name.split('.')
        step_functions = {}
        errors = {}
        biz = kwargs.get('biz')
        for service in self.app.services.values():
            sfn_name = service.sfn_name
            if sfn_name in step_functions or (biz is not None and sfn_name != biz):
                continue

            filename = pathlib.Path(project_dir, *module_path[:-1]) / f"{sfn_name}.{self.extension}"
            try:
                sfn = create_step_function(sfn_name, filename)
                step_functions[sfn_name] = sfn
            except WriterError as e:
                errors[sfn_name] = str(e)

        if errors:
            for sfn_name, error in errors.items():
                print(f"Error in {sfn_name}: {error}", file=self.error)
            raise WriterError()
        else:
            for idx, (sfn_name, sfn) in enumerate(step_functions.items()):
                if idx > 0:
                    print("---", file=self.output)
                print(json.dumps(sfn, indent=2), file=self.output)


def create_step_function(sfn_name, filepath):
    """Returns a tuple of step function, error"""
    try:
        with filepath.open() as file:
            data = yaml.load(file, Loader=yaml.SafeLoader)
            if not data:
                raise WriterError(f"The content of the {sfn_name} microservice seems to be empty.")

            first = PassState({'name': INITIAL_STATE_NAME})

            all_states = [first]
            states = State.get_or_raise(data, 'states')
            add_actions(all_states, states)

            first.state['Result'] = {}
            first.add_next_or_end('Next', all_states[1].name)

            # global catch state
            if 'catch' not in data:
                error_fallback = EndState({'name': LAMBDA_ERROR_FALLBACK})
                all_states.append(error_fallback)
            else:
                error_fallback = PassState({'name': LAMBDA_ERROR_FALLBACK})
                all_states.append(error_fallback)
                add_actions(all_states, data['catch'])

            return {
                "Version": "1.0",
                "Comment": data.get('comment', sfn_name),
                "StartAt": "Init",
                "States": {state.name: state.state for state in all_states}
            }
    except FileNotFoundError:
        raise WriterError(f"The source for the {sfn_name} microservice should be found in {os.getcwd()}/{filepath}.")
    except Exception as e:
        raise WriterError(str(e))


def add_actions(states, actions):
    if not actions:
        raise WriterError("Actions list cannot be empty.")

    previous_state = states[-1] if len(states) > 0 else None
    for action in actions:
        state = new_state(action, previous_state)
        states.append(state)
        previous_state = state

        if action == actions[-1] and 'Next' not in state.state:
            state.add_next_or_end('End', True)

        states.extend(state.catch_states)


def new_state(action, previous_state):
    def add_next_to_previous_state():
        if isinstance(previous_state, ChoiceState):
            if 'Default' not in previous_state.state:
                previous_state.state['Default'] = state.name
        else:
            if 'Next' not in previous_state.state and 'End' not in previous_state.state:
                previous_state.state['Next'] = state.name

    if 'choices' in action:
        state = ChoiceState(action)
    elif 'fail' in action:
        state = FailState(action)
    elif 'pass' in action:
        state = PassState(action)
    elif 'success' in action:
        state = SuccessState(action)
    elif 'tech' in action:
        state = TechState(action)
    elif 'wait' in action:
        state = WaitState(action)
    else:
        raise WriterError(f"Undefined type of action for {action}")

    if previous_state is not None:
        add_next_to_previous_state()

    return state


class State(ABC):

    def __init__(self, action, **kwargs):
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
            raise WriterError(f"The key {key} is missing for {action}")

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
    def __init__(self, action=None, **kwargs):
        kwargs.update({
            "Type": "Succeed",
        })
        super().__init__(action, **kwargs)

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class FailState(State):
    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Fail", **kwargs)

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class ChoiceState(State):

    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Choice", **kwargs)

        choices = self.get_or_raise(action, 'choices')
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
    def __init__(self, action, **kwargs):
        kwargs.setdefault("Type", "Pass")
        super().__init__(action, **kwargs)

    def add_next_or_end(self, key, value):
        self.state[key] = value


class EndState(PassState):
    def __init__(self, action, **kwargs):
        super().__init__(action, **kwargs)
        self.state['End'] = True

    def add_next_or_end(self, key, value):
        super().add_next_or_end(key, value)


class WaitState(PassState):
    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Wait", **kwargs)
        self.state['Seconds'] = action['wait']
        self.add_goto(action)


class TechState(PassState):
    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Task", **kwargs)

        tech_data = self.get_or_raise(action, 'tech')
        if not tech_data:
            raise WriterError(f"The content of tech action is empty")

        try:
            self.state['Resource'] = \
                f"arn:aws:lambda:eu-west-1:935392763270:function:{self.get_or_raise(tech_data, 'service')}"
            self.state["InputPath"] = f"$"
            self.state["ResultPath"] = f"$.{self.slug}.result"
            self.state["OutputPath"] = "$"
            self.state["Parameters"] = self.get_call_data(action, tech_data)

            if 'catch' not in action:
                self.state["Catch"] = [
                    {
                        "ErrorEquals": ["BadRequestError"],
                        "Next": LAMBDA_ERROR_FALLBACK
                    },
                    {
                        "ErrorEquals": ["States.TaskFailed"],
                        "Next": LAMBDA_ERROR_FALLBACK
                    },
                ]
            else:
                add_actions(self.catch_states, action['catch'])
                self.state["Catch"] = [{
                    "ErrorEquals": ["BadRequestError"],
                    "Next": self.catch_states[0].name
                }]

        except KeyError as e:
            raise WriterError(f"The key {e} is missing for {action}")

        self.add_goto(action)

        # complementary informations
        timeout = tech_data.get('timeout')
        if timeout is not None:
            self.state["TimeoutSeconds"] = timeout

    @staticmethod
    def get_call_data(action, tech_data):

        # get route and method
        route = method = None
        if 'get' in tech_data:
            route = tech_data['get']
            method = 'GET'
        if 'post' in tech_data:
            if route is not None:
                raise WriterError(f"A route was already defined for {action}")
            route = tech_data['post']
            method = 'POST'
        if route is None:
            raise WriterError(f"No route defined for {action}")

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
