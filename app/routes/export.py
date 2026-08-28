"""
ArogyaMitra PDF & Printable Summary Export Router
Source of truth: systemdesign.md Section 10 & brandguideline.md Section 20
"""
import json
from fastapi import APIRouter, HTTPException, Response
from app.db import get_medical_db
from app.services.pdf_service import generate_summary_pdf
from app.services.encryption_service import decrypt_clinical_data
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/export", tags=["export"])

@router.get("/summary-pdf/{consultation_id}")
def export_summary_pdf(consultation_id: str):
    """Generates and downloads the official ArogyaMitra pre-consultation summary PDF."""
    conn = get_medical_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, p.patient_id, p.name, p.gender, p.date_of_birth, p.phone, p.abha_id, p.address,
               d.name as doctor_name, d.department as doctor_dept, d.specialization as doctor_spec
        FROM consultations c
        JOIN patients p ON c.patient_id = p.patient_id
        LEFT JOIN doctors d ON c.doctor_id = d.doctor_id
        WHERE c.consultation_id = ?
    """, (consultation_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    con_data = dict(row)
    
    cursor.execute("SELECT * FROM ai_summaries WHERE consultation_id = ?", (consultation_id,))
    sum_row = cursor.fetchone()
    conn.close()
    
    if not sum_row:
        raise HTTPException(status_code=404, detail="Summary not yet generated for this consultation")
        
    sum_data = dict(sum_row)
    raw_struct = decrypt_clinical_data(sum_data.get("structured_data_json"))
    # Decrypt narrative summary_text if present so exported PDF includes full AI narrative
    from app.services.encryption_service import decrypt_clinical_data as _decrypt_text
    narrative_text = None
    if sum_data.get("summary_text"):
        try:
            narrative_text = _decrypt_text(sum_data.get("summary_text"))
        except Exception:
            narrative_text = None
    structured = {}
    if raw_struct:
        try:
            structured = json.loads(raw_struct)
        except Exception:
            structured = {}
            
    summary_payload = {
        "status": sum_data["status"],
        "chief_complaint": structured.get("chief_complaint", con_data.get("chief_complaint_summary", "")),
        "history_of_present_illness": structured.get("history_of_present_illness", "Reported as above."),
        "past_medical_history": structured.get("past_medical_history", "None reported."),
        "past_surgical_history": structured.get("past_surgical_history", "None reported."),
        "medications": structured.get("medications", []),
        "allergies": structured.get("allergies", []),
        "family_history": structured.get("family_history", "Non-contributory."),
        "personal_history": structured.get("personal_history", "Standard routine."),
        "review_of_systems": structured.get("review_of_systems", "Unremarkable."),
        "previous_investigations_summary": structured.get("previous_investigations_summary", "No prior scans."),
        "ayush_notes": structured.get("ayush_notes"),
        "doctor_notes": sum_data.get("doctor_notes"),
        "verified_at": sum_data.get("verified_at")
    }
    # Attach full AI narrative when available
    if narrative_text:
        summary_payload["full_summary_text"] = narrative_text
    
    patient_payload = {
        "name": con_data["name"],
        "gender": con_data["gender"],
        "date_of_birth": con_data["date_of_birth"],
        "phone": con_data["phone"],
        "abha_id": con_data["abha_id"]
    }
    
    doctor_payload = {
        "name": con_data.get("doctor_name", "OPD Attending Physician"),
        "department": con_data.get("doctor_dept", "General Medicine OPD")
    }
    
    pdf_bytes = generate_summary_pdf(patient_payload, con_data, summary_payload, doctor_payload)
    
    log_action("PATIENT_RECORD_VIEWED", role="SYSTEM", patient_id=con_data["patient_id"], details=f"Downloaded PDF for consultation {consultation_id}")
    
    filename = f"ArogyaMitra_Summary_{con_data.get('token_code', 'Report')}_{con_data['name'].replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
