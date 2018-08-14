#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
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

# Standard Library Imports
import sys

from setuptools import setup


if sys.version_info < (2, 7) or (sys.version_info >= (3, 0) and sys.version_info < (3, 3)):
    print('PySceneDetect requires at least Python 2.7 or 3.3 to run.')
    sys.exit(1)


def get_requires(include_opencv=False):
    # type: (bool) -> List[str]
    """ Get Requires: Returns a list of required packages PySceneDetect depends on.

    Arguments:
        include_opencv (bool): Whether to include the cv2 module in the returned module
            list or not (default is False). Package may not be able to be installed via
            pip, thus the default behaviour is to have users install it separately for now.
    """
    requires = ['numpy', 'Click']
    if include_opencv:
        requires += ['cv2']
    return requires


setup(
    name='PySceneDetect',
    version='0.4.1',
    description="A cross-platform, OpenCV-based video scene detection program and Python library. ",
    long_description=open('package-info.rst').read(),
    author='Brandon Castellano',
    author_email='brandon248@gmail.com',
    url='https://github.com/Breakthrough/PySceneDetect',
    license="BSD 3-Clause",
    keywords="video computer-vision analysis",
    install_requires=get_requires(),        # OpenCV must be installed separately so it is excluded.
    extras_require={'progress_bar': ['tqdm']},
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    packages=['scenedetect',
              'scenedetect.detectors',
              'scenedetect.cli'],
    package_data={'': ['../LICENSE*', '../USAGE.md', '../package-info.rst']},
    #include_package_data = True,           # Must leave this to the default.
    #test_suite="unitest.py",               # Auto-detects tests from setup.cfg
    entry_points={"console_scripts": ["scenedetect=scenedetect:main"]},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Multimedia :: Video',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Multimedia :: Video :: Non-Linear Editor',
        'Topic :: Utilities'
    ]
)

