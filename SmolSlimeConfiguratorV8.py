# Import all needed stuff
import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import sys
import os
import shutil
import requests
import subprocess
import platform
import tempfile
import json
import webbrowser
import re
#import hashlib
#from tkinter import colorchooser
from tkinter import filedialog
import tkinter as tk
import queue

# For safety...
serial_queue = queue.Queue()
ser_lock = threading.Lock()

# Wanted to add a funny meow when you press the meow button but i couldnt pack it all into a single .exe so no funny meow for you :<
#import pygame

#def resource_path(relative_path):
#    try:
#        base_path = sys._MEIPASS
#    except Exception:
#        base_path = os.path.abspath(".")
#    return os.path.join(base_path, relative_path)

# Set theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

#pygame.mixer.init()
#meow_sound = pygame.mixer.Sound("meow.wav")

# Set variables and start serial
ser = None
connected = False
read_thread = None
stop_read = threading.Event()
custom_fw_path = None

SETTINGS_PATH = os.path.join(tempfile.gettempdir(), "smolslime_config.json")

default_settings = {
    "theme": "dark",
    "accent": "dark-blue",
    "tooltips": True,
    "favorites": ["Custom (User provided .uf2 / .hex)"],
    "seen_favorite_hint": False
}

settings = default_settings.copy()

def load_settings():
    global settings
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                settings.update(json.load(f))
        except Exception:
            pass

def save_settings():
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f)

load_settings()
ctk.set_appearance_mode(settings["theme"])
ctk.set_default_color_theme(settings["accent"])



# Pull data from latest releases + file browser
def fetch_latest_firmware_assets():
    api_url = "https://api.github.com/repos/Shine-Bright-Meow/SlimeNRF-Firmware-CI/releases/latest"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        assets = data.get("assets", [])
        fw_dict = {}

        for asset in assets:
            name = asset.get("name", "")
            url = asset.get("browser_download_url", "")
            if name.endswith((".uf2", ".hex")):
                fw_dict[name] = url

        if not fw_dict:
            append_text("No UF2 or HEX found in latest release. check internet and if still issue, post a issue on github, https://icmt.cc\n", "error")

        return fw_dict

    except Exception as e:
        append_text(f"[Error fetching firmware list] {e}\n", "error")
        return {}


# Start base window, size & name
app = ctk.CTk()
app.title("SmolSlimeConfigurator")
app.geometry("1010x500")

# Overdone tooltip overlay
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
        global TOOLTIPS_ENABLED
        TOOLTIPS_ENABLED = settings.get("tooltips", True)

    def show_tip(self, event=None):
        if not TOOLTIPS_ENABLED or self.tipwindow or not self.text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # Match theme colors
        bg_color = "#333333" if settings["theme"] == "dark" else "#FFFFFF"
        fg_color = "#FFFFFF" if settings["theme"] == "dark" else "#000000"

        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=bg_color)

        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background=bg_color,
            foreground=fg_color,
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        )
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


# Sniff them sweet sweet Smol Slimes (Looks for the COM port)
def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    filtered = []
# Filter out all ports except USB
    for port in ports:
        if sys.platform.startswith("linux"):
            if "ttyACM" in port.device:
                filtered.append(port.device)
        else:
            filtered.append(port.device)

    return filtered

# Refresh the dropdown menu 
def refresh_ports():
    ports = list_serial_ports()
    if ports:
        port_option.configure(values=ports)
        port_option.set(ports[0])
    else:
        port_option.configure(values=["No ports found"])
        port_option.set("No ports found")

# El button to connect your Smol Slimes to El program
def connect_to_port():
    global ser, connected, read_thread, stop_read

    port = port_option.get()
    if not port or "No ports" in port:
        append_text("No valid port selected.\n", "error")
        return

    if ser and ser.is_open:
        stop_read.set()
        try:
            ser.close()
        except Exception:
            pass
        ser = None
        connected = False

    stop_read = threading.Event()

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        connected = True
        status_label.configure(text=f"Connected to {port}", text_color="green")
        append_text(f"Connected to {port}\n", "success")

        read_thread = threading.Thread(target=read_serial, daemon=True)
        read_thread.start()

    except serial.SerialException as e:
        append_text(f"Failed to connect: {e}\n")
        status_label.configure(text="Connection failed", text_color="red")

