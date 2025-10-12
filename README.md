# SmolSlimeConfigurator <img src="icon.png" width="32" height="32" alt="SmolSlimeConfiguratorICON">
Pure Simple UI Configurator for SlimeVR Smol Slimes (Unofficial)


<img width="1316" height="539" alt="newyes" src="https://github.com/user-attachments/assets/ce07f8ac-0857-42c3-9a02-f86d84e19fcc" />

# Features

- **Easy-to-use UI** — clean, modern interface.  
- **Configure your trackers effortlessly** — one-click buttons for gyro calibration, pairing, and more.
- **Helpful tooltips** — hover over any button to see what it does, perfect for beginners.
- **Automatic firmware updater** — just plug your tracker in via USB, select your firmware type and flash the latest build instantly.
- **Always up to date** — Firmware list automatically fetches the latest daily builds from GitHub.
- **Custom firmware support** — flash your own `.uf2` file with a single click.
- **Favorites system** — star your most-used firmware versions by right clicking.
- **Cross-platform** — works seamlessly on **Windows**, **Linux**, **macOS**, and **Android**.
- **Theme customization** — switch between **light/dark mode** and choose your favorite accent color.

# Download
There are 2 options to run the Configurator:
- Single file executable from [Releases](https://github.com/ICantMakeThings/SmolSlimeConfigurator/releases) (Windows, Linux, macOS, Android)
- Python file from the uploaded files above.
- Building it from source looks like: `pyinstaller --onefile --windowed --icon=icon.png --add-data "icon.png:." SmolSlimeConfiguratorVx.py`

# Instructions
**Note: There is a [Video](https://youtu.be/2PHelwy7Rcs) explaining usage, and [This Video](https://www.youtube.com/watch?v=ENINHh4L8tk) for android usage explenation**

## **First install**

+ Plug in the tracker or reciever, hold one side of a wire on rst pin ![image](https://github.com/user-attachments/assets/7cdaae27-21f9-428f-9327-d39bbf8dabc2) (4th pin down from where B+ pin is)
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
+ You cant flash Nordic-eByte/Holyiot Receivers
+ Looking for old source code? look [here](https://github.com/ICantMakeThings/SmolSlimeConfigurator/tree/OldVersions)

