from core.instagram_engine import InstagramService as CoreInstagramService


class InstagramService(CoreInstagramService):
    """Wrapper de servicio de Instagram para separar la UI de la implementación.

    Este módulo expone InstagramService para que los diálogos no importen
    directamente instagrapi ni la clase de engine interna.
    """

    def __init__(self, security_service=None, db_service=None):
        super().__init__()
        self.security_service = security_service
        self.db = db_service

    def update_settings(self, account_id, changes, cliente_id=None):
        if not self.db:
            raise RuntimeError("No DB service configured for InstagramService")
        return self.db.update_settings(account_id, changes, cliente_id)

    def get_account_state(self, account_id, cliente_id=None):
        if not self.db:
            raise RuntimeError("No DB service configured for InstagramService")
        return self.db.get_account_state(account_id, cliente_id)

    def clear_account_pauses(self, account_id, cliente_id=None):
        if not self.db:
            raise RuntimeError("No DB service configured for InstagramService")
        return self.db.clear_account_pauses(account_id, cliente_id)