# If smolslime escapes (disconnects) de program tries to catch it and put it back in the dungeon (reconnects)
def attempt_reconnect():
    global ser, connected, stop_read, read_thread

    port = port_option.get()
    if not port or "No ports" in port:
        append_text("No valid port to reconnect.\n")
        return

    def reconnect_loop():
        global ser, connected, stop_read, read_thread
        retries = 0
        max_retries = 15 // 2

        while not connected and retries < max_retries:
            try:
                if ser and ser.is_open:
                    with ser_lock:
                        ser.close()
                    ser = None

                ser = serial.Serial(port, 115200, timeout=1)
                connected = True
                stop_read.clear()
                read_thread = threading.Thread(target=read_serial, daemon=True)
                read_thread.start()
                status_label.configure(text=f"Connected to {port}", text_color="green")
                append_text("\nSuccessfully reconnected!\n", "success")
                break

            except serial.SerialException:
                retries += 1
                append_text(".", None)
                console.update_idletasks()
                time.sleep(2)

        if not connected:
            append_text("\nFailed to reconnect.\n", "error")
            status_label.configure(text="Not connected", text_color="red")

    threading.Thread(target=reconnect_loop, daemon=True).start()

# Send commands via serial,
def send_command(cmd):
    global ser, connected
    if ser and ser.is_open:
        try:
            with ser_lock:
                ser.write((cmd + "\n").encode())
            append_text(f">>> {cmd}\n")
        except (serial.SerialException, OSError) as e:
            append_text(f"[Error] Serial write failed: {e}\n", "error")
            disconnect_serial()
    else:
        append_text("Not connected.\n", "error")

def read_serial():
    global ser, stop_read, connected
    while not stop_read.is_set():
        try:
            if ser and ser.in_waiting:
                with ser_lock:
                    line = ser.readline().decode(errors="ignore").rstrip('\r\n \t')
                if line:
                    serial_queue.put(line)
            else:
                time.sleep(0.01)
        except (OSError, serial.SerialException) as e:
            append_text(f"Device disconnected: {e}\n", "error")
            disconnect_serial()
            attempt_reconnect()
            break


def disconnect_serial():
    global ser, connected
    try:
        if ser:
            with ser_lock:
                ser.close()
    except Exception:
        pass
    ser = None
    connected = False
    status_label.configure(text="Not connected", text_color="red")




# Let the code add MORE!! (more lines of serial that is)
def append_text(text, color=None):
    console.configure(state="normal")
    tag = None
    if color == "error":
        tag = "red"
    elif color == "success":
        tag = "green"

    # Check if user is at bottom
    at_bottom = console.yview()[1] == 1.0

    if tag:
        console.insert("end", text, tag)
    else:
        console.insert("end", text)

    if at_bottom:
        console.see("end")

    console.update_idletasks()
    console.configure(state="disabled")




# The thing that asks for the custom .U2F
def on_tracker_change(choice):
    global custom_fw_path
    if choice == "Custom…":
        path = filedialog.askopenfilename(title="Select firmware (.uf2 or .hex)", filetypes=[("Firmware files", "*.uf2 *.hex"), ("UF2 files", "*.uf2"), ("HEX files", "*.hex")])
        if path:
            custom_fw_path = path
            send_button.configure(text=f"Flash: {os.path.basename(path)}")
        else:
            tracker_select.set(tracker_names[0])
    else:
        custom_fw_path = None
        send_button.configure(text="Flash Firmware")


# Top UI | Yk the serial buttons
top_frame = ctk.CTkFrame(app)
top_frame.pack(pady=5, padx=10, fill="x")

initial_ports = list_serial_ports()
if not initial_ports:
    initial_ports = ["No ports found"]

