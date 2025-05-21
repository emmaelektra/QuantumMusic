import pygame
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from ExperimentalSetupGUIReal import ExperimentalSetupGUIReal
import time
from collections import defaultdict
import socket
import json
import matplotlib.font_manager as fm
import threading
import signal
import sys

def handle_sigterm(signum, frame):
    print("🛑 Received SIGTERM, shutting down histogramUDP.py")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

# --------------------- Font Setup ---------------------
"""
minion_path = '/Users/emmasokoll/Library/Fonts/MinionPro-Regular.otf'
fm.fontManager.addfont(minion_path)
minion_prop = fm.FontProperties(fname=minion_path)
plt.rcParams.update({
    'font.family': minion_prop.get_name(),
    'mathtext.fontset': 'custom',
    'mathtext.rm': minion_prop.get_name(),
})
"""
# --------------------- Pygame Setup ---------------------
pygame.init()
width, height = 1680, 1050
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Quantum Experiment GUI")
white = (255, 255, 255)
black = (0, 0, 0)
gray = (200, 200, 200)
font = pygame.font.SysFont("Arial",36)

# === Global Matplotlib setup for the big plot ===
big_plot_width, big_plot_height = int(width * 0.4), int(height * 0.4)
big_fig, big_ax = plt.subplots(figsize=(big_plot_width / 140, big_plot_height / 90))
big_canvas = FigureCanvas(big_fig)

# === Global Matplotlib setup for the small plot (if you still want it) ===
small_plot_width, small_plot_height = int(width * 0.2), int(height * 0.2)
small_fig, small_ax = plt.subplots(figsize=(small_plot_width / 100, small_plot_height / 70))
small_canvas = FigureCanvas(small_fig)


# --------------------- Experiment Setup ---------------------
num_channels = 4
num_photons = 2
input_state = [1, 0, 1, 0]
exp_setup = ExperimentalSetupGUIReal(num_output_channels=num_channels, num_photons=num_photons)

random_noise_value = 0

# Beam Splitter and Rotation setup
bs_connections = []
for layer in range(num_channels):
    start_index = layer % 2
    for i in range(start_index, num_channels - 1, 2):
        bs_connections.append((i, i + 1))
num_bs_gates = len(bs_connections)

rotation_targets = []
for layer in range(num_channels - 2):
    apply_even = (layer % 2 == 0)
    for mode in range(num_channels):
        channel_number = mode + 1
        if channel_number == 1:
            continue
        if (channel_number % 2 == 0 and apply_even) or (channel_number % 2 == 1 and not apply_even):
            rotation_targets.append((layer, mode))
num_rotation_gates = len(rotation_targets)

# --------------------- Slider Variables ---------------------
slider_width = 300  # Wider sliders for smoother control
slider_scale_bs = 1
slider_scale_rgate = 1
gate_values_theta = [0] * num_bs_gates
rotation_gate_angles = [0] * num_rotation_gates

sampling_flag = False
measured_state = None
flash_alpha = 0
fade_speed = 20
state_counts = defaultdict(int)

initial_probs, initial_output_states, initial_channel_probs = exp_setup.run_experiment(input_state, gate_values=[(0, 0)] * num_bs_gates)
output_states = [str(state) for state in initial_output_states]
for state in output_states:
    state_counts[state] = 0
probs = initial_probs

is_fullscreen = False
dragging_slider_bs = -1
dragging_rotation_slider = -1

# --- UDP Listener Setup ---
GUI_UDP_IP = "0.0.0.0"
GUI_UDP_PORT = 12345
latest_pot_values = [0] * 9  # You have 9 values from ESPs
pot_lock = threading.Lock()

def gui_udp_listener():
    global latest_pot_values, sampling_flag
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((GUI_UDP_IP, GUI_UDP_PORT))
    while True:
        data, addr = sock.recvfrom(1024)
        text = data.decode(errors="ignore").strip()
        # try parsing JSON first
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            msg = None

        if isinstance(msg, dict):
            if msg.get("sample"):
                sampling_flag = True
                # no need to update sampling_interval here
                continue

        # otherwise fall back to your old code:
        parts = text.split(",")
        if len(parts) == 9:
            values = list(map(int, parts))
            with pot_lock:
                latest_pot_values = values
        else:
            print(f"Warning: expected 9 pots, got {len(parts)}")


listener_thread = threading.Thread(target=gui_udp_listener, daemon=True)
listener_thread.start()

# Variable to track which slider is being dragged (-1 means none)
dragging_slider_1 = -1
dragging_slider_2 = -1

