"""
ArogyaMitra Authentication & Staff Account Lifecycle Router
Source of truth: User Requirements 4-10, 12, 14, 15, 16

Handles:
- Patient Registration (Identity DB + Medical DB) & Login
- Staff Login (Doctor, Radiologist, Admin) from Staff Identity DB
- Forced First-Login Password Change
- Admin Staff Credential Generator (DOC-XXXX, RAD-XXXX, ADM-XXXX)
- Soft Deactivation / Activation of Staff Accounts
- Explicit Logout & Audit Logging
"""
import uuid
import random
import string
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List, Optional

from app.db import (
    get_patient_identity_db,
    get_staff_identity_db,
    get_medical_db,
    hash_password
)
from app.models import (
    PatientRegisterRequest,
    PatientLoginRequest,
    StaffLoginRequest,
    StaffChangePasswordRequest,
    StaffGenerateCredentialsRequest,
    StaffToggleStatusRequest,
    LoginRequest,
    DemoSwitchRequest
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])

def _generate_temp_password(length: int = 8) -> str:
    """Generates a secure alphanumeric temporary password."""
    chars = string.ascii_letters + string.digits + "@#$"
    return "".join(random.choice(chars) for _ in range(length))

# ============================================================
# 1. PATIENT AUTHENTICATION (REGISTER & LOGIN)
# ============================================================

@router.post("/patient/register")
def register_patient_account(req: PatientRegisterRequest, request: Request):
    """
    Registers a new patient account in Patient Identity DB
    and creates clinical reference profile in Medical DB.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Check existing in Patient Identity DB
    conn_id = get_patient_identity_db()
    cur_id = conn_id.cursor()
    
    # Normalize login identifier (phone or ABHA)
    login_id = req.phone.strip().replace(" ", "").replace("-", "")
    cur_id.execute("SELECT * FROM patient_accounts WHERE login_id = ?", (login_id,))
    if cur_id.fetchone():
        conn_id.close()
        raise HTTPException(status_code=400, detail="A patient account with this phone number already exists. Please log in.")
    
    patient_id = f"pat_{uuid.uuid4().hex[:8]}"
    pwd_hash = hash_password(req.password)
    now = datetime.now().isoformat()
    
    cur_id.execute("""
        INSERT INTO patient_accounts (patient_id, login_id, password_hash, full_name, account_status, created_at, last_login)
        VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
    """, (patient_id, login_id, pwd_hash, req.name, now, now))
    conn_id.commit()
    conn_id.close()
    
    # 2. Create Clinical Profile in Medical DB
    conn_med = get_medical_db()
    cur_med = conn_med.cursor()
    
    cur_med.execute("""
        INSERT INTO patients (patient_id, abha_id, name, date_of_birth, gender, phone, address, preferred_language, blood_group, emergency_contact, registration_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id, req.abha_id or f"91-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}@abdm",
        req.name, req.date_of_birth, req.gender, req.phone, req.address or "",
        req.preferred_language or "en", req.blood_group or "Unknown", req.emergency_contact or "", now
    ))
    
    # Auto-create active consultation
    consultation_id = f"con_{uuid.uuid4().hex[:8]}"
    cur_med.execute("SELECT COUNT(*) FROM consultations")
    q_num = cur_med.fetchone()[0] + 101
    token_code = f"AM-{q_num}"
    
    cur_med.execute("""
        INSERT INTO consultations (consultation_id, patient_id, doctor_id, date_time, status, queue_number, token_code, chief_complaint_summary)
        VALUES (?, ?, 'doc_1', ?, 'IN_PROGRESS', ?, ?, 'Pre-Consultation Intake Started')
    """, (consultation_id, patient_id, now, q_num, token_code))
    
    conn_med.commit()
    
    cur_med.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    patient_record = dict(cur_med.fetchone())
    conn_med.close()
    
    log_action("ACCOUNT_CREATED", user_id=patient_id, role="PATIENT", patient_id=patient_id, details=f"New patient account registered: {req.name}", ip_address=client_ip)
    
    return {
        "success": True,
        "message": "Patient account registered successfully.",
        "user": {
            "patient_id": patient_id,
            "login_id": login_id,
            "role": "PATIENT",
            "name": req.name,
            "preferred_language": req.preferred_language or "en"
        },
        "patient": patient_record,
        "consultation_id": consultation_id,
        "token_code": token_code
    }

