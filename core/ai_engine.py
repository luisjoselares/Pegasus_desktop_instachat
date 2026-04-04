import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        # En el escritorio, tomamos la key directamente del entorno
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

# Modificación en core/ai_engine.py
    def generate_response(self, user_input, system_prompt=None):
        if not self.client:
            return "Configuración de IA pendiente."
        
        # Si no viene un prompt específico, usamos uno por defecto
        contexto = system_prompt if system_prompt else "Eres Pegasus, un asistente profesional."
        
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
            return f"Error IA: {e}"