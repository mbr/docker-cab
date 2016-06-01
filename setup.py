#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    buf = open(os.path.join(os.path.dirname(__file__), fname), 'rb').read()
    return buf.decode('utf8')


setup(
    name='concierge',
    version='0.3.0.dev1',
    description='Generate configuration files based on docker state changes.',
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='https://github.com/mbr/docker-pygen',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    install_requires=['jinja2', 'click', 'docker-py'],
    data_files=['templates/path.tpl'],
    entry_points={
        'console_scripts': [
            'concierge = docker_pygen.cli:cli',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
    ])
