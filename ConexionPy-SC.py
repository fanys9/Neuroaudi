# -*- coding: utf-8 -*-
"""
Interfaz de respuestas + recepción de trials desde SuperCollider por OSC
"""

import csv
import os
import threading
from datetime import datetime
import keyboard  # type: ignore[import-untyped]
from pythonosc import dispatcher, osc_server  # type: ignore[import-untyped]

# CONFIGURACIÓN
# Nombre del participante: se asigna por interfaz web/GUI o por input() si se ejecuta por consola
subject = ""

# Ruta fija del CSV
#log_path = r"C:\Users\Maleja\Downloads\Tech\NeuroAudi\AudiCollab\respuestas_piloto.csv"
log_path = r"C:\Users\fanys\NeuroAudi\Python\respuestas_piloto.csv"

OSC_IP = "127.0.0.1"
OSC_PORT = 57121   # el mismo que pusiste en SuperCollider

# Variable global donde guardamos la info del trial actual
current_trial = {
    "trial": None,
    "az": None,
    "el": None,
    "dist": None,
    "freq": None,
}

# MANEJADOR OSC

def on_trial(address, trial, az, el, dist, freq):
    """
    Callback que recibe los trials desde SuperCollider.
    Mensaje esperado: /trial, trial, az, el, dist, freq
    """
    global current_trial
    current_trial["trial"] = int(trial)
    current_trial["az"] = float(az)
    current_trial["el"] = float(el)
    current_trial["dist"] = float(dist)
    current_trial["freq"] = float(freq)

    print(f"[OSC] Trial {trial} | az={az} el={el} dist={dist} freq={freq}")


def start_osc_server():
    disp = dispatcher.Dispatcher()
    disp.map("/trial", on_trial)

    server = osc_server.ThreadingOSCUDPServer((OSC_IP, OSC_PORT), disp)
    print(f"[OSC] Escuchando en {OSC_IP}:{OSC_PORT} ...")

    # Correr en hilo separado para no bloquear el teclado
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

# ARCHIVO CSV

# Crear archivo CSV con encabezado solo si no existe
file_exists = os.path.exists(log_path)

with open(log_path, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow([
            "timestamp",
            "subject",
            "trial",
            "azimuth",
            "elevation",
            "distance",
            "freq",
            "respuesta",
            "correcto"
        ])

# FUNCIÓN DE MAPEADO

def expected_key_from_stim(az, el):
    """
    Evaluación SOLO de izquierda (A) vs derecha (D)
    según el azimut del estímulo.
    Ignora elevación y distancia.
    """
    if az is None:
        return None

    az = float(az) % 360

    # Hemicampo derecho
    if 0 <= az < 180:
        return "D"

    # Hemicampo izquierdo
    if 180 <= az < 360:
        return "A"

    return None

# MAIN LOOP: TECLADO

def main():
    start_osc_server()

    # Contadores para estadísticas
    answered_trials = set()
    correct_count = 0
    total_count = 0

    print("=== Interfaz de respuestas ===")
    print("Sujeto:", subject)
    print("Presiona:")
    print("  A = Izquierda")
    print("  D = Derecha")
    print("Pulsa ESC para terminar.\n")

    while True:
        event = keyboard.read_event()  # espera a que se presione una tecla
        if event.event_type == keyboard.KEY_DOWN:
            key = event.name.upper()

            if key == "ESC":
                print("Terminando experimento...")
                break

            if key in ["W", "A", "S", "D", "X"]:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Solo nos interesa A/D en esta fase
                if key not in ["A", "D"]:
                    print("En esta fase solo usamos A (izquierda) y D (derecha).")
                    continue

                # Tomamos el trial y la posición actual que llegó por OSC
                trial = current_trial["trial"]
                az = current_trial["az"]
                el = current_trial["el"]
                dist = current_trial["dist"]
                freq = current_trial["freq"]

                if trial is None:
                    print("⚠ Aún no se ha recibido ningún trial desde SuperCollider.")
                    continue

                # Evitar más de una respuesta por trial
                if trial in answered_trials:
                    print(f"Ya se registró una respuesta para el trial {trial}, se ignora esta tecla.")
                    continue

                expected = expected_key_from_stim(az, el)
                correcto = (expected == key) if expected is not None else None

                # Marcamos que este trial ya tiene respuesta
                answered_trials.add(trial)

                # Actualizar contadores SOLO si la respuesta es A/D con esperado definido
                if expected is not None:
                    total_count += 1
                    if correcto:
                        correct_count += 1

                print(f"{subject} | Trial {trial}: tecla={key}, esperado={expected}, correcto={correcto}")

                # Guardar en CSV
                with open(log_path, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        ts,
                        subject,
                        trial,
                        az,
                        el,
                        dist,
                        freq,
                        key,
                        correcto
                    ])

    # Al salir, mostrar resumen
    if total_count > 0:
        acc = correct_count / total_count * 100
        print(f"\nResumen sujeto {subject}: {correct_count}/{total_count} correctos = {acc:.1f}%")
    else:
        print("\nNo se registraron respuestas válidas (A/D).")


if __name__ == "__main__":
    subject = input("Nombre del sujeto: ")
    main()