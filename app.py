# -*- coding: utf-8 -*-
"""
DESPLIEGUE (CRISP-DM) - IoT + TinyML + Web Dashboard + Telegram
- Lee DHT11 + HC-SR04 cada 3s
- Predice estado con model1.pkl (NORMAL / ADVERTENCIA / EMERGENCIA / EMERGENCIA_CON_PRESENCIA)
- FAILSAFE:
    temp >= 28.0 -> fuerza EMERGENCIA
    temp >= 28.0 y dist < 10.0 -> fuerza EMERGENCIA_CON_PRESENCIA
- LED físico:
    NORMAL -> OFF
    ADVERTENCIA -> BLINK (parpadeo)
    EMERGENCIA / EMERGENCIA_CON_PRESENCIA -> ON fijo
- Telegram SOLO en EMERGENCIA_CON_PRESENCIA
- Dashboard web en Flask (temp, hum, distancia, estado, led)
"""

import os
import time
import threading
from datetime import datetime

import joblib
import telepot
from flask import Flask, jsonify, render_template

import adafruit_dht
import board
import RPi.GPIO as GPIO


# ---------------- CONFIG ----------------
READ_INTERVAL_SEC = 3

# Pines
LED_PIN = 23
DHT_PIN = board.D4
TRIG_PIN = 18
ECHO_PIN = 24

# Parpadeo (ADVERTENCIA)
BLINK_PERIOD_SEC = 1.0   # 1.0 => 0.5 ON, 0.5 OFF
LED_TICK_SEC = 0.2

# Presencia y umbral de emergencia (failsafe)
DISTANCIA_PRESENCIA_CM = 10.0
TEMP_EMERGENCIA_C = 28.0

# Modelo
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model1.pkl")

# Telegram
BOT_TOKEN = "7128105026:AAFBsU_FQhXr9fXnp9eF5QQLE4Ad2K5XqAo"
CHAT_ID = 565648492

# Anti-spam (segundos)
TELEGRAM_COOLDOWN_SEC = 60
# ----------------------------------------


