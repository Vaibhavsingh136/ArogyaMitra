"""
ArogyaMitra Clinical History Intake & AI Dialogue Router
Source of truth: systemdesign.md Module B & User Requirements 1, 2, 3, 23, 24

Handles:
- Centralized language state delivery
- Localized question branching and touch chips
- Live conversational synchronization
- AI draft summary synthesis (with skippable document support)
"""
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional
from app.db import get_medical_db
from app.models import QuestionResponseInput, StructuredHistoryUpdate
from app.services.ai_engine import (
    translate_prompt, normalize_response_to_english, determine_next_question, generate_clinical_summary
)
from app.services.encryption_service import encrypt_clinical_data, decrypt_clinical_data
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/intake", tags=["intake"])

@router.get("/questions")
def get_all_questions(lang: str = "en"):
    """Returns question tree localized into the target language with touch options."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions")
    raw_questions = [dict(q) for q in cursor.fetchall()]
    conn.close()
    
    localized_questions = []
    for q in raw_questions:
        q_copy = dict(q)
        q_copy["question_text"] = translate_prompt(q["question_text"], lang)
        
        options = json.loads(q["options_json"]) if q.get("options_json") else []
        translated_options = [translate_prompt(opt, lang) for opt in options]
        q_copy["options"] = translated_options
        q_copy["original_options"] = options
        localized_questions.append(q_copy)
        
    return {"questions": localized_questions}

@router.get("/session/{consultation_id}")
def get_intake_session(consultation_id: str):
    """Retrieves full responses, current progress, and structured history for an intake session."""
    conn = get_medical_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM consultations WHERE consultation_id = ?", (consultation_id,))
    consultation = cursor.fetchone()
    if not consultation:
        conn.close()
        raise HTTPException(status_code=404, detail="Consultation session not found")
        
    cursor.execute("""
        SELECT r.*, q.question_text, q.category as q_category, q.question_type 
        FROM history_responses r
        LEFT JOIN questions q ON r.question_id = q.question_id
        WHERE r.consultation_id = ?
        ORDER BY r.timestamp ASC
    """, (consultation_id,))
    raw_responses = cursor.fetchall()
    responses = []
    for r in raw_responses:
        r_dict = dict(r)
        r_dict["original_response"] = decrypt_clinical_data(r_dict.get("original_response"))
        r_dict["translated_response"] = decrypt_clinical_data(r_dict.get("translated_response"))
        responses.append(r_dict)
    
    cursor.execute("SELECT * FROM medical_histories WHERE consultation_id = ?", (consultation_id,))
    med_hist_row = cursor.fetchone()
    med_hist = None
    if med_hist_row:
        med_hist = dict(med_hist_row)
        for field in ["chief_complaint", "hpi", "past_medical_history", "past_surgical_history", "drug_history", "allergies", "family_history", "personal_history", "review_of_systems", "ayush_pariksha"]:
            if med_hist.get(field):
                med_hist[field] = decrypt_clinical_data(med_hist[field])
    
    cursor.execute("SELECT * FROM ai_summaries WHERE consultation_id = ?", (consultation_id,))
    ai_sum_row = cursor.fetchone()
    ai_summary = None
    if ai_sum_row:
        ai_summary = dict(ai_sum_row)
        ai_summary["summary_text"] = decrypt_clinical_data(ai_summary.get("summary_text"))
        raw_struct = decrypt_clinical_data(ai_summary.get("structured_data_json"))
        try:
            ai_summary["structured_data"] = json.loads(raw_struct) if raw_struct else {}
        except Exception:
            ai_summary["structured_data"] = {}
            
    conn.close()
    
    return {
        "consultation": dict(consultation),
        "responses": responses,
        "medical_history": med_hist,
        "ai_summary": ai_summary
    }

@router.post("/submit-response")
def submit_response(req: QuestionResponseInput, request: Request):
    """
    Records a patient's voice, touch, or text response, normalizes to English for clinical reference,
    and computes the next adaptive question in the patient's selected language.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    response_id = f"resp_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    norm_english = req.translated_response or normalize_response_to_english(req.original_response, req.current_language)
    
    # Store encrypted in database
    enc_orig = encrypt_clinical_data(req.original_response)
    enc_trans = encrypt_clinical_data(norm_english)
    
    cursor.execute("""
        INSERT INTO history_responses (response_id, consultation_id, question_id, category, original_response, translated_response, input_method, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (response_id, req.consultation_id, req.question_id, req.category, enc_orig, enc_trans, req.input_method, now))
    
    # Fetch all responses for branching logic
    cursor.execute("SELECT * FROM history_responses WHERE consultation_id = ?", (req.consultation_id,))
    all_responses = []
    for r in cursor.fetchall():
        rd = dict(r)
        rd["translated_response"] = decrypt_clinical_data(rd.get("translated_response"))
        all_responses.append(rd)
        
    next_q_id = determine_next_question(req.question_id, norm_english, all_responses)
    
    next_question_data = None
    if next_q_id and next_q_id != "q_complete":
        cursor.execute("SELECT * FROM questions WHERE question_id = ?", (next_q_id,))
        q_row = cursor.fetchone()
        if q_row:
            next_q = dict(q_row)
            next_q["question_text"] = translate_prompt(next_q["question_text"], req.current_language)
            opts = json.loads(next_q["options_json"]) if next_q.get("options_json") else []
            next_q["options"] = [translate_prompt(o, req.current_language) for o in opts]
            next_question_data = next_q
            
    conn.commit()
    conn.close()
    
    log_action("SUBMIT_INTAKE_RESPONSE", role="PATIENT", details=f"Consultation {req.consultation_id}: recorded {req.category} in {req.current_language} via {req.input_method}", ip_address=client_ip)
    
    return {
        "success": True,
        "response_id": response_id,
        "normalized_response": norm_english,
        "next_question_id": next_q_id,
        "next_question": next_question_data,
        "is_complete": next_q_id == "q_complete"
    }

@router.post("/generate-summary/{consultation_id}")
def trigger_summary_generation(consultation_id: str, request: Request, language: Optional[str] = "en"):
    """
    Synthesizes conversational responses, uploaded documents (optional),
    lab reports, and radiology reports into an AI Clinical Intake Summary with DRAFT status.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, p.name, p.gender, p.date_of_birth, p.phone, p.abha_id, p.preferred_language
        FROM consultations c
        JOIN patients p ON c.patient_id = p.patient_id
        WHERE c.consultation_id = ?
    """, (consultation_id,))
    con_row = cursor.fetchone()
    if not con_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    con_dict = dict(con_row)
    lang = con_dict.get("preferred_language") or language or "en"
    
    patient_info = {
        "name": con_dict["name"],
        "gender": con_dict["gender"],
        "date_of_birth": con_dict["date_of_birth"],
        "phone": con_dict["phone"],
        "abha_id": con_dict["abha_id"]
    }
    
    # Fetch and decrypt responses
    cursor.execute("SELECT * FROM history_responses WHERE consultation_id = ?", (consultation_id,))
    responses = []
    for r in cursor.fetchall():
        rd = dict(r)
        rd["original_response"] = decrypt_clinical_data(rd.get("original_response"))
        rd["translated_response"] = decrypt_clinical_data(rd.get("translated_response"))
        responses.append(rd)
        
    # Fetch documents & OCR
    cursor.execute("SELECT * FROM documents WHERE consultation_id = ? OR patient_id = ?", (consultation_id, con_dict["patient_id"]))
    documents = [dict(d) for d in cursor.fetchall()]
    
    # Fetch lab reports
    cursor.execute("SELECT * FROM lab_reports WHERE consultation_id = ? OR patient_id = ?", (consultation_id, con_dict["patient_id"]))
    lab_reports_raw = [dict(l) for l in cursor.fetchall()]
    lab_reports = []
    for lr in lab_reports_raw:
        cursor.execute("SELECT * FROM lab_results WHERE lab_report_id = ?", (lr["lab_report_id"],))
        lr["results"] = [dict(res) for res in cursor.fetchall()]
        lr["notes"] = decrypt_clinical_data(lr.get("notes"))
        lab_reports.append(lr)
        
    # Fetch radiology reports
    cursor.execute("SELECT * FROM radiology_reports WHERE consultation_id = ? OR patient_id = ?", (consultation_id, con_dict["patient_id"]))
    radiology_reports = []
    for rr in cursor.fetchall():
        rrd = dict(rr)
        rrd["findings"] = decrypt_clinical_data(rrd.get("findings"))
        rrd["impression"] = decrypt_clinical_data(rrd.get("impression"))
        radiology_reports.append(rrd)
        
    # Generate structured summary via AI engine
    summary_out = generate_clinical_summary(patient_info, responses, documents, lab_reports, radiology_reports, language=lang)
    
    summary_id = f"sum_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    # Encrypt summary text and structured data at rest
    enc_summary_text = encrypt_clinical_data(summary_out["summary_text"])
    enc_structured_data = encrypt_clinical_data(json.dumps(summary_out["structured_data"]))
    
    cursor.execute("""
        INSERT INTO ai_summaries (summary_id, consultation_id, generated_at, summary_text, structured_data_json, status)
        VALUES (?, ?, ?, ?, ?, 'DRAFT')
        ON CONFLICT(consultation_id) DO UPDATE SET
            generated_at = excluded.generated_at,
            summary_text = excluded.summary_text,
            structured_data_json = excluded.structured_data_json,
            status = 'DRAFT'
    """, (summary_id, consultation_id, now, enc_summary_text, enc_structured_data))
    
    # Update consultation status
    chief_comp = summary_out["structured_data"].get("chief_complaint", "Intake Completed")
    cursor.execute("""
        UPDATE consultations
        SET status = 'SUBMITTED', chief_complaint_summary = ?
        WHERE consultation_id = ?
    """, (chief_comp, consultation_id))
    
    # Upsert Medical History table
    hist_id = f"hist_{uuid.uuid4().hex[:8]}"
    s_data = summary_out["structured_data"]
    cursor.execute("""
        INSERT INTO medical_histories (history_id, patient_id, consultation_id, chief_complaint, hpi, past_medical_history, past_surgical_history, drug_history, allergies, family_history, personal_history, review_of_systems, ayush_pariksha, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(consultation_id) DO UPDATE SET
            chief_complaint = excluded.chief_complaint,
            hpi = excluded.hpi,
            past_medical_history = excluded.past_medical_history,
            past_surgical_history = excluded.past_surgical_history,
            drug_history = excluded.drug_history,
            allergies = excluded.allergies,
            family_history = excluded.family_history,
            personal_history = excluded.personal_history,
            review_of_systems = excluded.review_of_systems,
            ayush_pariksha = excluded.ayush_pariksha,
            updated_at = excluded.updated_at
    """, (
        hist_id, con_dict["patient_id"], consultation_id,
        encrypt_clinical_data(s_data.get("chief_complaint")),
        encrypt_clinical_data(s_data.get("history_of_present_illness")),
        encrypt_clinical_data(s_data.get("past_medical_history")),
        encrypt_clinical_data(s_data.get("past_surgical_history")),
        encrypt_clinical_data(", ".join(s_data.get("medications", []))),
        encrypt_clinical_data(", ".join(s_data.get("allergies", []))),
        encrypt_clinical_data(s_data.get("family_history")),
        encrypt_clinical_data(s_data.get("personal_history")),
        encrypt_clinical_data(s_data.get("review_of_systems")),
        encrypt_clinical_data(json.dumps({"notes": s_data.get("ayush_notes")})),
        now
    ))
    
    conn.commit()
    conn.close()
    
    log_action("SUMMARY_GENERATED", role="SYSTEM", patient_id=con_dict["patient_id"], details=f"Generated draft summary for consultation {consultation_id}", ip_address=client_ip)
    
    return {
        "success": True,
        "summary_id": summary_id,
        "status": "DRAFT",
        "summary_text": summary_out["summary_text"],
        "structured_data": summary_out["structured_data"]
    }
