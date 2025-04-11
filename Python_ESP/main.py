import socket
import json
import threading
import time
from ESP32Class import ESPLED

PORT = 80
channel_1_brightness = 77
channel_3_brightness = 77

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
# Setup TCP server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', PORT))
server.listen(10)  # Allow multiple connections
server.setblocking(False)
print("✅ Waiting for ESP connections...")

def handle_client(client):
    client.settimeout(0.5)
    with client:
        while True:
            try:
                data = client.recv(1024).decode()
                if not data:
                    break  # No data means client closed connection

                # Parse CSV: esp_id, p1, p2, p3
                parts = data.strip().split(",")
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
                    elif esp_id == 4:
                        ESP.pot_value_ps_1 = p2 if p2 is not None else 0
                        ESP.pot_value_ps_2 = p3 if p3 is not None else 0
                else:
                    print(f"❌ Unknown esp_id: {esp_id}")
                    continue

            except ValueError as e:
                print(f"❌ ValueError parsing CSV: {e} | Data: {data}")
                continue
            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ Unexpected error with ESP {esp_id}: {e}")
                break

            # Prepare and send the brightness JSON response
            print(f"Response from {esp_id}: {ESP.response_data}")
            response_csv = (ESP.response_data + "\n").encode()
            client.sendall(response_csv)
            time.sleep(0.001)


def accept_connections():
    """
    Continuously accept new connections only from allowed IPs.
    Stop accepting once all allowed clients have connected.
    """
    connected_ips = set()

    while connected_ips != ALLOWED_IPS:
        try:
            client, addr = server.accept()
            client_ip = addr[0]
            if client_ip in ALLOWED_IPS:
                if client_ip not in connected_ips:
                    print(f"✅ Connection from {client_ip}")
                    connected_ips.add(client_ip)
                    threading.Thread(target=handle_client, args=(client,), daemon=True).start()
                else:
                    print(f"Duplicate connection from {client_ip}. Closing connection.")
                    client.close()
            else:
                print(f"Unauthorized connection from {client_ip}. Closing connection.")
                client.close()
        except BlockingIOError:
            #print("Blocking IO")
            time.sleep(0.1)
            continue

    print("All predefined ESP devices are connected. No longer accepting new connections.")


def calculate_logic():
    """Calculates brightness values based on received ESP data."""
    while True:
        try:
            ESP1.get_output(channel_1_brightness, 0)
            ESP2.get_output(channel_3_brightness, 0)
            ESP3.get_output(ESP1.output_brightness_2, ESP2.output_brightness_1)
            ESP4.get_output(ESP1.output_brightness_1, ESP3.output_brightness_1)
            ESP5.get_output(ESP3.output_brightness_2, ESP2.output_brightness_2)
            ESP6.get_output(ESP4.output_brightness_2, ESP5.output_brightness_1)
            # (Additional logic for other ESPs can be enabled as needed)
            time.sleep(0.0001)  # Prevent excessive CPU usage
        except Exception as e:
            print(f"❌ Error in logic calculation: {e}")

# Start connection handling and logic calculation in separate threads.
thread1 = threading.Thread(target=accept_connections, daemon=True)
thread2 = threading.Thread(target=calculate_logic, daemon=True)
thread1.start()
thread2.start()

# Keep the main thread alive.
try:
    while True:
        time.sleep(0.0001)
except KeyboardInterrupt:
    print("🔚 Shutting down server...")