#!/usr/bin/env python

from distutils.core import setup

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

setup(
    name='bottle-couchbase',
    version='0.2.0',
    url='https://github.com/42matters/bottle-couchbase',
    description='Couchbase integration for Bottle.',
    author='Bo Wang',
    author_email='bo@42matters.com',
    license='MIT',
    platforms='any',
    py_modules=[
        'bottle_couchbase'
    ],
    requires=[
        'bottle (>=0.9)',
        'couchbase (==1.2.5)'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    cmdclass={'build_py': build_py}
)
