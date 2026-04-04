import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        # En el escritorio, tomamos la key directamente del entorno
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def generate_response(self, user_input, thread_id="default"):
        if not self.client:
            return "Configuración de IA pendiente."
        try:
            # Tu lógica original del repo
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Eres Pegasus, un asistente profesional."},
                    {"role": "user", "content": user_input}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error IA: {e}"