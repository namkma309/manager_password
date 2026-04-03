import sqlite3
import os

DB_FILE = "vault.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Phân hệ Cấu Hình Hệ Thống
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Phân hệ Lưu Trữ Bản Mã
    c.execute('''
        CREATE TABLE IF NOT EXISTS vault_entries (
            id TEXT PRIMARY KEY,
            iv TEXT,
            ciphertext TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_config(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Lưu khóa nếu chưa có, Cập nhật nếu đã tồn tại
    c.execute('''
        INSERT INTO system_config (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def get_config(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT value FROM system_config WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_entries():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Chú ý: Cấu trúc chèn mới đứng đầu như logic cũ, ta sắp xếp ROWID ngược
    c.execute('SELECT id, iv, ciphertext FROM vault_entries ORDER BY ROWID DESC')
    rows = c.fetchall()
    conn.close()
    
    entries = []
    for r in rows:
        entries.append({
            "id": r[0],
            "iv": r[1],
            "ciphertext": r[2]
        })
    return entries

def add_entry(entry_id, iv, ciphertext):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO vault_entries (id, iv, ciphertext)
        VALUES (?, ?, ?)
    ''', (entry_id, iv, ciphertext))
    conn.commit()
    conn.close()

def delete_entry(entry_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM vault_entries WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()

def clear_vault():
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass
    init_db()

# Tự động nạp cấu trúc Database khi khởi động
init_db()