# --------------------- Helper Functions ---------------------
def send_histogram_data(histogram_data, measured_state):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("127.0.0.1", 9999)
    data = {"histogram_data": histogram_data, "measured_state": measured_state}
    json_data = json.dumps(data)
    client_socket.sendto(json_data.encode("utf-8"), server_address)

    # NEW: Send measured_state to main.py
    measured_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    measured_server_address = ("127.0.0.1", 5678)  # New port for measured_state
    measured_state_str = ",".join(map(str, measured_state))
    measured_socket.sendto(measured_state_str.encode("utf-8"), measured_server_address)


def sample_state(probs, states):
    if len(probs) > 0 and np.any(probs):
        return np.random.choice(len(states), p=probs)
    return None

def draw_slider(x, y, value, max_value, label, width=500, display_scale=1.0):
    pygame.draw.rect(screen, gray, (x, y, width, 10))

    # Calculate the position of the knob
    knob_x = x + (value * display_scale / max_value) * width
    pygame.draw.circle(screen, black, (int(knob_x), y + 5), 8)

    # Calculate the label based on scaled display value
    display_value = value * display_scale
    label_surface = font.render(f"{label}: {display_value:.2f}", True, black)
    screen.blit(label_surface, (x, y - 25))

def update_plots():
    global last_sample_time, measured_state, flash_alpha, state_counts, probs, sampling_flag

    gate_values = [(gate_values_theta[i], 0) for i in range(num_bs_gates)]

    probs, output_states_raw, channel_probs = exp_setup.run_experiment(
        input_state,
        gate_values=gate_values,
        rotation_gate_angles=rotation_gate_angles
    )

    if sampling_flag:
        # do exactly one measurement
        state_index = sample_state(probs, output_states_raw)
        if state_index is not None:
            measured_state = output_states_raw[state_index]
            state_counts[str(measured_state)] += 1

        flash_alpha = 255
        counts = [state_counts[s] for s in output_states]
        send_histogram_data(histogram_data=counts,
                            measured_state=measured_state)

        sampling_flag = False  # reset until next cycle

    counts = [state_counts[state] for state in output_states]
    plot_width, plot_height = int(width * 0.4), int(height * 0.4)

    #fig, ax = plt.subplots(figsize=(plot_width / 140, plot_height / 90))
    big_ax.clear()
    if plot_mode == "histogram":
        big_ax.bar(range(len(counts)), counts, color='blue')
        big_ax.set_title(
            f"Measurement Counts Over Time\n{num_channels} channels, {num_photons} photons, input {input_state}",
            fontsize=15)
        big_ax.set_xlabel("Output States")
        big_ax.set_ylabel("Count")
        big_ax.set_xticks(range(len(output_states)))
        big_ax.set_xticklabels(output_states, rotation='vertical', fontsize=10, ha='center')
        big_fig.tight_layout(rect=[0, 0.05, 1, 1])

    else:  # plot_mode == "channel_probs"
        all_channel_probs = list(channel_probs) + [random_noise_value]
        big_ax.bar(range(num_channels + 1), all_channel_probs, color=['red'] * num_channels + ['gray'])
        big_ax.set_title(f"Per-Channel Occupation Probabilities", fontsize=15)
        big_ax.set_xlabel("Channel")
        big_ax.set_ylabel("Probability")
        big_ax.set_xticks(range(num_channels + 1))
        big_ax.set_xticklabels([f"q[{i}]" for i in range(num_channels)] + ["Noise"], fontsize=12, ha='center')
        big_ax.set_ylim(0, 1.1)  # Probabilities between 0 and 1 (plus a little headroom)

        plt.tight_layout()
    #canvas = FigureCanvas(fig)
    #canvas.draw()
    #plot_surface = pygame.image.frombuffer(canvas.buffer_rgba().tobytes(), canvas.get_width_height(), "RGBA")
    #screen.blit(plot_surface, (width - plot_width - 310, 20))
    #plt.close(fig)
    big_canvas.draw()
    buf = big_canvas.buffer_rgba()
    plot_surface = pygame.image.frombuffer(buf.tobytes(),
                                           big_canvas.get_width_height(),
                                           "RGBA")
    screen.blit(plot_surface, (width - big_plot_width - 310, 20))

    #small_plot_width, small_plot_height = int(width * 0.2), int(height * 0.2)
    #fig, ax = plt.subplots(figsize=(small_plot_width / 100, small_plot_height / 70))
    small_ax.clear()
    small_ax.bar(range(len(probs)), probs, color='green')
    small_ax.set_ylim(0, 1)
    small_ax.set_title("Theoretical Probability Distribution", fontsize=15)
    small_ax.set_xticks(range(len(output_states)))
    small_ax.set_xticklabels(output_states, rotation='vertical', fontsize=10, ha='center')
    plt.tight_layout()
    #canvas = FigureCanvas(fig)
    #canvas.draw()
    #small_plot_surface = pygame.image.frombuffer(canvas.buffer_rgba().tobytes(), canvas.get_width_height(), "RGBA")
    #screen.blit(small_plot_surface, (20, height - small_plot_height - 400))
    #plt.close(fig)
    small_canvas.draw()
    buf2 = small_canvas.buffer_rgba()
    small_surf = pygame.image.frombuffer(buf2.tobytes(),
                                       small_canvas.get_width_height(),
                                       "RGBA")
    screen.blit(small_surf, (20, height - small_plot_height - 400))

    if measured_state is not None:
        state_text = font.render(f"Measured State: {measured_state}", True, black)
        text_x, text_y = width - 650, 970
        screen.blit(state_text, (text_x, text_y))

        if flash_alpha > 0:
            flash_x = text_x + state_text.get_width() + 13
            flash_y = text_y - 2
            flash_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(flash_surface, (255, 0, 0, flash_alpha), (15, 20), 10)
            screen.blit(flash_surface, (flash_x, flash_y))
            flash_alpha = max(0, flash_alpha - fade_speed)

