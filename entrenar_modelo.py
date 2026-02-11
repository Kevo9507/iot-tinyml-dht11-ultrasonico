# -*- coding: utf-8 -*-
"""
Entrenamiento TinyML
Clasificación térmica + presencia
Salida: model1.pkl
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# ---------------- CONFIG ----------------
DATASET = "dataset2.csv"
MODEL_OUT = "model1.pkl"
TEST_SIZE = 0.2
RANDOM_STATE = 42
# ----------------------------------------

print("Cargando dataset...")
df = pd.read_csv(DATASET)

print("\nColumnas detectadas:")
print(df.columns)

# ---------------- LIMPIEZA ----------------
df = df.dropna(subset=[
    "temperatura",
    "humedad",
    "distancia_cm",
    "estado_temp",
    "estado_presencia"
])

# ---------------- ETIQUETA FINAL ----------------
def crear_label_final(row):
    if row["estado_temp"] == "EMERGENCIA" and row["estado_presencia"] == "PRESENCIA":
        return "EMERGENCIA_CON_PRESENCIA"
    else:
        return row["estado_temp"]

df["label_final"] = df.apply(crear_label_final, axis=1)

print("\nDistribución de clases:")
print(df["label_final"].value_counts())

# ---------------- FEATURES / LABEL ----------------
X = df[["temperatura", "humedad", "distancia_cm"]]
y = df["label_final"]

# ---------------- SPLIT ----------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)

# ---------------- MODELO TinyML ----------------
pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("mlp", MLPClassifier(
        hidden_layer_sizes=(8,),   # red pequeña
        activation="relu",
        solver="adam",
        max_iter=500,
        random_state=RANDOM_STATE
    ))
])

print("\nEntrenando modelo...")
pipeline.fit(X_train, y_train)

print("\nEvaluando modelo...")
y_pred = pipeline.predict(X_test)

print("\n=== REPORTE DE CLASIFICACIÓN ===")
print(classification_report(y_test, y_pred))

print("=== MATRIZ DE CONFUSIÓN ===")
print(confusion_matrix(y_test, y_pred))

# ---------------- GUARDAR MODELO ----------------
joblib.dump(pipeline, MODEL_OUT)
print(f"\nModelo guardado como: {MODEL_OUT}")
