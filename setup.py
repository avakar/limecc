#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
setup(name='limecc',
    version='0.2',
    description='Lexer and parser generator with a lemon-like description language',
    author='Martin Vejnár',
    author_email='avakar@ratatanek.cz',
    url='http://github.com/avakar/limecc',
    install_requires=['Jinja2>=2.7.0'],
    packages=['limecc'],
    package_dir={'': 'src'},
    license = "Boost",
    entry_points = {
        'console_scripts': [
            'limecc = limecc.limecc:_main',
            ],
        },
    test_suite = "limecc.tests",
    )
