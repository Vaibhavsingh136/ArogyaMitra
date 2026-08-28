"""
ArogyaMitra Doctor Dashboard, Dossier & Clinical Verification Router
Source of truth: systemdesign.md Section 9, 11 & User Requirements 14, 17, 18, 19, 22

Handles:
- Physician patient queue & workload metrics
- Comprehensive multi-tab patient clinical dossier:
  1. AI Summary & Verification
  2. Structured Medical History & Spoken Transcript
  3. Chronological Medical Timeline (Consultations, Documents, Labs, Radiology)
  4. Scanned OCR Documents
  5. Laboratory Diagnostic Reports & Alerts
  6. Radiology Reports & Imaging Studies
- Physician summary editing & digital verification stamping
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional

from app.db import get_medical_db
from app.models import SummaryEditRequest, SummaryVerifyRequest
from app.services.encryption_service import encrypt_clinical_data, decrypt_clinical_data
from app.services.ai_engine import translate_text_block
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/doctor", tags=["doctor"])

@router.get("/dashboard-stats")
def get_dashboard_stats(doctor_id: Optional[str] = "doc_1"):
    """Calculates real-time OPD dashboard metrics."""
    conn = get_medical_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM consultations")
    total_patients = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM consultations WHERE status IN ('SUBMITTED', 'DOCTOR_REVIEWING')")
    pending_verify = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM consultations WHERE status IN ('VERIFIED', 'COMPLETED')")
    verified_today = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM lab_reports WHERE doctor_alert = 1")
    abnormal_labs = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_patients": total_patients,
        "pending_verification": pending_verify,
        "verified_today": verified_today,
        "abnormal_lab_alerts": abnormal_labs
    }

@router.get("/queue")
def get_patient_queue(doctor_id: Optional[str] = None):
    """Retrieves OPD intake queue with priority ordering."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, p.name as patient_name, p.abha_id, p.date_of_birth, p.gender, p.phone, p.preferred_language,
               s.status as summary_status, s.summary_id,
               d.name as doctor_name
        FROM consultations c
        JOIN patients p ON c.patient_id = p.patient_id
        LEFT JOIN doctors d ON c.doctor_id = d.doctor_id
        LEFT JOIN ai_summaries s ON c.consultation_id = s.consultation_id
        ORDER BY 
            CASE c.status 
                WHEN 'SUBMITTED' THEN 1 
                WHEN 'DOCTOR_REVIEWING' THEN 2 
                WHEN 'IN_PROGRESS' THEN 3 
                WHEN 'VERIFIED' THEN 4 
                ELSE 5 
            END,
            c.queue_number ASC
    """)
    rows = cursor.fetchall()
    queue = [dict(r) for r in rows]
    conn.close()
    return {"queue": queue}

@router.get("/patient-dossier/{consultation_id}")
def get_patient_dossier(consultation_id: str, lang: str = 'en', request: Request = None):
    """
    Comprehensive multi-source patient dossier for physician evaluation:
    1. Demographics & ABHA Identity
    2. AI Clinical Summary (Draft or Verified)
    3. Structured Medical History (Chief complaint, HPI, PMH, PSH, Meds, Allergies, Family, ROS, AYUSH)
    4. Conversational Dialogue Transcript
    5. Digitized Historical Documents & OCR Entities
    6. Laboratory Reports & Flag Alerts
    7. Radiology Reports & Diagnostic Impressions
    8. Chronological Medical Timeline
    """
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    # 1. Consultation & Patient Record
    cursor.execute("""
        SELECT c.*, p.patient_id, p.abha_id, p.name as patient_name, p.date_of_birth, p.gender, 
               p.phone, p.address, p.preferred_language, p.blood_group, p.emergency_contact
        FROM consultations c
        JOIN patients p ON c.patient_id = p.patient_id
        WHERE c.consultation_id = ?
    """, (consultation_id,))
    con_row = cursor.fetchone()
    if not con_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    con_data = dict(con_row)
    patient_id = con_data["patient_id"]
    
    # 2. AI Summary
    cursor.execute("SELECT * FROM ai_summaries WHERE consultation_id = ?", (consultation_id,))
    sum_row = cursor.fetchone()
    ai_summary = None
    if sum_row:
        ai_summary = dict(sum_row)
        ai_summary["summary_text"] = decrypt_clinical_data(ai_summary.get("summary_text"))
        raw_struct = decrypt_clinical_data(ai_summary.get("structured_data_json"))
        try:
            ai_summary["structured_data"] = json.loads(raw_struct) if raw_struct else {}
        except Exception:
            ai_summary["structured_data"] = {}
        # Translate summary text on-the-fly for the requesting doctor's UI language
        try:
            if lang and lang != 'en':
                ai_summary["summary_text"] = translate_text_block(ai_summary["summary_text"], lang)
        except Exception:
            # Non-fatal: if translation fails, return original English summary
            pass
            
    # 3. Medical History
    cursor.execute("SELECT * FROM medical_histories WHERE consultation_id = ?", (consultation_id,))
    hist_row = cursor.fetchone()
    med_history = None
    if hist_row:
        med_history = dict(hist_row)
        for f in ["chief_complaint", "hpi", "past_medical_history", "past_surgical_history", "drug_history", "allergies", "family_history", "personal_history", "review_of_systems"]:
            if med_history.get(f):
                med_history[f] = decrypt_clinical_data(med_history[f])
        raw_ayush = decrypt_clinical_data(med_history.get("ayush_pariksha"))
        try:
            med_history["ayush_parsed"] = json.loads(raw_ayush) if raw_ayush else {}
        except Exception:
            med_history["ayush_parsed"] = {}

    # 4. History Responses & Dialogue Transcript
    cursor.execute("""
        SELECT r.*, q.question_text, q.category as question_category
        FROM history_responses r
        LEFT JOIN questions q ON r.question_id = q.question_id
        WHERE r.consultation_id = ?
        ORDER BY r.timestamp ASC
    """, (consultation_id,))
    responses = []
    for r in cursor.fetchall():
        rd = dict(r)
        rd["original_response"] = decrypt_clinical_data(rd.get("original_response"))
        rd["translated_response"] = decrypt_clinical_data(rd.get("translated_response"))
        responses.append(rd)

    # 5. Documents & OCR
    cursor.execute("""
        SELECT d.*, o.extracted_text, o.extracted_entities_json, o.confidence_score
        FROM documents d
        LEFT JOIN ocr_results o ON d.document_id = o.document_id
        WHERE d.patient_id = ?
        ORDER BY d.upload_date DESC
    """, (patient_id,))
    documents = []
    for dr in cursor.fetchall():
        d = dict(dr)
        d["extracted_text"] = decrypt_clinical_data(d.get("extracted_text"))
        raw_ent = decrypt_clinical_data(d.get("extracted_entities_json"))
        try:
            d["extracted_entities"] = json.loads(raw_ent) if raw_ent else {}
        except Exception:
            d["extracted_entities"] = {}
        documents.append(d)

    # 6. Lab Reports & Results
    cursor.execute("SELECT * FROM lab_reports WHERE patient_id = ? ORDER BY test_date DESC", (patient_id,))
    lab_reports = []
    for lr in cursor.fetchall():
        lab_dict = dict(lr)
        lab_dict["notes"] = decrypt_clinical_data(lab_dict.get("notes"))
        cursor.execute("SELECT * FROM lab_results WHERE lab_report_id = ?", (lab_dict["lab_report_id"],))
        lab_dict["results"] = [dict(res) for res in cursor.fetchall()]
        lab_reports.append(lab_dict)

    # 7. Radiology Reports
    cursor.execute("SELECT * FROM radiology_reports WHERE patient_id = ? ORDER BY study_date DESC", (patient_id,))
    radiology_reports = []
    for rr in cursor.fetchall():
        rad_dict = dict(rr)
        rad_dict["findings"] = decrypt_clinical_data(rad_dict.get("findings"))
        rad_dict["impression"] = decrypt_clinical_data(rad_dict.get("impression"))
        radiology_reports.append(rad_dict)

    # 8. Chronological Medical Timeline Assembly
    timeline = []
    # Consultations
    cursor.execute("SELECT * FROM consultations WHERE patient_id = ? ORDER BY date_time DESC", (patient_id,))
    for c in cursor.fetchall():
        timeline.append({
            "type": "CONSULTATION",
            "date": c["date_time"][:10],
            "title": f"OPD Consultation ({c['status']})",
            "details": c["chief_complaint_summary"] or "General evaluation",
            "badge": c["status"],
            "badge_color": "emerald" if c["status"] == "VERIFIED" else "amber"
        })
    # Documents
    for d in documents:
        timeline.append({
            "type": "DOCUMENT",
            "date": d["document_date"] or d["upload_date"][:10],
            "title": f"Scanned {d['document_type'].replace('_', ' ').title()}",
            "details": f"OCR Confidence: {d.get('confidence_score', 0.9):.0%}",
            "badge": "OCR SCANNED",
            "badge_color": "blue"
        })
    # Lab Reports
    for lr in lab_reports:
        flag_summary = ", ".join([f"{r['test_name']}: {r['value']} {r['unit']} ({r['flag']})" for r in lr["results"] if r.get("flag") != "NORMAL"])
        timeline.append({
            "type": "LAB_REPORT",
            "date": lr["test_date"][:10],
            "title": lr["test_type"],
            "details": flag_summary or "All parameters within normal reference limits.",
            "badge": "ALERT" if lr["doctor_alert"] else "NORMAL",
            "badge_color": "red" if lr["doctor_alert"] else "green"
        })
    # Radiology Reports
    for rr in radiology_reports:
        timeline.append({
            "type": "RADIOLOGY",
            "date": rr["study_date"][:10],
            "title": f"{rr['modality']}: {rr['study_type']}",
            "details": rr["impression"] or "Study completed.",
            "badge": "ALERT" if rr["alert_flag"] else "NORMAL",
            "badge_color": "red" if rr["alert_flag"] else "purple"
        })
        
    timeline.sort(key=lambda x: x["date"], reverse=True)
    conn.close()
    
    log_action("PATIENT_RECORD_VIEWED", role="DOCTOR", patient_id=patient_id, details=f"Doctor opened clinical dossier for {con_data['patient_name']}", ip_address=client_ip)
    
    return {
        "consultation": con_data,
        "ai_summary": ai_summary,
        "medical_history": med_history,
        "responses": responses,
        "documents": documents,
        "lab_reports": lab_reports,
        "radiology_reports": radiology_reports,
        "timeline": timeline
    }

@router.post("/edit-summary")
def edit_summary(req: SummaryEditRequest, request: Request):
    """Allows attending doctor to edit the AI draft summary."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    enc_text = encrypt_clinical_data(req.summary_text)
    
    cursor.execute("""
        UPDATE ai_summaries
        SET summary_text = ?, doctor_notes = ?, status = 'EDITED'
        WHERE summary_id = ? OR consultation_id = ?
    """, (enc_text, req.doctor_notes, req.summary_id, req.consultation_id))
    
    cursor.execute("""
        UPDATE consultations SET status = 'DOCTOR_REVIEWING' WHERE consultation_id = ?
    """, (req.consultation_id,))
    
    conn.commit()
    conn.close()
    
    log_action("SUMMARY_EDITED", role="DOCTOR", details=f"Doctor edited summary for consultation {req.consultation_id}", ip_address=client_ip)
    return {"success": True, "status": "EDITED"}

