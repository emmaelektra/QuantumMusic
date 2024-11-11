import math
import numpy as np
import strawberryfields as sf
from strawberryfields.ops import *
import itertools
import random

class ExperimentalSetupGUI:
    def __init__(self, num_output_channels, num_photons, dim=-1):
        self.num_output_channels = num_output_channels
        self.num_photons = num_photons
        if dim == -1:
            self.dim = num_photons + 1
        else:
            self.dim = dim

    def get_all_possible_output_states_configurations(self):
        states = []
        # Iterate over possible numbers of lost photons (from 0 to num_photons)
        for lost_photons in range(self.num_photons + 1):
            remaining_photons = self.num_photons - lost_photons
            # Generate all possible distributions of remaining photons across the output channels
            for partition in itertools.product(range(remaining_photons + 1), repeat=self.num_output_channels):
                if sum(partition) == remaining_photons:  # Only include states with the correct total photon count
                    states.append(list(partition))
        return states

    def get_probability_of_output_states_configurations(self, experimental_probabilities, states):
        final_probabilities = []
        for state in states:
            try:
                # Compute the flat index for the current state
                index = np.ravel_multi_index(state, (self.dim,) * self.num_output_channels)
                final_probabilities.append(experimental_probabilities[index])
            except (IndexError, ValueError) as e:
                print(f"Warning: State {state} - {e}")
                final_probabilities.append(0)
        return final_probabilities

    def run_experiment(self, photon_placement, angle_first_rotation_gates=None, gate_values=None):
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

        print(f"photon_placement: {photon_placement}")
        print(f"angle_first_rotation_gates: {angle_first_rotation_gates}")
        print(f"gate_values {gate_values}")

        def simulate():
            try:
                with boson_sampling.context as q:
                    # Prepare the input Fock states
                    for i in range(self.num_output_channels):
                        if i < len(photon_placement) and photon_placement[i] == 1:
                            Fock(1) | q[i]
                        else:
                            Vac | q[i]

                    # Apply rotation gates
                    for i in range(min(len(angle_first_rotation_gates), len(q))):
                        Rgate(angle_first_rotation_gates[i]) | q[i]

                    # Apply beamsplitter gates to create connectivity
                    for i in range(len(q) - 1):
                        if i < len(gate_values):
                            gate_value = gate_values[i]
                            BSgate(gate_value[0], gate_value[1]) | (q[i], q[i + 1])

                    # Connect last mode to the first if needed
                    if len(q) > 1 and len(gate_values) > len(q) - 1:
                        BSgate(gate_values[-1][0], gate_values[-1][1]) | (q[-1], q[0])

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
            return [], []  # Return empty lists instead of None to prevent unpacking issues

        # Call the function to get output state configurations
        out_put_states_configurations = self.get_all_possible_output_states_configurations()
        probabilities = self.get_probability_of_output_states_configurations(simulation_probabilities,
                                                                        out_put_states_configurations)

        # Ensure probabilities and configurations have matching lengths
        if len(simulation_probabilities) != len(out_put_states_configurations):
            print("Warning: Probabilities and output state configurations have different lengths.")
            out_put_states_configurations = out_put_states_configurations[:len(simulation_probabilities)]

        return probabilities, out_put_states_configurations
