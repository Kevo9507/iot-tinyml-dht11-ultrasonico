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
