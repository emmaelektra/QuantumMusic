import random
import socket
import json
import threading
import time
from ESP32Class import ESPLED
import subprocess
import math
import cmath
import os
import signal
import atexit
import time
import sys
import csv


# Launch the GUI script in a separate process
try:
    gui_process = subprocess.Popen([sys.executable, "histogramUDP.py"])
    client_process = subprocess.Popen([sys.executable, r"C:\Users\Inkuele\Desktop\Emma_MA\eigensoundlab\tcp-client.py"])
    print("Launched histogram")
    print("Launched client-tcp")
except Exception as e:
    print(f"❌ Failed to start histogramUDP.py: {e}")

print("Continuing with UDP logic...")

# Function to clean up on exit
def cleanup():
    print("🧹 Cleaning up histogramUDP.py and client-tcp.py...")
    if gui_process and gui_process.poll() is None:
        try:
            gui_process.terminate()
            gui_process.wait(timeout = 5)
            print("histogramUDP.py terminated")
        except Exception as e:
            print(f"⚠️ Could not terminate child process: {e}")
    if client_process and client_process.poll() is None:
        try:
            client_process.terminate()
            client_process.wait(timeout = 5)
            print("client-tcp.py terminated")
        except Exception as e:
            print(f"⚠️ Could not terminate child process: {e}")

# Register cleanup function to run on exit
atexit.register(cleanup)

PORT = 80

GUI_IP = "127.0.0.1"  # localhost
GUI_PORT = 12345      # port where GUI listens
gui_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# New socket for receiving measured_state
measured_state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
measured_state_port = 5678
measured_state_socket.bind(("0.0.0.0", measured_state_port))

latest_measured_state = None
def listen_for_measured_state():
    global latest_measured_state
    while True:
        data, addr = measured_state_socket.recvfrom(1024)
        latest_measured_state = list(map(int, data.decode().strip().split(",")))
        print(f"📩 Received measured_state: {latest_measured_state}")
        measured_event.set()  # ← wake up calculate_pulse()

max_brightness = 60
channel_1_brightness = max_brightness
channel_2_brightness = 0
channel_3_brightness = max_brightness
channel_4_brightness = 0

# Define ESP instances explicitly
ESP1 = ESPLED("192.168.4.3", 1, 2000)
ESP2 = ESPLED("192.168.4.4", 2, 2000)
ESP3 = ESPLED("192.168.4.5", 3, 2000, 2000)
ESP4 = ESPLED("192.168.4.6", 4, 2000, 2000, 2000)
ESP5 = ESPLED("192.168.4.7", 5, 2000)
ESP6 = ESPLED("192.168.4.8", 6, 2000)

# Dictionary for quick lookup by esp_id
ESP_MAP = {
    1: ESP1,
    2: ESP2,
    3: ESP3,
    4: ESP4,
    5: ESP5,
    6: ESP6
}

ALLOWED_IPS = {"192.168.4.3", "192.168.4.4", "192.168.4.5", "192.168.4.6", "192.168.4.7", "192.168.4.8"}
# Setup udp
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_port = 1234

print("✅ Waiting for ESP connections...")

def handle_esps(udp_socket):
    """Constantly recieves data over udp from esps and updates corresponding class attributes"""
    while True:
        data, addr = udp_socket.recvfrom(1024)
        decoded = data.decode(errors="replace").strip()

        #print(f"📡 Data from {addr}: {decoded}")
        # Parse CSV: esp_id, p1, p2, p3
        parts = decoded.split(",")
        while len(parts) < 4:
            parts.append("")  # Ensure always 4 values

        esp_id = int(parts[0]) if parts[0] else None
        p1 = int(parts[1]) if parts[1] else None
        p2 = int(parts[2]) if parts[2] else None
        p3 = int(parts[3]) if parts[3] else None

        if esp_id in ESP_MAP:
            ESP = ESP_MAP[esp_id]
            ESP.pot_value = p1

            if esp_id == 3:
                ESP.pot_value_ps_1 = p2 if p2 is not None else 0
                #print(f"📡 Data from {ESP.response_data}: {decoded}")
            elif esp_id == 4:
                ESP.pot_value_ps_1 = p2 if p2 is not None else 0
                ESP.pot_value_ps_2 = p3 if p3 is not None else 0
                #print(f"Data from ESP4: {decoded}")
            if ESP.response_data is not None:
                udp_socket.sendto((ESP.response_data + "\n").encode(), (ESP.ip, 1234))
            # Forward all ESP pot values to the GUI
            pots_to_send = [
                ESP1.pot_value,  # BS1
                ESP2.pot_value,  # BS2
                ESP3.pot_value,  # BS3
                ESP4.pot_value,  # BS4
                ESP5.pot_value,  # BS5
                ESP6.pot_value,  # BS6
                ESP4.pot_value_ps_1,  # RG1
                ESP3.pot_value_ps_1,  # RG2
                ESP4.pot_value_ps_2  # RG3
            ]

            pots_str = ",".join(map(str, pots_to_send))
            gui_socket.sendto(pots_str.encode(), (GUI_IP, GUI_PORT))

        else:
            print(f"❌ Unknown esp_id: {esp_id}")
            continue

        #print(f"📡 Data from ESP6: {ESP6.pot_value, ESP6.input_intensity1, ESP6.input_intensity2, ESP6.output_intensity1, ESP6.output_intensity2}")
        #print(f"📡 Data from ESP4: {ESP4.pot_value, ESP4.input_intensity1, ESP4.input_intensity2, ESP4.output_intensity1, ESP4.output_intensity2}")

