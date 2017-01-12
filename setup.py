#!/usr/bin/env python
#
# PySceneDetect setup.py
#


import glob
import sys

from setuptools import setup


if sys.version_info < (2, 6) or (3, 0) <= sys.version_info < (3, 3):
    print('PySceneDetect requires at least Python 2.6 or 3.3 to run.')
    sys.exit(1)


def get_requires():
    requires = ['numpy']
    if sys.version_info == (2, 6):
        requires += ['argparse']
    return requires


setup(
    name='PySceneDetect',
    version='0.3.6',
    description="A cross-platform, OpenCV-based video scene detection program and Python library. ",
    long_description=open('package-info.rst').read(),
    author='Brandon Castellano',
    author_email='brandon248@gmail.com',
    url='https://github.com/Breakthrough/PySceneDetect',
    license="BSD 2-Clause",
    keywords="video computer-vision analysis",
    install_requires=get_requires(),
    extras_require={
        #'GUI': ['gi'],
        #'VIDEOENC': ['moviepy']
    },
    packages=['scenedetect'],
    package_data={'': ['../LICENSE*', '../USAGE.md', '../package-info.rst']},
    #include_package_data = True,   # Only works with this line commented.
    #test_suite="unitest.py",
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Multimedia :: Video',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Multimedia :: Video :: Non-Linear Editor',
        'Topic :: Utilities'
    ]
)
