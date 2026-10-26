
.. _scenedetect-output:

------
Output
------

.. automodule:: scenedetect.output
   :no-members:

.. Functions defined in the `scenedetect.output.image` and `scenedetect.output.video` submodules
   are re-exported from `scenedetect.output`, but `automodule :members:` skips imported names, so
   every object is listed explicitly below. Add new public functions here.

Splitting Video
---------------

.. seealso:: CLI: :ref:`split-video <command-split-video>` | Config file: :ref:`[split-video] <config-split-video>`

.. autofunction:: scenedetect.output.split_video_ffmpeg

.. autofunction:: scenedetect.output.split_video_mkvmerge

.. autofunction:: scenedetect.output.is_ffmpeg_available

.. autofunction:: scenedetect.output.is_mkvmerge_available

Saving Images
-------------

.. seealso:: CLI: :ref:`save-images <command-save-images>` | Config file: :ref:`[save-images] <config-save-images>`

.. autofunction:: scenedetect.output.save_images

Scene Lists
-----------

.. seealso:: CLI: :ref:`list-scenes <command-list-scenes>` (CSV), :ref:`save-html <command-save-html>`, :ref:`save-edl <command-save-edl>`, :ref:`save-fcp <command-save-fcp>`, :ref:`save-otio <command-save-otio>`

.. autofunction:: scenedetect.output.write_scene_list

.. autofunction:: scenedetect.output.write_scene_list_html

.. autofunction:: scenedetect.output.write_scene_list_edl

.. autofunction:: scenedetect.output.write_scene_list_fcpx

.. autofunction:: scenedetect.output.write_scene_list_fcp7

.. autofunction:: scenedetect.output.write_scene_list_otio

Filename Formatting
-------------------

.. seealso:: CLI: the ``-f/--filename`` option of :option:`split-video <scenedetect split-video -f>` and :option:`save-images <scenedetect save-images -f>`

.. autofunction:: scenedetect.output.default_formatter

.. autodata:: scenedetect.output.PathFormatter

.. autoclass:: scenedetect.output.VideoMetadata
   :members:

.. autoclass:: scenedetect.output.SceneMetadata
   :members:
