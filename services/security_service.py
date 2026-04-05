import base64
import hashlib
from cryptography.fernet import Fernet

class SecurityService:
    def __init__(self, hwid):
        self.hwid = hwid
        self.fernet = Fernet(self._generate_key(hwid))

    def _generate_key(self, hwid):
        """Genera una llave Fernet de 32 bytes en Base64 a partir del HWID."""
        raw_key = hashlib.sha256(hwid.encode()).digest()
        return base64.urlsafe_b64encode(raw_key)

    def encrypt(self, text):
        if text is None:
            return None
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text:
            return None
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            return None