import os

from setuptools import setup, find_packages

_here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

version = {}
with open(os.path.join(_here, 'coworks', 'version.py')) as f:
    exec(f.read(), version)

setup(
    name='coworks',
    version=version['__version__'],
    description='Coworks is a unified compositional microservices framework over AWS serverless technologies.',
    long_description=long_description,
    author='Guillaume Doumenc',
    author_email='gdoumenc@fpr-coworks.com',
    url='https://github.com/gdoumenc/coworks',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'anyconfig>=0.9.11',
        'aws_xray_sdk>=2.5.0',
        'boto3>=1.13.15',
        'chalice>=1.14.1',
        'jinja2>=2.11',
        'pyyaml>=5.3.1',
        'requests_toolbelt>=0.9.1',
        'python_terraform>=0.10.1'
    ],
    keywords='python3 serverless microservice aws-lambda aws step-functions',
    entry_points={
        'console_scripts': ['cws=coworks.cws.client:main'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        "License :: OSI Approved :: MIT License",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: System :: Distributed Computing'
    ],
)
