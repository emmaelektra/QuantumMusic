import pygame
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from ExperimentalSetupGUI import ExperimentalSetupGUI

# Initialize pygame
pygame.init()

# Set up the display with larger dimensions
width, height = 3000, 1600  # Increase the dimensions as needed
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Quantum Experiment GUI with Pygame")

# Colors and fonts
white = (255, 255, 255)
black = (0, 0, 0)
gray = (200, 200, 200)
font = pygame.font.Font(None, 36)

# Initialize your experimental setup with the number of channels (m)
num_channels = 4  # Change this as needed for testing
exp_setup = ExperimentalSetupGUI(num_output_channels=num_channels, num_photons=2)

# Initial slider values for gate parameters
num_gates = num_channels * (num_channels - 1) // 2  # Corresponds to the logic for m layers
gate_values_1 = [0] * num_gates  # First parameter for each gate
gate_values_2 = [0] * num_gates  # Second parameter for each gate


# Function to draw a slider
def draw_slider(x, y, value, max_value, label):
    pygame.draw.rect(screen, gray, (x, y, 300, 10))  # Increase width for better visibility
    knob_x = x + (value / max_value) * 300  # Match width of slider
    pygame.draw.circle(screen, black, (int(knob_x), y + 5), 8)
    label_surface = font.render(f"{label}: {value:.2f}", True, black)
    screen.blit(label_surface, (x, y - 25))


# Function to update and display the plot
def update_plot():
    # Combine both sets of slider values into gate tuples
    gate_values = [(gate_values_1[i], gate_values_2[i]) for i in range(num_gates)]

    # Run the experiment and get probabilities and output states
    probs, output_states = exp_setup.run_experiment([0, 0, 1, 1], gate_values=gate_values)
    print("len probs = ", len(probs))
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

    # Create a plot
    fig, ax = plt.subplots(figsize=(5.5, 4.5))  # Adjust figsize as needed
    ax.bar(range(len(probs)), probs)
    ax.set_title("Probabilities of Output States")
    ax.set_xlabel("Output States")
    ax.set_ylabel("Probability")

    # Set x-axis labels to the output states
    ax.set_xticks(range(len(output_states)))
    ax.set_xticklabels(output_states_str, rotation='vertical', fontsize=7, ha='center')  # Rotate and align for better readability

    # Adjust plot layout to ensure labels are fully shown
    plt.tight_layout()

    # Render the plot onto the pygame surface
    canvas = FigureCanvas(fig)
    canvas.draw()
    plot_surface = pygame.image.frombuffer(canvas.buffer_rgba().tobytes(), canvas.get_width_height(), "RGBA")
    screen.blit(plot_surface, (700, 0))  # Adjust position to fit in the window
    plt.close(fig)


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
        draw_slider(50, 50 + i * 70, value, 2 * np.pi, f"Gate {i + 1} - Param 1")

    # Draw sliders for the second parameter of each gate
    for i, value in enumerate(gate_values_2):
        draw_slider(400, 50 + i * 70, value, 2 * np.pi, f"Gate {i + 1} - Param 2")

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

    # Update and display the plot
    update_plot()

    # Update the display
    pygame.display.flip()

# Quit pygame
pygame.quit()



