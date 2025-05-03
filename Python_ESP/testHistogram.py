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

# --------------------- Font Setup ---------------------
minion_path = '/Users/emmasokoll/Library/Fonts/MinionPro-Regular.otf'
fm.fontManager.addfont(minion_path)
minion_prop = fm.FontProperties(fname=minion_path)
plt.rcParams.update({
    'font.family': minion_prop.get_name(),
    'mathtext.fontset': 'custom',
    'mathtext.rm': minion_prop.get_name(),
})

# --------------------- Global Variables ---------------------
measured_state = None
stop_event = None  # This will be set when calling GUI_loop()

latest_probs = None
latest_output_states = None
latest_channel_probs = None
quantum_lock = threading.Lock()

# --------------------- Experiment Setup ---------------------
num_channels = 4
num_photons = 3
input_state = [1, 1, 1, 0]
exp_setup = ExperimentalSetupGUIReal(num_output_channels=num_channels, num_photons=num_photons)

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
        if (mode + 1) == 1:
            continue
        if (mode + 1) % 2 == (0 if apply_even else 1):
            rotation_targets.append((layer, mode))
num_rotation_gates = len(rotation_targets)

# --------------------- Sliders and State Variables ---------------------
black = (0, 0, 0)
gray = (200, 200, 200)

slider_width = 300
slider_scale_bs = 1
slider_scale_rgate = 1
gate_values_theta = [0] * num_bs_gates
rotation_gate_angles = [0] * num_rotation_gates

sampling_interval = 2
last_sample_time = time.time()
flash_alpha = 0
fade_speed = 20
random_noise_value = 0

initial_probs, initial_output_states, initial_channel_probs = exp_setup.run_experiment(
    input_state, gate_values=[(0, 0)] * num_bs_gates
)

output_states = [list(state) for state in initial_output_states]

state_counts = defaultdict(int)
for state in output_states:
    state_counts[tuple(state)] = 0

probs = initial_probs  # you forgot this too
is_fullscreen = False

# --------------------- Helper Functions ---------------------
def send_histogram_data(histogram_data, measured_state):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("127.0.0.1", 9999)
    data = {"histogram_data": histogram_data, "measured_state": measured_state}
    json_data = json.dumps(data)
    client_socket.sendto(json_data.encode("utf-8"), server_address)

def sample_state(probs, states):
    if len(probs) > 0 and np.any(probs):
        return np.random.choice(len(states), p=probs)
    return None

def draw_slider(screen, x, y, value, max_value, label, width=500, display_scale=1.0, font=None):
    pygame.draw.rect(screen, gray, (x, y, width, 10))
    knob_x = x + (value * display_scale / max_value) * width
    pygame.draw.circle(screen, black, (int(knob_x), y + 5), 8)
    if font:
        display_value = value * display_scale
        label_surface = font.render(f"{label}: {display_value:.2f}", True, black)
        screen.blit(label_surface, (x, y - 25))

def quantum_worker(ESP_MAP):
    global latest_probs, latest_output_states, latest_channel_probs

    while not stop_event.is_set():
        # Read ESP values
        gate_values_theta_local = gate_values_theta.copy()
        rotation_gate_angles_local = rotation_gate_angles.copy()

        if 1 in ESP_MAP and ESP_MAP[1].pot_value is not None:
            gate_values_theta_local[0] = np.interp(ESP_MAP[1].pot_value, [0, 4095], [0, np.pi / 2])
        if 2 in ESP_MAP and ESP_MAP[2].pot_value is not None:
            gate_values_theta_local[1] = np.interp(ESP_MAP[2].pot_value, [0, 4095], [0, np.pi / 2])
        if 3 in ESP_MAP:
            if ESP_MAP[3].pot_value is not None:
                gate_values_theta_local[2] = np.interp(ESP_MAP[3].pot_value, [0, 4095], [0, np.pi / 2])
            if ESP_MAP[3].pot_value_ps_1 is not None:
                rotation_gate_angles_local[0] = np.interp(ESP_MAP[3].pot_value_ps_1, [0, 4095], [0, np.pi])
        if 4 in ESP_MAP:
            if ESP_MAP[4].pot_value is not None:
                gate_values_theta_local[3] = np.interp(ESP_MAP[4].pot_value, [0, 4095], [0, np.pi / 2])
            if ESP_MAP[4].pot_value_ps_1 is not None:
                rotation_gate_angles_local[1] = np.interp(ESP_MAP[4].pot_value_ps_1, [0, 4095], [0, np.pi])
            if ESP_MAP[4].pot_value_ps_2 is not None:
                rotation_gate_angles_local[2] = np.interp(ESP_MAP[4].pot_value_ps_2, [0, 4095], [0, np.pi])
        if 5 in ESP_MAP and ESP_MAP[5].pot_value is not None:
            gate_values_theta_local[4] = np.interp(ESP_MAP[5].pot_value, [0, 4095], [0, np.pi / 2])
        if 6 in ESP_MAP and ESP_MAP[6].pot_value is not None:
            gate_values_theta_local[5] = np.interp(ESP_MAP[6].pot_value, [0, 4095], [0, np.pi / 2])

        gate_values = [(theta, 0) for theta in gate_values_theta_local]

        try:
            # Compute new simulation
            probs_local, output_states_raw, channel_probs_local = exp_setup.run_experiment(
                input_state,
                gate_values=gate_values,
                rotation_gate_angles=rotation_gate_angles_local
            )

            # Save results thread-safely
            with quantum_lock:
                latest_probs = probs_local
                latest_output_states = output_states_raw
                latest_channel_probs = channel_probs_local

        except Exception as e:
            print(f"❌ quantum_worker error: {e}")

        time.sleep(0.3)  # Don't run continuously

