import threading
import socket
import hashlib
import time
import os
import math
import csv
import sys
from threading import Thread
from pathlib import Path
import random
import base64
import json

import json
import os

base = os.path.dirname(os.path.abspath(__file__))
path_json = r"C:\Users\User\Desktop\Desenvolvimento Integrado\cliente-servidor\server\sorteio.json"



ACTUAL_DIR = Path(os.path.dirname(os.path.abspath(sys.argv[0])))

def imprimir_opcoes():
    print('1 - Recostruir imagem')
    print('2 - Recuperar imagems')
    print('4 - Sair')

def calculate_signal_gain(g):
    n = 64
    s = 794 if len(g) > 50000 else 436
    for c in range(n):
        for l in range(s):
            y = 100 + (1 / 20) * l * math.sqrt(l)
            g[l + c * s] = g[l + c * s] * y
    return g


def read_signal(model: str, signal: int):
    with open(ACTUAL_DIR / "signals" / f"signal-{model}-{signal}.csv", "r") as file:
        reader = csv.reader(file)
        array = list(map(lambda x: float(x[0]), reader))
        return calculate_signal_gain(array)
    
def save_image(filepath, b64_content):
    with open(filepath, 'wb') as file:
        file.write(base64.b64decode(b64_content))

def envia_requisicao(client, username, data):
    # converte dict em string JSON
    json_str = json.dumps(data)

    # envia mensagem inicial com username
    client.send(f'1_|{username}|{json_str}'.encode())


def sorteio():
    with open(path_json, "r") as f:
        data = json.load(f)

    # Garantir que são listas (caso o JSON inicial esteja vazio)
    if "time_to_next_request" not in data:
        data["time_to_next_request"] = []
    if "algorithm" not in data:
        data["algorithm"] = []
    if "model" not in data:
        data["model"] = []
    if "n_model" not in data:
        data["n_model"] = []

    # Gerar valores aleatórios desta iteração
    time_to_next_request = random.randint(1, 5)
    algorithm = random.choice(["cgne", "cgnr"])
    model = random.choice(["30x30", "60x60"])
    n_model = random.randint(0, 2)

    # Adicionar os valores nas listas
    data["time_to_next_request"].append(time_to_next_request)
    data["algorithm"].append(algorithm)
    data["model"].append(model)
    data["n_model"].append(n_model)

    # Salvar tudo
    with open(path_json, "w") as f:
        json.dump(data, f, indent=4)

    # Retornar só os valores gerados nesta chamada
    return time_to_next_request, algorithm, model, n_model

def first():
    # Carregar o que já existe
    with open(path_json, "r") as f:
        data = json.load(f)

    # Sortear e atualizar
    rand_request = random.randint(3, 7)
    data['rand_request'] = rand_request

    # salvar SEM apagar as listas existentes
    with open(path_json, "w") as f:  
        json.dump(data, f, indent=4)

    return rand_request


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

            if msg == 1:
                # client.send(f'<{username}> {msg}'.encode())
                rand_request = first()

                for i in range(rand_request):
                    print(f"executando a {i + 1}° requisição, no total de {rand_request}")

                    time_to_next_request, algorithm, model, n_model = sorteio()
                    
                    g = read_signal(model, n_model)
                    data = {'algorithm': algorithm, 'model': model, 'signal': g}


                    envia_requisicao(client, username, data)

                    print(f"A próxima requisição será enviada em {time_to_next_request} segundos.")
                    time.sleep(time_to_next_request)

            elif msg == 2:
                client.send(f'2_:{username}'.encode())
                print('enviou o 2')

        except Exception as e:
            print('Erro: ', e)
            stop_event.set()
            break
import ast

def create_image(username):
    path = ACTUAL_DIR / "users" / username    
    if not path.exists():
        os.mkdir(path)

def receiveMessages(client, stop_event):
    while not stop_event.is_set():
        try:
            data = client.recv(1000000)

            if not data:
                break

            # Primeiro, decodifica e transforma em JSON
            decoded = json.loads(data.decode())

            # Verifica o tipo da mensagem
            if decoded["type"] == "2_":
                username = decoded["username"]
                payload = decoded["payload"]

                for key, value in payload.items():
                    save_image(ACTUAL_DIR / "users" / username / key, value)

            else:
                print(data.decode())

        except Exception as e:
            print('Erro: ', e)
            stop_event.set()
            break


def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect(('localhost', 7776))
    except:
        return print('\nNão foi possível se conectar ao servidor!\n')
    
    print('\nConectado\n')

    username = input('Usuário> ')
    create_image(username)
    stop_event = threading.Event()

    recv_thread = threading.Thread(target=receiveMessages, args=(client, stop_event))
    recv_thread.start()

    send_thread = threading.Thread(target=sendMessages, args=[client, username, stop_event])
    send_thread.start()


main()








# def handle_client(client, addr, request_queue):
#     print(f"[NOVA CONEXÃO] {addr} conectado")

#     connected = True
#     flag = False
#     buffer = b''

#     while connected:
#         try:
#             data = client.recv(100000)
#             if not data:
#                 break

#             if data.startswith(b'EXIT'):
#                 connected = False

#             elif data.startswith(b'1_|'):
#                 parts = data.decode().split(b'|', 2)
#                 username = parts[1]
#                 buffer = parts[2]

#                 flag = True

#             if flag:
#                 buffer += data

#                 if b'fim' in buffer:
#                     json_bytes, _, buffer = buffer.partition(b'fim')
#                     data = json.loads(json_bytes.decode())  # agora é string limpa
#                     signal = np.array(data['signal'], np.float32).reshape((-1, 1))

#                     request_data = RequestData(username, data['algorithm'], data['model'], signal)
#                     request_queue.put(request_data)

#                     flag = False  

            
#             elif data.startswith(b'2_'):
#                 parts = data.decode().split(':')
#                 username = parts[1]

#                 dict_user = {}
#                 for key, value in images_64.items():
#                     if username in key:
#                         dict_user[key] = value
                 
#                 client.send(f'2_:{username}:{dict_user}'.encode())

#         except ConnectionResetError:
#             print(f"[DESCONECTADO] {addr} encerrou a conexão.")
#             break

#     client.close()