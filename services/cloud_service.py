import os
import traceback
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None


def _extract_rpc_result(response):
    data = getattr(response, 'data', None)
    if not data:
        return None
    if isinstance(data, list):
        if len(data) == 0:
            return None
        if len(data) == 1:
            item = data[0]
            if isinstance(item, dict) and 'key_string' in item:
                return item.get('key_string')
            return item
        first = data[0]
        if isinstance(first, dict) and 'key_string' in first:
            return first.get('key_string')
        return first
    if isinstance(data, dict):
        if 'key_string' in data:
            return data.get('key_string')
        return data
    return data


def get_active_groq_key_secure(cliente_id=None):
    if not supabase or cliente_id is None:
        return None
    try:
        cliente_id_str = str(cliente_id)
        response = supabase.rpc("obtener_llave_groq_segura", {"p_cliente_id": cliente_id_str}).execute()
        return _extract_rpc_result(response)
    except Exception as e:
        print(f"Error de seguridad: {e}")
        return None


def get_active_groq_key(cliente_id=None):
    return get_active_groq_key_secure(cliente_id)


def desactivar_llave_por_uso(key_string):
    if not supabase or not key_string:
        return False
    try:
        key_string_value = str(key_string)
        response = supabase.rpc("desactivar_llave_por_uso", {"key_string": key_string_value}).execute()
        if getattr(response, 'error', None):
            print(f"[FAILOVER] Error al desactivar llave: {response.error}")
            return False
        print("[FAILOVER] La llave ha llegado a su límite y fue desactivada en la nube.")
        return True
    except Exception as e:
        print(f"[FAILOVER] Error de seguridad al desactivar llave: {e}")
        return False


def quemar_llave_agotada(key_string):
    return desactivar_llave_por_uso(key_string)


def sincronizar_aplicacion(nombre_app="Bot_Instagram", version_app="1.0.0"):
    """
    Busca la aplicación en la BD. Si existe, actualiza su versión y retorna su ID.
    Si no existe, la inserta y retorna el nuevo ID.
    """
    if not supabase:
        return None

    try:
        app_data = {
            "nombre": nombre_app,
            "version_actual": version_app
        }

        response = supabase.table("aplicaciones").upsert(app_data, on_conflict="nombre").execute()
        if getattr(response, 'data', None):
            return response.data[0].get("id")

        retry = supabase.table("aplicaciones").select("id").eq("nombre", nombre_app).execute()
        if getattr(retry, 'data', None):
            return retry.data[0].get("id")

        return None
    except Exception as e:
        print(f"Error sincronizando aplicación: {e}")
        retry = supabase.table("aplicaciones").select("id").eq("nombre", nombre_app).execute()
        if getattr(retry, 'data', None):
            return retry.data[0].get("id")
        return None


def registrar_nuevo_usuario(datos_usuario, hwid, app_id, expiracion_codigo):
    if not supabase:
        return {"exito": False, "mensaje": "Conexión a Supabase no configurada."}

    try:
        hwid_response = supabase.table("licencias").select("id").eq("hwid_pc", hwid).execute()
        hwid_ya_existe = bool(getattr(hwid_response, 'data', None)) and len(hwid_response.data) > 0

        if hwid_ya_existe:
            estado_licencia = "TRIAL_AGOTADO"
            mensajes_trial = 0
            fecha_vencimiento_default = "2099-12-31"
        else:
            estado_licencia = "TRIAL"
            mensajes_trial = 10
            fecha_vencimiento_default = None

        cliente_payload = {
            "nombre_completo": datos_usuario.get("nombre"),
            "email": datos_usuario.get("email"),
            "password": datos_usuario.get("pw")
        }
        print(f"[DEBUG] Insertando cliente: {cliente_payload}")
        cliente_response = supabase.table("clientes").insert(cliente_payload).execute()
        if not getattr(cliente_response, 'data', None):
            raise Exception("No se pudo crear el cliente.")

        cliente_id = cliente_response.data[0].get("id")
        if not cliente_id:
            raise Exception("ID de cliente no disponible.")

        licencia_payload = {
            "cliente_id": cliente_id,
            "app_id": app_id,
            "estado": estado_licencia,
            "hwid_pc": hwid,
            "mensajes_restantes": mensajes_trial,
            "fecha_vencimiento": fecha_vencimiento_default,
            "expiracion_codigo": expiracion_codigo
        }
        licencia_response = supabase.table("licencias").insert(licencia_payload).execute()
        if not getattr(licencia_response, 'data', None):
            raise Exception("No se pudo crear la licencia.")

        licencia_id = licencia_response.data[0].get("id")
        if not licencia_id:
            raise Exception("ID de licencia no disponible.")

        pago_payload = {
            "cliente_id": cliente_id,
            "licencia_id": licencia_id,
            "monto": 0,
            "estado": "PENDIENTE",
            "metodo_pago": "REGISTRO",
            "referencia": "AUTO_REGISTRO",
            "fecha_transferencia": datetime.now().isoformat()
        }
        pago_response = supabase.table("pagos").insert(pago_payload).execute()
        if not getattr(pago_response, 'data', None):
            raise Exception("No se pudo registrar el pago.")

        mensaje_exito = "Usuario registrado"
        if hwid_ya_existe:
            mensaje_exito = "Usuario registrado, pero este equipo ya agotó su periodo de prueba."

        return {"exito": True, "mensaje": mensaje_exito}
    except Exception as e:
        mensaje_error = str(e)
        if "clientes_email_key" in mensaje_error or "duplicate" in mensaje_error.lower():
            return {"exito": False, "mensaje": "Este correo ya está registrado en el sistema."}
        return {"exito": False, "mensaje": f"Error de servidor: {mensaje_error}"}


