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
from pythonosc import udp_client

# --------------------- Font Setup ---------------------
minion_path = '/Users/emmasokoll/Library/Fonts/MinionPro-Regular.otf'
fm.fontManager.addfont(minion_path)
minion_prop = fm.FontProperties(fname=minion_path)
plt.rcParams.update({
    'font.family': minion_prop.get_name(),
    'mathtext.fontset': 'custom',
    'mathtext.rm': minion_prop.get_name(),
})

# --------------------- Pygame Setup ---------------------
pygame.init()
width, height = 1680, 1050
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Quantum Experiment GUI")
white = (255, 255, 255)
black = (0, 0, 0)
gray = (200, 200, 200)
font = pygame.font.Font(minion_path, 36)

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

sampling_interval = 2
last_sample_time = time.time()
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

# --------------------- Helper Functions ---------------------
client = udp_client.SimpleUDPClient("127.0.0.1", 8888)
def send_histogram_data(histogram_data, current_channel_probs, measured_state):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("127.0.0.1", 9999)

    probs_list = current_channel_probs.tolist()

    data = {
        "histogram_data": histogram_data,
        "current_channel_probs": probs_list,
        "measured_state": measured_state
    }

    # now this will succeed
    json_data = json.dumps(data)
    client_socket.sendto(json_data.encode("utf-8"), server_address)

    client.send_message("/histogram_data",        histogram_data)
    client.send_message("/current_channel_probs", current_channel_probs.tolist())
    client.send_message("/measured_state",        measured_state)

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

current_channel_probs = []
def update_plots():
    global last_sample_time, measured_state, flash_alpha, state_counts, probs, current_channel_probs

    gate_values = [(gate_values_theta[i], 0) for i in range(num_bs_gates)]

    probs, output_states_raw, channel_probs = exp_setup.run_experiment(
        input_state,
        gate_values=gate_values,
        rotation_gate_angles=rotation_gate_angles
    )
    if time.time() - last_sample_time >= sampling_interval:
        state_index = sample_state(probs, output_states_raw)
        if state_index is not None:
            measured_state = str(output_states_raw[state_index])
            state_counts[measured_state] += 1
        flash_alpha = 255
        counts = [state_counts[state] for state in output_states]
        current_channel_probs = channel_probs
        send_histogram_data(histogram_data=counts, current_channel_probs = current_channel_probs, measured_state=measured_state)

        global random_noise_value
        random_noise_value = np.random.rand()  # Random value between 0 and 1

        last_sample_time = time.time()

    counts = [state_counts[state] for state in output_states]
    plot_width, plot_height = int(width * 0.4), int(height * 0.4)

    fig, ax = plt.subplots(figsize=(plot_width / 140, plot_height / 90))

    if plot_mode == "histogram":
        ax.bar(range(len(counts)), counts, color='blue')
        ax.set_title(
            f"Measurement Counts Over Time\n{num_channels} channels, {num_photons} photons, input {input_state}",
            fontsize=15)
        ax.set_xlabel("Output States")
        ax.set_ylabel("Count")
        ax.set_xticks(range(len(output_states)))
        ax.set_xticklabels(output_states, rotation='vertical', fontsize=10, ha='center')
    else:  # plot_mode == "channel_probs"
        all_channel_probs = list(current_channel_probs) + [random_noise_value]
        ax.bar(range(num_channels + 1), all_channel_probs, color=['red'] * num_channels + ['gray'])
        ax.set_title(f"Per-Channel Occupation Probabilities", fontsize=15)
        ax.set_xlabel("Channel")
        ax.set_ylabel("Probability")
        ax.set_xticks(range(num_channels + 1))
        ax.set_xticklabels([f"q[{i}]" for i in range(num_channels)] + ["Noise"], fontsize=12, ha='center')
        ax.set_ylim(0, 1.1)  # Probabilities between 0 and 1 (plus a little headroom)

    plt.tight_layout()
    canvas = FigureCanvas(fig)
    canvas.draw()
    plot_surface = pygame.image.frombuffer(canvas.buffer_rgba().tobytes(), canvas.get_width_height(), "RGBA")
    screen.blit(plot_surface, (width - plot_width - 310, 20))
    plt.close(fig)

    small_plot_width, small_plot_height = int(width * 0.2), int(height * 0.2)
    fig, ax = plt.subplots(figsize=(small_plot_width / 100, small_plot_height / 70))
    ax.bar(range(len(probs)), probs, color='green')
    ax.set_ylim(0, 1)
    ax.set_title("Theoretical Probability Distribution", fontsize=15)
    ax.set_xticks(range(len(output_states)))
    ax.set_xticklabels(output_states, rotation='vertical', fontsize=10, ha='center')
    plt.tight_layout()
    canvas = FigureCanvas(fig)
    canvas.draw()
    small_plot_surface = pygame.image.frombuffer(canvas.buffer_rgba().tobytes(), canvas.get_width_height(), "RGBA")
    screen.blit(small_plot_surface, (20, height - small_plot_height - 400))
    plt.close(fig)

    if measured_state is not None:
        state_text = font.render(f"Measured State: {measured_state}", True, black)
        text_x, text_y = width - 650, 950
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
while running:
    screen.fill(white)

    y_offset = 50

    for i, theta in enumerate(gate_values_theta):
        draw_slider(50, 50 + i * 70, theta, np.pi, f"BS θ {i + 1}", width=slider_width, display_scale=2)

    for i, angle in enumerate(rotation_gate_angles):
        draw_slider(380, 50 + i * 70, angle, np.pi, f"Rgate {i+1}", width=slider_width)


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for i in range(num_bs_gates):
                if 50 <= event.pos[0] <= 50 + slider_width and 50 + i * 70 - 10 <= event.pos[1] <= 50 + i * 70 + 10:
                    dragging_slider_bs = i
            for i in range(num_rotation_gates):
                if 380 <= event.pos[0] <= 380 + slider_width and 50 + i * 70 - 10 <= event.pos[1] <= 50 + i * 70 + 10:
                    dragging_rotation_slider = i
        elif event.type == pygame.MOUSEBUTTONUP:
            dragging_slider_bs = -1
            dragging_rotation_slider = -1
        elif event.type == pygame.MOUSEMOTION:
            if dragging_slider_bs != -1:
                x = max(50, min(50 + slider_width, event.pos[0]))
                theta = (x - 50) / (slider_width * slider_scale_bs) * (np.pi / 2)
                theta = min(max(theta, 0), np.pi / 2)
                gate_values_theta[dragging_slider_bs] = theta
            if dragging_rotation_slider != -1:
                x = max(380, min(380 + slider_width, event.pos[0]))
                angle = (x - 380) / (slider_width * slider_scale_rgate) * (np.pi)
                angle = min(max(angle, 0), np.pi)
                rotation_gate_angles[dragging_rotation_slider] = angle
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
