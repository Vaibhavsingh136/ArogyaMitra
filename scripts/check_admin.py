import sqlite3
from pathlib import Path
p = Path(__file__).resolve().parents[1] / 'data' / 'staff_identity.db'
print('DB path:', p)
if not p.exists():
    print('DB missing')
    raise SystemExit(2)
conn = sqlite3.connect(str(p))
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT staff_id, login_id, password_hash, must_change_password, account_status FROM staff_accounts WHERE login_id = ?", ('SIH@2026',))
r = cur.fetchone()
if not r:
    print('No SIH@2026')
else:
    print(dict(r))
conn.close()
