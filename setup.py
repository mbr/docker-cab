#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    buf = open(os.path.join(os.path.dirname(__file__), fname), 'rb').read()
    return buf.decode('utf8')


setup(name='docker-cab',
      version='0.4.0.dev1',
      description='Automatically configures your reverse proxy based.',
      long_description=read('README.rst'),
      author='Marc Brinkmann',
      author_email='git@marcbrinkmann.de',
      url='https://github.com/mbr/docker-cab',
      license='MIT',
      packages=find_packages(exclude=['tests']),
      install_requires=['jinja2', 'click', 'docker-py'],
      entry_points={
          'console_scripts': [
              'docker-cab = docker_cab.cli:cli',
          ],
      },
      classifiers=[
          'Programming Language :: Python :: 3',
      ])
