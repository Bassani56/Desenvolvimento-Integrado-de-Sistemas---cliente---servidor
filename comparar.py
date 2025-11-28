from psutil import virtual_memory, swap_memory

def bytes_to_gigas(value):
    return f'{value / 1024 / 1024 / 1024: .2f}GB'

# print(bytes_to_gigas(virtual_memory().total))
# print(bytes_to_gigas(virtual_memory().used))

# print('swap: ', bytes_to_gigas(swap_memory().total))

# pesado = list(range(100_000_000))
# pesado2 = list(range(100_000_000))

# print(bytes_to_gigas(virtual_memory().used))

# del pesado
# del pesado2 

# print(bytes_to_gigas(virtual_memory().used))


import psutil

# processes = psutil.process_iter()

# for process in processes:
#     name = process.name()
#     # if name.startswith('Visual'):
#     print(name)

import psutil
import time

while True:
    cpu_percent = psutil.cpu_percent(interval=1)  # % de uso da CPU

    mem = psutil.virtual_memory()
    mem_percent = mem.percent

    print(f"CPU: {cpu_percent}% ")
    print(f"Memória: {mem_percent}%")

    print()

    time.sleep(1)
