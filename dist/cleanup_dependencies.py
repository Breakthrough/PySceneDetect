# -*- coding: utf-8 -*-
import glob
import os
import shutil

BASE_PATH = 'dist/scenedetect'

DIRECTORY_GLOBS = [
    'altgraph-*.dist-info',
    'certifi',
    'importlib_metadata-*.dist-info',
    'matplotlib',
    'PIL',
    'PyQt5',
    'pip-*.dist-info',
    'psutil',
    'pyinstaller-*.dist-info',
    'setuptools-*.dist-info',
    'tcl8',
    'wheel-*.dist-info',
    'wx',
]

FILE_GLOBS = [
    '_asyncio.pyd',
    '_bz2.pyd',
    '_decimal.pyd',
    '_elementtree.pyd',
    '_hashlib.pyd',
    '_lzma.pyd',
    '_multiprocessing.pyd',
    '_overlapped.pyd',
    '_tkinter.pyd',
    'd3dcompiler*.dll',
    'kiwisolver.*.pyd',
    'libEGL.dll',
    'libGLESv2.dll',
    'opengl32sw.dll',
    'Qt5*.dll',
    'wxbase*.dll',
    'wxmsw315u*.dll',
]

for dir_glob in DIRECTORY_GLOBS:
    for dir_path in glob.glob(os.path.join(BASE_PATH, dir_glob)):
        shutil.rmtree(dir_path)

for file_glob in FILE_GLOBS:
    for file_path in glob.glob(os.path.join(BASE_PATH, file_glob)):
        os.remove(file_path)
