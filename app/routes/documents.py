"""
ArogyaMitra Medical Document Digitization & OCR Router
Source of truth: systemdesign.md Section 7, User Requirement 3 & 19

Handles:
- Optional / skippable document uploads
- Multilingual OCR entity extraction
- Storing extracted clinical text encrypted at rest
"""
import os
import uuid
import json
import shutil
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from typing import Dict, Any, List, Optional
from app.config import UPLOAD_DIR, SAMPLE_DOCS_DIR
from app.db import get_medical_db
from app.services.ocr_engine import process_document_ocr, SAMPLE_OCR_DATABASE, validate_document_type
from app.services.encryption_service import encrypt_clinical_data, decrypt_clinical_data
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.get("/samples")
def get_sample_presets():
    """Returns realistic preset medical documents for 1-click evaluation."""
    samples = [
        {
            "id": "prescription_sample_1.png",
            "title": "Prescription - Hypertension & Headache (Dr. V. K. Aggarwal)",
            "type": "PRESCRIPTION",
            "date": "2023-11-15",
            "preview_url": "/static/sample_docs/prescription_sample_1.png",
            "description": "Printed OPD prescription with Amlodipine & Paracetamol dosage and instructions."
        },
        {
            "id": "lab_report_sample_1.png",
            "title": "Diabetic & Lipid Panel (Metropolis Labs)",
            "type": "LAB_REPORT",
            "date": "2024-07-10",
            "preview_url": "/static/sample_docs/lab_report_sample_1.png",
            "description": "Multi-parameter biochemistry panel with elevated Fasting Glucose, HbA1c & Cholesterol."
        },
        {
            "id": "discharge_summary_sample.png",
            "title": "Cardiac Inpatient Discharge Summary (Fortis)",
            "type": "DISCHARGE_SUMMARY",
            "date": "2024-01-20",
            "preview_url": "/static/sample_docs/discharge_summary_sample.png",
            "description": "Hospital discharge card for Angina Pectoris with cardiology medications & echo report."
        }
    ]
    return {"samples": samples}

@router.get("/list/{patient_id}")
def get_patient_documents(patient_id: str):
    """Retrieves all scanned documents for a patient."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, o.extracted_text, o.extracted_entities_json, o.confidence_score, o.processed_at
        FROM documents d
        LEFT JOIN ocr_results o ON d.document_id = o.document_id
        WHERE d.patient_id = ?
        ORDER BY d.upload_date DESC
    """, (patient_id,))
    rows = cursor.fetchall()
    docs = []
    for r in rows:
        d = dict(r)
        d["extracted_text"] = decrypt_clinical_data(d.get("extracted_text"))
        raw_ent = decrypt_clinical_data(d.get("extracted_entities_json"))
        try:
            d["extracted_entities"] = json.loads(raw_ent) if raw_ent else {}
        except Exception:
            d["extracted_entities"] = {}
        docs.append(d)
    conn.close()
    return {"documents": docs}

@router.post("/upload")
async def upload_document(
    patient_id: str = Form(...),
    consultation_id: Optional[str] = Form(None),
    document_type: str = Form("PRESCRIPTION"),
    preset_sample_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    request: Request = None
):
    """
    Uploads a medical document or selects a preset sample, triggers OCR extraction,
    and returns structured clinical entities. Document upload is completely optional in patient flow.
    """
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    if preset_sample_id:
        file_name = preset_sample_id
        file_path = f"/static/sample_docs/{preset_sample_id}"
    elif file:
        file_name = file.filename
        dest_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file_name}")
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file_path = f"/data/uploads/{doc_id}_{file_name}"
    else:
        file_name = "prescription_sample_1.png"
        file_path = f"/static/sample_docs/{file_name}"

    # Validate document before running full OCR
    validation = validate_document_type(file_name, file_path)
    # Threshold for accepting automatic OCR
    OCR_CONFIDENCE_THRESHOLD = 0.65
    if not validation.get("valid") or validation.get("confidence", 0.0) < OCR_CONFIDENCE_THRESHOLD:
        # Save document record but mark as REJECTED for OCR to avoid costly processing
        cursor = get_medical_db().cursor()
        cursor.execute("""
            INSERT INTO documents (document_id, patient_id, consultation_id, document_type, file_name, file_path, upload_date, document_date, language, ocr_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'en', 'REJECTED')
        """, (doc_id, patient_id, consultation_id, 'OTHER', file_name, file_path, now, None))
        get_medical_db().commit()
        # Log and return a friendly rejection reason
        log_action("DOCUMENT_REJECTED", role="PATIENT", patient_id=patient_id, details=f"Rejected upload {file_name}: {validation.get('reason')}", ip_address=client_ip)
        return {
            "success": False,
            "message": "Uploaded file does not appear to be a supported medical document. Please upload a prescription, lab report, discharge summary, or imaging report.",
            "reason": validation.get("reason"),
            "confidence": validation.get("confidence", 0.0)
        }

    # Process OCR & clinical entity extraction
    ocr_data = process_document_ocr(file_name, file_path)
    
    conn = get_medical_db()
    cursor = conn.cursor()
    
    # Save Document record
    cursor.execute("""
        INSERT INTO documents (document_id, patient_id, consultation_id, document_type, file_name, file_path, upload_date, document_date, language, ocr_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'en', 'COMPLETED')
    """, (doc_id, patient_id, consultation_id, ocr_data["document_type"], file_name, file_path, now, ocr_data["document_date"]))
    
    # Save Encrypted OCR Result
    ocr_id = f"ocr_{uuid.uuid4().hex[:8]}"
    enc_text = encrypt_clinical_data(ocr_data["extracted_text"])
    enc_entities = encrypt_clinical_data(json.dumps(ocr_data["extracted_entities"]))
    
    cursor.execute("""
        INSERT INTO ocr_results (ocr_id, document_id, extracted_text, extracted_entities_json, confidence_score, processed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ocr_id, doc_id, enc_text, enc_entities, ocr_data["confidence_score"], now))
    
    conn.commit()
    conn.close()
    
    log_action("DOCUMENT_UPLOADED", role="PATIENT", patient_id=patient_id, details=f"Scanned {file_name} as {ocr_data['document_type']} (Confidence: {ocr_data['confidence_score']:.0%})", ip_address=client_ip)
    
    return {
        "success": True,
        "document_id": doc_id,
        "file_name": file_name,
        "file_path": file_path,
        "document_type": ocr_data["document_type"],
        "document_date": ocr_data["document_date"],
        "ocr": {
            "extracted_text": ocr_data["extracted_text"],
            "extracted_entities": ocr_data["extracted_entities"],
            "confidence_score": ocr_data["confidence_score"]
        }
    }
