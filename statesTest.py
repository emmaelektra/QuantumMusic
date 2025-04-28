import numpy as np
import random

class FakeMode:
    def __init__(self, index):
        self.index = index

    def __repr__(self):
        return f"q[{self.index}]"

# Settings
num_output_channels = 4
num_layers = num_output_channels
gate_values = [(np.random.uniform(0, np.pi), np.random.uniform(0, np.pi)) for _ in range(num_output_channels * 2)]

# Fake quantum modes (like q[0], q[1], q[2], q[3])
q = [FakeMode(i) for i in range(num_output_channels)]

for layer in range(num_layers):
    print(f"\n=== Layer {layer} ===")
    start_index = layer % 2
    for i in range(start_index, len(q) - 1, 2):
        if len(gate_values) > 0:
            gate_value = gate_values.pop(0)
            print(f"BSgate on ({i}, {i + 1}) with values {gate_value}")

    # Special case: last BS layer → no Rgates after it
    if layer == num_layers - 1:
        print("Last layer, no Rgates applied.")
        break

    # Special case: second-to-last layer → no Rgates applied after it
    if layer == num_layers - 2:
        print("No Rgates applied (between second-last and last layer).")
        continue

    # Otherwise: apply Rgates selectively
    applied_any_rgate = False
    apply_even = (layer % 2 == 0)  # Even layer index → even channels (1-indexed)

    for mode in range(len(q)):
        channel_number = mode + 1  # Convert to 1-based indexing
        if channel_number == 1:
            continue  # NEVER apply Rgate on channel 1 (mode 0)
        if (channel_number % 2 == 0 and apply_even) or (channel_number % 2 == 1 and not apply_even):
            angle = random.uniform(-np.pi, np.pi)
            print(f"Rgate({angle:.4f}) on q[{mode}]")
            applied_any_rgate = True

    if not applied_any_rgate:
        print("No Rgates applied on this layer.")
