# controllers/instagram_controller.py
from services.instagram_service import InstagramService

class InstagramController:
    """
    Controlador Senior para la gestión de cuentas de Instagram.
    Actúa como puente entre LocalDBService y la interfaz modernizada de Pegasus.
    """
    def __init__(self, db_service, engine=None, security_service=None, cliente_id=None):
        self.db = db_service
        self.view = None
        self.engine = engine if engine is not None else InstagramService()
        self.security_service = security_service
        self.cliente_id = cliente_id
        self.main_controller = None
        if cliente_id and hasattr(self.engine, 'set_cliente_id'):
            self.engine.set_cliente_id(cliente_id)

    def set_main_controller(self, controller):
        self.main_controller = controller

    def set_licencia_id(self, licencia_id):
        self.engine.set_licencia_id(licencia_id)

    def set_trial_status_callback(self, callback):
        self.engine.set_trial_status_callback(callback)

    def set_view(self, view, cliente_id=None):
        """Vincula la página de cuentas y realiza la carga inicial."""
        self.view = view
        if cliente_id is not None:
            self.cliente_id = cliente_id
            if hasattr(self.engine, 'set_cliente_id'):
                self.engine.set_cliente_id(cliente_id)
        self.refresh(cliente_id)

    def refresh(self, cliente_id=None):
        """Actualiza la lista de tarjetas obteniendo los datos reales de la DB."""
        if self.view:
            current_id = cliente_id if cliente_id is not None else self.cliente_id
            accounts = self.db.obtener_cuentas(current_id)
            conversaciones = self.db.obtener_conversaciones_recientes(current_id)
            for account in accounts:
                account["conversations"] = conversaciones
            self.view.load_accounts(accounts)

    def add_account(self, data, cliente_id=None):
        """
        Procesa el alta de una cuenta desde el AddAccountDialog.
        'data' contiene: user, pass, type, start, end, proxy, prompt.
        """
        if not data.get('user') or not data.get('pass'):
            print("⚠️ Error: Intento de agregar cuenta con campos obligatorios vacíos.")
            return

        account_data = data.copy()
        if self.security_service and account_data.get('pass'):
            account_data['pass'] = self.security_service.encrypt(account_data['pass'])

        # Guardamos en la base de datos
        self.db.agregar_cuenta(account_data, cliente_id or self.cliente_id)
        
        # Opcional: Registrar el evento inicial en el log de la tarjeta
        # (Necesitaremos el ID, pero al refrescar aparecerá con el default 'Sistema listo')
        self.refresh(cliente_id)
        print(f"Controlador: Cuenta {data['user']} añadida correctamente.")

    def toggle_bot(self, account_id, state):
        """
        Activa o desactiva la operación de la IA para una cuenta específica.
        Sincroniza con la DB y actualiza el log visual (Cyan).
        """
        self.db.actualizar_estado_bot(account_id, state)
        
        # Actualizamos el log para que el usuario vea el cambio en la tarjeta
        status_text = "ENCENDIDO" if state else "APAGADO"
        log_msg = f"Bot {status_text} - El sistema está en modo {'automático' if state else 'manual'}."
        self.db.actualizar_log(account_id, log_msg)
        
        # Imprimimos en consola para el desarrollador (Debug)
        print(f"Controlador: Switch de Bot ID {account_id} movido a {status_text}")

        if self.main_controller:
            if state:
                self.main_controller.iniciar_bot()
            else:
                self.main_controller.detener_bot()

    def get_conversation_history(self, thread_id):
        if not thread_id:
            return []
        if hasattr(self.db, 'obtener_conversacion_completa'):
            return self.db.obtener_conversacion_completa(thread_id)
        return []

    def update_account_context(self, account_id, prompt):
        """
        Actualiza el System Prompt (Personalidad) de la cuenta.
        """
        # Nota: Asegúrate de que el método actualizar_contexto exista en tu database_service
        # Si no lo tienes, puedes añadirlo rápidamente.
        if hasattr(self.db, 'actualizar_contexto'):
            self.db.actualizar_contexto(account_id, prompt)
            self.db.actualizar_log(account_id, "Contexto de IA actualizado con éxito.")
            print(f"Controlador: Prompt actualizado para cuenta {account_id}")
        else:
            print("⚠️ Error: El método 'actualizar_contexto' no existe en el DB Service.")

    def delete_account(self, account_id):
        """Elimina la cuenta y refresca la vista inmediatamente."""
        self.db.eliminar_cuenta(account_id)
        self.refresh()
        print(f"Controlador: Cuenta {account_id} eliminada físicamente de la DB.")