def update_simulation(ESP_MAP):
    global last_sample_time, measured_state, flash_alpha, state_counts, random_noise_value, probs, channel_probs

    with quantum_lock:
        if latest_probs is None:
            return
        probs = latest_probs
        output_states_raw = latest_output_states
        channel_probs = latest_channel_probs

    now = time.time()
    if now - last_sample_time >= sampling_interval:
        state_index = sample_state(probs, output_states_raw)
        if state_index is not None:
            measured_state = list(output_states_raw[state_index])
            state_counts[tuple(measured_state)] += 1

        flash_alpha = 255
        counts = [state_counts[tuple(state)] for state in output_states]
        send_histogram_data(histogram_data=counts, measured_state=measured_state)
        random_noise_value = np.random.rand()

        last_sample_time = now

def draw_gui(screen, font, plot_mode, width, height, ESP_MAP):
    global flash_alpha

    screen.fill((255, 255, 255))  # Clear screen

    # --- First plot: Measurement Counts or Channel Probs ---
    plot_width, plot_height = int(width * 0.4), int(height * 0.4)
    fig1, ax1 = plt.subplots(figsize=(plot_width / 140, plot_height / 90))

    counts = [state_counts[tuple(state)] for state in output_states]

    if plot_mode == "histogram":
        ax1.bar(range(len(counts)), counts, color='blue')
        ax1.set_title("Measurement Counts Over Time", fontsize=15)
        ax1.set_xlabel("Output States")
        ax1.set_ylabel("Count")
        ax1.set_xticks(range(len(output_states)))
        ax1.set_xticklabels(output_states, rotation='vertical', fontsize=10, ha='center')  # <-- fix xticks
    else:
        all_channel_probs = list(channel_probs) + [random_noise_value]
        ax1.bar(range(num_channels + 1), all_channel_probs, color=['red'] * num_channels + ['gray'])
        ax1.set_title("Per-Channel Occupation Probabilities", fontsize=15)
        ax1.set_xlabel("Channel")
        ax1.set_ylabel("Probability")
        ax1.set_xticks(range(num_channels + 1))
        ax1.set_xticklabels([f"q[{i}]" for i in range(num_channels)] + ["Noise"], fontsize=10, ha='center')
        ax1.set_ylim(0, 1.1)

    plt.tight_layout()
    canvas1 = FigureCanvas(fig1)
    canvas1.draw()
    plot_surface1 = pygame.image.frombuffer(canvas1.buffer_rgba().tobytes(), canvas1.get_width_height(), "RGBA")
    screen.blit(plot_surface1, (width - plot_width - 310, 20))
    plt.close(fig1)

    # --- Second plot: Theoretical probabilities ---
    small_plot_width, small_plot_height = int(width * 0.2), int(height * 0.2)
    fig2, ax2 = plt.subplots(figsize=(small_plot_width / 100, small_plot_height / 70))
    ax2.bar(range(len(probs)), probs, color='green')
    ax2.set_ylim(0, 1)
    ax2.set_title("Theoretical Probability Distribution", fontsize=15)
    ax2.set_xticks(range(len(output_states)))
    ax2.set_xticklabels(output_states, rotation='vertical', fontsize=10, ha='center')  # <-- fix xticks

    plt.tight_layout()
    canvas2 = FigureCanvas(fig2)
    canvas2.draw()
    plot_surface2 = pygame.image.frombuffer(canvas2.buffer_rgba().tobytes(), canvas2.get_width_height(), "RGBA")
    screen.blit(plot_surface2, (20, height - small_plot_height - 400))
    plt.close(fig2)

    # --- Sliders ---
    for i, theta in enumerate(gate_values_theta):
        draw_slider(screen, 50, 50 + i * 70, theta, np.pi, f"BS θ {i + 1}", width=slider_width, display_scale=2, font=font)
    for i, angle in enumerate(rotation_gate_angles):
        draw_slider(screen, 380, 50 + i * 70, angle, np.pi, f"Rgate {i+1}", width=slider_width, font=font)

    # --- Measured State ---
    if measured_state is not None:
        state_text = font.render(f"Measured State: {measured_state}", True, (0,0,0))
        screen.blit(state_text, (width - 650, 950))
        if flash_alpha > 0:
            flash_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(flash_surface, (255, 0, 0, flash_alpha), (15, 20), 10)
            screen.blit(flash_surface, (width - 650 + 250, 950))
            flash_alpha = max(0, flash_alpha - fade_speed)


# --------------------- Main Loop ---------------------
def GUI_loop(screen, font, stop_event_arg, ESP_MAP, sampling_interval=2.0):
    global stop_event
    stop_event = stop_event_arg  # bind to module-global stop_event

    pygame.display.set_caption("Quantum Experiment GUI")

    # ✅ START THE QUANTUM THREAD HERE (just once!)
    quantum_thread = threading.Thread(target=quantum_worker, args=(ESP_MAP,), daemon=True)
    quantum_thread.start()

    width, height = screen.get_size()
    white = (255, 255, 255)

    running = True
    plot_mode = "histogram"
    clock = pygame.time.Clock()

    dragging_slider_bs = -1
    dragging_rotation_slider = -1

    while running:
        if stop_event.is_set():
            running = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                stop_event.set()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    stop_event.set()
                elif event.key == pygame.K_s:
                    plot_mode = "channel_probs" if plot_mode == "histogram" else "histogram"
                    print(f"Switched to {plot_mode}")

        update_simulation(ESP_MAP)
        draw_gui(screen, font, plot_mode, width, height, ESP_MAP)

        pygame.display.flip()
        clock.tick(24)  # 24 FPS for smoother updates

    pygame.quit()
    print("GUI thread stopped.")


def get_measured_state():
    return measured_state
