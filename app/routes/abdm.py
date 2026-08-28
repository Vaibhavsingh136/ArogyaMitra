"""
ABDM / ABHA Mock Gateway Router
Source of truth: systemdesign.md Section 15
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from app.db import get_db
from app.models import ABHAVerifyRequest
from app.services.abdm_service import ABDMAdapter
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/abdm", tags=["abdm"])

@router.post("/verify-abha")
def verify_abha_endpoint(req: ABHAVerifyRequest, request: Request):
    """Verifies ABHA ID format and mock demographics."""
    res = ABDMAdapter.verify_abha(req.abha_id)
    log_action("MOCK_ABDM_VERIFY", details=f"ABHA verification attempted for {req.abha_id}: {res['status']}", ip_address=request.client.host if request.client else "127.0.0.1")
    return res

@router.get("/fhir-bundle/{consultation_id}")
def export_fhir_bundle(consultation_id: str):
    """Generates an interoperable FHIR Document Bundle for the patient intake record."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, p.name, p.gender, p.date_of_birth, p.phone, p.abha_id
        FROM consultations c
        JOIN patients p ON c.patient_id = p.patient_id
        WHERE c.consultation_id = ?
    """, (consultation_id,))
    con_row = cursor.fetchone()
    if not con_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    con_dict = dict(con_row)
    
    cursor.execute("SELECT * FROM ai_summaries WHERE consultation_id = ?", (consultation_id,))
    sum_row = cursor.fetchone()
    conn.close()
    
    summary_data = {
        "status": sum_row["status"] if sum_row else "DRAFT",
        "chief_complaint": con_dict.get("chief_complaint_summary", "Intake Recorded"),
        "history_of_present_illness": "Pre-consultation history collected via ArogyaMitra AI engine."
    }
    
    bundle = ABDMAdapter.generate_fhir_bundle(con_dict, summary_data)
    return {"fhir_bundle": bundle}
