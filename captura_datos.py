# -*- coding: utf-8 -*-
"""
captura_datos_sensores.py
Recolección REAL DHT11 + HC-SR04
Lectura cada 3 segundos durante 10 minutos
Dataset estable para TinyML
"""

import time
import csv
from datetime import datetime

import adafruit_dht
import board
import RPi.GPIO as GPIO

# ================= CONFIGURACIÓN =================
# DHT11
PIN_DHT = board.D4        # GPIO4 (Pin físico 7)

# HC-SR04
TRIG = 24                 # GPIO24 (Pin físico 18)
ECHO = 25                 # GPIO25 (Pin físico 22)

INTERVALO = 3             # segundos
DURACION_MIN = 10
ARCHIVO = "dataset.csv"

DIST_PRESENCIA = 10       # cm
# ================================================

print("========================================")
print(" RECOLECCIÓN DHT11 + ULTRASÓNICO (ESTABLE)")
print("========================================")

# GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)

time.sleep(2)  # estabilización sensores

# Inicializar DHT (SE RECREA SI FALLA)
def crear_dht():
    return adafruit_dht.DHT11(PIN_DHT, use_pulseio=False)

dht = crear_dht()

total_muestras = int((DURACION_MIN * 60) / INTERVALO)
print(f"Intervalo: {INTERVALO} s")
print(f"Duración: {DURACION_MIN} min")
print(f"Total muestras: {total_muestras}")
print("========================================")

# -------- FUNCIÓN DISTANCIA (NO BLOQUEANTE) --------
def medir_distancia():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    timeout = time.time() + 0.05  # 50 ms

    while GPIO.input(ECHO) == 0:
        if time.time() > timeout:
            return None

    inicio = time.time()

    while GPIO.input(ECHO) == 1:
        if time.time() > timeout:
            return None

    fin = time.time()
    distancia = (fin - inicio) * 34300 / 2
    return round(distancia, 2)

# -------- CSV --------
with open(ARCHIVO, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp",
        "temperature",
        "humidity",
        "distance_cm",
        "estado_termico",
        "presencia"
    ])

    muestras = 0

    try:
        while muestras < total_muestras:
            try:
                # ===== DHT11 =====
                temp = dht.temperature
                hum = dht.humidity

                if temp is None or hum is None:
                    raise RuntimeError

                # Clasificación térmica
                if 15 <= temp <= 22:
                    estado = "NORMAL"
                elif 23 <= temp <= 27:
                    estado = "ADVERTENCIA"
                elif temp >= 28:
                    estado = "EMERGENCIA"
                else:
                    estado = "FUERA_RANGO"

            except RuntimeError:
                print("⚠ Error DHT11 → reinicializando sensor")
                dht.exit()
                time.sleep(1)
                dht = crear_dht()
                time.sleep(INTERVALO)
                continue

            # ===== PAUSA CLAVE =====
            time.sleep(0.5)

            # ===== ULTRASÓNICO =====
            distancia = medir_distancia()
            if distancia is None:
                print("⚠ Sin eco ultrasonico")
                time.sleep(INTERVALO)
                continue

            presencia = "PRESENCIA" if distancia < DIST_PRESENCIA else "SIN_PRESENCIA"

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            writer.writerow([
                timestamp,
                temp,
                hum,
                distancia,
                estado,
                presencia
            ])

            muestras += 1

            print(
                f"[{muestras}/{total_muestras}] "
                f"T={temp}°C H={hum}% "
                f"D={distancia}cm {presencia} {estado}"
            )

            time.sleep(INTERVALO)

    finally:
        GPIO.cleanup()
        dht.exit()

print("========================================")
print(" RECOLECCIÓN FINALIZADA")
print(f" Archivo: {ARCHIVO}")
print("========================================")