port_option = ctk.CTkOptionMenu(top_frame, values=initial_ports)
port_option.set(initial_ports[0])
port_option.pack(side="left", padx=5)
ToolTip(port_option, "Select the port for your device")

btn_refresh = ctk.CTkButton(top_frame, text="↻", width=10, command=refresh_ports)
btn_refresh.pack(side="left", padx=5)
ToolTip(btn_refresh, "Refresh serial port")

btn_connect = ctk.CTkButton(top_frame, text="Connect", command=connect_to_port)
btn_connect.pack(side="left", padx=5)
ToolTip(btn_connect, "Connect to the selected serial port")

progress_bar = ctk.CTkProgressBar(app, width=1000)
progress_bar.set(0)
progress_bar.pack_forget()

firmware_urls = {"Custom (User provided .uf2 / .hex)": None}

# Fill the dropdown menu with latest releases
selected_firmware = tk.StringVar(value="Select Firmware")

def open_firmware_popup():
    global firmware_urls
    popup = ctk.CTkToplevel(app)
    popup.title("Select Firmware")
    popup.geometry("300x400")
    popup.transient(app)

    # R-Click Hint
    if not settings.get("seen_favorite_hint", False):
        hint_popup = ctk.CTkToplevel(popup)
        hint_popup.title("Tip")
        hint_popup.geometry("260x100")
        hint_popup.transient(popup)

        hint_label = ctk.CTkLabel(
            hint_popup,
            text="Right-click firmware to star it!\nFavorites appear first and in gold",
            justify="center",
            wraplength=220
        )
        hint_label.pack(expand=True, fill="both", padx=10, pady=10)

        ok_button = ctk.CTkButton(hint_popup, text="Got it!", command=hint_popup.destroy)
        ok_button.pack(pady=(0, 10))

        settings["seen_favorite_hint"] = True
        save_settings()

        hint_popup.after(50, lambda: hint_popup.grab_set())

    def open_docs():
        webbrowser.open("https://docs.slimevr.dev/smol-slimes/firmware/smol-pre-compiled-firmware.html#-tracker")

    help_button = ctk.CTkButton(
        popup, text="Which Firmware to pick?", command=open_docs,
        fg_color="red", hover_color="#cc0000", text_color="white"
    )
    help_button.pack(padx=10, pady=(10, 5), fill="x")

    # Search bar
    search_var = tk.StringVar()

    search_entry = ctk.CTkEntry(popup, placeholder_text="Search firmware or paste URL...", textvariable=search_var)
    search_entry.pack(padx=10, pady=(0, 5), fill="x")

    scroll_frame = ctk.CTkScrollableFrame(popup, width=280, height=320)
    scroll_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def toggle_favorite(fw):
        favs = settings.setdefault("favorites", [])
        if fw in favs:
            favs.remove(fw)
        else:
            favs.append(fw)
        save_settings()
        update_list()

    def select_fw(fw):
        selected_firmware.set(fw)
        popup.destroy()

    def update_list(*args):
        search_term = search_var.get().lower()
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        favs = settings.get("favorites", [])
        items = list(firmware_urls.keys())
        sorted_items = sorted(items, key=lambda x: (x not in favs, x.lower()))

        for fw in sorted_items:
            if search_term in fw.lower():
                is_fav = fw in favs
                btn = ctk.CTkButton(
                    scroll_frame,
                    text=("☆ " if is_fav else "") + fw,
                    command=lambda f=fw: select_fw(f),
                    text_color="gold" if is_fav else None
                )
                btn.pack(fill="x", pady=2)
                btn.bind("<Button-3>", lambda e, f=fw: toggle_favorite(f))

    def on_paste_url(*args):
        text = search_var.get().strip()
        match = re.search(r'([^/\\]+\.uf2)$', text)
        if match:
            filename = match.group(1)
            search_var.set(filename)
        update_list()

    search_var.trace_add("write", on_paste_url)

    def scrollf(event):
        try:
            scroll_frame._on_mousewheel(event)
        except Exception:
            pass
        if event.num == 4:
            try:
                if hasattr(scroll_frame, "_parent_canvas") and scroll_frame._parent_canvas:
                    scroll_frame._parent_canvas.yview_scroll(-1, "units")
            except Exception:
                pass
        elif event.num == 5:
            try:
                if hasattr(scroll_frame, "_parent_canvas") and scroll_frame._parent_canvas:
                    scroll_frame._parent_canvas.yview_scroll(1, "units")
            except Exception:
                pass

    scroll_frame.bind_all("<MouseWheel>", scrollf)
    scroll_frame.bind_all("<Button-4>", scrollf)
    scroll_frame.bind_all("<Button-5>", scrollf)

    update_list()
    popup.wait_visibility()
    popup.after(50, lambda: popup.grab_set())

