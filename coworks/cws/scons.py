import json
import re
import subprocess

from SCons import Environment
from SCons.Builder import Builder
from SCons.Script import Glob, Help, ARGUMENTS

debug = int(ARGUMENTS.get('debug', 0))

MODULE_APP_SEP = '-'
venv = subprocess.check_output(['pipenv', '--venv']).decode('utf-8')
cws = f"{venv[:-1]}/bin/cws"

Help(f"""
       Type: 'scons stage={{stage}} to build the complete module,
       Type: 'scons microservice={{module}}{MODULE_APP_SEP}{{app}} stage={{stage}} to build the microservice,
       Omitting stage will build the stage 'dev'
       """)


def AllFiles(node='.', pattern='*', exclude=r'.*\.pyc$'):
    result = [AllFiles(dir, pattern, exclude) for dir in Glob(str(node) + '/*') if dir.isdir()]
    result += [source for source in Glob(str(node) + '/' + pattern) if
               source.isfile() and (exclude is None or re.match(exclude, source.name) is None)]
    return result


def Taint(ressource, terraform_dir):
    if debug:
        print("tainting ", ressource)
    return subprocess.check_output(f'terraform taint {ressource} > /dev/null 2>&1',
                                   shell=True, cwd=terraform_dir).decode('utf-8')


def Deploy(target, source, env=None):
    src_dir = env['SRC_DIR']
    terraform_dir = env['TERRAFORM_DIR']
    stage = ARGUMENTS.get('stage', 'dev')
    microservice = ARGUMENTS.get('microservice')
    for t in target:
        mod, app, _ = t.name.split(MODULE_APP_SEP)
        print(f"Create terraform files for {mod}{MODULE_APP_SEP}{app}")
        cmd = f"{cws} -p {src_dir} info -m {mod} -a {app}"
        if debug:
            print(cmd)
        info = subprocess.check_output(cmd.split(' ')).decode('utf-8')
        if debug:
            print(f"info: {info[:-1]}")
        name = json.loads(info[:-1])['name']

        cmd = f"{cws} -p {src_dir} export -f terraform-staging -m {mod} -a {app} -v workspace {stage}"
        if debug:
            print(cmd)
        content = subprocess.check_output(cmd.split(' ')).decode('utf-8')

        subprocess.check_output(f'rm -f _{mod}_{name}*.tf', cwd=terraform_dir, shell=True)
        with open(f"{terraform_dir}/_{mod}_{name}-{stage}.tf", 'w') as tgt:
            tgt.write(content)

        if microservice:
            ressource_name = f'{microservice}_{stage}'
        else:
            ressource_name = f'{mod}-{app}_{stage}'

        try:
            if debug:
                print(f"tainting : {ressource_name}")
            Taint(f'aws_lambda_function.{ressource_name}', terraform_dir)
            Taint(f'aws_lambda_permission.{ressource_name}', terraform_dir)
            Taint(f'aws_api_gateway_deployment.{ressource_name}', terraform_dir)
        except subprocess.CalledProcessError:
            pass


def CwsProject(src, microservices, src_dir='src', terraform_dir='terraform'):
    env = Environment.Base(BUILDERS={'Deploy': Builder(action=Deploy)}, SRC_DIR=src_dir, TERRAFORM_DIR=terraform_dir)

    for microservice in microservices:
        for workspace in microservice[1]:
            target = f'{microservice[0]}-{workspace}'
            env.Zip(f'{terraform_dir}/tmp/{target}', src, ZIPROOT=src_dir)
            env.Deploy(target, [f'{terraform_dir}/tmp/{target}.zip'])
