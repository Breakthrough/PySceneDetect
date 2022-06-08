#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
#

""" PySceneDetect setup.py - DEPRECATED.

Build using `python -m build` and installing the resulting .whl using `pip`.
"""

# Standard Library Imports
from typing import Dict, List
import sys
from setuptools import setup

def get_requires():
    # type: () -> List[str]
    """ Get Requires: Returns a list of required packages. """
    return [
        'appdirs'
        'Click',
        'numpy',
        'tqdm',
    ]

def get_extra_requires():
    # type: () -> Dict[str, List[str]]
    """ Get Extra Requires: Returns a list of extra/optional packages. """
    return {
        # TODO: Abstract this into a function that generates this
        # dictionary based on a list of compatible Python & opencv-python
        # package versions (will need to use the output for requirements.txt).
        # TODO: Is there a tool that can do this automagically?
        'opencv:python_version <= "3.5"':
            ['opencv-python<=4.2.0.32'],
        'opencv:python_version > "3.5"':
            ['opencv-python'],

        'opencv-headless:python_version <= "3.5"':
            ['opencv-python-headless<=4.2.0.32'],
        'opencv-headless:python_version > "3.5"':
            ['opencv-python-headless'],
    }

setup(
    name='scenedetect',
    version='0.6.0.3',
    description="A cross-platform, OpenCV-based video scene detection program and Python library. ",
    long_description=open('dist/package-info.rst').read(),
    author='Brandon Castellano',
    author_email='brandon248@gmail.com',
    url='https://github.com/Breakthrough/PySceneDetect',
    license="BSD 3-Clause",
    keywords="video computer-vision analysis",
    install_requires=get_requires(),
    extras_require=get_extra_requires(),
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    packages=['scenedetect',
              'scenedetect.backends',
              'scenedetect.cli',
              'scenedetect.detectors',
              'scenedetect.thirdparty'],
    entry_points={"console_scripts": ["scenedetect=scenedetect.__main__:main"]},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Multimedia :: Video',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Multimedia :: Video :: Non-Linear Editor',
        'Topic :: Utilities'
    ],
    project_urls={
        'Homepage': 'https://pyscenedetect.readthedocs.io/',
        'Manual': 'https://pyscenedetect.readthedocs.io/projects/Manual/en/latest/',
        'Changelog': 'https://pyscenedetect.readthedocs.io/en/latest/changelog/',
        'Bug Tracker': 'https://github.com/Breakthrough/PySceneDetect/issues',
    }
)
