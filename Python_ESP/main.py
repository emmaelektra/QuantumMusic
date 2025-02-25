import socket
import json
import threading
import time
from ESP32Class import ESPLED

PORT = 80
channel_1_brightness = 77
channel_3_brightness = 77

# Define ESP instances explicitly
ESP1 = ESPLED("192.168.4.3", 1, 2000, 2000)
ESP2 = ESPLED("192.168.4.4", 2, 2000, 2000)
ESP3 = ESPLED("192.168.4.5", 3, 2000, 2000)
ESP4 = ESPLED("192.168.4.6", 4, 2000, 2000)
ESP5 = ESPLED("192.168.4.7", 5, 2000, 2000)
ESP6 = ESPLED("192.168.4.8", 6, 2000, 2000)

# Dictionary for quick lookup by esp_id
ESP_MAP = {
    1: ESP1,
    2: ESP2,
    3: ESP3,
    4: ESP4,
    5: ESP5,
    6: ESP6
}

# Setup TCP server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', PORT))
server.listen(10)  # Allow multiple connections
server.setblocking(False)
print("✅ Waiting for ESP connections...")

def handle_client(client):
    """Handle a persistent connection from an ESP32 device."""
    client.settimeout(0.5)  # Use a short timeout to allow non-blocking loops
    with client:
        while True:
            try:
                data = client.recv(1024).decode().strip()
                if not data:
                    # No data means the connection was closed by the client.
                    break

                # Parse incoming JSON message
                message = json.loads(data)
                esp_id = message.get("esp_id")
                if esp_id in ESP_MAP:
                    ESP = ESP_MAP[esp_id]
                    ESP.pot_value = message["pot_value"]

                    # Handle any phase values if provided
                    if esp_id == 3:
                        ESP.pot_value_ps_1 = message.get("phase_value1", 0)
                    elif esp_id == 4:
                        ESP.pot_value_ps_1 = message.get("phase_value1", 0)
                        ESP.pot_value_ps_2 = message.get("phase_value2", 0)

                    # print(f"📩 Received data from ESP {esp_id}: {message}")

                    # Prepare the brightness response JSON and append newline.
                    response_json = json.dumps(ESP.response_data) + "\n"
                    client.sendall(response_json.encode())
                else:
                    print("Received message with unknown esp_id.")
            except socket.timeout:
                # No data received during this period; continue looping.
                continue
            except json.JSONDecodeError:
                print("❌ Invalid JSON received.")
            except Exception as e:
                print(f"❌ Error: {e}")
                break

def accept_connections():
    """Continuously accept new connections and start a thread for each."""
    while True:
        try:
            client, addr = server.accept()
            print(f"✅ Connection from {addr}")
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except BlockingIOError:
            time.sleep(0.1)
            continue

def calculate_logic():
    """Calculates brightness values based on received ESP data."""
    while True:
        try:
            ESP1.get_output(channel_1_brightness, 0)
            ESP2.get_output(channel_3_brightness, 0)
            # (Additional logic for other ESPs can be enabled as needed)
            time.sleep(0.1)  # Prevent excessive CPU usage
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
        time.sleep(0.1)
except KeyboardInterrupt:
    print("🔚 Shutting down server...")