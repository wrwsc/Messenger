from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os


def generate_key():
    return os.urandom(32)


# Функция для шифрования сообщения
def encrypt_message(message: str, key: bytes) -> bytes:
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend = default_backend())
    encryptor = cipher.encryptor()
    packer = padding.PKCS7(128).padder()
    padded_data = packer.update(message.encode()) + packer.finalize()
    encrypted_message = encryptor.update(padded_data) + encryptor.finalize()
    return iv + encrypted_message


# Функция для дешифрования сообщения
def decrypt_message(encrypted_message: bytes, key: bytes) -> str:
    iv = encrypted_message[:16]
    encrypted_data = encrypted_message[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend = default_backend())
    decrypt = cipher.decryptor()
    decrypted_data = decrypt.update(encrypted_data) + decrypt.finalize()
    unpacker = padding.PKCS7(128).unpadder()
    unpacker_data = unpacker.update(decrypted_data) + unpacker.finalize()
    return unpacker_data.decode()
