import json
import os
import random


base = os.path.dirname(os.path.abspath(__file__))
path_json = os.path.join(base, "sorteio.json")

# Ler
with open(path_json, "r") as f:
    data = json.load(f)

rand_request = random.randint(3, 7)
time_to_next_request = random.randint(1, 5)
algorithm = random.choice(["cgne", "cgnr"])
model = random.choice(["30x30", "60x60"])
n_model = random.randint(0, 2)

# Editar uma variável
data["rand_request"] = rand_request
data["time_to_next_request"] = time_to_next_request
data["algorithm"] = algorithm
data["model"] = model
data["n_model"] = n_model

with open(path_json, "w") as f:  
    json.dump(data, f, indent=4)
