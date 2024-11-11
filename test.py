import ExperimentalSetup as es
import numpy as np
import matplotlib.pyplot as plt


def plot_probabilities(output_states, probabilities):
    plt.figure(figsize=(10, 3))  # Increase the figure size

    plt.bar(range(len(output_states)), probabilities)
    plt.xticks(range(len(output_states)), output_states, rotation='vertical', fontsize=5)
    plt.xlabel('Output States')
    plt.ylabel('Probabilities')
    plt.title('Probabilities of Output States')
    plt.show()

def main():

    es_setup = es.ExperimentalSetup(4,3)
    probs, output_states = es_setup.run_experiment([1,1,1,0])
    print(probs)
    sum_probs = np.sum(probs)
    print(sum_probs)
    plot_probabilities(output_states, probs)
    print("output states = ", output_states)
    print("len output states = ", len(output_states))
    print("len probs = ", len(probs))

if __name__ == "__main__":
    main()