# --------------------- Main Loop ---------------------
running = True
plot_mode = "histogram"  # or "channel_probs"
if __name__ == "__main__":
    clock = pygame.time.Clock()

    while running:
        dt = clock.tick(30)  # limit to 60 FPS (dt in ms)
        # … your loop …
        screen.fill(white)

        # --- ADD this section to read the pots and update sliders ---
        # Read latest pots
        with pot_lock:
            current_pots = latest_pot_values.copy()

        pot_scale_factor = 4095  # or 1023 depending on ADC resolution
        # Smoothing factor between 0 (very slow) and 1 (instant)

        # Smooth 6 beam splitter sliders
        for i in range(min(len(gate_values_theta), 6)):
            gate_values_theta[i] = np.clip((current_pots[i] / pot_scale_factor) * (np.pi / 2), 0, np.pi / 2)
        for i in range(min(len(rotation_gate_angles), 3)):
            rotation_gate_angles[i] = np.clip((current_pots[i + 6] / pot_scale_factor) * (np.pi), 0, np.pi)

        y_offset = 50

        for i, theta in enumerate(gate_values_theta):
            draw_slider(50, 50 + i * 70, theta, np.pi, f"BS θ {i + 1}", width=slider_width, display_scale=2)

        for i, angle in enumerate(rotation_gate_angles):
            draw_slider(380, 50 + i * 70, angle, np.pi, f"Rgate {i+1}", width=slider_width)


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if a slider is clicked and start dragging it
                for i in range(num_bs_gates):
                    if 50 <= event.pos[0] <= 350 and 50 + i * 70 - 10 <= event.pos[1] <= 50 + i * 70 + 10:
                        dragging_slider_1 = i  # Start dragging this slider for param 1
                    if 400 <= event.pos[0] <= 700 and 50 + i * 70 - 10 <= event.pos[1] <= 50 + i * 70 + 10:
                        dragging_slider_2 = i  # Start dragging this slider for param 2
            elif event.type == pygame.MOUSEBUTTONUP:
                # Stop dragging when the mouse button is released
                dragging_slider_1 = -1
                dragging_slider_2 = -1
            elif event.type == pygame.MOUSEMOTION:
                # Update the slider value while dragging
                if dragging_slider_1 != -1:
                    x = max(50, min(350, event.pos[0]))  # Keep the knob within the slider range
                    gate_values_theta[dragging_slider_1] = (x - 50) / 300 * np.pi / 2
                if dragging_slider_2 != -1:
                    x = max(400, min(700, event.pos[0]))  # Keep the knob within the slider range
                    gate_values_theta[dragging_slider_2] = (x - 400) / 300 * np.pi / 2
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
                        width, height = screen.get_size()
                    else:
                        screen = pygame.display.set_mode((1680, 1050))
                        width, height = screen.get_size()
                if event.key == pygame.K_s:
                    if plot_mode == "histogram":
                        plot_mode = "channel_probs"
                    else:
                        plot_mode = "histogram"
                    print(f"Switched to {plot_mode}")

        update_plots()
        pygame.display.flip()

    pygame.quit()
print("✅ histogramUDP.py is exiting cleanly")