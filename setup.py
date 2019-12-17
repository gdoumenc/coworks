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
with open(os.path.join(_here, 'coworks', 'version.py')) as f:
    exec(f.read(), version)

setup(
    name='coworks',
    version=version['__version__'],
    description='Restful Microservice Framework on AWS.',
    long_description=long_description,
    author='Guillaume Doumenc',
    author_email='gdoumenc@fpr-coworks.com',
    url='https://github.com/gdoumenc/coworks',
    license='MIT',
    packages=['coworks'],
    include_package_data=True,
    install_requires=[
        'chalice',
    ],
    keywords='restful microservice aws chalice serverless',
    entry_points={
        'console_scripts': ['cws=coworks.cli:main'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        "License :: OSI Approved :: MIT License",
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Distributed Computing'
    ],
)
