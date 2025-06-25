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
from tkinter import filedialog
import tkinter as tk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ser = None
connected = False
read_thread = None
stop_read = threading.Event()
custom_fw_path = None

def fetch_latest_firmware_assets():
    api_url = "https://api.github.com/repos/Shine-Bright-Meow/SlimeNRF-Firmware-CI/releases/latest"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        assets = data.get("assets", [])
        fw_dict = {}
        for asset in assets:
            name = asset["name"]
            if name.endswith(".uf2"):
                fw_dict[name] = asset["browser_download_url"]
        return fw_dict
    except Exception as e:
        append_text(f"[Error fetching firmware list] {e}\n")
        return {}

app = ctk.CTk()
app.title("SmolSlime Configurator")
app.geometry("1010x490")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#FFFFFF", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    filtered = []

    for port in ports:
        if sys.platform.startswith("linux"):
            if "ttyACM" in port.device:
                filtered.append(port.device)
        else:
            filtered.append(port.device)

    return filtered

def refresh_ports():
    ports = list_serial_ports()
    if ports:
        port_option.configure(values=ports)
        port_option.set(ports[0])
    else:
        port_option.configure(values=["No ports found"])
        port_option.set("No ports found")

def connect_to_port():
    global ser, connected, read_thread, stop_read

    port = port_option.get()
    if not port or "No ports" in port:
        append_text("No valid port selected.\n")
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
        append_text(f"Connected to {port}\n")

        read_thread = threading.Thread(target=read_serial, daemon=True)
        read_thread.start()

    except serial.SerialException as e:
        append_text(f"Failed to connect: {e}\n")
        status_label.configure(text="Connection failed", text_color="red")

def send_command(cmd):
    global ser, connected
    if ser and ser.is_open:
        try:
            ser.write((cmd + "\n").encode())
            append_text(f">>> {cmd}\n")
        except (serial.SerialException, OSError) as e:
            append_text(f"[Error] Serial write failed: {e}\n")
            try:
                ser.close()
            except Exception:
                pass
            ser = None
            connected = False
            status_label.configure(text="Disconnected", text_color="red")
    else:
        append_text("Not connected.\n")

def read_serial():
    global ser, stop_read
    while not stop_read.is_set():
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode(errors="ignore").rstrip('\r\n \t')
                if line:
                    append_text(line + '\n')
            except Exception as e:
                append_text(f"[Serial error] {e}\n")
        time.sleep(0.01)

def append_text(text):
    console.configure(state="normal")
    console.insert("end", text)
    console.see("end")
    console.update_idletasks()
    console.configure(state="disabled")

def on_tracker_change(choice):
    global custom_fw_path
    if choice == "Custom…":
        path = filedialog.askopenfilename(title="Select firmware (.uf2)", filetypes=[("UF2 files", "*.uf2")])
        if path:
            custom_fw_path = path
            send_button.configure(text=f"Flash: {os.path.basename(path)}")
        else:
            tracker_select.set(tracker_names[0])
    else:
        custom_fw_path = None
        send_button.configure(text="Flash Firmware")


# Top UI
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


# Firmware options
firmware_urls = {"Custom (User provided .uf2)": None}

def populate_firmware_menu():
    global firmware_urls
    auto_fw = fetch_latest_firmware_assets()
    if auto_fw:
        firmware_urls = {**auto_fw, "Custom (User provided .uf2)": None}
        firmware_choice.configure(values=list(firmware_urls.keys()))
        firmware_choice.set("Select Firmware")
    else:
        firmware_urls = {"Custom (User provided .uf2)": None}
        firmware_choice.configure(values=["Custom (User provided .uf2)"])
        firmware_choice.set("Custom (User provided .uf2)")

firmware_choice = ctk.CTkOptionMenu(top_frame, values=["Loading..."])
firmware_choice.set("Loading...")
firmware_choice.pack(side="left", padx=5)
ToolTip(firmware_choice, "Select the tracker to update firmware")

app.after(100, populate_firmware_menu)

