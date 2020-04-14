import json
import os
import pathlib

import yaml

from coworks.cli.writer import Writer, WriterError


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

            first = PassState({'name': "Init"})

            all_states = [first]
            states = State.get_or_raise(data, 'states')
            add_actions(all_states, states)

            first.state['Result'] = {state.slug: state.data for state in all_states}
            first.state['Next'] = all_states[1].name

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

    previous_state = states[-1]
    for action in actions:
        state = create_state(action, previous_state)
        states.append(state)
        previous_state = state

        if action == actions[-1] and 'Next' not in state.state:
            state.state['End'] = True


def create_state(action, previous_state):
    def add_next(name):
        if 'Next' not in previous_state.state:
            if isinstance(previous_state, ChoiceState):
                previous_state.state['Default'] = name
            else:
                previous_state.state['Next'] = name

    if 'choices' in action:
        state = ChoiceState(action)
        add_next(state.name)
    elif 'tech' in action:
        state = TechState(action)
        add_next(state.name)
    else:
        raise WriterError(f"Undefined type of action for {action}")

    return state


class State:

    def __init__(self, action, **kwargs):
        self.action = action or {}
        self.state = {**kwargs}
        self.data = {}

    @property
    def name(self):
        return self.action.get('name', f'The action {self.action} has no name')

    @property
    def slug(self):
        return "_".join(self.name.split()).lower()

    @staticmethod
    def get_goto(action_or_choice):
        goto = action_or_choice.get('goto', None)
        if goto == "End":
            return "End", True
        return "Next", goto

    @staticmethod
    def get_or_raise(action, key):
        try:
            return action[key]
        except KeyError:
            raise WriterError(f"The key {key} is missing for {action}")


class SuccessState(State):
    def __init__(self, action=None, **kwargs):
        kwargs.update({
            "Type": "Succeed",
        })
        super().__init__(action, **kwargs)


class PassState(State):
    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Pass", **kwargs)


class TechState(State):
    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Task", **kwargs)

        tech_data = self.get_or_raise(action, 'tech')
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

        query_params = body = None
        params = tech_data.get('params', None)
        if method == "GET":
            query_params = [] if params else None
        else:
            body = params if params else None

        try:
            self.state['Resource'] = f"arn:aws:lambda:eu-west-1:935392763270:function:{tech_data['service']}"
            self.state["InputPath"] = f"$.{self.slug}.call"
            self.state["ResultPath"] = f"$.{self.slug}.result"
            self.state["OutputPath"] = "$"

            self.data = {
                'call': self.get_call_data(route, method, query_params, body)
            }
        except KeyError as e:
            raise WriterError(f"The key {e} is missing for {action}")

        k, v = self.get_goto(action)
        if v:
            self.state[k] = v

    @staticmethod
    def get_call_data(route, method='GET', uri_params=None, query_params=None, body=None):
        return {
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
                "Content-Type": "application/json"
            },
            "body": json.dumps(body) if body else None,
            "stageVariables": None,
        }


class ChoiceState(State):

    def __init__(self, action, **kwargs):
        super().__init__(action, Type="Choice", **kwargs)

        choices = self.get_or_raise(action, 'choices')
        self.state['Choices'] = self.create_choices_sequence(choices)

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
            key, value = self.get_goto(choice)
            if value is None:
                raise KeyError(f"The key goto is missing for {choice}")

            if 'not' in choice:
                switch.append({"Not": create_condition(choice['not']), key: value})
            elif 'or' in choice:
                switch.append({"Or": create_condition(choice['or']), key: value})
            elif 'and' in choice:
                switch.append({"And": create_condition(choice['and']), key: value})
            else:
                switch.append({**create_condition(choice), key: value})
        return switch