temp_path = r"C:\Users\Inkuele\Desktop\Emma_MA\eigensoundlab\matrix_temp.csv"
final_path = r"C:\Users\Inkuele\Desktop\Emma_MA\eigensoundlab\matrix_log.csv"

def write_matrix():
    while True:
        # Matrix written with potentiometer values here:
        matrix = [[ESP1.pot_value, ESP2.pot_value, ESP3.pot_value], 
                [ESP4.pot_value, ESP5.pot_value, ESP6.pot_value],
                [ESP4.pot_value_ps_1, ESP3.pot_value_ps_1, ESP4.pot_value_ps_2]]
                
        with open(temp_path, "w", newline = "") as csvfile:
            writer = csv.writer(csvfile)
            for row in matrix:
                writer.writerow(row)
                
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_path, final_path)
        except Exception as e:
            print(f"⚠️ Could not update matrix_log.csv: {e}")
        time.sleep(0.1)

E1_0 = math.sqrt(max_brightness) * cmath.exp(1j * 0)
E2_0 = 0
E3_0 = math.sqrt(max_brightness) * cmath.exp(1j * 0)
E4_0 = 0

def calculate_logic():
    """Calculates brightness values based on received ESP data."""
    while True:
        try:
            E1_1 = ESP1.Eout_1
            E2_1 = ESP1.Eout_2
            E3_1 = ESP2.Eout_1
            E4_1 = ESP2.Eout_2

            E1_2 = E1_1
            E2_2 = ESP3.Eout_1
            E3_2 = ESP3.Eout_2
            E4_2 = E4_1

            E1_3 = ESP4.Eout_1
            E2_3 = ESP4.Eout_2
            E3_3 = ESP5.Eout_1
            E4_3 = ESP5.Eout_2

            E1_4 = ESP4.Eout_1
            E2_4 = ESP6.Eout_1
            E3_4 = ESP6.Eout_2
            E4_4 = ESP5.Eout_2

            ESP1.get_output(E1_0, E2_0, max_brightness)
            ESP2.get_output(E3_0, E4_0, max_brightness)
            ESP3.get_output(E2_1, E3_1, max_brightness)
            ESP4.get_output(E1_2, E2_2, max_brightness)
            ESP5.get_output(E3_2, E4_2, max_brightness)
            ESP6.get_output(E2_3, E3_3, max_brightness)
            # (Additional logic for other ESPs can be enabled as needed)

            # Entanglement helper function
            def is_entangled(a_intensity, b_intensity, c_intensity, pot_value, pot_range=(1650, 2850)):
                return a_intensity > 0 and b_intensity > 0 and c_intensity > 0 and pot_range[0] <= pot_value <= pot_range[1]

            ESP3.entanglement = int(is_entangled(ESP1.output_intensity2, ESP2.output_intensity1, 1, ESP3.pot_value))
            ESP4.entanglement = int(is_entangled(ESP1.output_intensity1, ESP3.output_intensity1, ESP2.output_intensity1, ESP4.pot_value))
            if ESP4.entanglement == 1 and ESP3.entanglement == 1:
                ESP4.entanglement = 3
            elif ESP3.entanglement == 1 and ESP4.entanglement == 0:
                ESP4.entanglement = 2
            ESP5.entanglement = int(is_entangled(ESP3.output_intensity2, ESP2.output_intensity2, ESP1.output_intensity2, ESP5.pot_value))
            #print(f'3: {ESP3.output_intensity2} 2: {ESP2.output_intensity2} 1: {ESP1.output_intensity2} pot: {ESP}')
            ESP6.entanglement = int(is_entangled(ESP4.output_intensity2, ESP5.output_intensity1, 1, ESP6.pot_value))

            time.sleep(0.001)  # Prevent excessive CPU usage
        except Exception as e:
            print(f"❌ Error in logic calculation: {e}")

