from core.instagram_engine import InstagramService as CoreInstagramService


class InstagramService(CoreInstagramService):
    """Wrapper de servicio de Instagram para separar la UI de la implementación.

    Este módulo expone InstagramService para que los diálogos no importen
    directamente instagrapi ni la clase de engine interna.
    """

    def __init__(self, security_service=None):
        super().__init__()
        self.security_service = security_service
