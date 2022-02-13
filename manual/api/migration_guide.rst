
.. _scenedetect-migration_guide:

---------------------------------------------------------------
Migration Guide
---------------------------------------------------------------

===============================================================
VideoManager
===============================================================

TODO(v0.6)

===============================================================
StatsManager
===============================================================

TODO(v0.6)

===============================================================
save_images
===============================================================

The `downscale_factor` parameter has been removed from :py:func:`save_images <scenedetect.scene_manager.save_images>`. The existing `scale` parameter should be used instead. Equivalent functionality can be achieved by setting `scale` to `1.0 / downscale_factor`.