@router.post("/verify-summary")
def verify_summary(req: SummaryVerifyRequest, request: Request):
    """
    Physician verification step: Transitions summary to 'VERIFIED'
    with doctor digital stamp and audit timestamp.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    enc_text = encrypt_clinical_data(req.verified_summary_text) if req.verified_summary_text else None
    
    if enc_text:
        cursor.execute("""
            UPDATE ai_summaries
            SET status = 'VERIFIED', verified_by = ?, verified_at = ?, doctor_notes = ?, summary_text = ?
            WHERE summary_id = ? OR consultation_id = ?
        """, (req.doctor_id, now, req.doctor_notes, enc_text, req.summary_id, req.consultation_id))
    else:
        cursor.execute("""
            UPDATE ai_summaries
            SET status = 'VERIFIED', verified_by = ?, verified_at = ?, doctor_notes = ?
            WHERE summary_id = ? OR consultation_id = ?
        """, (req.doctor_id, now, req.doctor_notes, req.summary_id, req.consultation_id))
        
    cursor.execute("""
        UPDATE consultations
        SET status = 'VERIFIED'
        WHERE consultation_id = ?
    """, (req.consultation_id,))
    
    conn.commit()
    conn.close()
    
    log_action("SUMMARY_VERIFIED", user_id=req.doctor_id, role="DOCTOR", details=f"Doctor {req.doctor_id} verified summary for consultation {req.consultation_id}", ip_address=client_ip)
    
    return {
        "success": True,
        "status": "VERIFIED",
        "verified_at": now,
        "verified_by": req.doctor_id,
        "message": "Clinical summary successfully verified and signed by attending physician."
    }
