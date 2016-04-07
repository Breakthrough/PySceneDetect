
This folder includes a unit test/benchmarking script, as well as a script to
download .MP4 copies, of the current YouTube videos referenced in albanie's
shot-detection-benchmarks repo on Github:

    https://github.com/albanie/shot-detection-benchmarks

You can also view the discussion on any developments or changes to
PySceneDetect with respect to these benchmarks at:

    https://github.com/Breakthrough/PySceneDetect/issues/13

Note that This script depends on nficano's pytube library:

    https://github.com/nficano/pytube

--------

The videos currently included in this benchmark are: 

    Tv gameshow clip (the first 05:00 is used)
        https://www.youtube.com/watch?v=fkiDpLlQ9Wg

    Sports clip (05:11)
        https://www.youtube.com/watch?v=vFT8HXJlvfA

    Movie clip (03:12)
        https://www.youtube.com/watch?v=bpLtXIlkyYA

The benchmark "test" is only passed if the score for a given video (indexed by 
its YouTube URL and any time limits) matches or exceeds the current score 
stored in the benchmark index.

The scoring algorithm as of now will simply be to achieve the highest percent 
of fast cuts detected, as compared to a list of fast scene/shot cuts manually 
compiled for each test video above.

These scoring metrics will be changed in the future guided by the discussion 
in the [issue tracker](https://github.com/Breakthrough/PySceneDetect/issues/13), 
as well as to compensate for [future releases of PySceneDetect](http://pyscenedetect.readthedocs.org/en/latest/features/#version-roadmap).

