import json
import random

# ---------------------------
# BASE
# ---------------------------
SINAIS30 = [
    'client/signals/signal-30x30-0',
    'client/signals/signal-30x30-1',
    'client/signals/signal-30x30-2'
]

SINAIS60 = [
    'client/signals/signal-60x60-0',
    'client/signals/signal-60x60-1',
    'client/signals/signal-60x60-2'
]

MODELOS30 = ['../server/models/model-30x30.csv']
MODELOS60 = ['../server/models/model-60x60.csv']

ALGORITHMS = ["cgne", "cgnr"]

# ---------------------------
# GERADOR DE UM CLIENTE
# ---------------------------
def gerar_cliente():
    # Quantidade aleatória de requests
    rand_request = random.randint(3, 5)

    time_to_next_request = []
    algorithm_list = []
    model_list = []
    signal_list = []

    for _ in range(rand_request):
        # time_to_next_request aleatório entre 1 e 4 segundos
        time_to_next_request.append(random.randint(1, 4))

        # Algorithm aleatório
        algorithm = random.choice(ALGORITHMS)
        algorithm_list.append(algorithm)

        # Modelo aleatório
        model_size = random.choice(["30x30", "60x60"])

        if model_size == "30x30":
            model = random.choice(MODELOS30)
            signal = random.choice(SINAIS30)
        else:
            model = random.choice(MODELOS60)
            signal = random.choice(SINAIS60)

        model_list.append(model)
        signal_list.append(signal)

    # Monta o dicionário final do cliente
    return {
        "rand_request": rand_request,
        "time_to_next_request": time_to_next_request,
        "algorithm": algorithm_list,
        "model": model_list,
        "signal": signal_list
    }

# ---------------------------
# GERA TODOS OS CLIENTES
# ---------------------------
def gerar_json(num_clientes=3):
    dados = []
    
    arquivo = r"C:\Users\User\Desktop\Desenvolvimento Integrado\cliente-servidor\client\sorteio.json"

    for _ in range(num_clientes):
        dados.append(gerar_cliente())

    # Salvar sobrescrevendo o JSON anterior
    with open(arquivo, "w") as f:
        json.dump(dados, f, indent=4)

    print(f"Novo JSON gerado em {arquivo}!")

# ---------------------------
# EXECUTAR
# ---------------------------
if __name__ == "__main__":
    gerar_json(num_clientes=3)
