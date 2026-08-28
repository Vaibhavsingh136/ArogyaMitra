"""
ArogyaMitra Administrative Controls, System Config & Security Audit Router
Source of truth: systemdesign.md Section 14 & User Requirements 9, 10, 14, 22
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List
from app.db import get_medical_db
from app.models import SystemConfigUpdate
from app.services.audit_service import get_audit_logs, log_action
from app.models import ForceInitRequest, ForceTokenRequest
from app.db import force_init_db_if_allowed, create_force_init_token, consume_force_init_token
from app.config import AUTH_SECRET_KEY, FORCE_INIT_DB, ADMIN_ALLOWED_IPS

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/audit-logs")
def fetch_audit_logs(limit: int = 100):
    """Retrieves recent security and compliance audit logs."""
    logs = get_audit_logs(limit=limit)
    return {"audit_logs": logs}

@router.get("/config")
def get_system_config():
    """Retrieves operational system configuration parameters."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_config")
    rows = cursor.fetchall()
    config = {r["key"]: r["value"] for r in rows}
    conn.close()
    return {"config": config}

@router.post("/config")
def update_system_config(req: SystemConfigUpdate, request: Request):
    """Updates operational parameters."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    if req.mock_abdm is not None:
        cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('mock_abdm', ?)", ("true" if req.mock_abdm else "false",))
    if req.ayush_mode is not None:
        cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('ayush_mode', ?)", ("true" if req.ayush_mode else "false",))
    if req.retention_days is not None:
        cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('retention_policy_days', ?)", (str(req.retention_days),))
        
    conn.commit()
    conn.close()
    
    log_action("UPDATE_SYSTEM_CONFIG", user_id="ADMIN", role="ADMIN", details="Admin updated system operational parameters", ip_address=client_ip)
    return {"success": True, "message": "System configuration updated successfully"}


@router.post('/generate-force-token')
def generate_force_token(req: ForceTokenRequest, request: Request):
    """Generates a one-time force-init token for admin to use when triggering forced DB init.
    Returns token and expiry. Requires admin credentials.
    """
    # Determine caller IP (respect X-Forwarded-For if present)
    xff = request.headers.get('x-forwarded-for')
    if xff:
        client_ip = xff.split(',')[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    # Restrict token generation to configured admin IPs
    if client_ip not in ADMIN_ALLOWED_IPS:
        raise HTTPException(status_code=403, detail=f"Token generation allowed only from admin IPs. Your IP: {client_ip}")

    # Validate admin credential against staff_identity
    from app.db import get_staff_identity_db, hash_password
    sconn = get_staff_identity_db()
    scur = sconn.cursor()
    scur.execute("SELECT * FROM staff_accounts WHERE login_id = ?", (req.admin_login,))
    staff = scur.fetchone()
    sconn.close()

    if not staff or staff['role'] != 'ADMIN' or staff['password_hash'] != hash_password(req.admin_password):
        raise HTTPException(status_code=403, detail='Invalid admin credentials')

    token, expires = create_force_init_token(staff['staff_id'], ttl_minutes=req.ttl_minutes or 15)
    log_action('GENERATE_FORCE_TOKEN', user_id=staff['staff_id'], role='ADMIN', details='Admin generated force-init token', ip_address=client_ip)
    return {"success": True, "token": token, "expires_at": expires}


@router.post("/force-init-db")
def admin_force_init(req: ForceInitRequest, request: Request):
    """Admin-only endpoint to trigger a safe forced DB initialization/seed.
    Requires valid admin credentials and either `FORCE_INIT_DB` env flag or matching `force_key`.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Validate admin credential
    conn = get_medical_db()
    cur = conn.cursor()
    # Staff identity check against staff_identity DB
    from app.db import get_staff_identity_db, hash_password
    sconn = get_staff_identity_db()
    scur = sconn.cursor()
    scur.execute("SELECT * FROM staff_accounts WHERE login_id = ?", (req.admin_login,))
    staff = scur.fetchone()
    sconn.close()

    if not staff or staff['role'] != 'ADMIN' or staff['password_hash'] != hash_password(req.admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin credentials")

    # If force_key equals static AUTH_SECRET_KEY or environment override enabled, allow
    if req.force_key and req.force_key == AUTH_SECRET_KEY:
        permitted = True
    elif FORCE_INIT_DB:
        permitted = True
    else:
        # Otherwise consume one-time token
        if not req.force_key:
            raise HTTPException(status_code=403, detail="Force init not permitted: missing force_key or environment override")
        ok, reason = consume_force_init_token(req.force_key)
        if not ok:
            raise HTTPException(status_code=403, detail=f"Invalid or expired force_key: {reason}")

    # Perform forced init
    try:
        force_init_db_if_allowed()
        log_action("FORCE_INIT_DB", user_id=staff['staff_id'], role='ADMIN', details='Admin triggered forced DB initialization', ip_address=client_ip)
        return {"success": True, "message": "Forced DB initialization completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")
