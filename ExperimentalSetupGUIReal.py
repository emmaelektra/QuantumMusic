import math
import numpy as np
import strawberryfields as sf
from strawberryfields.ops import *
import itertools
import random
from collections import defaultdict


class ExperimentalSetupGUIReal:
    def __init__(self, num_output_channels, num_photons, dim=-1):
        self.num_output_channels = num_output_channels
        self.num_photons = num_photons
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
                reduced_state = self.reduce_state(state)
                reduced_probabilities[reduced_state] += probability
            except (IndexError, ValueError) as e:
                print(f"Warning: State {state} - {e}")

        final_states = list(reduced_probabilities.keys())
        final_probabilities = list(reduced_probabilities.values())
        return final_probabilities, final_states

    def get_per_channel_probabilities(self, experimental_probabilities, states):
        """Sum probabilities for each channel having at least one photon."""
        per_channel_probs = np.zeros(self.num_output_channels)

        for state, prob in zip(states, experimental_probabilities):
            for mode in range(self.num_output_channels):
                if state[mode] > 0:  # If there is at least one photon in mode
                    per_channel_probs[mode] += prob

        return per_channel_probs

    def run_experiment(self, photon_placement, gate_values=None, rotation_gate_angles=None):
        boson_sampling = sf.Program(self.num_output_channels)

        def calculate_number_of_gates(n):
            return math.floor(n * n / 2)

        if gate_values is None:
            gate_values = [(random.uniform(0, np.pi), random.uniform(0, np.pi))
                           for _ in range(calculate_number_of_gates(len(photon_placement)))]

        #print(f"photon_placement: {photon_placement}")
        #print(f"gate_values: {gate_values}")

        def simulate():
            rotation_idx = 0
            try:
                with boson_sampling.context as q:
                    # Prepare the input Fock states
                    for i in range(self.num_output_channels):
                        if i < len(photon_placement) and photon_placement[i] == 1:
                            Fock(1) | q[i]
                            #print(f"Fock(1) | q[{i}]")
                        else:
                            Vac | q[i]
                            #print(f"Vac | q[{i}]")

                    num_layers = self.num_output_channels
                    for layer in range(num_layers):
                        start_index = layer % 2  # 0 or 1 for alternating layers
                        for i in range(start_index, len(q) - 1, 2):
                            if len(gate_values) > 0:
                                gate_value = gate_values.pop(0)
                                theta, phi = gate_value
                                BSgate(theta, phi) | (q[i], q[i + 1])
                                #print(f"BSgate({theta:.4f}, {phi:.4f}) | (q[{i}], q[{i + 1}])")

                        if layer == num_layers - 1:
                            #print("Last layer, no Rgates applied.")
                            break

                        if layer == num_layers - 2:
                            #print("No Rgates applied (between second-last and last layer).")
                            continue

                        # Apply rotation gates between BS layers
                        applied_any_rgate = False
                        apply_even = (layer % 2 == 0)

                        for mode in range(len(q) - 1):  # Only up to second-last mode (exclude last)
                            if (mode % 2 == 0 and apply_even) or (mode % 2 == 1 and not apply_even):
                                if rotation_gate_angles is not None and rotation_idx < len(rotation_gate_angles):
                                    angle = rotation_gate_angles[rotation_idx]
                                else:
                                    angle = random.uniform(0, 2 * np.pi)  # From 0 to 2π now
                                Rgate(angle) | q[mode]
                                #print(f"Rgate({angle:.4f}) | q[{mode}]")
                                rotation_idx += 1
                                applied_any_rgate = True

                        if not applied_any_rgate:
                            print("No Rgates applied on this layer.")

                # Run the engine
                eng = sf.Engine(backend='fock', backend_options={'cutoff_dim': self.dim})
                results = eng.run(boson_sampling)

                fock_probs = results.state.all_fock_probs()

                if fock_probs.ndim > 1:
                    fock_probs = fock_probs.flatten()

                if fock_probs.size == 0 or np.all(fock_probs == 0):
                    print("Simulation returned an empty or zero-filled probability array.")
                    return None

                #print(f"Simulation completed successfully. Probabilities length: {len(fock_probs)}")
                return fock_probs

            except Exception as e:
                print(f"Error during simulation: {e}")
                return None

        simulation_probabilities = simulate()
        if simulation_probabilities is None:
            #print("Simulation failed or returned None. Returning placeholder values.")
            return [], []

        output_states_configurations = self.get_all_possible_output_states_configurations()
        probabilities, final_states = self.get_probability_of_output_states_configurations(simulation_probabilities,
                                                                                           output_states_configurations)
        per_channel_probs = self.get_per_channel_probabilities(probabilities, final_states)

        #print(per_channel_probs)

        return probabilities, final_states, per_channel_probs

