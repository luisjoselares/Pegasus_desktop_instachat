# core/bot_engine.py
import time

class PegasusEngine:
    def __init__(self):
        self.is_running = False
        self.log_callback = None

    def set_callback(self, callback):
        self.log_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(f">>> {message}")

    def start(self, user, password):
        self.is_running = True
        self.log(f"Iniciando sesión para @{user}...")
        
        # Aquí va tu lógica de instagrapi original
        # Por ahora simulamos el bucle para probar la UI
        while self.is_running:
            self.log("Revisando mensajes nuevos...")
            time.sleep(5) 

    def stop(self):
        self.is_running = False
        self.log("Motor detenido.")