import base64
import hashlib
from cryptography.fernet import Fernet

class SecurityService:
    def __init__(self, hwid):
        # Generamos una llave de 32 bytes basada en el HWID
        key = hashlib.sha256(hwid.encode()).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, text):
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except:
            return None