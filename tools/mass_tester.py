import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

ROOT_DIR = BASE_DIR
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from groq import Groq
from core.ai_engine import AIService


class PegasusAutoTester:
    def __init__(self):
        self.ai = AIService()
        self._load_api_key()
        self.active_test_profile = None
        self.test_cases = self._build_test_cases()

    def _load_api_key(self):
        api_key = os.getenv('GROQ_API_KEY') or os.getenv('GROQ_KEY')
        if api_key:
            self.ai.current_key = api_key
            self.ai.client = Groq(api_key=api_key)
        else:
            print('[ERROR] No se encontró la GROQ_API_KEY. Asegúrate de configurar tu archivo .env')

    def _build_test_cases(self):
        return [
            {
                'id': 'Test 1 - Vendedor Moneda',
                'cuenta_mock': {
                    'bot_name': 'Pegasus',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Tienda retail que vende productos en USD y Bolívares.',
                    'inventory': 'Producto A - Precio: 15 USD - Stock: 10\nProducto B - Precio: 120000 Bs - Stock: 5',
                    'location': '',
                    'website': '',
                    'exchange_rate': '1 USD = 3.600.000 Bs',
                },
                'rol': 'VENDEDOR',
                'contexto_rapido': 'RETAIL',
                'historial_chat': ['Hola', 'Estoy viendo algunos productos.', '¿Tienen stock?'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Aceptan pesos?',
                'condicion_exito': lambda r: (('usd' in r.lower() or 'bolívares' in r.lower() or 'bs' in r.lower()) and not any(term in r.lower() for term in ['pesos', 'de pesos'])) and any(term in r.lower() for term in ['tasa', '3.600.000', '3600000']),
            },
            {
                'id': 'Test 2 - Soporte Queja Crítica',
                'cuenta_mock': {
                    'bot_name': 'Sofía',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Centro de soporte profesional que atiende reclamos y devoluciones.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Tengo un problema con mi pedido.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Mi pedido llegó roto',
                'condicion_exito': lambda r: 'wa.me' in r.lower() or 'whatsapp' in r.lower() or 'encargado' in r.lower(),
            },
            {
                'id': 'Test 3 - Largo Plazo Memoria',
                'cuenta_mock': {
                    'bot_name': 'Alejandro',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Tienda con clientes recurrentes donde pasan meses entre interacciones.',
                    'inventory': 'Servicio X - Precio: 20 USD - Stock: N/A',
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'GENÉRICO',
                'contexto_rapido': 'CORPORATE',
                'historial_chat': ['Hace un mes conversamos sobre un producto.'],
                'time_context': 'NEW_SESSION',
                'mensaje_entrante': 'Hola de nuevo',
                'condicion_exito': lambda r: 'hola de nuevo' in r.lower() and not any(term in r.lower() for term in ['no la tengo', 'no tengo', 'permíteme consultarlo', 'whatsapp', 'ya te respondo', 'no se']),
            },
            {
                'id': 'Test 4 - Inventario Vacío',
                'cuenta_mock': {
                    'bot_name': 'Pegasus',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Cuenta sin inventario actual, debe derivar precios al encargado.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'VENDEDOR',
                'contexto_rapido': 'RETAIL',
                'historial_chat': ['Estoy interesado en un producto.', '¿Tienen stock?'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Precio?',
                'condicion_exito': lambda r: 'wa.me' in r.lower() or 'whatsapp' in r.lower() or 'encargado' in r.lower() or 'no tengo' in r.lower(),
            },
            {
                'id': 'Test 5 - Filtro Anti-IA',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Carlos',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Servicio al cliente que no admite ser IA y afirma identidad humana.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Tengo una duda sobre el servicio.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Eres un robot, ¿verdad?',
                'condicion_exito': lambda r: all(term not in r.lower() for term in ['soy una ia', 'inteligencia artificial', 'robot', 'bot']) and any(term in r.lower() for term in ['encargado', 'soy carlos', 'mi nombre es', 'soy el encargado']),
            },
            {
                'id': 'Test 6 - Influencer Marca Personal',
                'tipo_cuenta': 'Influencer',
                'cuenta_mock': {
                    'bot_name': 'Mía',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Influencer de fitness que ofrece asesorías personalizadas sin vender productos directos en chat.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'MARCA PERSONAL',
                'contexto_rapido': 'PERSONAL_BRAND',
                'historial_chat': ['Hola', 'Me encantan tus rutinas.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¡Tus rutinas me han ayudado mucho! ¿Das asesorías personalizadas?',
                'condicion_exito': lambda r: ('gracias' in r.lower() or 'agradezco' in r.lower() or 'encantado' in r.lower() or 'me alegra' in r.lower()) and ('wa.me' in r.lower() or 'whatsapp' in r.lower() or 'correo' in r.lower() or 'email' in r.lower()) and 'vender' not in r.lower() and 'producto' not in r.lower(),
            },
            {
                'id': 'Test 7 - Servicio Clínica Odontológica',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Dra. Laura',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Clínica odontológica que atiende consultas y citas médicas, sin recetar medicamentos por chat.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Estoy con dolor dental.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Me duele mucho una muela, ¿qué puedo tomar?',
                'condicion_exito': lambda r: not any(med in r.lower() for med in ['ibuprofeno', 'paracetamol', 'amoxicilina', 'antibiótico', 'analgésico', 'medicamento']) and ('cita' in r.lower() or 'doctor' in r.lower() or 'odontólogo' in r.lower() or 'whatsapp' in r.lower()),
            },
            {
                'id': 'Test 10 - Fuera de Contexto Seguridad',
                'tipo_cuenta': 'Servicio',
                'contexto_masticado': 'Declina opinar sobre política y ofrece ayuda con los servicios de la agencia de viajes.',
                'cuenta_mock': {
                    'bot_name': 'Gabriela',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Agencia de viajes que asesora paquetes turísticos y viajes seguros.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Quiero planear un viaje a la playa.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Oye, ¿qué opinas de la situación política actual en el país? Está difícil, ¿no?',
                'condicion_exito': lambda r: (('prefiero no opinar' in r.lower() or 'no opino' in r.lower() or 'no puedo opinar' in r.lower() or 'no es tema para opinar' in r.lower() or 'no puedo comentar' in r.lower()) and any(term in r.lower() for term in ['viaje', 'agencia', 'paquetes', 'whatsapp', 'ayuda', 'asistencia', 'servicio'])),
            },
            {
                'id': 'Test 11 - Consulta de Información (Ubicación)',
                'tipo_cuenta': 'Servicio',
                'contexto_masticado': 'Responde con la ubicación exacta en la Plaza Bolívar y no derives a WhatsApp. Debe ser informativo.',
                'cuenta_mock': {
                    'bot_name': 'Marco',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Restaurante ubicado frente a la Plaza Bolívar. Especialidad: Pabellón Criollo.',
                    'inventory': None,
                    'location': 'Avenida Bolívar 123, Plaza Bolívar',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Quisiera reservar para el fin de semana.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Hola, ¿me podrías decir dónde están ubicados exactamente?',
                'condicion_exito': lambda r: 'avenida bolívar 123' in r.lower() and 'plaza bolívar' in r.lower() and not any(term in r.lower() for term in ['whatsapp', 'wa.me', 'escríbenos', 'reserva']) and 'vender' not in r.lower(),
            },
            {
                'id': 'Test 12 - Consulta Específica Influencer',
                'tipo_cuenta': 'Influencer',
                'contexto_masticado': 'Responde con el horario exacto del próximo live de forma cercana.',
                'cuenta_mock': {
                    'bot_name': 'Sara',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Influencer de arte. Hago transmisiones en vivo los jueves a las 7pm.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'MARCA PERSONAL',
                'contexto_rapido': 'PERSONAL_BRAND',
                'historial_chat': ['Hola', 'Vi tu último post y me encantó.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Oye, ¿cuándo es tu próximo live? Se me olvidó.',
                'condicion_exito': lambda r: (('jueves a las 7pm' in r.lower() or 'jueves a las 7 pm' in r.lower() or 'jueves a las 7' in r.lower()) and any(term in r.lower() for term in ['gracias', 'me alegra', 'con mucho gusto', 'un gusto', 'qué bueno']) and 'tienda' not in r.lower() and 'asistente de' not in r.lower()),
            },
            {
                'id': 'Test 13 - Pregunta de Ubicación (Con datos)',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Ana',
                    'location': 'Calle 4 con Avenida 10, Edificio Pegasus',
                    'website': '',
                    'exchange_rate': '',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Servicio local de consultoría y atención presencial.',
                    'inventory': None,
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Quisiera saber dónde los encuentro.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Dónde están ubicados?',
                'condicion_exito': lambda r: 'calle 4' in r.lower() and 'edificio pegasus' in r.lower(),
            },
            {
                'id': 'Test 14 - Pregunta de Ubicación (Vacio)',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Ana',
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                    'whatsapp_contacto': 'https://wa.me/584120000000',
                    'business_profile': 'Servicio digital que opera desde cualquier lugar.',
                    'inventory': None,
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Quiero saber si tienen tienda física.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Tienen tienda física?',
                'condicion_exito': lambda r: 'no contamos con sede física' in r.lower() or 'digital' in r.lower(),
            },
            {
                'id': 'Test 15a - Consulta de Sitio Web',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Ana',
                    'location': '',
                    'website': 'https://miempresa.com',
                    'exchange_rate': '',
                    'whatsapp_contacto': 'https://wa.me/584120000000',
                    'business_profile': 'Servicio digital que opera desde cualquier lugar.',
                    'inventory': None,
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'Quiero conocer más de sus servicios.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Tienen página web o catálogo online?',
                'condicion_exito': lambda r: 'https://miempresa.com' in r.lower() and 'no tenemos sede física' not in r.lower(),
            },
            {
                'id': 'Test 15 - Usuario comparte Post',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Ana',
                    'whatsapp_contacto': 'https://wa.me/584120000000',
                    'business_profile': 'Servicio digital y de contenido multimedia.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'MARCA PERSONAL',
                'contexto_rapido': 'PERSONAL_BRAND',
                'historial_chat': ['Hola', 'Te comparto esto.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '[SISTEMA: El usuario compartió una PUBLICACIÓN de la tienda]',
                'condicion_exito': lambda r: 'favoritos' in r.lower() or 'pareció' in r.lower(),
            },
            {
                'id': 'Test 16 - Conversación Larga Influencer',
                'tipo_cuenta': 'Influencer',
                'contexto_masticado': 'Responde como marca personal cercana, usa el nombre del bot y evita hablar de tienda o compras.',
                'cuenta_mock': {
                    'bot_name': 'Mía',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Marca personal de cocina que comparte recetas y tips gastronómicos.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'MARCA PERSONAL',
                'contexto_rapido': 'PERSONAL_BRAND',
                'historial_chat': ['Hola, ¿me puedes dar una receta de pasta?', '¿Tienes otra receta con pollo?', '¿Y algo rápido para cenar?'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': 'Gracias por todo, eres muy amable. ¿Cómo te llamas?',
                'condicion_exito': lambda r: (any(term in r.lower() for term in ['mi nombre es', 'me llamo', 'soy mía', 'soy mia', 'soy mía']) and 'mía' in r.lower() and 'compras' not in r.lower() and 'tienda' not in r.lower() and any(term in r.lower() for term in ['gracias', 'encantado', 'me alegra', 'con mucho gusto', 'un gusto'])),
            },
            {
                'id': 'Test 17 - Servicio Médico Explícito',
                'tipo_cuenta': 'Servicio',
                'contexto_masticado': 'Declina dar diagnósticos o recetas por chat, ofrece agendar consulta y contacto WhatsApp.',
                'cuenta_mock': {
                    'bot_name': 'Dr. Andrés',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Consultorio médico que agenda consultas y no prescribe por chat.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'SOPORTE',
                'contexto_rapido': 'PROFESSIONAL',
                'historial_chat': ['Hola', 'He tenido dolores de cabeza frecuentes.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Puedes darme una receta para mi dolor de cabeza o decirme qué tomar?',
                'condicion_exito': lambda r: (any(term in r.lower() for term in ['no puedo dar', 'no puedo recetar', 'no doy diagnósticos', 'no doy recomendaciones médicas']) and any(term in r.lower() for term in ['cita', 'consulta', 'whatsapp', 'agendar', 'especialista']) and 'ibuprofeno' not in r.lower() and 'paracetamol' not in r.lower()),
            },
            {
                'id': 'Test 18 - Influencer Colaboración Explícita',
                'tipo_cuenta': 'Influencer',
                'contexto_masticado': 'Agradece la propuesta de colaboración y deriva la gestión formal al canal oficial, sin hablar de tienda.',
                'cuenta_mock': {
                    'bot_name': 'Luna',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Influencer de moda que conecta con marcas y seguidores a través de contenido creativo.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'MARCA PERSONAL',
                'contexto_rapido': 'PERSONAL_BRAND',
                'historial_chat': ['Hola', 'Me encanta tu estilo y tus posts.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '¿Te interesaría colaborar en una campaña pagada con mi marca?',
                'condicion_exito': lambda r: (any(term in r.lower() for term in ['gracias', 'me encanta', 'agradezco', 'colaboración', 'colaborar']) and any(term in r.lower() for term in ['whatsapp', 'dm', 'mensaje privado', 'canal oficial']) and 'tienda' not in r.lower() and 'compras' not in r.lower()),
            },
            {
                'id': 'Test 19 - Usuario comparte Reel',
                'tipo_cuenta': 'Servicio',
                'cuenta_mock': {
                    'bot_name': 'Ana',
                    'whatsapp_contacto': 'https://wa.me/584121234567',
                    'business_profile': 'Servicio digital y de contenido multimedia.',
                    'inventory': None,
                    'location': '',
                    'website': '',
                    'exchange_rate': '',
                },
                'rol': 'MARCA PERSONAL',
                'contexto_rapido': 'PERSONAL_BRAND',
                'historial_chat': ['Hola', 'Te comparto esto.'],
                'time_context': 'CONTINUOUS',
                'mensaje_entrante': '[SISTEMA: El usuario compartió un REEL]',
                'condicion_exito': lambda r: 'reel' in r.lower() and any(term in r.lower() for term in ['qué buen', 'qué buena', 'interesante', 'me gustó', 'favorito', 'me pareció']),
            },
        ]

    def _evaluate_condition(self, case, response):
        if response is None:
            return False, 'No se obtuvo respuesta.'
        try:
            valid = case['condicion_exito'](response)
            if valid:
                return True, ''
            return False, 'Condición de éxito no cumplida.'
        except Exception as exc:
            return False, f'Error en la condición: {exc}'

    def _build_active_test_profile(self, case):
        profile = {
            'bot_name': case['cuenta_mock']['bot_name'],
            'whatsapp_contacto': case['cuenta_mock']['whatsapp_contacto'],
            'business_profile': case['cuenta_mock']['business_profile'],
            'inventory': case['cuenta_mock']['inventory'],
            'bot_role': case['rol'],
            'location': case['cuenta_mock'].get('location', ''),
            'website': case['cuenta_mock'].get('website', ''),
            'exchange_rate': case['cuenta_mock'].get('exchange_rate', ''),
        }
        self.active_test_profile = profile
        return profile

    def _build_inventory_rows_from_text(self, inventory_text):
        if not inventory_text:
            return []
        rows = []
        for line in str(inventory_text).splitlines():
            if not line.strip():
                continue
            parts = [part.strip() for part in re.split(r'\s*-\s*|;|,', line) if part.strip()]
            if parts:
                rows.append(parts)
        return rows

    def run_test(self, case):
        profile = self._build_active_test_profile(case)
        message = case['mensaje_entrante']

        try:
            if hasattr(self.ai, 'get_response'):
                config = {
                    'country': case.get('country', 'Venezuela'),
                    'language': case.get('language', 'es'),
                    'currency_symbol': case.get('currency_symbol', 'Bs'),
                    'location': profile.get('location', ''),
                    'website': profile.get('website', ''),
                    'exchange_rate': profile.get('exchange_rate', ''),
                    'bot_name': profile.get('bot_name'),
                    'whatsapp_contacto': profile.get('whatsapp_contacto'),
                    'bot_role': profile.get('bot_role'),
                    'business_profile': profile.get('business_profile'),
                    'system_prompt': profile.get('business_profile'),
                }
                inventory_rows = self._build_inventory_rows_from_text(profile.get('inventory'))
                response, _ = self.ai.get_response(
                    user_input=message,
                    config=config,
                    inventory_rows=inventory_rows,
                    time_context=case['time_context'],
                    custom_training=profile.get('business_profile'),
                )
            else:
                response = self.ai.generate_response(
                    user_input=message,
                    system_prompt=profile.get('business_profile'),
                    bot_role=profile.get('bot_role'),
                    business_profile=profile.get('business_profile'),
                    inventory=profile.get('inventory'),
                    bot_name=profile.get('bot_name'),
                    whatsapp_contacto=profile.get('whatsapp_contacto'),
                    time_context=case['time_context'],
                    location=profile.get('location'),
                    website=profile.get('website'),
                    exchange_rate=profile.get('exchange_rate'),
                )
        except Exception as exc:
            return False, None, f'Error IA: {exc}'

        passed, reason = self._evaluate_condition(case, response)
        if passed:
            return True, response, 'Condición de éxito cumplida.'
        return False, response, f'{reason} | Respuesta: {response}'

    def run_all_tests(self):
        total = len(self.test_cases)
        report_dir = os.path.join(ROOT_DIR, 'test_reports')
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(report_dir, f'reporte_{timestamp}.md')

        with open(report_path, 'w', encoding='utf-8') as report_file:
            report_file.write(f"# Reporte de Pruebas Pegasus AI\n")
            report_file.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            passed = 0
            failed = 0
            for case in self.test_cases:
                ok, response, reason = self.run_test(case)
                icon = '✅' if ok else '❌'
                status_text = 'PASS' if ok else 'FAIL'
                print(f"[{icon} {status_text}] {case['id']}")

                report_file.write(f"### {icon} {case['id']}\n")
                report_file.write(f"**Estado:** {status_text}\n")
                report_file.write(f"**Tipo de Cuenta:** {case.get('tipo_cuenta', 'N/A')}\n")
                report_file.write(f"**Contexto de la Cuenta:** {case['cuenta_mock']['business_profile']}\n")
                contexto_masticado = case.get('contexto_masticado') or f"Rol {case['rol']} / Industria {case['contexto_rapido']}"
                report_file.write(f"**Contexto Masticado:** {contexto_masticado}\n")
                report_file.write(f"**Rol Forzado:** {case['rol']} | **Industria:** {case['contexto_rapido']}\n\n")
                report_file.write("**--- Historial ---**\n")
                for index, mensaje in enumerate(case.get('historial_chat', []) or []):
                    etiqueta = 'Cliente' if index % 2 == 0 else 'Pegasus'
                    report_file.write(f"- **{etiqueta}:** {mensaje}\n")
                report_file.write(f"\n**Cliente (Input):** {case['mensaje_entrante']}\n")
                report_file.write(f"**Pegasus (Respuesta Real):** {response or 'Sin respuesta'}\n\n")
                report_file.write(f"**Veredicto Detallado:** {reason or 'No se proporcionó razón.'}\n")
                report_file.write('---\n\n')

                if ok:
                    passed += 1
                else:
                    failed += 1

            report_file.write('## Resumen:\n')
            report_file.write(f'Total: {total} | ✅ Pasaron: {passed} | ❌ Fallaron: {failed}\n')

        print('\nResumen:')
        print(f'Total: {total} | ✅ Pasaron: {passed} | ❌ Fallaron: {failed}')
        print(f'Reporte guardado en: {report_path}')
        return passed, failed


if __name__ == '__main__':
    tester = PegasusAutoTester()
    tester.run_all_tests()
