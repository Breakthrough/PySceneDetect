# -*- mode: python -*-

import os

from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

# moviepy/imageio resolve their own version via importlib.metadata at import time,
# which needs the dist-info dirs bundled alongside the modules.
_metadata = (
    copy_metadata('moviepy')
    + copy_metadata('imageio')
    + copy_metadata('imageio_ffmpeg')
)


a = Analysis(['../../scenedetect/__main__.py'],
             pathex=['.'],
             binaries=None,
             datas=[
                ('LICENSE-PYTHON', '.'),
                ('README.txt', '.'),
                ('../../LICENSE', '.'),
                ('../../scenedetect.cfg', '.')
            ] + _metadata,
             hiddenimports=['moviepy', 'imageio', 'imageio_ffmpeg'],
             hookspath=[],
             runtime_hooks=['packaging/windows/pyi_rth_scenedetect.py'],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

# Drop imageio_ffmpeg's bundled ffmpeg-*.exe so we don't ship two copies of
# ffmpeg. The runtime hook (pyi_rth_scenedetect.py) redirects imageio_ffmpeg
# and moviepy at the GyanD ffmpeg.exe staged next to scenedetect.exe by
# scripts/stage_windows_dist.py. Keep __init__.py — pyinstaller-hooks-contrib
# declares `imageio_ffmpeg.binaries` as a hidden import, so the package still
# has to be importable.
def _drop_bundled_ffmpeg(toc):
    # TOC dest paths use the OS-native separator, so normalize before matching.
    prefix = 'imageio_ffmpeg' + os.sep + 'binaries' + os.sep
    return [t for t in toc if not (
        t[0].startswith(prefix) and not t[0].endswith('__init__.py')
    )]
a.binaries = _drop_bundled_ffmpeg(a.binaries)
a.datas = _drop_bundled_ffmpeg(a.datas)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='scenedetect',
          debug=False,
          strip=False,
          upx=True,
          console=True,
          version='.version_info',
          icon='pyscenedetect.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='scenedetect')
