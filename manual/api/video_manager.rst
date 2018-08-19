
VideoManager
---------------------------------------------------------------



Overview
===============================================================

.. automodule:: scenedetect.video_manager


``VideoManager`` Class 
===============================================================

.. autoclass:: scenedetect.video_manager.VideoManager
   :members:
   :undoc-members:

``video_manager`` Functions and Constants
===============================================================

The following functions and constants are available in the ``scenedetect.video_manager`` module.

.. autodata:: scenedetect.video_manager.DEFAULT_DOWNSCALE_FACTORS

.. autofunction:: scenedetect.video_manager.compute_downscale_factor

.. autoexception:: scenedetect.video_manager.InvalidDownscaleFactor

.. autofunction:: scenedetect.video_manager.get_video_name

.. autofunction:: scenedetect.video_manager.get_num_frames

.. autofunction:: scenedetect.video_manager.open_captures

.. autofunction:: scenedetect.video_manager.release_captures

.. autofunction:: scenedetect.video_manager.close_captures

.. autofunction:: scenedetect.video_manager.validate_capture_framerate

.. autofunction:: scenedetect.video_manager.validate_capture_parameters


VideoManager Exceptions
===============================================================

.. autoexception:: scenedetect.video_manager.VideoOpenFailure

.. autoexception:: scenedetect.video_manager.VideoFramerateUnavailable

.. autoexception:: scenedetect.video_manager.VideoParameterMismatch

.. autoexception:: scenedetect.video_manager.VideoDecodingInProgress

.. autoexception:: scenedetect.video_manager.VideoDecoderNotStarted

.. autoexception:: scenedetect.video_manager.InvalidDownscaleFactor


