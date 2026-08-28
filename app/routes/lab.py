"""
ArogyaMitra Laboratory Diagnostics Router
Source of truth: systemdesign.md Section 8 & 12
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional
from app.db import get_medical_db
from app.models import LabReportCreate
from app.services.encryption_service import encrypt_clinical_data, decrypt_clinical_data
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/lab", tags=["lab"])

@router.get("/reports")
def get_all_lab_reports():
    """Retrieves all laboratory reports and results."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, p.name as patient_name, p.abha_id, p.gender, p.date_of_birth
        FROM lab_reports r
        JOIN patients p ON r.patient_id = p.patient_id
        ORDER BY r.test_date DESC
    """)
    reports = []
    for row in cursor.fetchall():
        rep = dict(row)
        rep["notes"] = decrypt_clinical_data(rep.get("notes"))
        cursor.execute("SELECT * FROM lab_results WHERE lab_report_id = ?", (rep["lab_report_id"],))
        rep["results"] = [dict(res) for res in cursor.fetchall()]
        reports.append(rep)
    conn.close()
    return {"reports": reports}

@router.post("/add-report")
def add_lab_report(req: LabReportCreate, request: Request):
    """Adds a new laboratory report and associates it with the patient's record."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    lab_id = f"lab_rep_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    # Check if any result is flagged as abnormal
    has_critical = any(r.flag in ["HIGH", "LOW", "CRITICAL"] for r in req.results)
    doctor_alert = 1 if (req.doctor_alert or has_critical) else 0
    enc_notes = encrypt_clinical_data(req.notes)
    
    cursor.execute("""
        INSERT INTO lab_reports (lab_report_id, patient_id, consultation_id, document_id, test_date, test_type, status, doctor_alert, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'FINAL', ?, ?, ?)
    """, (lab_id, req.patient_id, req.consultation_id, req.document_id, req.test_date, req.test_type, doctor_alert, enc_notes, now))
    
    # Insert individual test results
    for r in req.results:
        res_id = f"lr_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO lab_results (result_id, lab_report_id, test_name, value, unit, reference_range, flag)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (res_id, lab_id, r.test_name, r.value, r.unit, r.reference_range, r.flag))
        
    conn.commit()
    conn.close()
    
    log_action("LAB_REPORT_UPLOADED", role="LAB", patient_id=req.patient_id, details=f"Added {req.test_type} with {len(req.results)} results (Alert: {bool(doctor_alert)})", ip_address=client_ip)
    
    return {
        "success": True,
        "lab_report_id": lab_id,
        "doctor_alert": bool(doctor_alert),
        "message": "Lab report successfully linked to patient medical timeline."
    }
