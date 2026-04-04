# controllers/instagram_controller.py

class InstagramController:
    def __init__(self, db_service, view=None):
        self.db = db_service
        self.view = view

    def set_view(self, view):
        self.view = view
        self.refresh_accounts()

    def refresh_accounts(self):
        accounts = self.db.obtener_cuentas()
        self.view.load_accounts(accounts)

    def add_account(self, user, password, prompt):
        # Guardamos en la base de datos (puedes encriptar el pass aquí)
        self.db.agregar_cuenta(user, password, system_prompt=prompt)
        self.refresh_accounts()

    def update_account_context(self, account_id, prompt):
        self.db.actualizar_contexto(account_id, prompt)
        self.refresh_accounts()

    def delete_account(self, account_id):
        self.db.eliminar_cuenta(account_id)
        self.refresh_accounts()