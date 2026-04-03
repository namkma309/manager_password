import os
import base64
import pyotp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SecurityManager:
    # ---------------- HARDWARE BINDING METHODS ----------------
    @staticmethod
    def get_machine_id() -> str:
        """Trích xuất UUID của phần cứng máy tính (Áp dụng Windows)."""
        import subprocess
        try:
            # Lệnh wmic lấy uuid của bo mạch chủ
            out = subprocess.check_output('wmic csproduct get uuid', shell=True).decode('utf-8')
            uuid_str = out.split('\n')[1].strip()
            if not uuid_str:
                return "DEFAULT_MACHINE_ID_FAILSAFE"
            return uuid_str
        except Exception:
            # Dự phòng cho trường hợp lỗi
            return "DEFAULT_MACHINE_ID_FAILSAFE"

    @staticmethod
    def get_hardware_key() -> bytes:
        """Sinh ra một khóa AES-256 từ mã UUID phần cứng cứng."""
        machine_id = SecurityManager.get_machine_id()
        # Dùng chuỗi machine_id băm thành 32 byte tĩnh (SHA-256 length is 32 bytes)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(machine_id.encode('utf-8'))
        return digest.finalize()

    # ---------------- OTP METHODS ----------------
    @staticmethod
    def generate_totp_secret() -> str:
        """Sinh mã ngẫu nhiên base32 để tích hợp với Google Authenticator."""
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, name: str, issuer: str = "Aura Vault") -> str:
        """Lấy URI để tạo QR code."""
        return pyotp.totp.TOTP(secret).provisioning_uri(name=name, issuer_name=issuer)

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Xác minh 6 số OTP do người dùng nhập."""
        import datetime
        totp = pyotp.TOTP(secret)
        current_app_otp = totp.now()
        
        # Ghi log debug
        try:
            with open("otp_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] XÁC MINH OTP\n")
                f.write(f" - Secret đang dùng: {secret}\n")
                f.write(f" - Mã do hệ thống tính toán (Bây giờ): {current_app_otp}\n")
                f.write(f" - Mã do bạn gõ vào: {code}\n")
                f.write("-" * 40 + "\n")
        except Exception:
            pass
            
        # Dung sai 2 chu kỳ (±60 giây)
        return totp.verify(code, valid_window=2)


    # ---------------- MASTER PASS METHODS ----------------
    @staticmethod
    def generate_salt() -> bytes:
        return os.urandom(16)

    @staticmethod
    def hash_data(text: str) -> str:
        """Hàm băm dữ liệu đơn giản dùng SHA256."""
        digest = hashes.Hash(hashes.SHA256())
        digest.update(text.encode('utf-8'))
        return digest.finalize().hex()

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Sinh khóa mã hóa sử dụng PBKDF2 với HMAC-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, # AES-256
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode('utf-8'))


    # ---------------- AES CORE ----------------
    @staticmethod
    def encrypt_data(key: bytes, plaintext: str) -> dict:
        """Mã hóa chuỗi ký tự bằng thuật toán AES-256-GCM."""
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        return {
            "iv": base64.b64encode(nonce).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
        }

    @staticmethod
    def decrypt_data(key: bytes, iv_b64: str, ciphertext_b64: str) -> str:
        """Giải mã dữ liệu AES-256-GCM về dạng văn bản gốc."""
        aesgcm = AESGCM(key)
        nonce = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception:
            return None
