"""One-off helper: reset seeded admin password and clear must_change_password flag
Usage: python reset_admin_password.py [login_id] [new_password]
Defaults: login_id=SIH@2026, new_password=SIH@2026
"""
import sys
from pathlib import Path
import sqlite3
import hashlib

def hash_password(password: str) -> str:
	salt = "ArogyaMitra_2026_Auth_Salt"
	return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

root = Path(__file__).resolve().parents[1]
db_path = root / "data" / "staff_identity.db"

login = sys.argv[1] if len(sys.argv) > 1 else 'SIH@2026'
new_pw = sys.argv[2] if len(sys.argv) > 2 else 'SIH@2026'

if not db_path.exists():
	print(f"Database not found: {db_path}")
	sys.exit(2)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
new_hash = hash_password(new_pw)
cur.execute("UPDATE staff_accounts SET password_hash = ?, must_change_password = 0 WHERE login_id = ?", (new_hash, login))
if cur.rowcount == 0:
	print(f"No rows updated. Check login_id '{login}' exists in staff_accounts.")
else:
	conn.commit()
	print(f"Updated login_id={login}: set new password and cleared must_change_password flag.")
conn.close()