# SmolSlimeConfigurator <img src="icon.png" width="32" height="32" alt="SmolSlimeConfiguratorICON">
Archive of old source code

```
pyinstaller \
  --onefile \
  --windowed \
  --icon=icon.png \
  --add-data "icon.png:." \
  --add-binary "/home/user/Documents/scripts/SmolSlimeConfigurator310/bin/nrfutil:." \
  SmolSlimeConfiguratorbeta.py
```
