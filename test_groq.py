import os
from dotenv import load_dotenv
from groq import Groq
from services.cloud_service import get_active_groq_key


def mask_value(value: str, keep: int = 4) -> str:
    if not value:
        return "<vacío>"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


def main():
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    print("SUPABASE_URL cargada:", bool(supabase_url))
    print("SUPABASE_KEY cargada:", bool(supabase_key))
    if supabase_url:
        print("SUPABASE_URL:", mask_value(supabase_url))
    if supabase_key:
        print("SUPABASE_KEY:", mask_value(supabase_key))

    active_key = get_active_groq_key()
    if not active_key:
        print("ERROR: No se encontraron llaves activas en la tabla pool_keys de Supabase")
        return

    print("Llave Groq activa encontrada:", mask_value(active_key))

    try:
        client = Groq(api_key=active_key)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Eres un asistente que responde OK."},
                {"role": "user", "content": "Hola, responde solo con la palabra OK."}
            ],
            max_tokens=10
        )
        respuesta = completion.choices[0].message.content
        print("Respuesta Groq:", repr(respuesta))
        if "OK" in respuesta:
            print("¡CONEXIÓN EXITOSA! Groq está respondiendo correctamente")
        else:
            print("Advertencia: la respuesta no es la esperada, pero la conexión funcionó.")
    except Exception as e:
        print("ERROR al conectar con Groq:", str(e))


if __name__ == "__main__":
    main()
