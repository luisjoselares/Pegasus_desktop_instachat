# core/bot_engine.py
import time
import json
from services.database_service import LocalDBService
from core.ai_engine import AIService

AGENDA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "agendar_cita",
            "description": "Agenda una nueva cita para un cliente en el sistema. Úsala SOLAMENTE cuando el cliente haya confirmado la fecha, la hora y el servicio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_nombre": {"type": "string", "description": "Nombre del cliente"},
                    "fecha_hora": {"type": "string", "description": "Fecha y hora en formato YYYY-MM-DD HH:MM"},
                    "servicio": {"type": "string", "description": "Servicio solicitado"}
                },
                "required": ["cliente_nombre", "fecha_hora", "servicio"]
            }
        }
    }
]

class PegasusEngine:
    def __init__(self):
        self.is_running = False
        self.log_callback = None
        self.db = LocalDBService()
        self.ai = AIService()
        self.chat_history = []
        self.pending_messages = []

    def set_callback(self, callback):
        self.log_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(f">>> {message}")

    def start(self, user, password):
        self.is_running = True
        self.log(f"Iniciando sesión para @{user}...")
        
        # Aquí va tu lógica de instagrapi original
        # Por ahora procesamos mensajes en cola para probar la UI
        while self.is_running:
            if self.pending_messages:
                message = self.pending_messages.pop(0)
                self.log(f"Procesando mensaje de usuario: {message}")
                response = self.process_user_message(message)
                self.log(f"Respuesta final: {response}")
            else:
                time.sleep(1)

    def stop(self):
        self.is_running = False
        self.log("Motor detenido.")

    def queue_message(self, message):
        self.pending_messages.append(message)

    def process_user_message(self, user_message):
        self.chat_history.append({"role": "user", "content": user_message})

        response = self.ai.generate_response(
            user_input=user_message,
            chat_history=self.chat_history,
            tools=AGENDA_TOOLS
        )

        if isinstance(response, dict) and response.get("tool_calls"):
            tool_call = response["tool_calls"][0]
            tool_name = None
            tool_args = None

            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name") or (tool_call.get("function") or {}).get("name")
                tool_args = (tool_call.get("function") or {}).get("arguments")
            else:
                tool_name = getattr(tool_call, "name", None)
                tool_function = getattr(tool_call, "function", None)
                tool_args = getattr(tool_function, "arguments", None) if tool_function else None

            if tool_name == "agendar_cita" and tool_args:
                try:
                    values = json.loads(tool_args)
                except Exception:
                    values = {}

                cliente_nombre = values.get("cliente_nombre")
                fecha_hora = values.get("fecha_hora")
                servicio = values.get("servicio")

                if cliente_nombre and fecha_hora and servicio:
                    self.db.insert_cita(cliente_nombre, fecha_hora, servicio)

                    tool_response = {
                        "role": "tool",
                        "name": "agendar_cita",
                        "content": "Cita agendada exitosamente"
                    }
                    if isinstance(tool_call, dict) and tool_call.get("id"):
                        tool_response["tool_call_id"] = tool_call.get("id")
                    elif hasattr(tool_call, "id"):
                        tool_response["tool_call_id"] = getattr(tool_call, "id")

                    self.chat_history.append(tool_response)

                    final_response = self.ai.generate_response(
                        user_input="",
                        chat_history=self.chat_history,
                        tools=None
                    )
                    if isinstance(final_response, tuple):
                        final_response = final_response[0]
                    self.chat_history.append({"role": "assistant", "content": final_response})
                    return final_response

        if isinstance(response, tuple):
            response = response[0]

        if isinstance(response, str):
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        return "Lo siento, ocurrió un error al procesar tu mensaje."
