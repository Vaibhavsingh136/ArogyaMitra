"""
ArogyaMitra Radiologist Role & Diagnostic Imaging Router
Source of truth: User Requirements 11, 14, 17, 22 & systemdesign.md Section 8

Handles:
- Radiologist study queue (X-Ray, CT, MRI, Ultrasound)
- Radiology diagnostic report upload & findings encryption
- Critical findings alert flag triggers
- Integration with patient medical dossier & timeline
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional

from app.db import get_medical_db
from app.models import RadiologyReportCreate
from app.services.encryption_service import encrypt_clinical_data, decrypt_clinical_data
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/radiology", tags=["radiology"])

@router.get("/stats")
def get_radiology_stats():
    """Returns radiologist dashboard metrics."""
    conn = get_medical_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM radiology_reports")
    total_studies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM radiology_reports WHERE status = 'PRELIMINARY'")
    pending_reports = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM radiology_reports WHERE status = 'FINAL'")
    completed_today = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM radiology_reports WHERE alert_flag = 1")
    critical_alerts = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_studies": total_studies,
        "pending_reports": pending_reports,
        "completed_today": completed_today,
        "critical_alerts": critical_alerts
    }

@router.get("/queue")
def get_radiology_queue():
    """Returns queue of imaging studies for radiologists."""
    conn = get_medical_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, p.name as patient_name, p.abha_id, p.gender, p.date_of_birth, p.phone
        FROM radiology_reports r
        JOIN patients p ON r.patient_id = p.patient_id
        ORDER BY r.study_date DESC
    """)
    rows = cursor.fetchall()
    studies = []
    for row in rows:
        st = dict(row)
        st["findings"] = decrypt_clinical_data(st.get("findings"))
        st["impression"] = decrypt_clinical_data(st.get("impression"))
        studies.append(st)
        
    conn.close()
    return {"queue": studies}

@router.get("/presets")
def get_radiology_presets():
    """Returns realistic radiology templates and presets for 1-click reporting."""
    presets = [
        {
            "study_type": "Chest X-Ray PA View",
            "modality": "XRAY",
            "clinical_indication": "Exertional chest tightness & shortness of breath",
            "findings": "Cardiomegaly noted with prominent left ventricular contour. Bilateral perihilar bronchovascular markings are accentuated. Costophrenic sulci and dome of diaphragm appear normal. Bony thorax intact.",
            "impression": "Cardiomegaly with mild pulmonary venous congestion. Findings suspicious for early left ventricular dysfunction.",
            "recommendation": "Recommend 2D Echocardiogram with Doppler and clinical correlation with cardiac markers.",
            "alert_flag": True
        },
        {
            "study_type": "Brain MRI without Contrast",
            "modality": "MRI",
            "clinical_indication": "Severe throbbing bilateral temporal headaches and episodic visual blurriness",
            "findings": "Brain parenchyma demonstrates unremarkable signal intensity on T1, T2, and FLAIR sequences. No evidence of acute intracranial hemorrhage or territorial infarct. Ventricles and basal cisterns are normal in size and configuration.",
            "impression": "Normal brain MRI study without acute intracranial abnormality or mass effect.",
            "recommendation": "Ophthalmological evaluation and blood pressure monitoring advised.",
            "alert_flag": False
        },
        {
            "study_type": "High-Resolution Chest CT (HRCT)",
            "modality": "CT",
            "clinical_indication": "Persistent cough, evening fever & wheezing",
            "findings": "Thin section CT of the chest demonstrates clear lung parenchyma without focal consolidation, ground glass opacities, or bronchiectasis. Mediastinal and hilar lymph nodes are not enlarged.",
            "impression": "Unremarkable HRCT Chest. No radiological evidence of active pulmonary infection or interstitial lung disease.",
            "recommendation": "Spirometry / pulmonary function testing recommended for reactive airway disease evaluation.",
            "alert_flag": False
        }
    ]
    return {"presets": presets}

@router.post("/upload-report")
def upload_radiology_report(req: RadiologyReportCreate, request: Request):
    """
    Saves a verified radiology diagnostic report, encrypts clinical findings at rest,
    and links the study to the patient's medical timeline.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    conn = get_medical_db()
    cursor = conn.cursor()
    
    rad_id = f"rad_rep_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    enc_findings = encrypt_clinical_data(req.findings)
    enc_impression = encrypt_clinical_data(req.impression)
    alert_int = 1 if req.alert_flag else 0
    
    cursor.execute("""
        INSERT INTO radiology_reports (
            radiology_id, patient_id, consultation_id, document_id, study_type,
            modality, clinical_indication, findings, impression, recommendation,
            radiologist_id, status, alert_flag, study_date, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'FINAL', ?, ?, ?)
    """, (
        rad_id, req.patient_id, req.consultation_id, req.document_id, req.study_type,
        req.modality, req.clinical_indication or "", enc_findings, enc_impression,
        req.recommendation or "", req.radiologist_id or "rad_1", alert_int, req.study_date, now
    ))
    
    conn.commit()
    conn.close()
    
    log_action(
        "RADIOLOGY_REPORT_UPLOADED",
        user_id=req.radiologist_id or "rad_1",
        role="RADIOLOGIST",
        patient_id=req.patient_id,
        details=f"Uploaded {req.modality} ({req.study_type}) report (Alert: {bool(alert_int)})",
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "radiology_id": rad_id,
        "message": "Radiology report successfully uploaded and linked to patient clinical timeline."
    }

@router.get("/patient-history/{patient_id}")
def get_patient_radiology_history(patient_id: str):
    """Retrieves all imaging reports associated with a patient."""
    conn = get_medical_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM radiology_reports WHERE patient_id = ? ORDER BY study_date DESC
    """, (patient_id,))
    rows = cursor.fetchall()
    reports = []
    for r in rows:
        rd = dict(r)
        rd["findings"] = decrypt_clinical_data(rd.get("findings"))
        rd["impression"] = decrypt_clinical_data(rd.get("impression"))
        reports.append(rd)
    conn.close()
    return {"radiology_reports": reports}
