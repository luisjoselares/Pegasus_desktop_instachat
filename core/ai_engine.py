import logging
import re
from groq import Groq
from dotenv import load_dotenv
from services.cloud_service import get_active_groq_key, desactivar_llave_por_uso, descontar_mensaje_trial, verificar_trial

load_dotenv()

class AIService:
    def __init__(self):
        self.current_key = None
        self.licencia_id = None
        self.cliente_id = None
        self.trial_status_callback = None
        self.client = None

    def set_licencia_id(self, licencia_id):
        self.licencia_id = licencia_id

    def set_cliente_id(self, cliente_id):
        self.cliente_id = cliente_id
        self._refresh_client()

    def set_trial_status_callback(self, callback):
        self.trial_status_callback = callback

    def _refresh_client(self):
        if not self.cliente_id:
            logging.debug("[NUBE] No hay un cliente identificado. Imposible solicitar llaves.")
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

    def _estimate_token_usage(self, text):
        if not text:
            return 1
        # Aproximación simple: 1 token por cada 4 caracteres de texto
        estimated = max(1, len(text) // 4)
        return estimated

    def generate_response(self, user_input, system_prompt=None):
        if not self.client:
            self._refresh_client()

        if not self.client:
            raise RuntimeError("Configuración de IA pendiente. No hay clave activa en Supabase.")

        contexto = system_prompt if system_prompt else "Eres Pegasus, un asistente profesional."

        input_tokens = 0
        if self.licencia_id:
            input_tokens = self._estimate_token_usage(user_input)
            expected_cost = input_tokens + 20
            validacion = verificar_trial(self.licencia_id, token_cost=expected_cost)
            if not validacion.get("permitido", False):
                mensaje = validacion.get("mensaje", "Acceso denegado por límite de prueba.")
                logging.warning(f"[TRIAL] El bot se ha detenido automáticamente: {mensaje}")
                return None
            if self.trial_status_callback:
                self.trial_status_callback(validacion.get("restantes"))
            logging.info(f"[TRIAL] Verificación previa exitosa. Uso de tokens estimado: {expected_cost}, estado: {validacion.get('restantes')}")

        for attempt in range(3):
            try:
                completion = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": contexto},
                        {"role": "user", "content": user_input}
                    ]
                )
                respuesta = completion.choices[0].message.content
                respuesta = self._sanitize_ai_response(respuesta)
                if self.licencia_id:
                    respuesta_tokens = self._estimate_token_usage(respuesta)
                    total_cost = input_tokens + respuesta_tokens
                    validacion = descontar_mensaje_trial(self.licencia_id, token_cost=total_cost)
                    if self.trial_status_callback:
                        self.trial_status_callback(validacion.get("restantes"))
                    logging.info(f"[TRIAL] Tokens descontados: {total_cost}, estado: {validacion.get('restantes')}")
                return respuesta
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

    def _sanitize_ai_response(self, respuesta):
        if not respuesta:
            return respuesta

        texto = respuesta.strip()

        # Evitar que el asistente admita ser IA o bot
        texto = re.sub(
            r"\b(asistente virtual|inteligencia artificial|IA|bot|robot|soy un bot|soy una IA|no soy humano|no soy una IA)\b",
            "encargado digital",
            texto,
            flags=re.IGNORECASE
        )

        fuera_contexto = [
            "clima", "meteorólogo", "veterinario", "médico", "doctor", "salud", "temperatura",
            "tiempo", "hotel", "seguro", "abogado", "jurídico", "ley", "finanzas", "bolsa",
            "dinero", "banco", "inversión", "codigo", "código", "teléfono", "móvil", "llamar",
            "correo", "dirección", "direcciones", "carro", "automóvil", "taxi", "transporte",
            "política", "político", "noticias"
        ]

        if any(palabra in texto.lower() for palabra in fuera_contexto):
            return "Lo siento, esa información no la tengo a mano; permíteme consultarlo con el encargado y te responderé con precisión."

        return texto
