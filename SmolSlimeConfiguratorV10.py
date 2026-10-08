# Import all needed stuff
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Property, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QFileDialog


APP_NAME = "SmolSlime Configurator"
FIRMWARE_REPOS = {
    "main": "https://api.github.com/repos/Shine-Bright-Meow/SlimeNRF-Firmware-CI/releases/latest",
    "kounocom": "https://api.github.com/repos/kounocom/SlimeNRF-Firmware-CI/releases/latest",
}
CUSTOM_FIRMWARE = "Custom firmware file..."
NRFUTIL_RELEASE_API = "https://api.github.com/repos/NordicSemiconductor/pc-nrfutil/releases/latest"


def resource_path(filename):
    bundle_directory = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_directory / filename


def settings_path():
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", Path.home())) / "SmolSlime"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "SmolSlime"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "smolslime"
    root.mkdir(parents=True, exist_ok=True)
    return root / "config.json"


def nrfutil_directory():
    return settings_path().parent


def get_nrfutil_path():
    executable_names = ("nrfutil.exe", "nrfutil") if os.name == "nt" else ("nrfutil",)
    configured = os.environ.get("SMOLSLIME_NRFUTIL")
    if configured:
        resolved = shutil.which(configured) or configured
        if os.path.isfile(resolved):
            return resolved

    try:
        cache_directory = nrfutil_directory()
    except OSError:
        cache_directory = None
    if cache_directory:
        for directory in (cache_directory, cache_directory / "tools"):
            for name in executable_names:
                candidate = directory / name
                if candidate.is_file():
                    return str(candidate)

    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for name in executable_names:
            candidate = bundle_dir / name
            if candidate.is_file():
                return str(candidate)

    for name in executable_names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return None


def download_nrfutil():
    asset_names = {
        "Windows": "nrfutil.exe",
        "Linux": "nrfutil-linux",
        "Darwin": "nrfutil-mac",
    }
    asset_name = asset_names.get(platform.system())
    if not asset_name:
        raise RuntimeError(f"Automatic nrfutil download is not supported on {platform.system()}.")

    headers = {"User-Agent": "SmolSlimeConfigurator", "Accept": "application/vnd.github+json"}
    release_response = requests.get(NRFUTIL_RELEASE_API, headers=headers, timeout=(10, 30))
    release_response.raise_for_status()
    release = release_response.json()
    asset = next(
        (item for item in release.get("assets", []) if item.get("name") == asset_name),
        None,
    )
    if not asset or not asset.get("browser_download_url"):
        raise RuntimeError(f"The latest Nordic release does not contain {asset_name}.")

    destination = nrfutil_directory() / asset_name
    temporary_path = None
    try:
        with requests.get(
            asset["browser_download_url"],
            headers={"User-Agent": "SmolSlimeConfigurator"},
            stream=True,
            timeout=(10, 120),
        ) as response:
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix="nrfutil-", suffix=".download", delete=False
            ) as download:
                temporary_path = Path(download.name)
                total_bytes = 0
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        download.write(chunk)
                        total_bytes += len(chunk)
        if total_bytes < 1024 * 1024:
            raise RuntimeError("The downloaded nrfutil file is unexpectedly small; it was discarded.")
        if os.name != "nt":
            temporary_path.chmod(0o755)
        os.replace(temporary_path, destination)
        return str(destination)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


