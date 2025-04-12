import socket

# Configuration
UDP_PORT = 1234  # Must match ESP32 sending port
BUFFER_SIZE = 1024

# Create and bind the UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind(("0.0.0.0", UDP_PORT))  # Listen on all interfaces

print(f"✅ Listening for UDP packets on port {UDP_PORT}...")

try:
    while True:
        data, addr = udp_socket.recvfrom(BUFFER_SIZE)
        message = data.decode().strip()
        sender_ip = addr[0]
        print(f"📡 Received from {sender_ip}: {message}")

except KeyboardInterrupt:
    print("\n🛑 UDP listener stopped.")
    udp_socket.close()
