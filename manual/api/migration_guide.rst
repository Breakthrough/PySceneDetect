
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

The `downscale_factor` parameter has been removed. The existing `scale` parameter should be used instead. Equivalent functionality can be achieved by calculating `scale` as `1.0 / downscale_factor`.
