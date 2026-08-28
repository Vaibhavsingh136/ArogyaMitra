"""
ArogyaMitra Security & Audit Logging Service
Tracks all security-critical actions: login, logout, password change,
account generation, deactivation, record views, summary edits, verifications,
document uploads, radiology reports, and consent changes.
Source of truth: systemdesign.md Section 14 & User Requirements
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.db import get_medical_db

def log_action(
    action: str,
    user_id: Optional[str] = None,
    role: Optional[str] = None,
    patient_id: Optional[str] = None,
    details: Optional[str] = "",
    ip_address: Optional[str] = "127.0.0.1"
):
    """Inserts an immutable security audit record into the Medical Database."""
    try:
        conn = get_medical_db()
        cursor = conn.cursor()
        log_id = f"log_{uuid.uuid4().hex[:10]}"
        cursor.execute("""
            INSERT INTO audit_logs (log_id, user_id, role, patient_id, action, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, user_id, role or "SYSTEM", patient_id, action, details, ip_address, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")

def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs for administrative security compliance."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, p.name as patient_name
        FROM audit_logs l
        LEFT JOIN patients p ON l.patient_id = p.patient_id
        ORDER BY l.timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    logs = [dict(r) for r in rows]
    conn.close()
    return logs