# Button to open firmware popup
firmware_button = ctk.CTkButton(
    top_frame, textvariable=selected_firmware, command=open_firmware_popup, width=200
)
firmware_button.pack(side="left", padx=5)
ToolTip(firmware_button, "Select the Firmware version for your smolslime")

# Populate firmware menu
def populate_firmware_menu():
    global firmware_urls
    auto_fw = fetch_latest_firmware_assets()
    if auto_fw:
        firmware_urls = {**auto_fw, "Custom (User provided .uf2 / .hex)": None}
    else:
        firmware_urls = {"Custom (User provided .uf2 / .hex)": None}


app.after(100, populate_firmware_menu)

# Loading bar
def animate_progress(target, step=0.02, interval=50):
    current = progress_bar.get()
    if current < target:
        progress_bar.set(min(current + step, target))
        app.after(interval, lambda: animate_progress(target, step, interval))
    else:
        if target == 1.0:
            app.after(2000, lambda: progress_bar.pack_forget())

def get_nrfutil_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(sys.executable))
        nrfutil_path = os.path.join(base_path, 'nrfutil')
        if sys.platform == "win32" and not nrfutil_path.endswith('.exe'):
            nrfutil_path += '.exe'
        return nrfutil_path
    else:
        return "nrfutil"

# HEX flashing usin command thingy, idk if works
def flash_hex_firmware(file_path):
    global ser, connected
    if not ser or not ser.is_open:
        append_text("Device not connected.\n", "error")
        return
    
    append_text("Entering bootloader...\n")
    send_command("dfu")
    time.sleep(2)

    port = ser.port
    append_text(f"Starting Flash on port: {port}...\n")
    ser.close()
    ser = None
    connected = False
    nrfutil_cmd = get_nrfutil_path()

    try:
        dfu_package = os.path.splitext(file_path)[0] + "_dfu_package.zip"

        append_text("Generating DFU package...\n")
        subprocess.run([
            nrfutil_cmd, "pkg", "generate",
            "--hw-version", "52",
            "--application-version", "1",
            "--sd-req", "0x00",
            "--application", file_path,
            dfu_package
        ], check=True, shell=False)

        append_text("Flashing DFU package via serial...\n")
        subprocess.run([
            nrfutil_cmd, "dfu", "serial",
            "--package", dfu_package,
            "--port", port,
            "--baud-rate", "115200"
        ], check=True, shell=False)

        append_text("YAY! FW Flashed!!!\n", "success")
        progress_bar.set(1.0)

    except FileNotFoundError:
        append_text("Error 420: run 'pip install nrfutil'.\n", "error")
    except subprocess.CalledProcessError as e:
        append_text(f"Error code: {e}\n", "error")
    finally:
        try:
            if os.path.exists(dfu_package):
                os.remove(dfu_package)
        except Exception:
            pass



