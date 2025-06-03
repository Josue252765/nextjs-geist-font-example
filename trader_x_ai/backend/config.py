import os
from cryptography.fernet import Fernet

# Encryption key - en producción esto debería estar en variables de entorno
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# APIs encriptadas de Kraken
KRAKEN_API_KEY = "3hMIwgplqSH+IZSYM86eEEYhrmh100Zit4q8sRtwGMDZ0cOqvRa9+0Ix"
KRAKEN_API_SECRET = "0Lbk3x4DJI/18KVvVeWPEM7U+jovml4U6jQU+KAHOtETP/UsqI9A1mCj6RVMXIKkzrVggTdCYmCkv1w59rItew=="

def get_decrypted_credentials():
    try:
        return {
            'api_key': KRAKEN_API_KEY,
            'api_secret': KRAKEN_API_SECRET
        }
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return None
