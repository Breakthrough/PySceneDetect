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

""" PySceneDetect setup.py

To install PySceneDetect:

    python setup.py install

To run the PySceneDetect unit tests (requires testvideo.mp4, link below):

    python setup.py test

You can obtain the required testvideo.mp4 from the PySceneDetect [resources
branch](https://github.com/Breakthrough/PySceneDetect/tree/resources) on Github,
or the following URL:

    https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/testvideo.mp4

"""

from setuptools import setup
from typing import Dict, List

def get_requires() -> List[str]:
    """ Get Requires: Returns a list of required packages. """
    return [
        'Click',
        'numpy',
        'tqdm',
        'appdirs'
    ]

def get_extra_requires() -> Dict[str, List[str]]:
    """ Get Extra Requires: Returns a list of extra/optional packages. """
    return {
        'opencv': ['opencv-python'],
        'opencv-headless': ['opencv-python-headless'],
    }


setup(
    name='scenedetect',
    version='0.6-dev',
    description="A cross-platform, OpenCV-based video scene detection program and Python library. ",
    long_description=open('package-info.rst').read(),
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
              'scenedetect.cli',
              'scenedetect.detectors',
              'scenedetect.thirdparty'],
    package_data={'': ['../LICENSE', '../USAGE.md', '../package-info.rst']},
    #include_package_data = True,           # Must leave this to the default.
    #test_suite="unitest.py",               # Auto-detects tests from setup.cfg
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