# Download the firmware once user selected and pressed the Firmware button,
# and also the actual logic for flashing (Resets, puts into DFU, waits for drive to appear, moves the .U2F to the drive)
def download_firmware():
    selection = selected_firmware.get()


    if selection == "Select Firmware":
        append_text("Please select a firmware option.\n", "error")
        return

    

    if selection == "Custom (User provided .uf2 / .hex)":
        file_path = filedialog.askopenfilename(filetypes=[("Firmware files", "*.uf2 *.hex"), ("UF2 files", "*.uf2"), ("HEX files", "*.hex")])
        if not file_path:
            append_text("No custom firmware selected.\n")
            return
        append_text(f"Selected custom firmware: {file_path}\n")
        local_path = file_path
        if local_path.endswith(".hex"):
            append_text("Starting flashing... [HEX]\n", "success")
            flash_hex_firmware(local_path)
            return
    else:
        firmware_url = firmware_urls.get(selection)
        if not firmware_url:
            append_text("No firmware URL for selected firmware.\n")
            return

        local_path = os.path.join(tempfile.gettempdir(), os.path.basename(firmware_url))

        try:
            append_text(f"Downloading firmware from {firmware_url}...\n", "success")
            response = requests.get(firmware_url, stream=True, timeout=20)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)

            append_text(f"Firmware downloaded to: {local_path}\n", "success")
            if local_path.endswith(".hex"):
                append_text("yoo HEX file! Loading...\n", "success")
                flash_hex_firmware(local_path)
                return

        except Exception as e:
            append_text(f"[Error] Firmware download failed: {e}\n", "error")
            return
    progress_bar.pack(pady=(5,5))
    animate_progress(0.2)

    append_text("Clearing Connection data and entering bootloader mode...\n")
    send_command("clear")
    time.sleep(0.5)
    send_command("dfu")
    animate_progress(0.4)

    append_text("Waiting up to 5 seconds for UF2 device to appear. If you have issues, please post an issue https://github.com/ICantMakeThings/SmolSlimeConfigurator \n")
    time.sleep(5)

    mount_point = None
    system = platform.system()
    try:
        candidate_paths = []

        if system == "Windows":
            import win32api
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            candidate_paths = drives

        elif system == "Darwin":
            candidate_paths = [os.path.join("/Volumes", d) for d in os.listdir("/Volumes")]

        elif system == "Linux":
            media_root = "/media"
            for root, dirs, _ in os.walk(media_root):
                for d in dirs:
                    candidate_paths.append(os.path.join(root, d))

        for path in candidate_paths:
            try:
                if os.path.isfile(os.path.join(path, "INFO_UF2.TXT")):
                    mount_point = path
                    break
            except Exception:
                continue

        if mount_point and os.path.isdir(mount_point):
            dest = os.path.join(mount_point, os.path.basename(local_path))
            append_text(f"Copying firmware to {dest}...\n")
            shutil.copy(local_path, dest)
            append_text(f"DONE: Firmware successfully flashed to {mount_point}\n", "success")
            animate_progress(1.0)
            app.after(2000, lambda: progress_bar.pack_forget())

        else:
            append_text("ERROR: Could not find NICENANO or UF2 boot device. Is the device in DFU/bootloader mode?\n", "error")
        progress_bar.pack_forget()

    except Exception as e:
        append_text(f"[Error flashing] {e}\n", "error")
        append_text("NOTE! On windows [WinError 433] doesn't mean it failed!\n", "success")
        progress_bar.pack_forget()


# Buttons!
def start_firmware_download():
    threading.Thread(target=download_firmware, daemon=True).start()

btn_download_fw = ctk.CTkButton(top_frame, text="⬇ Firmware", width=80, command=start_firmware_download)
btn_download_fw.pack(side="left", padx=5)
ToolTip(btn_download_fw, "Upgrade your firmware!")

status_label = ctk.CTkLabel(top_frame, text="Not connected", text_color="red")
status_label.pack(side="left", padx=10)

tab_view = ctk.CTkTabview(app, width=580, height=130, corner_radius=10, anchor="w")
tab_view.pack(pady=10, padx=10, fill="x")



# Make the repetitive stuff less messy
def ui_btn(parent, text, command, tooltip):
    btn = ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=110,
        height=30,
        anchor="center"
    )
    ToolTip(btn, tooltip)
    return btn


