import os

from setuptools import setup, find_packages

_here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

from coworks import __version__

setup(
    name='coworks',
    version=__version__,
    description='Coworks is a unified compositional microservices framework using Flask on AWS serverless technologies.',
    long_description=long_description,
    author='Guillaume Doumenc',
    author_email='gdoumenc@fpr-coworks.com',
    url='https://github.com/gdoumenc/coworks',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'anyconfig>=0.12',
        'boto3>=1.19',
        'flask>=2.0',
        'pyyaml>=6.0',
    ],
    keywords='python3 serverless microservice flask aws-lambda aws',
    entry_points={
        'console_scripts': [
            'cws=coworks.cws.client:client',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        "License :: OSI Approved :: MIT License",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: System :: Distributed Computing'
    ],
)