def verificar_trial(licencia_id, token_cost=1):
    if not supabase:
        return {"permitido": False, "mensaje": "Conexión a Supabase no configurada."}

    try:
        response = supabase.table("licencias").select("*").eq("id", licencia_id).execute()
        data = response.data if hasattr(response, 'data') else None
        if not data or len(data) == 0:
            return {"permitido": False, "mensaje": "Licencia no encontrada."}

        licencia = data[0]
        estado = licencia.get("estado")
        mensajes_restantes = licencia.get("mensajes_restantes")
        tokens_restantes = licencia.get("tokens_restantes")

        if mensajes_restantes is None:
            mensajes_restantes = 0
        if tokens_restantes is None:
            tokens_restantes = mensajes_restantes

        if str(estado).upper() == "ACTIVO":
            return {"permitido": True, "restantes": {"mensajes": "ILIMITADOS", "tokens": "ILIMITADOS"}}

        if str(estado).upper() == "TRIAL":
            if mensajes_restantes > 0 and tokens_restantes >= token_cost:
                return {"permitido": True, "restantes": {"mensajes": mensajes_restantes, "tokens": tokens_restantes}}
            return {"permitido": False, "mensaje": "Has agotado tus mensajes o tokens de prueba. Por favor, realiza un pago."}

        return {"permitido": False, "mensaje": "Has agotado tus mensajes o tokens de prueba. Por favor, realiza un pago."}
    except Exception as e:
        return {"permitido": False, "mensaje": f"Error de servidor: {e}"}


def descontar_mensaje_trial(licencia_id, token_cost=1):
    if not supabase:
        return {"permitido": False, "mensaje": "Conexión a Supabase no configurada."}

    try:
        response = supabase.table("licencias").select("*").eq("id", licencia_id).execute()
        data = response.data if hasattr(response, 'data') else None
        if not data or len(data) == 0:
            return {"permitido": False, "mensaje": "Licencia no encontrada."}

        licencia = data[0]
        estado = licencia.get("estado")
        mensajes_restantes = licencia.get("mensajes_restantes")
        tokens_restantes = licencia.get("tokens_restantes")

        if mensajes_restantes is None:
            mensajes_restantes = 0
        if tokens_restantes is None:
            tokens_restantes = mensajes_restantes

        if str(estado).upper() == "ACTIVO":
            return {"permitido": True, "restantes": {"mensajes": "ILIMITADOS", "tokens": "ILIMITADOS"}}

        if str(estado).upper() == "TRIAL":
            if mensajes_restantes > 0 and tokens_restantes >= token_cost:
                nuevo_mensajes = max(0, mensajes_restantes - 1)
                nuevo_tokens = max(0, tokens_restantes - token_cost)
                update_payload = {"mensajes_restantes": nuevo_mensajes}
                if "tokens_restantes" in licencia:
                    update_payload["tokens_restantes"] = nuevo_tokens
                if nuevo_mensajes == 0 or nuevo_tokens == 0:
                    update_payload["estado"] = "TRIAL_AGOTADO"
                supabase.table("licencias").update(update_payload).eq("id", licencia_id).execute()
                return {"permitido": True, "restantes": {"mensajes": nuevo_mensajes, "tokens": nuevo_tokens}}

            supabase.table("licencias").update({"estado": "TRIAL_AGOTADO"}).eq("id", licencia_id).execute()
            return {"permitido": False, "mensaje": "Has agotado tus mensajes o tokens de prueba. Por favor, realiza un pago."}

        return {"permitido": False, "mensaje": "Has agotado tus mensajes o tokens de prueba. Por favor, realiza un pago."}
    except Exception as e:
        return {"permitido": False, "mensaje": f"Error de servidor: {e}"}