@router.post("/patient/login")
def login_patient_account(req: PatientLoginRequest, request: Request):
    """
    Authenticates patient credentials from Patient Identity DB.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    login_id = req.login_id.strip().replace(" ", "").replace("-", "")
    pwd_hash = hash_password(req.password)
    
    conn_id = get_patient_identity_db()
    cur_id = conn_id.cursor()
    
    # Check by login_id (phone, ABHA, username, or direct match)
    cur_id.execute("""
        SELECT * FROM patient_accounts 
        WHERE (login_id = ? OR login_id = ? OR patient_id = ?)
    """, (login_id, req.login_id.strip(), req.login_id.strip()))
    account = cur_id.fetchone()
    
    if not account or account["password_hash"] != pwd_hash:
        conn_id.close()
        raise HTTPException(status_code=401, detail="Invalid patient credentials. Please check your phone/ABHA number and password.")
        
    if account["account_status"] != "ACTIVE":
        conn_id.close()
        raise HTTPException(status_code=403, detail="Your patient account has been deactivated. Please contact hospital support.")
        
    patient_id = account["patient_id"]
    now = datetime.now().isoformat()
    cur_id.execute("UPDATE patient_accounts SET last_login = ? WHERE patient_id = ?", (now, patient_id))
    conn_id.commit()
    conn_id.close()
    
    # Fetch clinical record from Medical DB
    conn_med = get_medical_db()
    cur_med = conn_med.cursor()
    cur_med.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    pat_row = cur_med.fetchone()
    patient_profile = dict(pat_row) if pat_row else {"patient_id": patient_id, "name": account["full_name"], "preferred_language": "en"}
    
    # Find or create active consultation session
    cur_med.execute("""
        SELECT * FROM consultations 
        WHERE patient_id = ? AND status IN ('IN_PROGRESS', 'SUBMITTED', 'DOCTOR_REVIEWING')
        ORDER BY date_time DESC LIMIT 1
    """, (patient_id,))
    con_row = cur_med.fetchone()
    
    if con_row:
        consultation_id = con_row["consultation_id"]
        token_code = con_row["token_code"]
    else:
        consultation_id = f"con_{uuid.uuid4().hex[:8]}"
        cur_med.execute("SELECT COUNT(*) FROM consultations")
        q_num = cur_med.fetchone()[0] + 101
        token_code = f"AM-{q_num}"
        cur_med.execute("""
            INSERT INTO consultations (consultation_id, patient_id, doctor_id, date_time, status, queue_number, token_code, chief_complaint_summary)
            VALUES (?, ?, 'doc_1', ?, 'IN_PROGRESS', ?, ?, 'Pre-Consultation Intake Started')
        """, (consultation_id, patient_id, now, q_num, token_code))
        conn_med.commit()
        
    conn_med.close()
    
    log_action("LOGIN", user_id=patient_id, role="PATIENT", patient_id=patient_id, details=f"Patient {account['full_name']} logged in", ip_address=client_ip)
    
    return {
        "success": True,
        "user": {
            "patient_id": patient_id,
            "login_id": account["login_id"],
            "role": "PATIENT",
            "full_name": account["full_name"],
            "preferred_language": patient_profile.get("preferred_language", "en")
        },
        "patient": patient_profile,
        "consultation_id": consultation_id,
        "token_code": token_code
    }

# ============================================================
# 2. STAFF AUTHENTICATION (DOCTOR, RADIOLOGIST, ADMIN)
# ============================================================

@router.post("/staff/login")
def login_staff_account(req: StaffLoginRequest, request: Request):
    """
    Authenticates Doctor, Radiologist, or Admin from Staff Identity DB.
    Enforces active account status and checks must_change_password flag.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    pwd_hash = hash_password(req.password)
    
    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    
    cur_staff.execute("""
        SELECT * FROM staff_accounts WHERE login_id = ?
    """, (req.login_id.strip(),))
    staff = cur_staff.fetchone()
    
    if not staff or staff["password_hash"] != pwd_hash:
        conn_staff.close()
        raise HTTPException(status_code=401, detail="Invalid staff Login ID or Password.")
        
    if staff["account_status"] != "ACTIVE":
        conn_staff.close()
        raise HTTPException(status_code=403, detail="Your staff account has been deactivated. Please contact the system administrator.")
        
    # Check expected role if requested
    if req.expected_role and staff["role"] != req.expected_role.upper():
        conn_staff.close()
        raise HTTPException(status_code=403, detail=f"This account is not authorized for the {req.expected_role} role.")
        
    now = datetime.now().isoformat()
    cur_staff.execute("UPDATE staff_accounts SET last_login = ? WHERE staff_id = ?", (now, staff["staff_id"]))
    conn_staff.commit()
    
    staff_dict = dict(staff)
    del staff_dict["password_hash"]  # Never expose hash
    conn_staff.close()
    
    # Retrieve profile from Medical DB if Doctor or Radiologist (include preferred_language)
    profile_info = {}
    conn_med = get_medical_db()
    cur_med = conn_med.cursor()
    
    if staff_dict["role"] == "DOCTOR":
        cur_med.execute("SELECT * FROM doctors WHERE staff_id = ?", (staff_dict["staff_id"],))
        doc = cur_med.fetchone()
        if doc:
            profile_info["doctor_id"] = doc["doctor_id"]
            profile_info["specialization"] = doc["specialization"]
            profile_info["department"] = doc["department"]
            profile_info["preferred_language"] = doc.get("preferred_language", "en") if isinstance(doc, dict) else doc[ "preferred_language" ] if doc and "preferred_language" in doc.keys() else "en"
        else:
            profile_info["doctor_id"] = "doc_1"
    elif staff_dict["role"] == "RADIOLOGIST":
        cur_med.execute("SELECT * FROM radiologists WHERE staff_id = ?", (staff_dict["staff_id"],))
        rad = cur_med.fetchone()
        if rad:
            profile_info["radiologist_id"] = rad["radiologist_id"]
            profile_info["department"] = rad["department"]
            profile_info["preferred_language"] = rad.get("preferred_language", "en") if isinstance(rad, dict) else rad[ "preferred_language" ] if rad and "preferred_language" in rad.keys() else "en"
        else:
            profile_info["radiologist_id"] = "rad_1"
            
    conn_med.close()
    
    log_action("LOGIN", user_id=staff_dict["staff_id"], role=staff_dict["role"], details=f"Staff user {staff_dict['login_id']} ({staff_dict['role']}) logged in", ip_address=client_ip)
    
    return {
        "success": True,
        "user": {
            "staff_id": staff_dict["staff_id"],
            "login_id": staff_dict["login_id"],
            "role": staff_dict["role"],
            "full_name": staff_dict["full_name"],
            "email": staff_dict.get("email", ""),
            "department": staff_dict.get("department", ""),
            "must_change_password": bool(staff_dict["must_change_password"]),
            **profile_info
        },
        "must_change_password": bool(staff_dict["must_change_password"])
    }

