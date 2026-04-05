import logging
from groq import Groq
from dotenv import load_dotenv
from services.cloud_service import get_active_groq_key, desactivar_llave_por_uso, descontar_mensaje_trial

load_dotenv()

class AIService:
    def __init__(self):
        self.current_key = None
        self.licencia_id = None
        self.cliente_id = None
        self.trial_status_callback = None
        self.client = None
        self._refresh_client()

    def set_licencia_id(self, licencia_id):
        self.licencia_id = licencia_id

    def set_cliente_id(self, cliente_id):
        self.cliente_id = cliente_id
        self._refresh_client()

    def set_trial_status_callback(self, callback):
        self.trial_status_callback = callback

    def _refresh_client(self):
        if not self.cliente_id:
            logging.critical("[NUBE] No hay un cliente identificado. Imposible solicitar llaves.")
            self.current_key = None
            self.client = None
            return

        self.current_key = get_active_groq_key(self.cliente_id)
        if not self.current_key:
            logging.critical("[NUBE] Permiso denegado o no hay llave activa para este cliente en Supabase.")
            self.client = None
        else:
            self.client = Groq(api_key=self.current_key)
            logging.info("[NUBE] Clave Groq activa actualizada desde Supabase.")

    def generate_response(self, user_input, system_prompt=None):
        if not self.client:
            self._refresh_client()

        if not self.client:
            raise RuntimeError("Configuración de IA pendiente. No hay clave activa en Supabase.")

        contexto = system_prompt if system_prompt else "Eres Pegasus, un asistente profesional."

        if self.licencia_id:
            validacion = descontar_mensaje_trial(self.licencia_id)
            if not validacion.get("permitido", False):
                mensaje = validacion.get("mensaje", "Acceso denegado por límite de prueba.")
                logging.warning(f"[TRIAL] El bot se ha detenido automáticamente: {mensaje}")
                return None
            if self.trial_status_callback:
                self.trial_status_callback(validacion.get("restantes"))
            logging.info(f"[TRIAL] Mensajes restantes: {validacion.get('restantes')}")

        for attempt in range(3):
            try:
                completion = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": contexto},
                        {"role": "user", "content": user_input}
                    ]
                )
                return completion.choices[0].message.content
            except Exception as e:
                mensaje_error = str(e)
                es_rate_limit = "429" in mensaje_error or "RateLimit" in mensaje_error or "rate limit" in mensaje_error.lower()
                logging.warning(f"[IA] Intento {attempt + 1} fallido: {mensaje_error}")

                if es_rate_limit and self.current_key:
                    desactivar_llave_por_uso(self.current_key)
                    self._refresh_client()
                    if not self.client:
                        break
                    continue
                raise RuntimeError(f"Error IA: {e}")

        return "En este momento nuestro sistema está saturado, por favor espera unos minutos"
