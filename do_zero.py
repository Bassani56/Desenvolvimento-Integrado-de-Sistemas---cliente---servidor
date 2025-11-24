from threading import Thread, Lock
import socket
import os
import csv
import numpy as np
from numpy.linalg import norm
from numpy.typing import NDArray
from pathlib import Path
import sys
import base64
from multiprocessing import Queue, Value
from ctypes import c_bool
from datetime import datetime, timezone
from time import time, sleep
import psutil
import base64
import matplotlib.pyplot as plt
import json
import random
import math

ACTUAL_DIR = Path(os.path.dirname(os.path.abspath(sys.argv[0])))

MIN_ERROR = .0001
MAX_WORKERS = 8

IMAGE_SHAPES = {
    '30x30': (900, 1),
    '60x60': (3600, 1)
}

FINAL_IMAGE_SHAPE = {
    '30x30': (30, 30),
    '60x60': (60, 60)
}

MODEL_SHAPES = {
    '30x30': (27904, 900),
    '60x60': (50816, 3600)
}

def sgemm(alpha, a, b, trans_a=False):
    if trans_a:
        a = a.T
    return alpha * np.dot(a, b)

def calc_error(b, a):
    return norm(b, 2) - norm(a, 2)

def cgne(h, g, image_shape, final_image_shape):
    f0 = np.zeros(image_shape, np.float32)
    r0 = g - sgemm(1.0, h, f0)
    p0 = sgemm(1.0, h, r0, trans_a=True)

    total_iterations = 0

    while total_iterations < 30:
        total_iterations += 1

        a0 = sgemm(1.0, r0, r0, trans_a=True) / sgemm(1.0, p0, p0, trans_a=True)
        f0 = f0 + a0 * p0
        r1 = r0 - a0 * sgemm(1.0, h, p0)

        error = calc_error(r1, r0)
        if error < MIN_ERROR:
            break

        beta = sgemm(1.0, r1, r1, trans_a=True) / sgemm(1.0, r0, r0, trans_a=True)
        p0 = sgemm(1.0, h, r0, trans_a=True) + beta * p0
        r0 = r1

    f0 = f0.reshape(final_image_shape)
    return f0, total_iterations

def cgnr(h, g, image_shape, reshaped_image_shape):
    f0 = np.zeros(image_shape, np.float32)
    r0 = g - sgemm(1.0, h, f0)
    z0 = sgemm(1.0, h, r0, trans_a=True)
    p0 = np.copy(z0)

    total_iterations = 0
    while total_iterations < 30:
        # Count iterations
        total_iterations += 1

        w = sgemm(1.0, h, p0)
        norm_z = norm(z0, 2) ** 2
        a = norm_z / norm(w) ** 2
        f0 = f0 + a * p0
        r1 = r0 - a * w

        error = abs(calc_error(r1, r0))
        if error < MIN_ERROR:
            break

        z0 = sgemm(1.0, h, r1, trans_a=True)
        b = norm(z0, 2) ** 2 / norm_z
        p0 = z0 + b * p0
        r0 = r1

    f0 = f0.reshape(reshaped_image_shape)

    return f0, total_iterations

ALGORITHM = {
    'cgne': cgne,
    'cgnr': cgnr
}

# def read_and_code(file_path, filename):
#     with open(file_path, 'rb') as f:
#         converted = base64.b64encode(f.read()).decode('utf-8')
#         images_64[filename] = converted

def read_model(model):
    with open(ACTUAL_DIR / "models" / f"model-{model}.csv", "r") as file:
        reader = csv.reader(file, delimiter=',')
        res = np.empty(MODEL_SHAPES[model], dtype=np.float32)
        for i, line in enumerate(reader):
            res[i] = np.array(line, np.float32)
        return res
    
def calculate_signal_gain(g):
    n = 64
    s = 794 if len(g) > 50000 else 436
    for c in range(n):
        for l in range(s):
            y = 100 + (1 / 20) * l * math.sqrt(l)
            g[l + c * s] = g[l + c * s] * y
    return g


def read_signal(model: str, signal: int):
    with open(ACTUAL_DIR / "client" / "signals" / f"signal-{model}-{signal}.csv", "r") as file:
        reader = csv.reader(file)
        array = list(map(lambda x: float(x[0]), reader))
        return calculate_signal_gain(array)
def main():
    username = str(input('username: '))

    algorithm = random.choice(["cgne", "cgnr"])
    model_type = random.choice(["30x30", "60x60"])
    signal = np.array(
    read_signal(model_type, random.randint(0, 2)), dtype=np.float32).reshape(-1, 1)

    img, iterations = ALGORITHM[algorithm](model_type, signal, IMAGE_SHAPES[model_type], FINAL_IMAGE_SHAPE[model_type])

    initial_time = 10
    final_time = 20
    # final_time = time()
    # elapsed_time = final_time - initial_time
    
    filename = f"{username}-final-{final_time}.png"
    filepath = ACTUAL_DIR / "images" / username / filename
    started_at = datetime.fromtimestamp(initial_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    ended_at = datetime.fromtimestamp(final_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

     # Save image
    metadata = {
        'Title': filename.replace(".png", ""),
        'Author': f"CGNR Processor",
        'Description': f"Username: {username} | Algorithm: {algorithm} | Started at: {started_at} | Ended at: {ended_at} | "
                       f"Size: {FINAL_IMAGE_SHAPE[model_type]} | Iterations: {iterations}"
    }
    plt.imsave(filepath, img, cmap='gray', metadata=metadata)

main()