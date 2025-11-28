import threading
import socket
import hashlib
import time
import os
import math
import csv
import sys
from threading import Lock
from pathlib import Path
import random
import base64
import json
from datetime import datetime
import os


file_lock = Lock()      
send_lock = Lock()      
print_lock = Lock()     

base = os.path.dirname(os.path.abspath(__file__))
path_json = r"C:\Users\User\Desktop\Desenvolvimento Integrado\cliente-servidor\server\sorteio.json"


ACTUAL_DIR = Path(os.path.dirname(os.path.abspath(sys.argv[0])))

SINAIS30 = ['client/signals/signal-30x30-0', 'client/signals/signal-30x30-1', 'client/signals/signal-30x30-2']
SINAIS60 = ['client/signals/signal-60x60-0','client/signals/signal-60x60-1','client/signals/signal-60x60-2']

MODELOS30 = ['../server/models/model-30x30.csv']
MODELOS60 = ['../server/models/model-60x60.csv']


def imprimir_opcoes():
    print('2 - Recostruir imagems')
    print('4 - Sair')

def sorteio():
    # with open(path_json, "r") as f:
    #     data = json.load(f)

    # if "algorithm" not in data:
    #     data["algorithm"] = []
    # if "model" not in data:
    #     data["model"] = []
    # if "signal" not in data:
    #     data["signal"] = []


    algorithm = random.choice(["cgne","cgnr"])
    model_size = random.choice(["30x30","60x60"])

    if model_size == "30x30":
        model = random.choice(MODELOS30)    # caminho real do servidor
        signal = random.choice(SINAIS30)    # caminho real do cliente
    else:
        model = random.choice(MODELOS60)
        signal = random.choice(SINAIS60)

    print('sorteio:: ', signal, algorithm, model, '\n')

    # data["algorithm"].append(algorithm)
    # data["model"].append(model)
    # data["signal"].append(signal)

    # # Salvar tudo
    # with open(path_json, "w") as f:
    #     json.dump(data, f, indent=4)

    # Retornar só os valores gerados nesta chamada
    return signal, algorithm, model


class serverData:
    def __init__(self):
        self.g = None
        self.algorithm = None
        self.model = None

def sendMessages(client, username, stop_event):
    # connected = True
    while not stop_event.is_set():
        try:
            imprimir_opcoes()
            msg = int(input('Escolha: '))

            if msg == 4:
                # connected = False
                client.send(f'EXIT:<{username}> saiu do chat'.encode())
                stop_event.set()
                break

            elif msg == 2:
                rand_request = random.randint(3, 7)

                data_set = []

                for i in range(rand_request):
                    print(f"executando a {i + 1}° requisição, no total de {rand_request}")

                    g, algorithm, model = sorteio()
                    
                    data = {'algorithm': algorithm, 'model': model, 'signal': g}

                    data_set.append(data)
                    print(f"[{i+1}/{rand_request}] (batch) Usuário: {username} | Modelo: {model} | Sinal: {g} | Algoritmo: {algorithm}")


                # envia_requisicao(client, username, data)
                json_str = json.dumps(data_set)

                # envia mensagem inicial com username
                client.send(f'2_|{username}|{json_str}'.encode())


        except Exception as e:
            print('Erro: ', e)
            stop_event.set()
            break

def create_paste(username):
    path = ACTUAL_DIR / "users" / username    
    if not path.exists():
        os.mkdir(path)

def receiveMessages(client, stop_event):
    while not stop_event.is_set():
        try:
            # 1. Recebe 4 bytes com o tamanho do JSON
            data = client.recv(1000000)
            if not data:
                break

            decoded_str = data.decode()
            decoded = json.loads(decoded_str)  # <-- transforma string em dict

            json_str = decoded['payload']  # agora funciona
            tipo = decoded['type']


            if tipo == "1_":
                print("IDs recebidos:", json_str)

            if tipo == "2_":
                header = decoded['payload']['header']
                img_b64 = decoded['payload']['image']

                # converter Base64 para bytes
                img_bytes = base64.b64decode(img_b64)

                # salvar imagem
                name = f"{header['username']}_{header['algorithm']}_{header['start_dt'].replace(':','-')}_{header['end_dt'].replace(':','-')}_{header['size']}_{header['iters']}.png"
                path = f"users/{header['username']}/{name}"
                
                with file_lock:
                    with open(path, "wb") as f:
                        f.write(img_bytes)

                path = r'C:\Users\User\Desktop\Desenvolvimento Integrado\cliente-servidor\server\relatorio\imagens-relatorio_1764250066.8843918.csv'
                time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                linha = (
                    f"{time_now} | "
                    f"Imagem: {name} | "
                    f"Usuário: {header['username']} | "
                    f"Algoritmo: {header['algorithm']} | "
                    f"Inicio: {header['start_dt']} | "
                    f"Fim: {header['end_dt']} | "
                    f"Tamanho: {header['size']} | "
                    f"Iteracoes: {header['iters']}\n")

                # adicionar linha ao CSV em modo append
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(linha)

                print("Imagem salva:", path)

        except Exception as e:
            print("Erro:", e)
            break

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect(('localhost', 7776))
    except:
        return print('\nNão foi possível se conectar ao servidor!\n')
    
    print('\nConectado\n')

    username = input('Usuário> ')
    create_paste(username)
    stop_event = threading.Event()

    recv_thread = threading.Thread(target=receiveMessages, args=(client, stop_event))
    recv_thread.start()

    send_thread = threading.Thread(target=sendMessages, args=[client, username, stop_event])
    send_thread.start()


main()

