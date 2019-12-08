from setuptools import setup
import os
import sys

_here = os.path.abspath(os.path.dirname(__file__))

if sys.version_info[0] < 3:
    with open(os.path.join(_here, 'README.rst')) as f:
        long_description = f.read()
else:
    with open(os.path.join(_here, 'README.rst'), encoding='utf-8') as f:
        long_description = f.read()

version = {}
with open(os.path.join(_here, 'sleet', 'version.py')) as f:
    exec(f.read(), version)

setup(
    name='sleet',
    version=version['__version__'],
    description='Micro Service Framework on AWS.',
    long_description=long_description,
    author='Guillaume Doumenc',
    author_email='gdoumenc@fpr-coworks.com',
    url='https://github.com/bast/somepackage',
    project_urls={
        'Documentation': 'https://packaging.python.org/tutorials/distributing-packages/',
        'Funding': 'https://donate.pypi.org',
        'Say Thanks!': 'http://saythanks.io/to/example',
        'Source': 'https://github.com/pypa/sampleproject/',
        'Tracker': 'https://github.com/pypa/sampleproject/issues',
    },
    license='MIT',
    packages=['sleet'],
    include_package_data=True,
    keywords='microservice aws synchronous asynchronous',
    classifiers=[
        'Development Status :: 3 - Alpha',
        "License :: OSI Approved :: MIT License",
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Distributed Computing'
    ],
)
