from ESP32Class import ESPLED
import socket
import json
import threading
import time

PORT = 80

channel_1_brightness = 77
channel_3_brightness = 77

# ✅ Define ESP instances explicitly
ESP1 = ESPLED("192.168.4.3", 1, 2000, 2000)
ESP2 = ESPLED("192.168.4.4", 2, 2000, 2000)
ESP3 = ESPLED("192.168.4.5", 3, 2000, 2000)
ESP4 = ESPLED("192.168.4.6", 4, 2000, 2000)
ESP5 = ESPLED("192.168.4.7", 5, 2000, 2000)
ESP6 = ESPLED("192.168.4.8", 6, 2000, 2000)

# Dictionary for quick lookup
ESP_MAP = {
    1: ESP1,
    2: ESP2,
    3: ESP3,
    4: ESP4,
    5: ESP5,
    6: ESP6
}

# Setup socket server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', PORT))
server.listen(10)  # Allow multiple ESPs to connect
server.setblocking(False)  # Enable non-blocking mode

print("✅ Waiting for ESP connections...")

def handle_client(client):
    """Handles a single client connection."""
    client.settimeout(0.5)  # Avoid blocking while receiving data
    with client:
        try:
            data = client.recv(1024).decode().strip()
            if not data:
                return

            message = json.loads(data)
            esp_id = message.get("esp_id")

            if esp_id in ESP_MAP:
                ESP = ESP_MAP[esp_id]
                ESP.pot_value = message["pot_value"]

                # Handle phase values for ESP 3 and ESP 4
                if esp_id == 3:
                    ESP.pot_value_ps_1 = message.get("phase_value1", 0)
                elif esp_id == 4:
                    ESP.pot_value_ps_1 = message.get("phase_value1", 0)
                    ESP.pot_value_ps_2 = message.get("phase_value2", 0)

                print(f"📩 Received data from ESP {esp_id}: {message}")

                # ✅ Send response data back to the ESP
                response_json = json.dumps(ESP.response_data)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(0.01)  # Lower timeout to reduce lag
                        sock.connect((ESP.ip, PORT))
                        sock.sendall(response_json.encode())
                except:
                    pass  # Silently ignore connection failures

        except json.JSONDecodeError:
            print("❌ Invalid JSON received.")
        except socket.timeout:
            print("⚠️ Timeout while receiving data.")

def accept_connections():
    """Accepts multiple client connections in parallel."""
    while True:
        try:
            client, _ = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except BlockingIOError:
            continue  # No new connections, keep looping

def calculate_logic():
    """Calculates brightness values based on received ESP data."""
    while True:
        try:
            ESP1.get_output(channel_1_brightness, 0)
            print("ESP brightness 1:", ESP1.output_brightness_1, "ESP brightness 2:", ESP1.output_brightness_2)
            """
            ESP2.get_output(channel_3_brightness, 0)
            ESP3.get_output(ESP1.output_brightness_2, ESP2.output_brightness_1)
            ESP4.get_output(ESP1.output_brightness_1, ESP3.output_brightness_1)
            ESP5.get_output(ESP3.output_brightness_2, ESP2.output_brightness_2)
            ESP6.get_output(ESP4.output_brightness_2, ESP5.output_brightness_1)
            """
            time.sleep(0.05)  # Prevent excessive CPU usage
        except Exception as e:
            print(f"❌ Error in logic calculation: {e}")

# Start both tasks as separate threads
thread1 = threading.Thread(target=accept_connections, daemon=True)
thread2 = threading.Thread(target=calculate_logic, daemon=True)

thread1.start()
thread2.start()

# Keep the main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down server...")