def download_firmware():
    selection = firmware_choice.get()

    if selection == "Select Firmware":
        append_text("Please select a firmware option.\n")
        return

    if selection == "Custom (User provided .uf2)":
        file_path = filedialog.askopenfilename(filetypes=[("UF2 files", "*.uf2")])
        if not file_path:
            append_text("No custom firmware selected.\n")
            return
        append_text(f"Selected custom firmware: {file_path}\n")
        local_path = file_path
    else:
        firmware_url = firmware_urls.get(selection)
        if not firmware_url:
            append_text("No firmware URL for selected firmware.\n")
            return

        local_path = os.path.join(tempfile.gettempdir(), os.path.basename(firmware_url))

        try:
            append_text(f"Downloading firmware from {firmware_url}...\n")
            response = requests.get(firmware_url, stream=True, timeout=20)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            append_text(f"Firmware downloaded to: {local_path}\n")
        except Exception as e:
            append_text(f"[Error] Firmware download failed: {e}\n")
            return

    append_text("Clearing Connection data and entering bootloader mode...\n")
    send_command("clear")
    time.sleep(0.5)
    send_command("dfu")
    label_matches = ["NICENANO", "UF2", "XIAO-SENSE", "zephyr"]
    append_text(f"Waiting up to 10 seconds for usb to appear. If the drive's name is something other than {', '.join(label_matches)}, please post an issue https://github.com/ICantMakeThings/SmolSlimeConfigurator, mentioning the name of the usb drive, precisely.\n")
    time.sleep(10)  # Sleep to wait for USB drive to pop up

    mount_point = None
    system = platform.system()
    try:
        if system == "Windows":
            import win32api
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            for drive in drives:
                try:
                    vol_name = win32api.GetVolumeInformation(drive)[0]
                    if any(label in vol_name.upper() for label in label_matches):
                        mount_point = drive
                        break
                except Exception:
                    continue

        elif system == "Darwin":
            volumes_path = "/Volumes"
            for vol in os.listdir(volumes_path):
                if any(label in vol.upper() for label in label_matches):
                    mount_point = os.path.join(volumes_path, vol)
                    break

        elif system == "Linux":
            media_path = "/media"
            for root, dirs, _ in os.walk(media_path):
                for dir in dirs:
                    if any(label in dir.upper() for label in label_matches):
                        mount_point = os.path.join(root, dir)
                        break
                if mount_point:
                    break

        if mount_point and os.path.isdir(mount_point):
            dest = os.path.join(mount_point, os.path.basename(local_path))
            append_text(f"Copying firmware to {dest}...\n")
            shutil.copy(local_path, dest)
            append_text(f"DONE: Firmware successfully flashed to {mount_point}\n")
        else:
            append_text("ERROR: Could not find NICENANO or UF2 boot device. Is the device in DFU/bootloader mode?\n")
    except Exception as e:
        append_text(f"[Error flashing] {e}\n")


btn_download_fw = ctk.CTkButton(top_frame, text="⬇ Firmware", width=20, command=download_firmware)
btn_download_fw.pack(side="left", padx=5)
ToolTip(btn_download_fw, "Upgrade your firmware!")


status_label = ctk.CTkLabel(top_frame, text="Not connected", text_color="red")
status_label.pack(side="left", padx=10)


tab_view = ctk.CTkTabview(app, width=580, height=130, corner_radius=10, anchor="w")
tab_view.pack(pady=10, padx=10, fill="x")

# Tab for tracker
tracker_tab = tab_view.add("Tracker")
tracker_btn_frame = ctk.CTkFrame(tracker_tab)
tracker_btn_frame.pack(pady=10, padx=10)
btn = ctk.CTkButton(tracker_btn_frame, text="Info", command=lambda: send_command("info"))
btn.grid(row=0, column=0, padx=5, pady=5)
ToolTip(btn, "Get device information")

btn = ctk.CTkButton(tracker_btn_frame, text="Reboot", command=lambda: send_command("reboot"))
btn.grid(row=0, column=1, padx=5, pady=5)
ToolTip(btn, "Soft reset the device")

btn = ctk.CTkButton(tracker_btn_frame, text="Scan", command=lambda: send_command("scan"))
btn.grid(row=0, column=2, padx=5, pady=5)
ToolTip(btn, "Restart sensor scan")

btn = ctk.CTkButton(tracker_btn_frame, text="Calibrate", command=lambda: send_command("calibrate"))
btn.grid(row=0, column=3, padx=5, pady=5)
ToolTip(btn, "Calibrate sensor ZRO")

btn = ctk.CTkButton(tracker_btn_frame, text="Calibrate 6 Sides", command=lambda: send_command("6-side"))
btn.grid(row=0, column=4, padx=5, pady=5)
ToolTip(btn, "Calibrate 6-side accelerometer")

