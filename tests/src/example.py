# from collections import defaultdict
#
# import click
# import os
#
# from coworks import TechMicroService, entry
# from coworks.config import Config
# from coworks.cws.command import CwsCommand
# from coworks.cws.runner import CwsRunner
#
#
# class TestCmd(CwsCommand):
#
#     @property
#     def options(self):
#         return [
#             *super().options,
#             click.option('-a', '--a', required=True),
#             click.option('--b')
#         ]
#
#     @classmethod
#     def multi_execute(cls, project_dir, workspace, execution_list):
#         for command, options in execution_list:
#             assert command.app is not None
#             assert command.app.config is not None
#             a = options['a']
#             b = options['b']
#             if a:
#                 command.output.write(f"test command with a={a}")
#                 command.output.write("/")
#             command.output.write(f"test command with b={b}")
#
#
# class TechMS(TechMicroService):
#     """Technical microservice for the Coworks tutorial example."""
#     version = "1.2"
#     values = defaultdict(int)
#     init_value = None
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#
#         @self.deferred
#         def init(workspace):
#             # self.init_value = 'test'
#
#     @entry
#     def get(self, usage="test"):
#         """Entrypoint for testing named parameter."""
#         return f"Simple microservice for {usage}.\n"
#
#     @entry
#     def get_value(self, index):
#         """Entrypoint for testing positional parameter."""
#         return f"{self.values[index]}\n"
#
#     @entry
#     def put_value(self, index, value=0):
#         self.values[index] = value
#         return value
#
#     @entry
#     def get_init(self):
#         return f"Initial value is {self.init_value}.\n"
#
#     @entry
#     def get_env(self):
#         return f"Simple microservice for {os.getenv('test')}.\n"
#
#
# # usefull for test info (don't remove)
# tech_app = TechMS()
# TestCmd(tech_app, name='test')
# CwsTemplateWriter(tech_app)
#
# app = TechMS(configs=Config(environment_variables_file="config/vars_dev.json"))
# TestCmd(tech_app, name='test')
#
#
# class RunnerMock(CwsRunner):
#
#     @classmethod
#     def multi_execute(cls, project_dir, workspace, execution_list):
#         for command, options in execution_list:
#             port = options['port']
#             assert type(port) is int
#
#
# project1 = TechMS()
# RunnerMock(project1)
# project2 = TechMS()
