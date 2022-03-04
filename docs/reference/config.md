
Settings File
----------------------------------------------------------

Most command line parameters can be set using a configuration file. [Click here to download a `scenedetect.cfg` template](https://github.com/Breakthrough/PySceneDetect/blob/v0.6/scenedetect.cfg) containing every possible option with comments that describe each one. Note that lines starting with a `#` are comments and will be ignored.  The `scenedetect.cfg` template file is also available in the folder where PySceneDetect is installed.

A configuration file path can be specified using the `-c`/`--config` argument. PySceneDetect also looks for a config file named `scenedetect.cfg` in one of the following locations:

 * Windows:
     * `C:/Users/%USERNAME%/AppData/Local/PySceneDetect/scenedetect.cfg`

 * Linux:
     * `~/.config/PySceneDetect/scenedetect.cfg`
     * `$XDG_CONFIG_HOME/scenedetect.cfg`

 * Mac:
     * `~/Library/Preferences/PySceneDetect/scenedetect.cfg`

Run `scenedetect help` to see the exact path on your system which will be used (it will be listed under the help text for the -c/--config option). Specifying a config file path using -c/--config overrides the user config file. Specifying values via the command line override any values in the config file.

The syntax of a configuration file is:

```
[command]
option_a = value
#comment
option_b = 1
```

For example:

```
[global]
min-scene-len = 0.8s

[detect-content]
threshold = 26

[split-video]
preset = slow
rate-factor = 17
# Don't need to use quotes even if filename contains spaces
filename = $VIDEO_NAME-Clip-$SCENE_NUMBER

[save-images]
format = jpeg
quality = 80
num-images = 3
```

See the `scenedetect.cfg` file in the location you installed PySceneDetect or [download it from Github](https://github.com/Breakthrough/PySceneDetect/blob/v0.6/scenedetect.cfg) for a complete listing of all configuration options.
