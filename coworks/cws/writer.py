import pathlib
from abc import abstractmethod
from dataclasses import dataclass
from typing import List

import click
from jinja2 import Environment, PackageLoader, select_autoescape, TemplateNotFound

from coworks import TechMicroService
from coworks.config import CORSConfig
from coworks.cws.command import CwsCommand, CwsCommandOptions
from coworks.cws.error import CwsCommandError

DEFAULT_STEP = 'update'


class CwsWriterError(CwsCommandError):
    ...


class CwsWriter(CwsCommand):

    def __init__(self, app=None, *, name):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--output', default=None),
            click.option('--step', default=DEFAULT_STEP),
            click.option('--config', default=None),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        ]

    def _execute(self, options):
        self._export_header(options)
        self._export_content(options)
        print('', file=self.output, flush=True)

    def _export_header(self, options):
        ...

    @abstractmethod
    def _export_content(self, options):
        """ Main export function.
        :param options: Command optons.
        :return: None.

        Abstract method which must be redefined in any subclass. The content should be written in self.output.
        """

    def _format(self, content):
        return content


class CwsTemplateWriter(CwsWriter):
    """Writer with  jinja templating."""

    def __init__(self, app=None, *, name='export', data=None, template_filenames=None, env=None):
        super().__init__(app, name=name)
        self.data = data or {}
        self.template_filenames = template_filenames or self.default_template_filenames
        self.env = env or Environment(
            loader=PackageLoader("coworks.cws.writer"),
            autoescape=select_autoescape(['html', 'xml'])
        )

    @property
    @abstractmethod
    def default_template_filenames(self):
        """Must be redefined to set template file for writing."""

    def _validate_context(self, options: CwsCommandOptions):
        """ Validator called before templating.

        :param options: context used for templating.
        :return: validated context.
        """
        return options

    def _export_content(self, options):
        self._validate_context(options)
        module_path = options.module.split('.')

        # Get parameters for execution
        try:
            config = next(
                (app_config for app_config in self.app.configs if app_config.workspace == options.workspace)
            )
        except StopIteration:
            raise CwsCommandError("A workspace is mandatory in the python configuration for deploying.\n")

        environment_variable_files = [p.as_posix() for p in
                                      config.existing_environment_variables_files(options.project_dir)]
        data = {
            'writer': self,
            'project_dir': options.project_dir,
            'module': options.module,
            'module_path': pathlib.PurePath(*module_path),
            'module_dir': pathlib.PurePath(*module_path[:-1]),
            'module_file': module_path[-1],
            'handler': options.service,
            'app': self.app,
            'ms_name': self.app.ms_name,
            'app_config': config,
            'environment_variable_files': environment_variable_files,
            **options.to_dict()
        }
        data.update(self.data)
        try:
            for template_filename in self.template_filenames:
                template = self.env.get_template(template_filename)
                print(self._format(template.render(**data)), file=self.output)
        except TemplateNotFound as e:
            raise CwsWriterError(f"Cannot find template {str(e)}")
        except Exception as e:
            raise CwsWriterError(e)


UID_SEP = '_'


@dataclass
class TerraformEntry:
    app: TechMicroService
    parent_uid: str
    path: str
    methods: List[str]
    cors: CORSConfig

    @property
    def uid(self):
        def remove_brackets(path):
            return f"{path.replace('{', '').replace('}', '')}"

        if self.path is None:
            return UID_SEP

        last = remove_brackets(self.path)
        return f"{self.parent_uid}{UID_SEP}{last}" if self.parent_uid else last

    @property
    def is_root(self):
        return self.path is None

    @property
    def parent_is_root(self):
        return self.parent_uid == UID_SEP

    def __repr__(self):
        return f"{self.uid}:{self.methods}"


class CwsTerraformWriter(CwsTemplateWriter):

    def __init__(self, app=None, *, name='terraform', data=None, **kwargs):

        data = data or {
            'layer_zip_file': 'layer.zip',
        }
        super().__init__(app, name=name, data=data, **kwargs)

    @property
    def default_template_filenames(self):
        return ['terraform.j2']

    def _export_header(self, options):
        print("// Do NOT edit this file as it is auto-generated by cws\n", file=self.output)

    @property
    def entries(self):
        """Returns the list of flatten path (prev, last, keys)."""
        all_pathes_id = {}

        def add_entry(previous, last, meth):
            entry = TerraformEntry(self.app, previous, last, meth, self.app.config.cors)
            uid = entry.uid
            if uid not in all_pathes_id:
                all_pathes_id[uid] = entry
            if all_pathes_id[uid].methods is None:
                all_pathes_id[uid].methods = meth
            return uid

        for route, methods in self.app.routes.items():
            previous_uid = UID_SEP
            splited_route = route[1:].split('/')

            # special root case
            if splited_route == ['']:
                add_entry(None, None, methods.keys())
                continue

            # creates intermediate resources
            last_path = splited_route[-1:][0]
            for prev in splited_route[:-1]:
                previous_uid = add_entry(previous_uid, prev, None)

            # set entryes keys for last entry
            add_entry(previous_uid, last_path, methods.keys())

        return all_pathes_id


class CwsTerraformStagingWriter(CwsTerraformWriter):
    def __init__(self, app=None, *, name='terraform-staging', data=None, **kwargs):
        super().__init__(app, name=name, data=data, **kwargs)

    @property
    def default_template_filenames(self):
        return ['terraform_staging.j2']

    @property
    def options(self):
        return [
            *super().options,
            click.option('--custom_layers', default=[]),
            click.option('--common_layers', default=[]),
            click.option('--binary_media_types', default=[]),
        ]

    def _validate_context(self, options):
        options.setdefault('custom_layers', [])
        options.setdefault('common_layers', [])
        options.setdefault('binary_media_types', [])
        return options
