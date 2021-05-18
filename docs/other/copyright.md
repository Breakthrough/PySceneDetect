
## PySceneDetect License Agreement

```md

                PySceneDetect License (BSD 3-Clause)
          < http://www.bcastell.com/projects/PySceneDetect >

Copyright (C) 2014-2021, Brandon Castellano.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above
       copyright notice, this list of conditions and the following
       disclaimer in the documentation and/or other materials
       provided with the distribution.

    3. Neither the name of the copyright holder nor the names of its
       contributors may be used to endorse or promote products derived
       from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```


## Ancillary Software Licenses

This section contains links to the license agreements for all third-party software libraries used and distributed with PySceneDetect.  You can find copies of all the relevant license agreements referenced below if you installed a copy of PySceneDetect by looking at the LICENSE files in the installation directory.

-----------------------------------------------------------------------

### NumPy

 - Copyright (C) 2005-2016, NumPy Developers.
 - URL: <a href="http://www.numpy.org/license.html" alt="NumPy License">http://www.numpy.org/license.html</a>


### OpenCV

 - Copyright (C) 2017, Itseez.
 - URL: <a href="http://opencv.org/license.html" alt="OpenCV License">http://opencv.org/license.html</a>


### click

 - Copyright (C) 2017, Armin Ronacher.
 - URL: <a href="http://click.pocoo.org/license/" alt="click License">http://click.pocoo.org/license/</a>


### tqdm

 - Copyright (C) 2013-2018, Casper da Costa-Luis, Google Inc., and Noam Yorav-Raphael.
 - URL: <a href="https://raw.githubusercontent.com/tqdm/tqdm/master/LICENCE" alt="tqdm License">https://raw.githubusercontent.com/tqdm/tqdm/master/LICENCE</a>


### simpletable

 - Copyright (C) 2014-2019, Matheus Vieira Portela and others
 - URL: <a href="https://github.com/matheusportela/simpletable/blob/master/LICENSE" alt="simpletable License">https://github.com/matheusportela/simpletable/blob/master/LICENSE</a>

-----------------------------------------------------------------------

### FFmpeg and mkvmerge

This software may also invoke mkvmerge or FFmpeg, if available.

FFmpeg is a trademark of Fabrice Bellard.
mkvmerge is Copyright (C) 2005-2016, Matroska.

Certain distributions of PySceneDetect may include the above software;
see the included LICENSE-FFMPEG and LICENSE-MKVMERGE files, or visit the
below URLs for details.  In source distributions of PySceneDetect,
neither mkvmerge nor FFmpeg is not distributed, and requires manual
installation in order to allow automatic video splitting capability.
These programs can be obtained from following URLs (note that mkvmerge
is a part of the MKVToolNix package):

    FFmpeg:   [ https://ffmpeg.org/download.html ]
    mkvmerge: [ https://mkvtoolnix.download/downloads.html ]

Once installed, ensure the program can be accessed system-wide by calling
the `mkvmerge` or `ffmpeg` command from a terminal/command prompt.
PySceneDetect will automatically use whichever program is available on
the computer, depending on the specified command-line options.

