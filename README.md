# IoT + TinyML + DHT11 + Ultrasonico

Sistema IoT implementado en Raspberry Pi que:
- Mide temperatura y humedad con DHT11
- Detecta presencia con sensor ultrasónico HC-SR04
- Clasifica estados mediante TinyML
- Muestra resultados en un dashboard web
- Envía alertas por Telegram en estados críticos

## Estados del sistema
- NORMAL
- ADVERTENCIA
- EMERGENCIA
- EMERGENCIA_CON_PRESENCIA

## Tecnologías
- Python
- Scikit-learn (MLPClassifier)
- Flask
- Edge Impulse
- Raspberry Pi

## Estructura del proyecto

iot-tinyml-dht11-ultrasonico/
│
├── app2.py
├── captura_datos.py
├── captura_datos_sensores.py
├── entrenar_modelo.py
├── model1.pkl
│
├── templates/
│ └── dashboard_dht11_ultra.html
iot-tinyml-dht11-ultrasonico/
## Autor
Kevin García Buitrón  
Universidad Politécnica Salesiana  
Electrónica y Automatización
