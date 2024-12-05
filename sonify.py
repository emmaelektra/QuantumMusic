from pythonosc import udp_client
import socket
import json
import numpy as np

# Set up the OSC client for SuperCollider
client = udp_client.SimpleUDPClient("127.0.0.1", 57120)  # SuperCollider's default port
# Initialize histogram data

harmonic_ratios = [1, 1.5, 2, 3, 4.5, 6, 8, 9, 9.5, 10, 11, 12.5, 14, 16, 17]  # Ratios for harmonic intervals

# Function to send drone data to SuperCollider
def send_drone_to_supercollider(histogram_data, measured_state, base_freq=30, max_amplitude=1):
    num_bins = 16  # Maximum number of bins
    histogram_data = histogram_data[:num_bins]  # Limit data to max bins
    freqs = [base_freq + i * 20 for i in range(len(histogram_data))]  # Frequencies for bins

    # Apply logarithmic scaling
    log_scaled_amplitudes = [np.log1p(amp) for amp in histogram_data]  # log1p(amp) = log(1 + amp)

    # Normalize amplitudes dynamically to ensure the sum does not exceed max_amplitude
    total_scaled = sum(log_scaled_amplitudes)
    if total_scaled > max_amplitude:
        normalized_amplitudes = [amp * (max_amplitude / total_scaled) for amp in log_scaled_amplitudes]
    else:
        normalized_amplitudes = log_scaled_amplitudes

    # Send frequencies, amplitudes, and total amplitude to SuperCollider
    client.send_message("/drone", freqs + normalized_amplitudes)

    # Send the measured state as a separate OSC message
    client.send_message("/measured_state", measured_state)

# Set up a server to receive histogram data
def receive_data_from_test_script():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("127.0.0.1", 9999))  # Bind to local host and port

    print("Listening for data...")
    while True:
        data, _ = server_socket.recvfrom(1024)  # Buffer size is 1024 bytes
        parsed_data = json.loads(data.decode("utf-8"))  # Decode and parse the JSON data

        histogram_data = parsed_data.get("histogram_data", [])
        measured_state = parsed_data.get("measured_state", [])

        print("Received histogram data:", histogram_data)
        print("Received measured state:", measured_state)

        send_drone_to_supercollider(histogram_data, measured_state)  # Send to SuperCollider


histogram_data = [0] * 16  # Start with all bins at zero
measured_state = [0] * 4  # Start with all bins at zero
send_drone_to_supercollider(histogram_data, measured_state)  # Send initial silent state
# Start the listener
if __name__ == "__main__":
    receive_data_from_test_script()
