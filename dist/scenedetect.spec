# -*- mode: python -*-

block_cipher = None


a = Analysis(['../scenedetect/__main__.py'],
             pathex=['.'],
             binaries=None,
             datas=[
                ('../*.md', '.'),
                ('../windows/*', '.'),
                ('../dist/LICENSE-*', '.'),
                ('../docs/', 'docs/'),
                ('../scenedetect.cfg', '.')
            ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

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
