import socket
import json
import threading
import time
from ESP32Class import ESPLED
import testHistogram
import pygame

# Setup pygame ON THE MAIN THREAD
pygame.init()
screen = pygame.display.set_mode((1680, 1050))
pygame.display.set_caption("Quantum Experiment GUI")
font = pygame.font.Font('/Users/emmasokoll/Library/Fonts/MinionPro-Regular.otf', 36)

stop_event = threading.Event()
current_measured_state = None

PORT = 80
max_brightness = 50
channel_1_brightness = max_brightness
channel_2_brightness = 0
channel_3_brightness = max_brightness
channel_4_brightness = 0

total_pulse_time = 10
refresh_rate = total_pulse_time/5000

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
    while not stop_event.is_set():
        try:
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
                udp_socket.sendto((ESP.response_data + "\n").encode(), (ESP.ip, 1234))
            else:
                print(f"❌ Unknown esp_id: {esp_id}")
                continue
        except OSError:
            # Happens when socket is closed -> exit thread
            break
    print("ESP handler thread stopped.")
            #print(f"📡 Data from ESP2: {ESP2.refresh_rate}")
            #print(f"📡 Data from ESP3: {ESP3.output_brightness_1, ESP3.output_brightness_2}")
            #print(f"📡 Data from ESP4: {ESP4.entanglement}")
            #print({decoded})
            #print(f"📡 Data from ESP5: {ESP5.output_brightness_1, ESP5.output_brightness_2, ESP5.entanglement, ESP5.previous_entanglement1, ESP5.previous_entanglement2}")
            #if ESP2.output_brightness_2 == 0 and ESP3.entanglement != 0:
            #    print("ESP5 repeated")
            #print(f"📡 Data from ESP6: {ESP6.response_data}, Decoded: {decoded}, ESP6 Input 1: {ESP4.output_brightness_2} Input 2: {ESP5.output_brightness_1} Output1: {ESP6.output_brightness_1}, Output2: {ESP6.output_brightness_2}")
            #print(ESP3.response_data)

def calculate_logic():
    """Calculates brightness values based on received ESP data."""
    while not stop_event.is_set():
        try:
            ESP1.get_output(channel_1_brightness, channel_2_brightness, 0, 0, max_brightness)
            ESP2.get_output(channel_3_brightness, channel_4_brightness, 0, 0, max_brightness)
            ESP3.get_output(ESP1.output_brightness_2, ESP2.output_brightness_1, ESP1.entanglement, ESP2.entanglement, max_brightness)
            ESP4.get_output(ESP1.output_brightness_1, ESP3.output_brightness_1, ESP1.entanglement, ESP3.entanglement, max_brightness)
            ESP5.get_output(ESP3.output_brightness_2, ESP2.output_brightness_2, ESP3.entanglement, ESP2.entanglement, max_brightness)
            ESP6.get_output(ESP4.output_brightness_2, ESP5.output_brightness_1, ESP4.entanglement, ESP5.entanglement, max_brightness)
            # (Additional logic for other ESPs can be enabled as needed)
            time.sleep(0.005)  # Prevent excessive CPU usage
        except Exception as e:
            print(f"❌ Error in logic calculation: {e}")
    print("Logic calculator thread stopped.")

def calculate_pulse(total_pulse_time, refresh_rate):
    current_time = 0
    time_per_pixel = (total_pulse_time)/(1000) # 1000 for 5x200 pixels full length
    #refresh_rate = 1/time_per_pixel
    #esp_pixel_per_second = 1/refresh_rate
    ESP1.refresh_rate = ESP2.refresh_rate = time_per_pixel
    current_pixel = 0
    while not stop_event.is_set():
        if current_time <= time_per_pixel * 400:
            ESP1.pulse_start = current_pixel
        else:
            ESP1.pulse_start = -1
        if current_time <= time_per_pixel * 600:
            ESP2.pulse_start = current_pixel
        else:
            ESP2.pulse_start = -1
        if time_per_pixel * 600 >= current_time >= time_per_pixel * 300:
            ESP3.pulse_start = current_pixel
        else:
            ESP3.pulse_start = -1
        if (time_per_pixel * 400) <= current_time <= (time_per_pixel * 1000):
            ESP4.pulse_start = current_pixel
        else:
            ESP4.pulse_start = -1
        if time_per_pixel * 600 <= current_time <= 1000:
            ESP5.pulse_start = current_pixel
        else:
            ESP5.pulse_start = -1
        if time_per_pixel * 800 <= current_time <= 1000:
            ESP6.pulse_start = current_pixel
        else:
            ESP6.pulse_start = -1
        current_time = current_time + time_per_pixel
        current_pixel = current_pixel + 1
        if current_time > total_pulse_time:
        # if current_time >= total_pulse_time + delay:
            current_time = 0
            current_pixel = 0
        time.sleep(time_per_pixel)
    print("Pulse generator thread stopped.")

def calculate_strobe():
    while not stop_event.is_set():
        if current_measured_state is not None:
            ESP4.strobe1 = current_measured_state[0]
            ESP5.strobe1 = current_measured_state[1]
            ESP5.strobe2 = current_measured_state[2]
            ESP6.strobe2 = current_measured_state[2]
        time.sleep(0.01)
    print("Strobe calculator thread stopped.")  # <-- ADD HERE


# Start connection handling and logic calculation in separate threads.
udp_socket.bind(("0.0.0.0", udp_port))

# Start ESP and logic threads
thread1 = threading.Thread(target=handle_esps, args=(udp_socket,), daemon=True)
thread2 = threading.Thread(target=calculate_logic, daemon=True)
thread3 = threading.Thread(target=calculate_pulse, args=(total_pulse_time, refresh_rate), daemon=True)
thread4 = threading.Thread(target=calculate_strobe, daemon=True)

thread1.start()
thread2.start()
thread3.start()
thread4.start()

try:
    # 👇 Directly run the GUI (blocking, on main thread)
    testHistogram.GUI_loop(screen, font, stop_event, ESP_MAP, sampling_interval=2.0)

except KeyboardInterrupt:
    print("KeyboardInterrupt detected. Stopping...")
    stop_event.set()
    time.sleep(0.1)

# Close UDP socket
try:
    udp_socket.close()
    print("🔒 UDP socket closed.")
except Exception as e:
    print(f"❌ Error closing UDP socket: {e}")

print("✅ Shutdown complete.")