def validar_licencia_cliente(cliente_id, app_id=None, hwid_actual=None):
    if not supabase:
        return {
            "valido": False,
            "mensaje": "No se puede validar la licencia: conexión a Supabase no configurada."
        }

    if app_id is None:
        return {
            "valido": False,
            "mensaje": "No se proporcionó el ID de aplicación para validar la licencia."
        }

    try:
        cliente_id = str(cliente_id)
        app_id = int(app_id) if app_id is not None else None
        print(f"[DEBUG] validar_licencia_cliente cliente_id={cliente_id} app_id={app_id}")
        response = (
            supabase
            .table("licencias")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("app_id", app_id)
            .execute()
        )
        print(f"[DEBUG] Supabase response type: {type(response)}")
        if getattr(response, 'error', None):
            return {
                "valido": False,
                "mensaje": f"Error de Supabase al validar licencia: {response.error}"
            }
        data = response.data if hasattr(response, "data") else None
        print(f"[DEBUG] Supabase response data: {data}")
        if not data or len(data) == 0:
            return {
                "valido": False,
                "mensaje": "No tienes una licencia registrada para esta aplicación."
            }

        def parse_date(value):
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value).date()
                except ValueError:
                    try:
                        return datetime.strptime(value, "%Y-%m-%d").date()
                    except Exception:
                        return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return None

        def is_expired(lic):
            estado = str(lic.get("estado", "")).upper()
            if estado in ["TRIAL", "TRIAL_AGOTADO"]:
                return False
            fecha = parse_date(lic.get("fecha_vencimiento"))
            return fecha is not None and date.today() > fecha

        def license_priority(lic):
            estado = str(lic.get("estado", "")).upper()
            mensajes_restantes = lic.get("mensajes_restantes") or 0
            if estado == "ACTIVO":
                return 0
            if estado == "TRIAL" and mensajes_restantes > 0:
                return 1
            if estado == "TRIAL":
                return 2
            if estado == "TRIAL_AGOTADO":
                return 3
            return 4

        active_candidates = [lic for lic in data if not is_expired(lic)]
        if not active_candidates:
            licencia = data[0]
        else:
            licencia = sorted(active_candidates, key=lambda lic: license_priority(lic))[0]

        fecha_vencimiento_raw = licencia.get("fecha_vencimiento")
        estado = licencia.get("estado")

        licencia_vencimiento = parse_date(fecha_vencimiento_raw)

        estado_normalizado = str(estado).upper() if estado is not None else ""
        mensajes_restantes = licencia.get("mensajes_restantes")
        if mensajes_restantes is None:
            mensajes_restantes = 0

        if estado_normalizado == "ACTIVO":
            if not licencia_vencimiento or date.today() > licencia_vencimiento:
                return {
                    "valido": False,
                    "mensaje": "Tu suscripción ha vencido."
                }
        elif estado_normalizado == "TRIAL":
            tokens_restantes = licencia.get("tokens_restantes")
            if tokens_restantes is None:
                tokens_restantes = mensajes_restantes
            if mensajes_restantes <= 0 or tokens_restantes <= 0:
                return {
                    "valido": False,
                    "mensaje": "Has agotado tus mensajes o tokens de prueba. Por favor, realiza un pago."
                }
        elif estado_normalizado == "TRIAL_AGOTADO":
            return {
                "valido": False,
                "mensaje": "Has agotado tus mensajes o tokens de prueba. Por favor, realiza un pago."
            }
        else:
            return {
                "valido": False,
                "mensaje": "Licencia inválida."
            }

        hwid_pc = licencia.get("hwid_pc")
        if hwid_actual:
            if hwid_pc and hwid_pc != hwid_actual:
                return {
                    "valido": False,
                    "mensaje": "Esta licencia está vinculada a otro equipo."
                }
            if not hwid_pc:
                supabase.table("licencias").update({"hwid_pc": hwid_actual}).eq("id", licencia["id"]).execute()

        return {
            "valido": True,
            "datos_licencia": licencia,
            "datos": licencia
        }
    except Exception as e:
        error_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        print(f"[ERROR] validar_licencia_cliente excepción:\n{error_text}")
        return {
            "valido": False,
            "mensaje": f"Error al validar la licencia: {repr(e)}"
        }
