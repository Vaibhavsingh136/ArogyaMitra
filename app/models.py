"""
ArogyaMitra Pydantic Data Models & Request/Response Schemas
Source of truth: systemdesign.md Section 12, 13 & User Requirements
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ============================================================
# AUTHENTICATION & IDENTITY SCHEMAS
# ============================================================

class PatientRegisterRequest(BaseModel):
    name: str
    phone: str
    password: str
    date_of_birth: str = "1985-01-01"
    gender: str = "Male"
    abha_id: Optional[str] = ""
    preferred_language: str = "en"
    address: Optional[str] = ""
    blood_group: Optional[str] = "Unknown"
    emergency_contact: Optional[str] = ""

class PatientLoginRequest(BaseModel):
    login_id: str  # Phone number, ABHA ID, or username
    password: str

class StaffLoginRequest(BaseModel):
    login_id: str  # Login ID (e.g. DOC-1001, RAD-1001, SIH@2026)
    password: str
    expected_role: Optional[str] = None  # DOCTOR, RADIOLOGIST, ADMIN

class StaffChangePasswordRequest(BaseModel):
    login_id: str
    old_password: str
    new_password: str
    confirm_password: str

class StaffGenerateCredentialsRequest(BaseModel):
    role: str  # DOCTOR, RADIOLOGIST, ADMIN
    full_name: str
    email: Optional[str] = ""
    department: Optional[str] = "General Medicine"
    specialization: Optional[str] = "Internal Medicine"
    qualification: Optional[str] = "MBBS, MD"
    registration_no: Optional[str] = "REG-9999"

class StaffToggleStatusRequest(BaseModel):
    staff_id: str
    account_status: str  # ACTIVE, INACTIVE

# Legacy / Demo Compatibility
class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None

class DemoSwitchRequest(BaseModel):
    role: str
    user_id: Optional[str] = None

# ============================================================
# PATIENT CLINICAL & CONSENT SCHEMAS
# ============================================================

class PatientRegistration(BaseModel):
    name: str
    date_of_birth: str  # YYYY-MM-DD
    gender: str         # Male, Female, Other
    phone: str
    address: Optional[str] = ""
    preferred_language: str = "en"
    abha_id: Optional[str] = ""
    blood_group: Optional[str] = "Unknown"
    emergency_contact: Optional[str] = ""

class ConsentRequest(BaseModel):
    patient_id: str
    consultation_id: Optional[str] = None
    consent_type: str = "PRE_CONSULTATION_AI_INTAKE"
    consent_status: str = "GRANTED"  # GRANTED, REVOKED
    audio_guided: bool = False

# ============================================================
# CLINICAL INTAKE & DIALOGUE SCHEMAS
# ============================================================

class QuestionResponseInput(BaseModel):
    consultation_id: str
    question_id: str
    category: str
    original_response: str
    translated_response: Optional[str] = None
    input_method: str = "VOICE"  # VOICE, TOUCH, TEXT
    current_language: str = "en"

class StructuredHistoryUpdate(BaseModel):
    consultation_id: str
    chief_complaint: Optional[str] = None
    hpi: Optional[str] = None
    past_medical_history: Optional[str] = None
    past_surgical_history: Optional[str] = None
    drug_history: Optional[str] = None
    allergies: Optional[str] = None
    family_history: Optional[str] = None
    personal_history: Optional[str] = None
    review_of_systems: Optional[str] = None
    ayush_pariksha: Optional[Dict[str, Any]] = None

# ============================================================
# SUMMARY VERIFICATION SCHEMAS
# ============================================================

class SummaryEditRequest(BaseModel):
    summary_id: str
    consultation_id: str
    summary_text: str
    structured_data: Optional[Dict[str, Any]] = None
    doctor_notes: Optional[str] = None

class SummaryVerifyRequest(BaseModel):
    summary_id: str
    consultation_id: str
    doctor_id: str
    doctor_notes: Optional[str] = ""
    verified_summary_text: Optional[str] = None

# ============================================================
# LAB DIAGNOSTICS SCHEMAS
# ============================================================

class LabResultItem(BaseModel):
    test_name: str
    value: str
    unit: str
    reference_range: str
    flag: str = "NORMAL"  # NORMAL, HIGH, LOW, CRITICAL

class LabReportCreate(BaseModel):
    patient_id: str
    consultation_id: Optional[str] = None
    document_id: Optional[str] = None
    test_date: str
    test_type: str
    doctor_alert: bool = False
    notes: Optional[str] = ""
    results: List[LabResultItem] = []

# ============================================================
# RADIOLOGY & IMAGING SCHEMAS (FIRST-CLASS ROLE)
# ============================================================

class RadiologyReportCreate(BaseModel):
    patient_id: str
    consultation_id: Optional[str] = None
    document_id: Optional[str] = None
    study_type: str  # e.g., Chest X-Ray PA, Brain MRI, Abdominal USG
    modality: str    # XRAY, CT, MRI, USG
    clinical_indication: Optional[str] = ""
    findings: str
    impression: str
    recommendation: Optional[str] = ""
    radiologist_id: Optional[str] = "rad_1"
    alert_flag: bool = False
    study_date: str

# ============================================================
# DOCUMENT & OCR SCHEMAS
# ============================================================

class DocumentEntityExtraction(BaseModel):
    diagnoses: List[str] = []
    medications: List[Dict[str, Any]] = []
    investigations: List[Dict[str, Any]] = []
    procedures: List[str] = []
    dates: List[str] = []
    confidence_score: float = 0.95

# ============================================================
# ABDM & ADMIN SCHEMAS
# ============================================================

class ABHAVerifyRequest(BaseModel):
    abha_id: str
    auth_method: str = "OTP"  # OTP, DEMO_LINK

class SystemConfigUpdate(BaseModel):
    mock_abdm: Optional[bool] = None
    ayush_mode: Optional[bool] = None
    retention_days: Optional[int] = None
    active_languages: Optional[List[str]] = None

# Admin-only force init request
class ForceInitRequest(BaseModel):
    admin_login: str
    admin_password: str
    force_key: Optional[str] = None


class ForceTokenRequest(BaseModel):
    admin_login: str
    admin_password: str
    ttl_minutes: Optional[int] = 15