class AppBackend(QObject):
    logMessage = Signal(str, str)
    portsChanged = Signal()
    connectionChanged = Signal()
    firmwareOptionsChanged = Signal()
    firmwareSelectionChanged = Signal()
    firmwareSourceChanged = Signal()
    localFirmwareChanged = Signal()
    themeChanged = Signal()
    tooltipsChanged = Signal()
    progressChanged = Signal()

    def __init__(self):
        super().__init__()
        self._settings_path = settings_path()
        # Set theme
        self._settings = {
            "firmware_source": "main",
            "custom_firmware_repo": "",
            "favorites": [],
            "theme": "Dark Green",
            "tooltips": True,
        }
        self._load_settings()
        # Set variables and start serial
        self._ports = []
        self._connected_port = ""
        self._serial = None
        # For safety...
        self._serial_lock = threading.Lock()
        self._auto_reconnect_port = ""
        self._auto_reconnect_attempts = 0
        self._auto_reconnect_max_attempts = 7
        self._flash_in_progress = False
        self._firmware_urls = {}
        self._firmware_options = ["Select firmware", CUSTOM_FIRMWARE]
        self._selected_firmware = "Select firmware"
        self._local_firmware_path = ""
        self._progress = 0.0

        self._port_refresh_timer = QTimer(self)
        self._port_refresh_timer.setInterval(2000)
        self._port_refresh_timer.timeout.connect(self._auto_refresh_ports)
        self._port_refresh_timer.start()

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(2000)
        self._reconnect_timer.timeout.connect(self._attempt_auto_reconnect)

        self._serial_timer = QTimer(self)
        self._serial_timer.setInterval(40)
        self._serial_timer.timeout.connect(self._read_serial)
        self._serial_timer.start()
        self._refresh_ports()
        threading.Thread(target=self._load_firmware_assets, daemon=True).start()

    def _load_settings(self):
        try:
            loaded = json.loads(self._settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._settings.update(loaded)
            self._settings["theme"] = {
                "dark": "Dark",
                "light": "Light",
            }.get(self._settings.get("theme"), self._settings.get("theme", "Dark Green"))
            if self._settings["theme"] not in {"Light", "Dark", "Dark Blue", "Dark Green"}:
                self._settings["theme"] = "Dark Green"
        except (OSError, ValueError):
            pass
        self._settings.pop("advanced_mode", None)
        if not isinstance(self._settings.get("tooltips"), bool):
            self._settings["tooltips"] = True
        favorites = self._settings.get("favorites", [])
        if not isinstance(favorites, list):
            favorites = []
        self._settings["favorites"] = list(dict.fromkeys(
            name for name in favorites if isinstance(name, str) and name != CUSTOM_FIRMWARE
        ))

    def _save_settings(self):
        try:
            self._settings_path.write_text(
                json.dumps(self._settings, indent=2), encoding="utf-8"
            )
        except OSError as error:
            self.logMessage.emit(f"Could not save settings: {error}", "error")

    # Sniff them sweet sweet Smol Slimes (Looks for the COM port)
    def _refresh_ports(self):
        available = [port.device for port in serial.tools.list_ports.comports()]
        # Filter out all ports except USB
        if sys.platform.startswith("linux"):
            available = [port for port in available if "ttyACM" in port or "ttyUSB" in port]
        if available == self._ports:
            return
        new_ports = [port for port in available if port not in self._ports]
        self._ports = available
        self.portsChanged.emit()
        if (
            len(new_ports) == 1
            and not self.connected
            and not self._auto_reconnect_port
            and not self._flash_in_progress
        ):
            port = new_ports[0]
            self.logMessage.emit(f"New device detected on {port}; connecting...", "info")
            self.connectToPort(port)

    # Refresh the dropdown menu
    def _auto_refresh_ports(self):
        if not self.connected:
            self._refresh_ports()

    # Pull data from latest releases + file browser
    def _load_firmware_assets(self):
        source = self._settings.get("firmware_source", "main")
        if source == "local":
            self._firmware_urls = {}
            self._update_firmware_options()
            return
        api_url = (
            self._settings.get("custom_firmware_repo", "").strip()
            if source == "custom"
            else FIRMWARE_REPOS.get(source, FIRMWARE_REPOS["main"])
        )
        assets = {}
        if not api_url:
            self.logMessage.emit("Custom firmware repo is empty.", "error")
        else:
            try:
                response = requests.get(api_url, timeout=15)
                response.raise_for_status()
                release = response.json()
                if isinstance(release, list):
                    release = release[0] if release else {}
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if name.lower().endswith((".uf2", ".hex")):
                        assets[name] = asset.get("browser_download_url", "")
            except (requests.RequestException, ValueError, AttributeError) as error:
                self.logMessage.emit(f"Could not load firmware list: {error}", "error")

        self._firmware_urls = assets
        self._update_firmware_options()
        self.logMessage.emit(f"Loaded {len(assets)} firmware options.", "info")

    # Populate firmware menu
    def _update_firmware_options(self):
        favorites = [
            name for name in self._settings["favorites"] if name in self._firmware_urls
        ]
        remaining = sorted(
            (name for name in self._firmware_urls if name not in favorites),
            key=str.lower,
        )
        self._firmware_options = ["Select firmware", *favorites, *remaining, CUSTOM_FIRMWARE]
        self.firmwareOptionsChanged.emit()

    @Property(list, notify=portsChanged)
    def ports(self):
        return self._ports

    @Property(bool, notify=connectionChanged)
    def connected(self):
        return self._serial is not None and self._serial.is_open

    @Property(str, notify=connectionChanged)
    def connectionStatus(self):
        return f"Connected: {self._connected_port}" if self.connected else "Not connected"

    @Property(list, notify=firmwareOptionsChanged)
    def firmwareOptions(self):
        return self._firmware_options

    @Property(list, notify=firmwareOptionsChanged)
    def firmwareFavorites(self):
        return self._settings["favorites"]

    @Property(str, notify=firmwareSelectionChanged)
    def selectedFirmware(self):
        return self._selected_firmware

    @selectedFirmware.setter
    def selectedFirmware(self, name):
        if name != self._selected_firmware:
            self._selected_firmware = name
            self.firmwareSelectionChanged.emit()

    @Property(str, notify=firmwareSourceChanged)
    def firmwareSource(self):
        return self._settings.get("firmware_source", "main")

    @Property(str, notify=firmwareSourceChanged)
    def customFirmwareRepo(self):
        return self._settings.get("custom_firmware_repo", "")

    @Property(str, notify=localFirmwareChanged)
    def localFirmwarePath(self):
        return self._local_firmware_path

    @Property(str, notify=themeChanged)
    def theme(self):
        return self._settings.get("theme", "Dark Green")

    @Property(bool, notify=tooltipsChanged)
    def tooltipsEnabled(self):
        return self._settings.get("tooltips", True)

    # Platform name ting ting
    @Property(str, constant=True)
    def platformName(self):
        return {"Darwin": "macOS"}.get(platform.system(), platform.system())

    @Property(float, notify=progressChanged)
    def progress(self):
        return self._progress

    def _set_progress(self, value):
        self._progress = max(0.0, min(1.0, value))
        self.progressChanged.emit()

    @Slot(str)
    # El button to connect your Smol Slimes to El program
    def connectToPort(self, port):
        self._cancel_auto_reconnect()
        if self.connected:
            self.disconnectSerial()
        if not port:
            self.logMessage.emit("Select a serial port first.", "error")
            return
        try:
            self._serial = serial.Serial(port, 115200, timeout=0.02)
            self._connected_port = port
            self.connectionChanged.emit()
            self.logMessage.emit(f"Connected to {port}.", "success")
        except (serial.SerialException, OSError) as error:
            self._serial = None
            self._connected_port = ""
            self.connectionChanged.emit()
            self.logMessage.emit(f"Could not connect: {error}", "error")

    @Slot()
    def disconnectSerial(self):
        self._cancel_auto_reconnect()
        with self._serial_lock:
            if self._serial:
                try:
                    self._serial.close()
                except serial.SerialException:
                    pass
            self._serial = None
            self._connected_port = ""
        self.connectionChanged.emit()

    def _cancel_auto_reconnect(self):
        self._reconnect_timer.stop()
        self._auto_reconnect_port = ""
        self._auto_reconnect_attempts = 0

    # If smolslime escapes (disconnects) de program tries to catch it and put it back in the dungeon (reconnects)
    def _start_auto_reconnect(self, port):
        if not port or self._flash_in_progress:
            return
        self._cancel_auto_reconnect()
        self._auto_reconnect_port = port
        self.logMessage.emit(f"Connection lost; reconnecting to {port}...", "info")
        self._attempt_auto_reconnect()

    def _attempt_auto_reconnect(self):
        port = self._auto_reconnect_port
        if not port or self._flash_in_progress:
            self._reconnect_timer.stop()
            return

        self._auto_reconnect_attempts += 1
        try:
            self._serial = serial.Serial(port, 115200, timeout=0.02)
        except (serial.SerialException, OSError):
            if self._auto_reconnect_attempts >= self._auto_reconnect_max_attempts:
                self._reconnect_timer.stop()
                self._auto_reconnect_port = ""
                self._auto_reconnect_attempts = 0
                self.logMessage.emit(f"Failed to reconnect to {port}.", "error")
            else:
                self._reconnect_timer.start()
            return

        self._connected_port = port
        self._cancel_auto_reconnect()
        self.connectionChanged.emit()
        self.logMessage.emit(f"Successfully reconnected to {port}.", "success")

    @Slot(str)
    # Send commands via serial,
    def sendCommand(self, command):
        command = command.strip()
        if not command:
            return
        with self._serial_lock:
            if not self._serial or not self._serial.is_open:
                self.logMessage.emit("Not connected to a device.", "error")
                return
            try:
                self._serial.write((command + "\n").encode("utf-8"))
            except (serial.SerialException, OSError) as error:
                self.logMessage.emit(f"Serial write failed: {error}", "error")
                return
        self.logMessage.emit(f">>> {command}", "command")

    @Slot(str)
    def sendReceiverAdd(self, address):
        if address.strip():
            self.sendCommand(f"add {address.strip()}")
        else:
            self.logMessage.emit("Enter a tracker address to add.", "error")

    @Slot(str)
    def sendTrackerSet(self, address):
        if address.strip():
            self.sendCommand(f"set {address.strip()}")
        else:
            self.logMessage.emit("Enter a receiver address to set.", "error")

    @Slot(str)
    def sendTrackerReset(self, reset_type):
        if reset_type in {"zro", "acc", "mag", "bat", "all"}:
            self.sendCommand(f"reset {reset_type}")

    @Slot(str)
    def setTheme(self, theme):
        if theme not in {"Light", "Dark", "Dark Blue", "Dark Green"}:
            return
        self._settings["theme"] = theme
        self._save_settings()
        self.themeChanged.emit()

    @Slot(bool)
    def setTooltipsEnabled(self, enabled):
        self._settings["tooltips"] = enabled
        self._save_settings()
        self.tooltipsChanged.emit()

    @Slot()
    def openRepository(self):
        QDesktopServices.openUrl(
            QUrl("https://github.com/ICantMakeThings/SmolSlimeConfigurator")
        )

    @Slot(str)
    def setFirmwareSource(self, source):
        if source not in {"main", "kounocom", "custom", "local"}:
            return
        self._settings["firmware_source"] = source
        self._save_settings()
        self.firmwareSourceChanged.emit()
        threading.Thread(target=self._load_firmware_assets, daemon=True).start()

    @Slot()
    # The thing that asks for the custom .U2F
    def chooseLocalFirmware(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Select firmware", "", "Firmware (*.uf2 *.hex)"
        )
        if path:
            self._local_firmware_path = path
            self.localFirmwareChanged.emit()

    @Slot(str)
    def setCustomFirmwareRepo(self, url):
        self._settings["custom_firmware_repo"] = url.strip()
        self._save_settings()
        if self.firmwareSource == "custom":
            threading.Thread(target=self._load_firmware_assets, daemon=True).start()

    @Slot(str)
    def selectFirmware(self, name):
        self.selectedFirmware = name

    @Slot(str)
    # fave ting ting
    def toggleFirmwareFavorite(self, name):
        if name not in self._firmware_urls:
            return
        favorites = self._settings["favorites"]
        if name in favorites:
            favorites.remove(name)
        else:
            favorites.insert(0, name)
        self._save_settings()
        self._update_firmware_options()

    @Slot(str, str)
    def flashFirmware(self, firmware_input, selected_firmware):
        if not self.connected:
            self.logMessage.emit("Connect to a device before flashing.", "error")
            return

        if self.firmwareSource == "local":
            if not self._local_firmware_path:
                self.logMessage.emit("Choose a local firmware file first.", "error")
                return
            threading.Thread(
                target=self._flash_local_file,
                args=(self._local_firmware_path,),
                daemon=True,
            ).start()
            return

        firmware_input = firmware_input.strip()
        if firmware_input.lower().startswith(("http://", "https://")):
            parsed_url = urlparse(firmware_input)
            if (
                parsed_url.scheme not in {"http", "https"}
                or not parsed_url.netloc
                or Path(unquote(parsed_url.path)).suffix.lower() not in {".uf2", ".hex"}
            ):
                self.logMessage.emit("Paste a direct .uf2 or .hex firmware URL.", "error")
                return
            threading.Thread(
                target=self._download_and_flash, args=(firmware_input,), daemon=True
            ).start()
            return

        if selected_firmware.startswith(("http://", "https://")):
            firmware_input = selected_firmware
            parsed_url = urlparse(firmware_input)
            if (
                not parsed_url.netloc
                or Path(unquote(parsed_url.path)).suffix.lower() not in {".uf2", ".hex"}
            ):
                self.logMessage.emit("Paste a direct .uf2 or .hex firmware URL.", "error")
                return
            threading.Thread(
                target=self._download_and_flash, args=(firmware_input,), daemon=True
            ).start()
            return

        if selected_firmware == "Select firmware":
            self.logMessage.emit("Select a firmware option first.", "error")
            return
        if selected_firmware == CUSTOM_FIRMWARE:
            path, _ = QFileDialog.getOpenFileName(
                None, "Select firmware", "", "Firmware (*.uf2 *.hex)"
            )
            if not path:
                return
            threading.Thread(target=self._flash_local_file, args=(path,), daemon=True).start()
            return

        url = self._firmware_urls.get(selected_firmware)
        if url:
            threading.Thread(target=self._download_and_flash, args=(url,), daemon=True).start()
        else:
            self.logMessage.emit("No download URL is available for this firmware.", "error")

    # Download the firmware once user selected and pressed the Firmware button,
    # and also the actual logic for flashing (Resets, puts into DFU, waits for drive to appear, moves the .U2F)
    def _download_and_flash(self, url):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            filename = Path(unquote(urlparse(url).path)).name or "firmware.uf2"
            # OS temp dir
            local_path = Path(tempfile.gettempdir()) / filename
            with local_path.open("wb") as firmware_file:
                shutil.copyfileobj(response.raw, firmware_file)
            self.logMessage.emit(f"Downloaded {filename}.", "success")
            self._flash_local_file(str(local_path))
        except (requests.RequestException, OSError) as error:
            self.logMessage.emit(f"Firmware download failed: {error}", "error")

    def _flash_local_file(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix not in {".hex", ".uf2"}:
            self.logMessage.emit("Choose a .uf2 or .hex firmware file.", "error")
            return
        self._flash_in_progress = True
        try:
            if suffix == ".hex":
                self._flash_hex(file_path)
            else:
                self._flash_uf2(file_path)
        finally:
            self._flash_in_progress = False

    def _flash_uf2(self, file_path):
        self._set_progress(0.1)
        self.logMessage.emit("Requesting bootloader mode...", "info")
        self.sendCommand("clear")
        time.sleep(0.4)
        self.sendCommand("dfu")
        self._close_serial_for_flash()
        self._set_progress(0.25)
        self.logMessage.emit("Waiting for the UF2 drive...", "info")
        time.sleep(5)
        mount_point = self._find_uf2_mount()
        if not mount_point:
            self._set_progress(0)
            self.logMessage.emit("UF2 drive not found. Is the device in bootloader mode?", "error")
            return
        try:
            destination = Path(mount_point) / Path(file_path).name
            shutil.copy2(file_path, destination)
            self._set_progress(1)
            self.logMessage.emit(f"Firmware copied to {destination}.", "success")
        except OSError as error:
            self._set_progress(0)
            self.logMessage.emit(f"Could not copy firmware: {error}", "error")

    def _find_uf2_mount(self):
        if os.name == "nt":
            roots = [f"{letter}:\\" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
        elif platform.system() == "Darwin":
            roots = [str(path) for path in Path("/Volumes").glob("*")]
        else:
            roots = ["/run/media", "/media", "/mnt"]
            user = os.environ.get("USER", "")
            if user:
                roots.insert(0, f"/run/media/{user}")
        for root in roots:
            try:
                if (Path(root) / "INFO_UF2.TXT").is_file():
                    return root
                for current, directories, _ in os.walk(root):
                    directories[:] = directories[:32]
                    if (Path(current) / "INFO_UF2.TXT").is_file():
                        return current
            except OSError:
                continue
        return None

    def _close_serial_for_flash(self):
        with self._serial_lock:
            if self._serial:
                try:
                    self._serial.close()
                except serial.SerialException:
                    pass
            self._serial = None
        self.connectionChanged.emit()

    # HEX flashing usin command thingy, Shud work gud
    def _flash_hex(self, file_path):
        nrfutil = get_nrfutil_path()
        if not nrfutil:
            self.logMessage.emit("Downloading nrfutil...", "info")
            try:
                nrfutil = download_nrfutil()
                self.logMessage.emit(f"nrfutil installed at {nrfutil}.", "success")
            except (OSError, requests.RequestException, ValueError, RuntimeError) as error:
                self.logMessage.emit(f"Could not download nrfutil: {error}", "error")
                return
        with self._serial_lock:
            if not self._serial or not self._serial.is_open:
                self.logMessage.emit("Device is no longer connected.", "error")
                return
            port = self._connected_port
        self.logMessage.emit(f"Entering bootloader on {port}...", "info")
        self.sendCommand("dfu")
        time.sleep(2)
        self._close_serial_for_flash()
        dfu_package = str(Path(file_path).with_name(Path(file_path).stem + "_dfu_package.zip"))
        try:
            self._set_progress(0.2)
            self._run_nrfutil(
                nrfutil,
                [
                    "pkg", "generate", "--hw-version", "52", "--application-version", "1",
                    "--sd-req", "0x00", "--application", file_path, dfu_package,
                ],
                "Generating DFU package",
            )
            self._set_progress(0.55)
            self._run_nrfutil(
                nrfutil,
                ["dfu", "serial", "--package", dfu_package, "--port", port, "--baud-rate", "115200"],
                "Flashing DFU package",
            )
            self._set_progress(1)
            self.logMessage.emit("Firmware flashed successfully.", "success")
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            self._set_progress(0)
            self.logMessage.emit(f"nrfutil failed: {error}", "error")
        finally:
            try:
                os.remove(dfu_package)
            except OSError:
                pass

    def _run_nrfutil(self, executable, arguments, label):
        self.logMessage.emit(f"{label}...", "info")
        result = subprocess.run(
            [executable, *arguments], capture_output=True, text=True, check=False, timeout=180
        )
        if result.stdout.strip():
            self.logMessage.emit(result.stdout.strip(), "info")
        if result.returncode:
            details = result.stderr.strip() or result.stdout.strip() or "No diagnostic output was returned."
            raise RuntimeError(f"exit status {result.returncode}: {details}")
        if result.stderr.strip():
            self.logMessage.emit(result.stderr.strip(), "info")

    # Let the code add MORE!! (more lines of serial that is)
    def _read_serial(self):
        try:
            with self._serial_lock:
                if not self._serial or not self._serial.is_open or not self._serial.in_waiting:
                    return
                line = self._serial.readline().decode("utf-8", errors="replace").strip()
            if line:
                self.logMessage.emit(line, "device")
        except (serial.SerialException, OSError) as error:
            self.logMessage.emit(f"Device disconnected: {error}", "error")
            port = self._connected_port
            self.disconnectSerial()
            if port and not self._flash_in_progress:
                self._start_auto_reconnect(port)


# Start base window, size & name
def main():
    QQuickStyle.setStyle("Material")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("SmolSlime")
    # MY GUY THE ICON IS THE MOST IMPORTANT TING
    app.setWindowIcon(QIcon(str(resource_path("icon.png"))))
    backend = AppBackend()
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"backend": backend})
    qml_path = resource_path("Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    # The MOST PORTAN' PART!!!
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())