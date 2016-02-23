#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
from setuptools import setup, find_packages


setup(name='metacorus-django-utils',
    version='1.1.6',
    author='S.Prymak',
    author_email='sprymak@metacorus.com',
    url='https://github.com/sprymak/metacorus-django-utils',
    license='LICENSE',
    packages=find_packages(),
    install_requires=[
        "html5lib",
        "simplejson",
        "unidecode",
    ],
)