btn = ctk.CTkButton(tracker_btn_frame, text="Mag Clear", command=lambda: send_command("mag"))
btn.grid(row=0, column=5, padx=5, pady=5)
ToolTip(btn, "Clear magnetometer calibration")

btn = ctk.CTkButton(tracker_btn_frame, text="Pairing Mode", command=lambda: send_command("pair"))
btn.grid(row=1, column=0, padx=5, pady=5)
ToolTip(btn, "Enter pairing mode")

btn = ctk.CTkButton(tracker_btn_frame, text="Clear Con. Data", command=lambda: send_command("clear"))
btn.grid(row=1, column=1, padx=5, pady=5)
ToolTip(btn, "Clear pairing data")

btn = ctk.CTkButton(tracker_btn_frame, text="DFU", command=lambda: send_command("dfu"))
btn.grid(row=1, column=2, padx=5, pady=5)
ToolTip(btn, "Enter DFU bootloader (if available)")

btn = ctk.CTkButton(tracker_btn_frame, text="Uptime", command=lambda: send_command("uptime"))
btn.grid(row=1, column=3, padx=5, pady=5)
ToolTip(btn, "Get device uptime")

btn = ctk.CTkButton(tracker_btn_frame, text="Debug", command=lambda: send_command("debug"))
btn.grid(row=1, column=4, padx=5, pady=5)
ToolTip(btn, "Print debug log")

btn = ctk.CTkButton(tracker_btn_frame, text="Meow!", command=lambda: send_command("meow"))
btn.grid(row=1, column=5, padx=5, pady=5)
ToolTip(btn, "Meow!")



# Tab for receiver
receiver_tab = tab_view.add("Receiver")
receiver_btn_frame = ctk.CTkFrame(receiver_tab)
receiver_btn_frame.pack(pady=10, padx=10)

btn = ctk.CTkButton(receiver_btn_frame, text="Info", command=lambda: send_command("info"))
btn.grid(row=0, column=0, padx=5, pady=5)
ToolTip(btn, "Get device information")

btn = ctk.CTkButton(receiver_btn_frame, text="List", command=lambda: send_command("list"))
btn.grid(row=0, column=1, padx=5, pady=5)
ToolTip(btn, "Get paired devices")

btn = ctk.CTkButton(receiver_btn_frame, text="Reboot", command=lambda: send_command("reboot"))
btn.grid(row=0, column=2, padx=5, pady=5)
ToolTip(btn, "Soft reset the device")

btn = ctk.CTkButton(receiver_btn_frame, text="Pairing Mode", command=lambda: send_command("pair"))
btn.grid(row=0, column=3, padx=5, pady=5)
ToolTip(btn, "Enter pairing mode")

btn = ctk.CTkButton(receiver_btn_frame, text="Remove", command=lambda: send_command("remove"))
btn.grid(row=0, column=4, padx=5, pady=5)
ToolTip(btn, "Remove last paired device")

btn = ctk.CTkButton(receiver_btn_frame, text="Exit Pairing Mode", command=lambda: send_command("exit"))
btn.grid(row=0, column=5, padx=5, pady=5)
ToolTip(btn, "Exit pairing mode")

btn = ctk.CTkButton(receiver_btn_frame, text="Clear Conn'd Devices", command=lambda: send_command("clear"))
btn.grid(row=1, column=0, padx=5, pady=5)
ToolTip(btn, "Clear stored devices")

btn = ctk.CTkButton(receiver_btn_frame, text="DFU", command=lambda: send_command("dfu"))
btn.grid(row=1, column=1, padx=5, pady=5)
ToolTip(btn, "Enter DFU bootloader (if available)")

btn = ctk.CTkButton(receiver_btn_frame, text="Uptime", command=lambda: send_command("uptime"))
btn.grid(row=1, column=2, padx=5, pady=5)
ToolTip(btn, "Get device uptime")

btn = ctk.CTkButton(receiver_btn_frame, text="Meow!", command=lambda: send_command("meow"))
btn.grid(row=1, column=3, padx=5, pady=5)
ToolTip(btn, "Meow!")

# CLI
console = ctk.CTkTextbox(app, width=1000, height=220, corner_radius=10)
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

command_entry.bind("<Return>", lambda event: send_custom_command())

app.mainloop()
