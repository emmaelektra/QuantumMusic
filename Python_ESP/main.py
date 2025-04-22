import socket
import json
import threading
import time
from ESP32Class import ESPLED

PORT = 80
channel_1_brightness = 77
channel_2_brightness = 0
channel_3_brightness = 77
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
            udp_socket.sendto((ESP.response_data + "\n").encode(), (ESP.ip, 1234))
        else:
            print(f"❌ Unknown esp_id: {esp_id}")
            continue
        #print(f"📡 Data from ESP2: {ESP2.output_brightness_2}")
        #print(f"📡 Data from ESP3: {ESP3.output_brightness_1, ESP3.output_brightness_2}")
        print(f"📡 Data from ESP4: {ESP4.entanglement}")
        #print({decoded})
        #print(f"📡 Data from ESP5: {ESP5.output_brightness_1, ESP5.output_brightness_2, ESP5.entanglement, ESP5.previous_entanglement1, ESP5.previous_entanglement2}")
        #if ESP2.output_brightness_2 == 0 and ESP3.entanglement != 0:
        #    print("ESP5 repeated")
        #print(f"📡 Data from ESP6: {ESP6.response_data}, Decoded: {decoded}, ESP6 Input 1: {ESP4.output_brightness_2} Input 2: {ESP5.output_brightness_1} Output1: {ESP6.output_brightness_1}, Output2: {ESP6.output_brightness_2}")
    #print(ESP3.response_data)

def calculate_logic():
    """Calculates brightness values based on received ESP data."""
    while True:
        try:
            ESP1.get_output(channel_1_brightness, channel_2_brightness, 0, 0)#, None, None)
            ESP2.get_output(channel_3_brightness, channel_4_brightness, 0, 0)#, None, None)
            ESP3.get_output(ESP1.output_brightness_2, ESP2.output_brightness_1, ESP1.entanglement, ESP2.entanglement)#, ESP1.pulse2_done, ESP2.pulse1_done)
            ESP4.get_output(ESP1.output_brightness_1, ESP3.output_brightness_1, ESP1.entanglement, ESP3.entanglement)#, ESP1.pulse1_done, ESP3.pulse1_done)
            ESP5.get_output(ESP3.output_brightness_2, ESP2.output_brightness_2, ESP3.entanglement, ESP2.entanglement)#, ESP3.pulse1_done, ESP2.pulse2_done)
            ESP6.get_output(ESP4.output_brightness_2, ESP5.output_brightness_1, ESP4.entanglement, ESP5.entanglement)#, ESP4.pulse2_done, ESP5.pulse1_done)
            # (Additional logic for other ESPs can be enabled as needed)
            time.sleep(0.0001)  # Prevent excessive CPU usage
        except Exception as e:
            print(f"❌ Error in logic calculation: {e}")

# Start connection handling and logic calculation in separate threads.
udp_socket.bind(("0.0.0.0", udp_port))
thread1 = threading.Thread(target=handle_esps, args=(udp_socket,),  daemon=True)
thread2 = threading.Thread(target=calculate_logic, daemon=True)
thread1.start()
thread2.start()

# Keep the main thread alive.
try:
    while True:
        time.sleep(0.0001)
except KeyboardInterrupt:
    print("🔚 Shutting down server...")