class IoTController:
    def __init__(self):
        # Cargar modelo
        self.model = joblib.load(MODEL_PATH)

        # Sensor DHT11
        self.dht = adafruit_dht.DHT11(DHT_PIN, use_pulseio=False)

        # Telegram
        self.bot = telepot.Bot(BOT_TOKEN) if BOT_TOKEN else None
        self._last_telegram_ts = 0.0

        # GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)

        GPIO.setup(TRIG_PIN, GPIO.OUT)
        GPIO.setup(ECHO_PIN, GPIO.IN)
        GPIO.output(TRIG_PIN, False)

        time.sleep(2)  # estabilizar

        # Estado compartido para la web
        self.lock = threading.Lock()
        self.state = {
            "temperature": None,
            "humidity": None,
            "distance_cm": None,
            "status": "N/A",
            "led": "OFF",
            "last_update": None
        }

        # Modo LED
        self.led_mode = "OFF"
        self._led_on = False
        self._last_toggle = time.time()

        self.running = True

        threading.Thread(target=self.sensor_loop, daemon=True).start()
        threading.Thread(target=self.led_loop, daemon=True).start()

    # ----------- ULTRASONICO (con timeout para no colgar) -----------
    def medir_distancia(self):
        GPIO.output(TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PIN, False)

        timeout = time.time() + 0.04  # 40 ms

        while GPIO.input(ECHO_PIN) == 0:
            if time.time() > timeout:
                return None
            inicio = time.time()

        while GPIO.input(ECHO_PIN) == 1:
            if time.time() > timeout:
                return None
            fin = time.time()

        duracion = fin - inicio
        distancia = (duracion * 34300) / 2
        return round(distancia, 1)

    # ----------- TELEGRAM (anti-spam) -----------
    def send_telegram_alert(self, msg):
        if not self.bot:
            return
        now = time.time()
        if (now - self._last_telegram_ts) < TELEGRAM_COOLDOWN_SEC:
            return
        try:
            self.bot.sendMessage(CHAT_ID, msg)
            self._last_telegram_ts = now
        except Exception as e:
            print("Error enviando Telegram:", e)

    # ----------- SENSOR + PREDICCIÓN -----------
    def sensor_loop(self):
        while self.running:
            temp = None
            hum = None
            dist = None
            status = "N/A"
            led_mode = self.led_mode
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # 1) Leer DHT
                temp = self.dht.temperature
                hum = self.dht.humidity
                if temp is None or hum is None:
                    raise RuntimeError("Lectura DHT inválida")

                # Pausa pequeña para evitar interferencias de timing
                time.sleep(0.2)

                # 2) Leer Ultrasonico
                dist = self.medir_distancia()
                if dist is None:
                    raise RuntimeError("Sin eco ultrasonico")

                # 3) Predicción del modelo (ML)
                status_ml = self.model.predict([[temp, hum, dist]])[0]

                # 4) FAILSAFE por umbral (REGLA DURA)
                #    Si temp >= 28, siempre EMERGENCIA, y si dist < 10 => EMERGENCIA_CON_PRESENCIA
                if float(temp) >= TEMP_EMERGENCIA_C:
                    status = "EMERGENCIA_CON_PRESENCIA" if float(dist) < DISTANCIA_PRESENCIA_CM else "EMERGENCIA"
                else:
                    status = status_ml

                # 5) LED según estado final
                if status == "NORMAL":
                    led_mode = "OFF"
                elif status == "ADVERTENCIA":
                    led_mode = "BLINK"
                else:
                    # EMERGENCIA o EMERGENCIA_CON_PRESENCIA
                    led_mode = "ON"

                # 6) Telegram SOLO si EMERGENCIA_CON_PRESENCIA
                if status == "EMERGENCIA_CON_PRESENCIA":
                    self.send_telegram_alert(
                        f"🚨 ALERTA: EMERGENCIA CON PRESENCIA\n"
                        f"Hora: {now_str}\n"
                        f"Temperatura: {temp} °C\n"
                        f"Humedad: {hum} %\n"
                        f"Distancia: {dist} cm\n"
                        f"LED: ON"
                    )

            except RuntimeError:
                # Mantener modo anterior si falla lectura
                pass

            # Guardar estado para la web
            with self.lock:
                self.state["temperature"] = temp
                self.state["humidity"] = hum
                self.state["distance_cm"] = dist
                self.state["status"] = status
                self.state["last_update"] = now_str

                self.led_mode = led_mode
                if self.led_mode == "OFF":
                    self.state["led"] = "OFF"
                elif self.led_mode == "BLINK":
                    self.state["led"] = "BLINK"
                else:
                    self.state["led"] = "ON"

            time.sleep(READ_INTERVAL_SEC)

    # ----------- LED LOOP -----------
    def led_loop(self):
        while self.running:
            with self.lock:
                mode = self.led_mode

            now = time.time()

            if mode == "OFF":
                if self._led_on:
                    GPIO.output(LED_PIN, GPIO.LOW)
                    self._led_on = False

            elif mode == "ON":
                if not self._led_on:
                    GPIO.output(LED_PIN, GPIO.HIGH)
                    self._led_on = True

            elif mode == "BLINK":
                half_period = BLINK_PERIOD_SEC / 2.0
                if (now - self._last_toggle) >= half_period:
                    self._led_on = not self._led_on
                    GPIO.output(LED_PIN, GPIO.HIGH if self._led_on else GPIO.LOW)
                    self._last_toggle = now

            time.sleep(LED_TICK_SEC)

    def get_state(self):
        with self.lock:
            return dict(self.state)

    def cleanup(self):
        self.running = False
        time.sleep(0.3)
        try:
            GPIO.output(LED_PIN, GPIO.LOW)
        except Exception:
            pass
        GPIO.cleanup()
        try:
            self.dht.exit()
        except Exception:
            pass


# ---------------- FLASK (VISTA WEB) ----------------
app = Flask(__name__)
controller = IoTController()


@app.route("/")
def index():
    return render_template("dashboard_dht11_ultra.html")


@app.route("/api/state")
def api_state():
    return jsonify(controller.get_state())


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        controller.cleanup()
