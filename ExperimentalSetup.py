import math
import strawberryfields as sf
from strawberryfields.ops import *
import itertools
import random


class ExperimentalSetup:

    def __init__(self, num_output_channels, num_photons, dim=-1):
        self.num_output_channels = num_output_channels
        self.num_photons = num_photons
        if dim == -1:
            self.dim = num_photons + 1
        else:
        else:
            self.dim = dim
        self.boson_sampling = sf.Program(num_output_channels)


    # photonplacement should be in following style [1,1,1,1,0]
    # angle_first_rotation_gates should be an array of angles
    # gate_values should be a list of tuples with transmission amplitude and phase shift [(t,p),(t,p),(t,p)]
    def run_experiment(self, photon_placement, angle_first_rotation_gates=None, gate_values=None):

        def calculate_number_of_gates(n):
            return math.floor(n * n / 2)

        def get_random_angle_first_rotation_gates():
            return [random.uniform(0, 2 * math.pi) for i in range(len(photon_placement))]

        def get_random_gate_values():
            return [(random.uniform(0, 2 * math.pi), random.uniform(0, 2 * math.pi)) for i in
                    range(calculate_number_of_gates(len(photon_placement)))]

        if angle_first_rotation_gates is None:
            angle_first_rotation_gates = get_random_angle_first_rotation_gates()
        if gate_values is None:
            gate_values = get_random_gate_values()

        print(f"photon_placement: {photon_placement}")
        print(f"angle_first_rotation_gates: {angle_first_rotation_gates}")
        print(f"gate_values {gate_values}")



        def check_if_number_of_photons_in_photon_placement_is_valid():
            if not all([x == 0 or x == 1 for x in photon_placement]):
                return False
            return sum(photon_placement) == self.num_photons

        if not check_if_number_of_photons_in_photon_placement_is_valid():
            raise ValueError("Invalid number of photons in photon placement")

        if len(angle_first_rotation_gates) != len(photon_placement):
            raise ValueError("Invalid number of angles in angle_first_rotation_gates")

        if len(gate_values) < calculate_number_of_gates(len(photon_placement)):
            raise ValueError("Invalid number of gate values in gate_values")

        def get_all_possible_output_states_configurations():
            states = []
            for lost_photons in range(self.num_photons + 1):
                remaining_photons = self.num_photons - lost_photons
                for partition in itertools.product(range(remaining_photons + 1), repeat=self.num_output_channels):
                    if sum(partition) == remaining_photons:
                        states.append(list(partition))
            return states

        def get_probability_of_output_states_configurations(experimental_probabilities, states):
            final_probabilities = []
            for i, state in enumerate(states):
                final_probabilities.append(experimental_probabilities[*states[i]])
            return final_probabilities


        def simulate():
            with self.boson_sampling.context as q:
                # Prepare the input Fock states
                for i in range(len(photon_placement)):
                    if photon_placement[i] == 1:
                        Fock(1) | q[i]
                        print(f"fock state {i}")
                    else:
                        Vac | q[i]
                        print(f"empty state {i}")

                # Apply the first rotation gates
                for i in range(len(angle_first_rotation_gates)):
                    Rgate(angle_first_rotation_gates[i]) | q[i]

                # Apply the beamsplitter gates
                i = 1
                for j in range(len(photon_placement) + 1):
                    if i % 2 != 0:
                        ch = 0
                        for bs_index in range(len(photon_placement)):
                            gate_value = gate_values.pop(0)
                            BSgate(gate_value[0], gate_value[1]) | (q[ch], q[ch + 1])
                            ch += 2
                            if ch + 1 >= len(photon_placement):
                                break
                        i += 1
                    elif i % 2 == 0:
                        ch = 0
                        for bs_index in range(len(photon_placement)):
                            gate_value = gate_values.pop(0)
                            BSgate(gate_value[0], gate_value[1]) | (q[ch+1], q[ch + 2])
                            ch = ch + 2
                            if ch >= len(photon_placement) - 2:
                                break
                        i += 1

                # initialise the engine
                eng = sf.Engine(backend='fock', backend_options={'cutoff_dim': self.dim})
                results = eng.run(self.boson_sampling)
                return results.state.all_fock_probs()

        simulation_probabilities = simulate()
        out_put_states_configurations = get_all_possible_output_states_configurations()
        probabilities = get_probability_of_output_states_configurations(simulation_probabilities, out_put_states_configurations)
        return probabilities, out_put_states_configurations








