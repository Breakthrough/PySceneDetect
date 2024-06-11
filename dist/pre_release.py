# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.abspath("."))

import scenedetect
VERSION = scenedetect.__version__

if len(sys.argv) <= 2 or not ("--ignore-installer" in sys.argv):
  installer_aip = ''
  with open("dist/installer/PySceneDetect.aip", "r") as f:
    installer_aip = f.read()

aip_version = f"<ROW Property=\"ProductVersion\" Value=\"{VERSION}\" Options=\"32\"/>"

assert aip_version in installer_aip, f"Installer project version does not match {VERSION}."

with open("dist/.version_info", "wb") as f:
    v = VERSION.split(".")
    assert 2 <= len(v) <= 3, f"Unrecognized version format: {VERSION}"

    if len(v) == 3:
        (maj, min, pat) = int(v[0]), int(v[1]), int(v[2])
    else:
        (maj, min, pat) = int(v[0]), int(v[1]), 0

    f.write(f"""# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
# Set not needed items to zero 0.
filevers=(0, {maj}, {min}, {pat}),
prodvers=(0, {maj}, {min}, {pat}),
# Contains a bitmask that specifies the valid bits 'flags'r
mask=0x3f,
# Contains a bitmask that specifies the Boolean attributes of the file.
flags=0x0,
# The operating system for which this file was designed.
# 0x4 - NT and there is no need to change it.
OS=0x4,
# The general type of file.
# 0x1 - the file is an application.
fileType=0x1,
# The function of the file.
# 0x0 - the function is not defined for this fileType
subtype=0x0,
# Creation date and time stamp.
date=(0, 0)
),
  kids=[
StringFileInfo(
  [
  StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u'github.com/Breakthrough'),
    StringStruct(u'FileDescription', u'www.scenedetect.com'),
    StringStruct(u'FileVersion', u'{VERSION}'),
    StringStruct(u'InternalName', u'PySceneDetect'),
    StringStruct(u'LegalCopyright', u'Copyright © 2024 Brandon Castellano'),
    StringStruct(u'OriginalFilename', u'scenedetect.exe'),
    StringStruct(u'ProductName', u'PySceneDetect'),
    StringStruct(u'ProductVersion', u'{VERSION}')])
  ]),
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
""".encode())