@router.post("/staff/change-password")
def change_staff_password(req: StaffChangePasswordRequest, request: Request):
    """
    Enforces password change on first login or manual change.
    Securely hashes the new password and clears must_change_password flag.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
        
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
        
    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    
    old_pwd_hash = hash_password(req.old_password)
    cur_staff.execute("""
        SELECT * FROM staff_accounts WHERE login_id = ?
    """, (req.login_id.strip(),))
    staff = cur_staff.fetchone()
    
    if not staff or staff["password_hash"] != old_pwd_hash:
        conn_staff.close()
        raise HTTPException(status_code=401, detail="Current temporary/old password is incorrect.")
        
    new_pwd_hash = hash_password(req.new_password)
    cur_staff.execute("""
        UPDATE staff_accounts
        SET password_hash = ?, must_change_password = 0
        WHERE login_id = ?
    """, (new_pwd_hash, req.login_id.strip()))
    conn_staff.commit()
    conn_staff.close()
    
    log_action("PASSWORD_CHANGED", user_id=staff["staff_id"], role=staff["role"], details=f"Password changed and account activated for {req.login_id}", ip_address=client_ip)
    
    return {
        "success": True,
        "message": "Password updated successfully. Your account is fully activated."
    }

# ============================================================
# 3. ADMIN STAFF ACCOUNT MANAGEMENT (GENERATE & DEACTIVATE)
# ============================================================

@router.post("/admin/generate-credentials")
def generate_staff_credentials(req: StaffGenerateCredentialsRequest, request: Request):
    """
    Administrator control: Generates unique staff credentials (Doctor, Radiologist, Admin)
    with a temporary password and must_change_password flag enabled.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    role_upper = req.role.upper()
    if role_upper not in ["DOCTOR", "RADIOLOGIST", "ADMIN"]:
        raise HTTPException(status_code=400, detail="Invalid staff role. Must be DOCTOR, RADIOLOGIST, or ADMIN.")
        
    # Generate Unique Login ID
    prefix_map = {"DOCTOR": "DOC", "RADIOLOGIST": "RAD", "ADMIN": "ADM"}
    prefix = prefix_map[role_upper]
    unique_num = random.randint(1000, 9999)
    login_id = f"{prefix}-{unique_num}"
    
    temp_password = f"{prefix}@{random.randint(1000, 9999)}"
    pwd_hash = hash_password(temp_password)
    staff_id = f"staff_{prefix.lower()}_{uuid.uuid4().hex[:6]}"
    now = datetime.now().isoformat()
    
    # 1. Insert into Staff Identity DB
    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    cur_staff.execute("""
        INSERT INTO staff_accounts (staff_id, login_id, password_hash, role, full_name, email, department, specialization, account_status, must_change_password, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 1, ?)
    """, (staff_id, login_id, pwd_hash, role_upper, req.full_name, req.email or "", req.department or "", req.specialization or "", now))
    conn_staff.commit()
    conn_staff.close()
    
    # 2. Insert clinical record into Medical DB if Doctor or Radiologist
    conn_med = get_medical_db()
    cur_med = conn_med.cursor()
    
    if role_upper == "DOCTOR":
        doc_id = f"doc_{uuid.uuid4().hex[:6]}"
        cur_med.execute("""
            INSERT INTO doctors (doctor_id, staff_id, name, specialization, department, room_no, qualification, registration_no)
            VALUES (?, ?, ?, ?, ?, 'OPD Room 105', ?, ?)
        """, (doc_id, staff_id, req.full_name, req.specialization or "General Medicine", req.department or "General OPD", req.qualification or "MBBS, MD", req.registration_no or f"MCI-{random.randint(10000,99999)}"))
    elif role_upper == "RADIOLOGIST":
        rad_id = f"rad_{uuid.uuid4().hex[:6]}"
        cur_med.execute("""
            INSERT INTO radiologists (radiologist_id, staff_id, name, department, qualification, registration_no)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rad_id, staff_id, req.full_name, req.department or "Department of Radiology & Imaging", req.qualification or "MD (Radiodiagnosis)", req.registration_no or f"RAD-{random.randint(10000,99999)}"))
        
    conn_med.commit()
    conn_med.close()
    
    log_action("ACCOUNT_CREATED", user_id="ADMIN", role="ADMIN", details=f"Admin generated credentials for {login_id} ({role_upper}: {req.full_name})", ip_address=client_ip)
    
    return {
        "success": True,
        "message": f"{role_upper.capitalize()} account created successfully.",
        "credentials": {
            "staff_id": staff_id,
            "login_id": login_id,
            "temporary_password": temp_password,
            "role": role_upper,
            "full_name": req.full_name,
            "must_change_password": True
        }
    }

@router.post("/admin/toggle-account-status")
def toggle_staff_account_status(req: StaffToggleStatusRequest, request: Request):
    """
    Soft deactivation/activation of staff accounts.
    Deactivated accounts cannot log in, while audit trails and medical records remain intact.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if req.account_status not in ["ACTIVE", "INACTIVE"]:
        raise HTTPException(status_code=400, detail="Status must be ACTIVE or INACTIVE.")
        
    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    
    cur_staff.execute("SELECT * FROM staff_accounts WHERE staff_id = ?", (req.staff_id,))
    staff = cur_staff.fetchone()
    if not staff:
        conn_staff.close()
        raise HTTPException(status_code=404, detail="Staff account not found.")
        
    cur_staff.execute("""
        UPDATE staff_accounts SET account_status = ? WHERE staff_id = ?
    """, (req.account_status, req.staff_id))
    conn_staff.commit()
    conn_staff.close()
    
    action_name = "ACCOUNT_DEACTIVATED" if req.account_status == "INACTIVE" else "ACCOUNT_ACTIVATED"
    log_action(action_name, user_id="ADMIN", role="ADMIN", details=f"Admin set account status of {staff['login_id']} ({staff['full_name']}) to {req.account_status}", ip_address=client_ip)
    
    return {
        "success": True,
        "staff_id": req.staff_id,
        "account_status": req.account_status,
        "message": f"Account {staff['login_id']} is now {req.account_status}."
    }

@router.get("/admin/staff-accounts")
def list_staff_accounts(role: Optional[str] = None):
    """
    Lists all staff accounts for administrator management.
    """
    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    if role:
        cur_staff.execute("""
            SELECT staff_id, login_id, role, full_name, email, department, specialization, account_status, must_change_password, created_at, last_login
            FROM staff_accounts WHERE role = ? ORDER BY created_at DESC
        """, (role.upper(),))
    else:
        cur_staff.execute("""
            SELECT staff_id, login_id, role, full_name, email, department, specialization, account_status, must_change_password, created_at, last_login
            FROM staff_accounts
            ORDER BY created_at DESC
        """)
    accounts = [dict(r) for r in cur_staff.fetchall()]
    conn_staff.close()
    return {"staff_accounts": accounts}

# ============================================================
# 4. LOGOUT & SESSION CONTROL
# ============================================================

@router.post("/logout")
def logout(request: Request):
    """
    Terminates the active session and logs audit record.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    log_action("LOGOUT", details="User terminated active session", ip_address=client_ip)
    return {"success": True, "message": "Session terminated successfully."}


@router.post("/staff/set-language")
def set_staff_language(payload: Dict[str, str], request: Request = None):
    """Sets preferred language for Doctor or Radiologist profiles.
    Payload: { "staff_id": "staff_doc_1", "preferred_language": "hi" }
    """
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    staff_id = payload.get("staff_id")
    lang = payload.get("preferred_language")
    if not staff_id or not lang:
        raise HTTPException(status_code=400, detail="staff_id and preferred_language are required")

    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    cur_staff.execute("SELECT * FROM staff_accounts WHERE staff_id = ?", (staff_id,))
    staff = cur_staff.fetchone()
    if not staff:
        conn_staff.close()
        raise HTTPException(status_code=404, detail="Staff account not found")

    role = staff["role"]
    conn_med = get_medical_db()
    cur_med = conn_med.cursor()
    if role == "DOCTOR":
        cur_med.execute("UPDATE doctors SET preferred_language = ? WHERE staff_id = ?", (lang, staff_id))
    elif role == "RADIOLOGIST":
        cur_med.execute("UPDATE radiologists SET preferred_language = ? WHERE staff_id = ?", (lang, staff_id))
    else:
        conn_med.close()
        conn_staff.close()
        raise HTTPException(status_code=400, detail="Language preference not applicable for this role")

    conn_med.commit()
    conn_med.close()
    conn_staff.close()

    log_action("LANGUAGE_PREFERENCE_SET", user_id=staff_id, role=role, details=f"Set preferred_language={lang}", ip_address=client_ip)
    return {"success": True, "staff_id": staff_id, "preferred_language": lang}

@router.get("/me")
def get_current_session():
    """
    Returns platform readiness and auth health status.
    """
    return {
        "authenticated": False,
        "platform": "ArogyaMitra",
        "supported_roles": ["PATIENT", "DOCTOR", "RADIOLOGIST", "ADMIN"]
    }

# ============================================================
# 5. LEGACY DEMO SWITCHER COMPATIBILITY
# ============================================================

@router.post("/demo-switch")
def demo_switch(req: DemoSwitchRequest, request: Request):
    """
    Demo switch backward compatibility for testing suites.
    """
    role = req.role.upper()
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    if role == "PATIENT":
        conn_med = get_medical_db()
        cur_med = conn_med.cursor()
        cur_med.execute("SELECT * FROM patients LIMIT 1")
        pat = cur_med.fetchone()
        conn_med.close()
        user_dict = {
            "user_id": "usr_pat_1",
            "patient_id": pat["patient_id"] if pat else "pat_1",
            "role": "PATIENT",
            "full_name": pat["name"] if pat else "Rajesh Kumar",
            "preferred_language": pat["preferred_language"] if pat else "hi"
        }
    else:
        conn_staff = get_staff_identity_db()
        cur_staff = conn_staff.cursor()
        cur_staff.execute("SELECT * FROM staff_accounts WHERE role = ? AND account_status = 'ACTIVE' LIMIT 1", (role,))
        staff = cur_staff.fetchone()
        conn_staff.close()
        if not staff:
            raise HTTPException(status_code=404, detail=f"No active demo user found for role {role}")
        user_dict = dict(staff)
        del user_dict["password_hash"]
        
    log_action("DEMO_ROLE_SWITCH", role=role, details=f"Switched session role to {role}", ip_address=client_ip)
    return {"success": True, "user": user_dict}

@router.get("/users")
def list_legacy_users():
    """Legacy user list endpoint."""
    conn_staff = get_staff_identity_db()
    cur_staff = conn_staff.cursor()
    cur_staff.execute("SELECT staff_id as user_id, login_id as username, role, full_name, email, created_at FROM staff_accounts")
    users = [dict(u) for u in cur_staff.fetchall()]
    conn_staff.close()
    return {"users": users}
