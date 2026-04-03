import json
import os

VAULT_FILE = 'vault_data.json'

def load_vault():
    """Tải nội dung vault từ hệ điều hành nếu tồn tại."""
    if not os.path.exists(VAULT_FILE):
        return None
    try:
        with open(VAULT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def save_vault(data):
    """Lưu đè vault mới xuống máy."""
    with open(VAULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