measured_event = threading.Event()

total_pulse_time = 12
strobe_time = 0.5

def calculate_pulse(total_pulse_time, strobe_time, pulse_id):
    BUSY_THRESHOLD = 0.002
    num_pixels = 1000
    time_per_pixel = total_pulse_time / num_pixels
  
    while True:
        start = time.perf_counter()

        # ——— 1) pulse sweep ———
        for px in range(num_pixels):
            #print(f'{px} {pulse_id}')
            setattr(ESP1, pulse_id, px if px < 0.4 * num_pixels else -1)
            setattr(ESP2, pulse_id, px if px < 0.6 * num_pixels else -1)
            setattr(ESP3, pulse_id, px if 0.1 * num_pixels < px < 0.6 * num_pixels else -1)
            setattr(ESP4, pulse_id, px if 0.1 * num_pixels < px < num_pixels else -1)
            setattr(ESP5, pulse_id, px if 0.6 * num_pixels < px < num_pixels else -1)
            setattr(ESP6, pulse_id, px if 0.7 * num_pixels < px < num_pixels else -1)
            if px == 970:
                # 1) tell the GUI to sample
                measured_event.clear()
                gui_socket.sendto(json.dumps({"sample": True}).encode(), (GUI_IP, GUI_PORT))

            target = start + (px + 1) * time_per_pixel
            now = time.perf_counter()
            to_sleep = target - now - BUSY_THRESHOLD

            if to_sleep > 0:
                time.sleep(to_sleep)

            while time.perf_counter() < target:
                pass

        setattr(ESP1, pulse_id, -1)
        setattr(ESP2, pulse_id, -1)
        setattr(ESP3, pulse_id, -1)
        setattr(ESP4, pulse_id, -1)
        setattr(ESP5, pulse_id, -1)
        setattr(ESP6, pulse_id, -1)

        # 2) wait (up to 500 ms) for the reply
        if not measured_event.wait(0.3):
            print("⚠️ measurement timeout")
            # you can decide here to skip or default to zeros
        # now latest_measured_state is guaranteed fresh

        # ——— 2) latch & print strobes ———
        if latest_measured_state and len(latest_measured_state) >= 4:
            a, b, c, d = latest_measured_state[:4]
            ESP4.strobe1 = a
            ESP6.strobe1 = b
            ESP6.strobe2 = c
            ESP5.strobe2 = d
        else:
            ESP4.strobe1 = ESP6.strobe1 = ESP6.strobe2 = ESP5.strobe2 = 0
        print("time_per_pixel:", time_per_pixel)
        print("Strobes ON:", ESP4.strobe1, ESP6.strobe1, ESP6.strobe2, ESP5.strobe2)

        # ——— 3) hold strobes ———
        time.sleep(strobe_time)
        print("Strobes still ON:", ESP4.strobe1, ESP6.strobe1, ESP6.strobe2, ESP5.strobe2)

        # ——— 4) clear strobes ———
        ESP4.strobe1 = ESP6.strobe1 = ESP6.strobe2 = ESP5.strobe2 = 0
        print("Strobes CLEARED", ESP4.strobe1, ESP6.strobe1, ESP6.strobe2, ESP5.strobe2)

        # ——— 5) random inter-cycle delay ———
        delay = random.uniform(0, 20)
        print(f"Waiting {delay:.2f}s for next cycle")
        time.sleep(delay)


# Start connection handling and logic calculation in separate threads.
udp_socket.bind(("0.0.0.0", udp_port))
thread1 = threading.Thread(target=handle_esps, args=(udp_socket,),  daemon=True)
thread2 = threading.Thread(target=calculate_logic, daemon=True)
thread3 = threading.Thread(target=calculate_pulse, args=(total_pulse_time, strobe_time, "pulse_start1"),  daemon=True)
thread4 = threading.Thread(target=calculate_pulse, args=(total_pulse_time, strobe_time, "pulse_start2"),  daemon=True)
thread5 = threading.Thread(target=calculate_pulse, args=(total_pulse_time, strobe_time, "pulse_start3"),  daemon=True)
thread6 = threading.Thread(target=write_matrix, daemon = True)
thread7 = threading.Thread(target=listen_for_measured_state, daemon=True)
thread1.start()
thread2.start()
thread3.start()
thread4.start()
thread5.start()
thread6.start()
thread7.start()

# Keep the main thread alive.
try:
    while True:
        time.sleep(0.0001)
except KeyboardInterrupt:
    print("🔚 Shutting down server...")