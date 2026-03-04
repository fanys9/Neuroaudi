# Neuroaudi
Interfaz web — Experimento de audio NeuroAudi
Interfaz web local (HTML + CSS + JavaScript) con backend Flask para controlar el experimento de audio que se comunica con SuperCollider por OSC.

Requisitos
Python 3.8 o superior
SuperCollider en ejecución
Dependencias de Python
Instalación
Abrir una terminal en la carpeta del proyecto (Python).

Crear un entorno virtual (recomendado):

python -m venv venv
venv\Scripts\activate
Instalar dependencias:

pip install -r requirements-web.txt
Ejecución
Asegurarse de que SuperCollider está corriendo y enviando mensajes OSC al puerto configurado en ConexionPy-SC.py (por defecto 57121).

Iniciar el servidor web:

python app.py
Abrir el navegador en:

http://127.0.0.1:5000/
En la interfaz:

Escribir el nombre del participante (obligatorio).
Pulsar Iniciar prueba Y arrancar el sonido
Durante la prueba: responder con A (izquierda) o D (derecha) según las instrucciones.
Detener prueba (botón rojo): detiene la reproducción, guarda los datos y finaliza la prueba.
Estructura del proyecto
Python/
├── app.py                 # Backend Flask 
├── ConexionPy-SC.py       # Lógica del experimento (SuperCollider + OSC)
├── requirements-web.txt   # Dependencias para la interfaz web
├── INSTRUCCIONES.md       # Este archivo
└── static/
    ├── index.html         # Página principal
    ├── css/
    │   └── style.css      # Estilos
    └── js/
        └── app.js         # Lógica de la interfaz (fetch al backend)
API del backend
GET /api/estado — Devuelve el estado actual: listo, ejecutando o detenido.
POST /api/iniciar — Inicia la prueba. Cuerpo JSON: { "nombre": "Nombre del participante" }. Devuelve error si el nombre está vacío o ya hay una prueba en ejecución.
POST /api/detener — Detiene la prueba (envía ESC), guarda los datos y finaliza la prueba.
POST /api/respuesta — Registra una respuesta del participante. Cuerpo JSON: { "nombre": "...", "respuesta": "left" | "right", "timestamp": "..." }. Solo acepta cuando el estado es ejecutando. El backend inyecta la tecla A/D para que la lógica existente la procese.
Notas
La aplicación corre solo en local (127.0.0.1:5000). No está pensada para acceso desde otras máquinas.
Para ejecutar el experimento por consola (sin interfaz web), usar: python ConexionPy-SC.py.

