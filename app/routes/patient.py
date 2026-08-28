"""
ArogyaMitra Patient Management Router
Source of truth: systemdesign.md Module A & User Requirements 4, 18, 22

Handles:
- Patient clinical profile
- Consultation session tracking
- Explicit audio-guided consent recording
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional
from app.db import get_medical_db
from app.models import PatientRegistration, ConsentRequest
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/patient", tags=["patient"])

@router.get("/list")
def get_patients():
    """Returns all registered patients (clinical summary)."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients ORDER BY registration_date DESC")
    patients = [dict(p) for p in cursor.fetchall()]
    conn.close()
    return {"patients": patients}

@router.get("/{patient_id}")
def get_patient_profile(patient_id: str, request: Request = None):
    """Retrieves patient clinical profile, recent consultations, and latest consent."""
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient_dict = dict(patient)
    
    # Consultations
    cursor.execute("""
        SELECT * FROM consultations WHERE patient_id = ? ORDER BY date_time DESC
    """, (patient_id,))
    consultations = [dict(c) for c in cursor.fetchall()]
    patient_dict["consultations"] = consultations
    
    # Consents
    cursor.execute("""
        SELECT * FROM consents WHERE patient_id = ? ORDER BY given_at DESC LIMIT 1
    """, (patient_id,))
    consent = cursor.fetchone()
    patient_dict["latest_consent"] = dict(consent) if consent else None
    
    conn.close()
    log_action("PATIENT_RECORD_VIEWED", role="PATIENT", patient_id=patient_id, details=f"Profile retrieved for {patient_dict['name']}", ip_address=client_ip)
    return {"patient": patient_dict}

@router.post("/register")
def register_patient(data: PatientRegistration, request: Request):
    """Legacy/Kiosk direct clinical registration."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    # Check if ABHA already exists
    if data.abha_id:
        cursor.execute("SELECT * FROM patients WHERE abha_id = ?", (data.abha_id,))
        existing = cursor.fetchone()
        if existing:
            patient_id = existing["patient_id"]
            cursor.execute("SELECT * FROM consultations WHERE patient_id = ? AND status IN ('IN_PROGRESS', 'SUBMITTED') ORDER BY date_time DESC LIMIT 1", (patient_id,))
            con = cursor.fetchone()
            if con:
                con_id = con["consultation_id"]
                token = con["token_code"]
            else:
                con_id = f"con_{uuid.uuid4().hex[:8]}"
                cursor.execute("SELECT COUNT(*) FROM consultations")
                q_num = cursor.fetchone()[0] + 101
                token = f"AM-{q_num}"
                cursor.execute("""
                    INSERT INTO consultations (consultation_id, patient_id, doctor_id, date_time, status, queue_number, token_code, chief_complaint_summary)
                    VALUES (?, ?, 'doc_1', ?, 'IN_PROGRESS', ?, ?, 'Pre-Consultation Intake Started')
                """, (con_id, patient_id, datetime.now().isoformat(), q_num, token))
                conn.commit()
            conn.close()
            return {
                "success": True, 
                "patient": dict(existing), 
                "consultation_id": con_id, 
                "token_code": token,
                "message": "Identified existing patient by ABHA ID"
            }
            
    patient_id = f"pat_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO patients (patient_id, abha_id, name, date_of_birth, gender, phone, address, preferred_language, blood_group, emergency_contact, registration_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id, data.abha_id, data.name, data.date_of_birth, data.gender,
        data.phone, data.address, data.preferred_language, data.blood_group,
        data.emergency_contact, now
    ))
    
    # Auto-create intake consultation session
    consultation_id = f"con_{uuid.uuid4().hex[:8]}"
    cursor.execute("SELECT COUNT(*) FROM consultations")
    q_num = cursor.fetchone()[0] + 101
    token = f"AM-{q_num}"
    
    cursor.execute("""
        INSERT INTO consultations (consultation_id, patient_id, doctor_id, date_time, status, queue_number, token_code, chief_complaint_summary)
        VALUES (?, ?, 'doc_1', ?, 'IN_PROGRESS', ?, ?, 'Pre-Consultation Intake Started')
    """, (consultation_id, patient_id, now, q_num, token))
    
    conn.commit()
    
    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    new_patient = dict(cursor.fetchone())
    conn.close()
    
    log_action("ACCOUNT_CREATED", role="PATIENT", patient_id=patient_id, details=f"Registered patient {data.name} (ABHA: {data.abha_id or 'None'})", ip_address=client_ip)
    
    return {
        "success": True,
        "patient": new_patient,
        "consultation_id": consultation_id,
        "token_code": token
    }

@router.post("/consent")
def record_consent(req: ConsentRequest, request: Request):
    """Records granular explicit patient consent with audio guidance flag."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    consent_id = f"cs_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO consents (consent_id, patient_id, consultation_id, consent_type, consent_status, given_at, audio_guided)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (consent_id, req.patient_id, req.consultation_id, req.consent_type, req.consent_status, now, 1 if req.audio_guided else 0))
    
    conn.commit()
    conn.close()
    
    log_action("CONSENT_UPDATED", role="PATIENT", patient_id=req.patient_id, details=f"Consent {req.consent_status} (Audio: {req.audio_guided})", ip_address=client_ip)
    return {"success": True, "consent_id": consent_id, "status": req.consent_status}
