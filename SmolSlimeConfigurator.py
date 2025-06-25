import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import sys

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ser = None
connected = False
read_thread = None
stop_read = threading.Event()


app = ctk.CTk()
app.title("SmolSlime Configurator")
app.geometry("600x490")

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

threading.Thread(target=read_serial, daemon=True).start()

# Top UI
top_frame = ctk.CTkFrame(app)
top_frame.pack(pady=5, padx=10, fill="x")

initial_ports = list_serial_ports()
if not initial_ports:
    initial_ports = ["No ports found"]

port_option = ctk.CTkOptionMenu(top_frame, values=initial_ports)
port_option.set(initial_ports[0])
port_option.pack(side="left", padx=5)

btn_refresh = ctk.CTkButton(top_frame, text="↻", width=10, command=refresh_ports)
btn_refresh.pack(side="left", padx=5)
btn_connect = ctk.CTkButton(top_frame, text="Connect", command=connect_to_port)
btn_connect.pack(side="left", padx=5)
status_label = ctk.CTkLabel(top_frame, text="Not connected", text_color="red")
status_label.pack(side="left", padx=10)

tab_view = ctk.CTkTabview(app, width=580, height=130, corner_radius=10, anchor="w")
tab_view.pack(pady=10, padx=10, fill="x")

# Tab for tracker
tracker_tab = tab_view.add("Tracker")
tracker_btn_frame = ctk.CTkFrame(tracker_tab)
tracker_btn_frame.pack(pady=10, padx=10)

ctk.CTkButton(tracker_btn_frame, text="Calibrate", command=lambda: send_command("calibrate")).grid(row=0, column=0, padx=5, pady=5)
ctk.CTkButton(tracker_btn_frame, text="Calibrate 6 Sides", command=lambda: send_command("6-side")).grid(row=0, column=1, padx=5, pady=5)
ctk.CTkButton(tracker_btn_frame, text="Clear Con. Data", command=lambda: send_command("clear")).grid(row=0, column=2, padx=5, pady=5)
ctk.CTkButton(tracker_btn_frame, text="DFU", command=lambda: send_command("dfu")).grid(row=1, column=0, padx=5, pady=5)
ctk.CTkButton(tracker_btn_frame, text="Info", command=lambda: send_command("info")).grid(row=1, column=1, padx=5, pady=5)

# Tab for reciever
receiver_tab = tab_view.add("Receiver")
receiver_btn_frame = ctk.CTkFrame(receiver_tab)
receiver_btn_frame.pack(pady=10, padx=10)

ctk.CTkButton(receiver_btn_frame, text="Pair", command=lambda: send_command("pair")).grid(row=0, column=0, padx=5, pady=5)
ctk.CTkButton(receiver_btn_frame, text="Exit Pair", command=lambda: send_command("exit")).grid(row=0, column=1, padx=5, pady=5)
ctk.CTkButton(receiver_btn_frame, text="List", command=lambda: send_command("list")).grid(row=0, column=2, padx=5, pady=5)
ctk.CTkButton(receiver_btn_frame, text="Clear Con. Data", command=lambda: send_command("clear")).grid(row=1, column=0, padx=5, pady=5)
ctk.CTkButton(receiver_btn_frame, text="DFU", command=lambda: send_command("dfu")).grid(row=1, column=1, padx=5, pady=5)
ctk.CTkButton(receiver_btn_frame, text="Info", command=lambda: send_command("info")).grid(row=1, column=2, padx=5, pady=5)

# CLI
console = ctk.CTkTextbox(app, width=580, height=220, corner_radius=10)
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
