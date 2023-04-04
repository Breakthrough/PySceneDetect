
## Settings File

A configuration file path can be specified using the `-c`/`--config` argument. PySceneDetect also looks for a config file named `scenedetect.cfg` in one of the following locations:

 * Windows:
     * `C:/Users/%USERNAME%/AppData/Local/PySceneDetect/scenedetect.cfg`

 * Linux:
     * `~/.config/PySceneDetect/scenedetect.cfg`
     * `$XDG_CONFIG_HOME/scenedetect.cfg`

 * Mac:
     * `~/Library/Preferences/PySceneDetect/scenedetect.cfg`

Run `scenedetect help` to see the exact path on your system which will be used (it will be listed under the help text for the -c/--config option).  You can [click here to download a `scenedetect.cfg` config file](https://raw.githubusercontent.com/Breakthrough/PySceneDetect/v0.6.1-release/scenedetect.cfg) to use as a template. Note that lines starting with a `#` are comments and will be ignored.  The `scenedetect.cfg` template file is also available in the folder where PySceneDetect is installed.

Specifying a config file path using -c/--config overrides the user config file. Specifying values on the command line will override those values in the config file.

The syntax of a configuration file is:

```
[command]
option_a = value
#comment
option_b = 1
```

### Example

```
[global]
min-scene-len = 0.8s

[detect-content]
threshold = 32
weights = 1.0 0.5 1.0 0.2

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

See the `scenedetect.cfg` file in the location you installed PySceneDetect or [download it from Github](https://raw.githubusercontent.com/Breakthrough/PySceneDetect/v0.6.1-release/scenedetect.cfg) for a complete listing of all configuration options.
