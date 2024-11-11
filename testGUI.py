import pygame
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from ExperimentalSetupGUI import ExperimentalSetupGUI
import time

# Initialize pygame
pygame.init()

# Set up the display with larger dimensions
width, height = 1680, 1050  # Starting dimensions for windowed mode
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Quantum Experiment GUI with Pygame")

# Colors and fonts
white = (255, 255, 255)
black = (0, 0, 0)
gray = (200, 200, 200)
font = pygame.font.Font(None, 36)

# Initialize your experimental setup with the number of channels (m)
num_channels = 4  # Change this as needed for testing
num_photons = 2
exp_setup = ExperimentalSetupGUI(num_output_channels=num_channels, num_photons=num_photons)

# Initial slider values for gate parameters
num_gates = num_channels * (num_channels - 1) // 2  # Corresponds to the logic for m layers
gate_values_1 = [0] * num_gates  # First parameter for each gate
gate_values_2 = [0] * num_gates  # Second parameter for each gate

# Sampling interval in seconds
sampling_interval = 3
last_sample_time = time.time()
# Initialize global variables for measured state and flash effect
measured_state = None
flash_alpha = 0  # Transparency level for flash effect (0 is fully transparent)
fade_speed = 20  # How quickly the flash fades out (higher means faster fade)



# Function to sample a state based on the probability distribution
# Function to sample a state based on the probability distribution
def sample_state(probs, states):
    if len(probs) > 0 and np.any(probs):  # Check if probs is non-empty and contains non-zero elements
        return np.random.choice(len(states), p=probs)
    return None

# Function to draw a slider
def draw_slider(x, y, value, max_value, label):
    pygame.draw.rect(screen, gray, (x, y, 300, 10))  # Increase width for better visibility
    knob_x = x + (value / max_value) * 300  # Match width of slider
    pygame.draw.circle(screen, black, (int(knob_x), y + 5), 8)
    label_surface = font.render(f"{label}: {value:.2f}", True, black)
    screen.blit(label_surface, (x, y - 25))


# Function to update and display the plot
def update_plot():
    global last_sample_time, measured_state, flash_alpha

    # Combine slider values into gate tuples
    gate_values = [(gate_values_1[i], gate_values_2[i]) for i in range(num_gates)]

    # Run the experiment and get probabilities and output states
    probs, output_states = exp_setup.run_experiment([0, 0, 1, 1], gate_values=gate_values)

    # Normalize probabilities to sum to 1
    if sum(probs) > 0:
        probs = np.array(probs) / sum(probs)

    # Sample a state every 3 seconds
    if time.time() - last_sample_time >= sampling_interval:
        state_index = sample_state(probs, output_states)
        if state_index is not None:
            measured_state = output_states[state_index]  # Get the sampled state
            flash_alpha = 255  # Set flash effect to fully opaque on new measurement
        last_sample_time = time.time()

    # Check if there are valid probabilities and output states
    if len(probs) == 0 or len(output_states) == 0:
        print("No valid data to plot.")
        return

    # Ensure that the number of probabilities matches the number of output states
    if len(probs) != len(output_states):
        print(f"Warning: Mismatch in length. Trimming probabilities from {len(probs)} to {len(output_states)}.")
        probs = probs[:len(output_states)]

    # Convert output states to strings for proper display
    output_states_str = [str(state) for state in output_states]

    # Calculate plot size based on the screen width and height
    plot_width, plot_height = int(width * 0.4), int(height * 0.4)

    # Create a plot
    fig, ax = plt.subplots(figsize=(plot_width / 140, plot_height / 90))  # Scale figure size to screen size
    ax.bar(range(len(probs)), probs)
    ax.set_title("Probabilities of Output States \n channels = %i, photons = %i" % (num_channels, num_photons))
    ax.set_xlabel("Output States")
    ax.set_ylabel("Probability")

    # Set x-axis labels to the output states
    ax.set_xticks(range(len(output_states)))
    ax.set_xticklabels(output_states_str, rotation='vertical', fontsize=7,
                       ha='center')  # Rotate and align for better readability

    # Adjust plot layout to ensure labels are fully shown
    plt.tight_layout()

    # Render the plot onto the pygame surface
    canvas = FigureCanvas(fig)
    canvas.draw()
    plot_surface = pygame.image.frombuffer(canvas.buffer_rgba().tobytes(), canvas.get_width_height(), "RGBA")
    screen.blit(plot_surface, (width - plot_width - 310, 20))  # Position plot based on screen width
    plt.close(fig)

    # Draw the measured state on the Pygame screen
    if measured_state is not None:
        state_text = font.render(f"Measured State: {measured_state}", True, black)
        text_x, text_y = width - 420, 155  # Define text position
        screen.blit(state_text, (text_x, text_y))

        # Flash symbol as a circle next to the measured state text with fading effect
        if flash_alpha > 0:
            flash_x = text_x + state_text.get_width() + 13  # Offset to the right of the text
            flash_y = text_y - 2  # Align vertically with the text

            # Draw a circular flash symbol with current alpha level
            flash_surface = pygame.Surface((30, 30), pygame.SRCALPHA)  # 30x30 area for the circle
            pygame.draw.circle(flash_surface, (255, 0, 0, flash_alpha), (15, 15), 10)  # Draw circle in the center
            screen.blit(flash_surface, (flash_x, flash_y))  # Position next to text

            flash_alpha = max(0, flash_alpha - fade_speed)  # Decrease alpha to create fade-out effect



# Variable to track if fullscreen is active
is_fullscreen = False

# Variable to track which slider is being dragged (-1 means none)
dragging_slider_1 = -1
dragging_slider_2 = -1

# Main loop
running = True
while running:
    screen.fill(white)

    # Draw sliders for the first parameter of each gate
    for i, value in enumerate(gate_values_1):
        draw_slider(50, 50 + i * 70, value, 2 * np.pi, f"Gate {i + 1} - theta")

    # Draw sliders for the second parameter of each gate
    for i, value in enumerate(gate_values_2):
        draw_slider(400, 50 + i * 70, value, 2 * np.pi, f"Gate {i + 1} - phi")

    # Check for events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if a slider is clicked and start dragging it
            for i in range(num_gates):
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
                gate_values_1[dragging_slider_1] = (x - 50) / 300 * 2 * np.pi
            if dragging_slider_2 != -1:
                x = max(400, min(700, event.pos[0]))  # Keep the knob within the slider range
                gate_values_2[dragging_slider_2] = (x - 400) / 300 * 2 * np.pi
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:  # Press 'F' to toggle fullscreen
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
                    width, height = screen.get_size()  # Update width and height
                else:
                    screen = pygame.display.set_mode((1680, 1050))
                    width, height = screen.get_size()  # Reset width and height

    # Update and display the plot
    update_plot()

    # Update the display
    pygame.display.flip()

# Quit pygame
pygame.quit()
