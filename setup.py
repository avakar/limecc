#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
setup(name='limecc',
    version='0.2',
    description='Lexer and parser generator with a lemon-like description language',
    author='Martin Vejnár',
    author_email='avakar@ratatanek.cz',
    url='http://github.com/avakar/limecc',
    install_requires=['Jinja2>=2.7.0', 'six>=1.10.0'],
    packages=['limecc'],
    package_dir={'': 'src'},
    license = "Boost",
    entry_points = {
        'console_scripts': [
            'limecc = limecc.__main__:_main',
            ],
        },
    test_suite = "limecc.tests",
    classifiers=[
        # Supported python versions
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',

        # License
        'License :: OSI Approved :: Boost Software License 1.0 (BSL-1.0)',

        # Topics
        'Topic :: Software Development :: Libraries',
    ]
    )