# Tracker tab
tracker_tab = tab_view.add("Tracker")
tracker_btn_frame = ctk.CTkFrame(tracker_tab)
tracker_btn_frame.pack(pady=10, padx=10)

ui_btn(tracker_btn_frame, "Info", lambda: send_command("info"), "Get device information").grid(row=0, column=0, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Reboot", lambda: send_command("reboot"), "Soft reset the device").grid(row=0, column=1, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Scan", lambda: send_command("scan"), "Restart sensor scan").grid(row=0, column=2, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Calibrate", lambda: send_command("calibrate"), "Calibrate sensor ZRO").grid(row=0, column=3, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Calibrate 6 Sides", lambda: send_command("6-side"), "Calibrate 6-side accelerometer").grid(row=0, column=4, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Mag Clear", lambda: send_command("mag"), "Clear magnetometer calibration").grid(row=0, column=5, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Battery", lambda: send_command("battery"), "Get battery information").grid(row=0, column=6, padx=5, pady=5)

ui_btn(tracker_btn_frame, "Pairing Mode", lambda: send_command("pair"), "Enter pairing mode").grid(row=1, column=0, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Clear Con. Data", lambda: send_command("clear"), "Clear pairing data").grid(row=1, column=1, padx=5, pady=5)
ui_btn(tracker_btn_frame, "DFU", lambda: send_command("dfu"), "Enter DFU bootloader (if available)").grid(row=1, column=2, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Uptime", lambda: send_command("uptime"), "Get device uptime").grid(row=1, column=3, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Debug", lambda: send_command("debug"), "Print debug log").grid(row=1, column=4, padx=5, pady=5)
ui_btn(tracker_btn_frame, "Meow!", lambda: send_command("meow"), "Meow!").grid(row=1, column=5, padx=5, pady=5)

# Receiver tab
receiver_tab = tab_view.add("Receiver")
receiver_btn_frame = ctk.CTkFrame(receiver_tab)
receiver_btn_frame.pack(pady=10, padx=10)

ui_btn(receiver_btn_frame, "Info", lambda: send_command("info"), "Get device information").grid(row=0, column=0, padx=5, pady=5)
ui_btn(receiver_btn_frame, "List", lambda: send_command("list"), "Get paired devices").grid(row=0, column=1, padx=5, pady=5)
ui_btn(receiver_btn_frame, "Reboot", lambda: send_command("reboot"), "Soft reset the device").grid(row=0, column=2, padx=5, pady=5)
ui_btn(receiver_btn_frame, "Remove", lambda: send_command("remove"), "Remove last paired device").grid(row=0, column=3, padx=5, pady=5)
ui_btn(receiver_btn_frame, "Pairing Mode", lambda: send_command("pair"), "Enter pairing mode").grid(row=0, column=4, padx=5, pady=5)

ui_btn(receiver_btn_frame, "✖ Saved Devices", lambda: send_command("clear"), "Clear stored devices").grid(row=1, column=0, padx=5, pady=5)
ui_btn(receiver_btn_frame, "DFU", lambda: send_command("dfu"), "Enter DFU bootloader (if available)").grid(row=1, column=1, padx=5, pady=5)
ui_btn(receiver_btn_frame, "Uptime", lambda: send_command("uptime"), "Get device uptime").grid(row=1, column=2, padx=5, pady=5)
ui_btn(receiver_btn_frame, "Meow!", lambda: send_command("meow"), "Meow!").grid(row=1, column=3, padx=5, pady=5)
ui_btn(receiver_btn_frame, "⎋ Pairing Mode", lambda: send_command("exit"), "Exit pairing mode").grid(row=1, column=4, padx=5, pady=5)

# Settings tab
settings_tab = tab_view.add("Settings")
settings_frame = ctk.CTkFrame(settings_tab)
settings_frame.pack(padx=10, pady=10, fill="both", expand=True)
version_label = ctk.CTkLabel(settings_frame, text="SmolSlimeConfigurator Version 8", text_color="gray")
version_label.pack(anchor="ne", padx=10, pady=5)

def toggle_theme(choice):
    settings["theme"] = choice
    ctk.set_appearance_mode(choice)
    save_settings()

def toggle_accent(choice):
    settings["accent"] = choice
    ctk.set_default_color_theme(choice)
    save_settings()

def toggle_tooltips():
    global TOOLTIPS_ENABLED
    settings["tooltips"] = not settings["tooltips"]
    TOOLTIPS_ENABLED = settings["tooltips"]
    save_settings()
    append_text(f"Tooltips {'enabled' if TOOLTIPS_ENABLED else 'disabled'}.\n", "success")

def open_repo():
    webbrowser.open("https://github.com/ICantMakeThings/SmolSlimeConfigurator")

appearance_frame = ctk.CTkFrame(settings_frame)
appearance_frame.pack(pady=10, fill="x")

ctk.CTkLabel(appearance_frame, text="Appearance Mode:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
theme_menu = ctk.CTkOptionMenu(appearance_frame, values=["light", "dark"], command=toggle_theme)
theme_menu.set(settings["theme"])
theme_menu.grid(row=0, column=1, padx=5, pady=5, sticky="w")

ctk.CTkLabel(appearance_frame, text="Accent Colour:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
accent_menu = ctk.CTkOptionMenu(appearance_frame, values=["blue", "green", "dark-blue"], command=toggle_accent)
accent_menu.set(settings["accent"])
accent_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")
ToolTip(accent_menu, "Requires app restart")

# Buttonssss
button_row = ctk.CTkFrame(settings_frame)
button_row.pack(pady=15)

tooltips_button = ctk.CTkButton(button_row, text="Toggle Tooltips", command=toggle_tooltips)
tooltips_button.pack(side="left", padx=10)
ToolTip(tooltips_button, "Yk what each button does? Turn off tooltips!")


repo_button = ctk.CTkButton(button_row, text="Open GitHub Repo", command=open_repo)
repo_button.pack(side="left", padx=10)

ToolTip(repo_button, "github.com/ICantMakeThings/SmolSlimeConfigurator")


# CLI
console = ctk.CTkTextbox(app, width=1000, height=220, corner_radius=10)
console.tag_config("red", foreground="red")
console.tag_config("green", foreground="lime")

console.pack(pady=(0, 5), padx=10)
console.configure(state="disabled")

def send_custom_command():
    cmd = command_entry.get().strip()
    if cmd:
        send_command(cmd)
        command_entry.delete(0, "end")

entry_frame = ctk.CTkFrame(app)
entry_frame.pack(pady=5, padx=10, fill="x")

command_entry = ctk.CTkEntry(entry_frame, placeholder_text="Enter custom command...")
command_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=5)

btn_send = ctk.CTkButton(entry_frame, text="Send", width=80, command=send_custom_command)
btn_send.pack(side="left", pady=5)

btn_clear = ctk.CTkButton(entry_frame, text="X", width=30, command=lambda: console.configure(state="normal") or console.delete("1.0", "end") or console.configure(state="disabled"))
btn_clear.pack(side="left", padx=(5,0), pady=5)
ToolTip(btn_clear, "Clear")

command_entry.bind("<Return>", lambda event: send_custom_command())

# MY GUY THE ICON IS THE MOST IMPORTANT TING
def resource_path(relative_path):
    """gapfpione."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if sys.platform.startswith("win"):
    app.iconbitmap(resource_path("icon.ico"))
elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
    img_path = resource_path("icon.png")
    try:
        img = tk.PhotoImage(file=img_path)
        app.iconphoto(True, img)
    except Exception as e:
        print(f"boohoo.. error: {e}")


def flush_serial_queue():
    while not serial_queue.empty():
        append_text(serial_queue.get() + "\n")
    app.after(50, flush_serial_queue)

app.after(50, flush_serial_queue)
# The MOST PORTAN' PART!!!
app.mainloop()
