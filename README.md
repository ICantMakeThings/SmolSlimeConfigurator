# SmolSlimeConfigurator <img src="icon.png" width="32" height="32" alt="SmolSlimeConfiguratorICON">
Pure Simple UI Configurator for SlimeVR Smol Slimes (Unofficial)

<img width="971" height="740" alt="ssccc" src="https://github.com/user-attachments/assets/ae0daa2f-2a61-4123-9c6c-dc71ff90ffdf" />



# Features

- **Easy-to-use interface** — clean, modern, and simple to use & Helpful tooltips.
- **Effortless configuration** — one-click buttons for calibration, pairing, and more.
- **Automatic firmware updater** — just plug your tracker in via USB, select your firmware type, and flash the latest build instantly.
- **Complete command set** — tracker and receiver commands are available without a separate advanced mode.
- **Always up to date** — the firmware list automatically fetches the latest daily builds from GitHub.
- **Custom firmware support** — flash your own `.uf2` or `.hex` files no problem.
- **Favorites system** — star your most-used firmware versions by Right-Clicking (Middle-Clicking on Mac).
- **Cross-platform desktop app** — available for **Windows**, **Linux**, and **macOS**.
- **Color themes** — choose Light, Dark, Dark Blue, or Dark Green; Dark Green is the default.
- **Cross-platform desktop UI** — built with PySide6 and Qt Quick/QML for Linux, macOS, and Windows.

# Download
There are 2 options to run the Configurator:
- Single-file executables are available from [Releases](https://github.com/ICantMakeThings/SmolSlimeConfigurator/releases) (Windows, Linux, macOS, Android).
- Run from source with Python 3.10 or newer:
```bash
python -m pip install -r requirements.txt
python SmolSlimeConfiguratorV10.py
```

GitHub Actions builds standalone desktop executables for Linux, macOS, and Windows on pushes and pull requests to `main`. Publishing a GitHub release also builds all three platforms and attaches their executables to the release.

HEX firmware flashing uses Nordic's standalone `nrfutil` release. If it is not already found at `SMOLSLIME_NRFUTIL`, in the app bundle, or on `PATH`, the app downloads the platform-specific executable from Nordic's official GitHub release and stores it beside the user's SmolSlime `config.json`. The app logs command output when flashing fails.

# Instructions![Uploading ssccc.png…]()

**Note:** There is a [video tutorial](https://youtu.be/2PHelwy7Rcs) explaining general usage, and [this video](https://www.youtube.com/watch?v=ENINHh4L8tk) covers **Android usage** in detail.
## **First install**

+ Plug in the tracker or receiver, hold one side of a wire on rst pin ![image](https://github.com/user-attachments/assets/7cdaae27-21f9-428f-9327-d39bbf8dabc2) (4th pin down from where B+ pin is)
and doubble tap gnd (usbc connector on the Nice!Nano)![image](https://github.com/user-attachments/assets/c1efbc20-bb2f-4fd8-9ecd-8869648ebf17)
+ Press "↻" refresh, then select the port from the dropdown menu on the left of the refresh button, then press "Connect"
+ Select the version of hardware from the dropdown menu called "Select Firmware", press "⬇ Firmware",  Wait ~20 seconds, the tracker will flash.

## **Pairing**
  
+ Plug in your Reciever, press "↻" refresh and select the port And then press "Connect"
+ To Configure your reciever, select the reciever tab, press pairing mode and power on each reciever one by one, you should notice ![image](https://github.com/user-attachments/assets/ab48dff0-e0f6-4113-a7f7-222260115964) the trackers being added, once all the trackers have been paired, press "Exit Pairing Mode"

## **Calibration**

+ Plug in a tracker, Press "↻" refresh, select the COM port & "Connect", press "Calibrate 6 Sides", do what the terminal says.
+ Then press "Calibrate", leave the tracker on a desk for 5~ seconds and done!

**Note: You can also doubble tap the trackers button instead of pressing "Calibrate"**

## **Updating Firmware**

+ Connect to the port, select the firmware, press "⬇ Firmware" and wait ~20 seconds.

**Note: Trackers and recievers need to be all updated on the same version or they wont want to pair**

Official SmolSlime docs [Here](https://docs.slimevr.dev/smol-slimes/)

# Odd notes:

+ If you want to feel safe running this program, read the Python code and run it from the .py.
+ If a tracker has old pair data it wont connect to your reciever, plug your tracker in and "Clear Con. data".
+ If the trackers and recievers arent on the same daily build, they will not want to connect.
+ There is a [.html](https://github.com/jitingcn/SmolSlimeWebConfigurator) version of this app, and hosted on a [website](https://gh.jtcat.com/SmolSlimeConfigurator.html), made by [jitingcn](https://github.com/jitingcn).
+ Looking for old source code? look [here](https://github.com/ICantMakeThings/SmolSlimeConfigurator/tree/OldVersions)

