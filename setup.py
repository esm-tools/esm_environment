#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ["esm_parser @ git+https://gitlab.awi.de/esm_tools/esm_parser.git",
                "esm_rcfile @ git+https://gitlab.awi.de/esm_tools/esm_rcfile.git" ]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Dirk Barbi",
    author_email='dirk.barbi@awi.de',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="ESM Environment python package to assemble environment information for compiling and running ESMs",
    install_requires=requirements,
    license="GNU General Public License v2",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='esm_environment',
    name='esm_environment',
    packages=find_packages(include=['esm_environment', 'esm_environment.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/dbarbi/esm_environment',
    version='3.0.0',
    zip_safe=False,
)
