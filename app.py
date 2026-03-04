# -*- coding: utf-8 -*-
"""
Backend Flask para la interfaz web del experimento de audio.
Solo invoca funciones existentes de ConexionPy-SC (no reimplementa lógica).

Flujo experimental:
- Iniciar: asigna nombre del participante y arranca logic.main() en un hilo (OSC + SuperCollider).
- Respuesta: el frontend captura A/D en JavaScript y POST /api/respuesta; el backend inyecta
  la tecla para que logic.main() la procese y guarde en CSV.
- Detener: envía ESC; main() termina de forma normal, guarda todos los datos y finaliza la prueba.
"""

import importlib.util
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# Cargar módulo de lógica (archivo ConexionPy-SC.py, nombre con guión)
_script_dir = Path(__file__).resolve().parent
_logic_path = _script_dir / "ConexionPy-SC.py"
_spec = importlib.util.spec_from_file_location("logic_experimento", _logic_path)
logic = importlib.util.module_from_spec(_spec)
sys.modules["logic_experimento"] = logic
_spec.loader.exec_module(logic)  # type: ignore[union-attr]

# Para detener: enviamos ESC al proceso (el main() existente sale con ESC)
try:
    import keyboard  # type: ignore[import-untyped]
except ImportError:
    keyboard = None

app = Flask(__name__, static_folder="static")

# Estado global: "listo" | "ejecutando" | "detenido"
_estado = "listo"
_lock = threading.Lock()


def _set_estado(valor: str) -> None:
    with _lock:
        global _estado
        _estado = valor


def _get_estado() -> str:
    with _lock:
        return _estado


def _run_main():
    """Ejecuta logic.main(); al terminar pone estado detenido."""
    try:
        logic.main()
    finally:
        if _get_estado() == "ejecutando":
            _set_estado("detenido")


@app.route("/")
def index():
    """Sirve la página principal."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/estado", methods=["GET"])
def api_estado():
    """Devuelve el estado actual del experimento."""
    return jsonify({"estado": _get_estado()})


@app.route("/api/iniciar", methods=["POST"])
def api_iniciar():
    """
    Inicia la prueba: asigna nombre del participante y arranca logic.main() en un hilo.
    Suposición: se usan logic.subject y logic.main() (sin reimplementar).
    """
    global _estado
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()

    if not nombre:
        return jsonify({"ok": False, "error": "El nombre del participante es obligatorio."}), 400

    if _get_estado() == "ejecutando":
        return jsonify({"ok": False, "error": "Ya hay una prueba en ejecución."}), 409

    # Asignar participante y arrancar lógica existente en segundo plano
    logic.subject = nombre
    _set_estado("ejecutando")
    thread = threading.Thread(target=_run_main, daemon=True)
    thread.start()

    return jsonify({"ok": True, "estado": "ejecutando"})


@app.route("/api/detener", methods=["POST"])
def api_detener():
    """
    Detiene la prueba de forma normal (reproducción se detiene, datos se mantienen).
    Envía ESC al proceso; el bucle principal de logic.main() termina y guarda todo.
    """
    if _get_estado() != "ejecutando":
        return jsonify({"ok": True, "estado": _get_estado()})

    if keyboard is None:
        _set_estado("detenido")
        return jsonify({"ok": True, "estado": "detenido"})

    try:
        keyboard.send("esc")
    except Exception:
        pass
    _set_estado("detenido")
    return jsonify({"ok": True, "estado": "detenido"})


@app.route("/api/respuesta", methods=["POST"])
def api_respuesta():
    """
    Recibe una respuesta del participante (A = izquierda, D = derecha) desde el frontend.
    Inyecta la tecla para que logic.main() la procese y guarde en CSV.
    Cuerpo: { "nombre": "...", "respuesta": "left" | "right", "timestamp": "..." }
    """
    if _get_estado() != "ejecutando":
        return jsonify({"ok": False, "error": "La prueba no está activa."}), 409

    data = request.get_json(silent=True) or {}
    respuesta = (data.get("respuesta") or "").strip().lower()
    if respuesta not in ("left", "right"):
        return jsonify({"ok": False, "error": "respuesta debe ser 'left' o 'right'."}), 400

    # Mapear a tecla: left → A, right → D (logic.main() usa keyboard.read_event())
    key = "a" if respuesta == "left" else "d"
    if keyboard is not None:
        try:
            keyboard.send(key)
        except Exception:
            return jsonify({"ok": False, "error": "Error al registrar la respuesta."}), 500

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
