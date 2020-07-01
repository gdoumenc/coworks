import re
import subprocess

from SCons import Environment
from SCons.Builder import Builder
from SCons.Script import Glob, Help, ARGUMENTS, ARGLIST

debug = int(ARGUMENTS.get('debug', 0))

MODULE_APP_SEP = '-'
venv = subprocess.check_output(['pipenv', '--venv']).decode('utf-8')
cws = f"{venv[:-1]}/bin/cws"

Help(f"""
       Usage : scons deploy-service=module-service1 deploy-service=module-service2
       """)


def AllFiles(src_dir='.', pattern='*', exclude=r'.*\.pyc$'):
    result = [AllFiles(dir, pattern, exclude) for dir in Glob(str(src_dir) + '/*') if dir.isdir()]
    result += [source for source in Glob(str(src_dir) + '/' + pattern) if
               source.isfile() and (exclude is None or re.match(exclude, source.name) is None)]
    return result


def Deploy(target, source, env=None):
    src_dir = env['SRC_DIR']
    terraform_dir = env['TERRAFORM_DIR']

    for t in target:
        mod, service = t.name.split(MODULE_APP_SEP)
        print(f"Create terraform files for {mod}{MODULE_APP_SEP}{service}")

        deploy_service_option = ""
        for arg in ARGLIST:
            key, value = arg
            if key == 'deploy_service':
                deploy_service_option = f"{deploy_service_option} --deploy-service={value}"

        cmd = f"{cws} -p {src_dir} -m {mod} -s {service} terraform-staging{deploy_service_option}"

        if debug:
            print(cmd)
        content = subprocess.check_output(cmd.split(' ')).decode('utf-8')
        subprocess.check_output(f'rm -f _{t}*.tf', cwd=terraform_dir, shell=True)

        with open(f"{terraform_dir}/_{t}.tf", 'w') as tgt:
            tgt.write(content)


def CwsProject(src, microservices, src_dir='src', terraform_dir='terraform'):
    env = Environment.Base(BUILDERS={'Deploy': Builder(action=Deploy)}, SRC_DIR=src_dir, TERRAFORM_DIR=terraform_dir)

    for microservice in microservices:
        target = f'{microservice}'
        env.Zip(f'{terraform_dir}/tmp/{target}', src, ZIPROOT=src_dir)
        env.Deploy(target, [f'{terraform_dir}/tmp/{target}.zip'])
