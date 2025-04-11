import socket
import time

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(255):
    payload = bytes([i])
    udp_sock.sendto(payload, ("192.168.4.3", 1234))
    time.sleep(0.01)

udp_sock.close()