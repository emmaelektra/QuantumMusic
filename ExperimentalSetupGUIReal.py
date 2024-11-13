import math
import numpy as np
import strawberryfields as sf
from strawberryfields.ops import *
import itertools
import random
from collections import defaultdict
import time


class ExperimentalSetupGUIReal:
    def __init__(self, num_output_channels, num_photons, dim=-1, efficiency=0.85, update_interval=3):
        self.num_output_channels = num_output_channels
        self.num_photons = num_photons
        self.efficiency = efficiency  # Efficiency of the system
        self.update_interval = update_interval  # Interval in seconds between experiments
        self.last_run_time = time.time() - update_interval  # Initialize to allow immediate first run
        self.cached_probabilities = []
        self.cached_states = []
        self.cached_measured_state = None
        if dim == -1:
            self.dim = num_photons + 1
        else:
            self.dim = dim

    def get_all_possible_output_states_configurations(self):
        states = []
        for lost_photons in range(self.num_photons + 1):
            remaining_photons = self.num_photons - lost_photons
            for partition in itertools.product(range(remaining_photons + 1), repeat=self.num_output_channels):
                if sum(partition) == remaining_photons:
                    states.append(list(partition))
        return states

    def reduce_state(self, state):
        """Reduce a state to a configuration where each channel has at most one photon."""
        return tuple(min(1, photon_count) for photon_count in state)

    def get_probability_of_output_states_configurations(self, experimental_probabilities, states):
        reduced_probabilities = defaultdict(float)

        for state in states:
            try:
                index = np.ravel_multi_index(state, (self.dim,) * self.num_output_channels)
                probability = experimental_probabilities[index]

                # Reduce state to indistinguishable form and accumulate probability
                reduced_state = self.reduce_state(state)
                reduced_probabilities[reduced_state] += probability

            except (IndexError, ValueError) as e:
                print(f"Warning: State {state} - {e}")

        final_states = list(reduced_probabilities.keys())
        final_probabilities = list(reduced_probabilities.values())

        return final_probabilities, final_states

    def apply_efficiency(self, photon_placement):
        """Apply the system efficiency by probabilistically removing photons from the placement."""
        adjusted_photon_placement = []
        for photon in photon_placement:
            if photon == 1 and random.random() > self.efficiency:
                adjusted_photon_placement.append(0)
            else:
                adjusted_photon_placement.append(photon)
        return adjusted_photon_placement

    def sample_state(self, probabilities, states):
        """Sample a state based on the reduced probability distribution."""
        if len(probabilities) > 0 and np.any(probabilities):
            index = np.random.choice(len(states), p=probabilities)
            return states[index]
        return None

    def run_experiment(self, photon_placement, angle_first_rotation_gates=None, gate_values=None):
        # Check if enough time has passed to run the experiment
        current_time = time.time()
        if current_time - self.last_run_time < self.update_interval:
            # Return cached probabilities, states, and measured state without recalculating
            return self.cached_probabilities, self.cached_states, self.cached_measured_state

        # Update last run time
        self.last_run_time = current_time

        # Apply efficiency to initial photon placement
        photon_placement = self.apply_efficiency(photon_placement)

        # Create a new Program instance for each run
        boson_sampling = sf.Program(self.num_output_channels)

        def calculate_number_of_gates(n):
            return math.floor(n * n / 2)

        # Generate random gate values if not provided
        if angle_first_rotation_gates is None:
            angle_first_rotation_gates = [random.uniform(0, 2 * np.pi) for _ in range(len(photon_placement))]
        if gate_values is None:
            gate_values = [(random.uniform(0, 2 * np.pi), random.uniform(0, 2 * np.pi))
                           for _ in range(calculate_number_of_gates(len(photon_placement)))]

        print(f"photon_placement (after efficiency): {photon_placement}")
        print(f"angle_first_rotation_gates: {angle_first_rotation_gates}")
        print(f"gate_values {gate_values}")

        def simulate():
            try:
                with boson_sampling.context as q:
                    # Prepare the input Fock states
                    for i in range(self.num_output_channels):
                        if i < len(photon_placement) and photon_placement[i] == 1:
                            Fock(1) | q[i]
                            print(f"fock state {i}")
                        else:
                            Vac | q[i]
                            print(f"empty state {i}")

                    # Apply rotation gates
                    for i in range(min(len(angle_first_rotation_gates), len(q))):
                        Rgate(angle_first_rotation_gates[i]) | q[i]

                    # Apply beamsplitter gates in m layers
                    for layer in range(self.num_output_channels):
                        start_index = layer % 2  # Alternate between starting at 0 and 1
                        for i in range(start_index, len(q) - 1, 2):
                            if len(gate_values) > 0:
                                gate_value = gate_values.pop(0)
                                BSgate(gate_value[0], gate_value[1]) | (q[i], q[i + 1])

                # Run the engine
                eng = sf.Engine(backend='fock', backend_options={'cutoff_dim': self.dim})
                results = eng.run(boson_sampling)

                fock_probs = results.state.all_fock_probs()

                # Flatten if needed
                if fock_probs.ndim > 1:
                    fock_probs = fock_probs.flatten()

                if fock_probs.size == 0 or np.all(fock_probs == 0):
                    print("Simulation returned an empty or zero-filled probability array.")
                    return None

                print(f"Simulation completed successfully. Probabilities length: {len(fock_probs)}")
                return fock_probs

            except Exception as e:
                print(f"Error during simulation: {e}")
                return None

        simulation_probabilities = simulate()
        if simulation_probabilities is None:
            print("Simulation failed or returned None. Returning placeholder values.")
            return [], [], None  # Return empty lists and None to indicate no measurement

        # Get all possible output state configurations
        output_states_configurations = self.get_all_possible_output_states_configurations()
        probabilities, final_states = self.get_probability_of_output_states_configurations(simulation_probabilities,
                                                                                           output_states_configurations)

        # Sample a state from the probabilities for measurement
        measured_state = self.sample_state(probabilities, final_states)

        # Cache results
        self.cached_probabilities = probabilities
        self.cached_states = final_states
        self.cached_measured_state = measured_state

        return probabilities, final_states, measured_state
