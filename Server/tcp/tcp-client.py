import socket
import numpy as np
import pickle
import threading
import time
import signal
import sys
from cryptography.fernet import Fernet
import os


# Load encryption key
folder = r'/Users/emmasokoll/Documents/MasterArbeitGit/QuantumMusic/Server/tcp'
with open(os.path.join(folder,"secret.key"), "rb") as key_file:
    secret_key = key_file.read()
cipher = Fernet(secret_key)

VPS_IP = "217.154.69.166"  # Replace with your actual VPS IP
PORT = 443
stop_event = threading.Event()

def encrypt_data(data):
    return cipher.encrypt(pickle.dumps(data))

def decrypt_data(data):
    return pickle.loads(cipher.decrypt(data))

def generate_matrix():
    return np.random.randint(1, 100, (12, 12))

def receive_numbers(sock):
    """Receives encrypted numbers from the VPS."""
    try:
        while not stop_event.is_set():
            sock.settimeout(1)  # Avoid blocking forever
            try:
                data = sock.recv(1024)
                if not data:
                    break
                number = decrypt_data(data)
                print(f"Received: {number}")
            except socket.timeout:
                continue
    except OSError:
        pass  # Socket closed, exit thread

def send_matrices(sock):
    """Sends encrypted matrices to the VPS."""
    try:
        while not stop_event.is_set():
            matrix = generate_matrix()
            sock.sendall(encrypt_data(matrix))
            print(f"Sent Matrix:\n{matrix}\n")
            time.sleep(5)
    except OSError:
        pass  # Socket closed, exit thread

def signal_handler(sig, frame):
    """Handles Ctrl+C for clean shutdown."""
    print("\nShutting down client...")
    stop_event.set()
    client_socket.close()  # Force recv() to fail
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def start_client():
    """Connects to VPS and starts concurrent send/receive."""
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((VPS_IP, PORT))
    print(f"Connected to VPS relay at {VPS_IP}:{PORT}")

    recv_thread = threading.Thread(target=receive_numbers, args=(client_socket,))
    send_thread = threading.Thread(target=send_matrices, args=(client_socket,))

    recv_thread.start()
    send_thread.start()

    try:
        recv_thread.join()
        send_thread.join()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    start_client()
