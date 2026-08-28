"""
ArogyaMitra 3-Tier Database Separation Architecture & Seed Engine
Source of truth: systemdesign.md Section 12, 13 & User Requirements 15-22

Database A: Patient Identity & Authentication DB (patient_identity.db)
Database B: Staff Identity & Credentials DB (staff_identity.db)
Database C: Medical / Clinical Records DB (medical_records.db - Encrypted at rest)
"""
import sqlite3
import json
import uuid
import hashlib
from datetime import datetime, timedelta
import secrets
from typing import Optional, Dict, Any, List

from app.config import (
    PATIENT_IDENTITY_DB_PATH,
    STAFF_IDENTITY_DB_PATH,
    MEDICAL_DB_PATH,
    DB_PATH
)
from app.services.encryption_service import encrypt_clinical_data, decrypt_clinical_data

def get_patient_identity_db():
    """Returns connection to isolated Patient Identity Database (DB A)."""
    # Set a busy timeout so transient locks are waited on instead of raising immediately
    conn = sqlite3.connect(PATIENT_IDENTITY_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def get_staff_identity_db():
    """Returns connection to isolated Staff Identity & Credentials Database (DB B)."""
    conn = sqlite3.connect(STAFF_IDENTITY_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def get_medical_db():
    """Returns connection to Clinical & Medical Records Database (DB C - Encrypted at rest)."""
    conn = sqlite3.connect(MEDICAL_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def get_db():
    """Default database accessor pointing to Medical DB for clinical services."""
    return get_medical_db()

def hash_password(password: str) -> str:
    """Standard SHA-256 password hashing with salt."""
    salt = "ArogyaMitra_2026_Auth_Salt"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def init_db():
    """Initializes all 3 isolated database tiers and seeds initial demonstration records."""
    from app.config import ENVIRONMENT, FORCE_INIT_DB

    # In production, avoid seeding demo data unless explicitly forced.
    if ENVIRONMENT.lower() == 'production' and not FORCE_INIT_DB:
        # Ensure databases/tables exist without seeding demo content
        init_patient_identity_db_seedless()
        init_staff_identity_db_seedless()
        init_medical_db_seedless()
        return

    # Development or forced initialization: create & seed as before
    init_patient_identity_db()
    init_staff_identity_db()
    init_medical_db()

def init_patient_identity_db():
    """Initializes Database A: Patient Identity DB."""
    conn = get_patient_identity_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_accounts (
        patient_id TEXT PRIMARY KEY,
        login_id TEXT UNIQUE NOT NULL, -- phone number or ABHA ID
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        account_status TEXT DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE
        created_at TEXT NOT NULL,
        last_login TEXT
    );
    """)
    conn.commit()

    # Seed Patient Accounts if empty
    cursor.execute("SELECT COUNT(*) FROM patient_accounts")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        patient_accounts = [
            ("pat_1", "+919876543210", hash_password("pat123"), "Rajesh Kumar", "ACTIVE", now, now),
            ("pat_2", "+919811122334", hash_password("pat123"), "Sunita Devi", "ACTIVE", now, now),
            ("pat_3", "+919723456789", hash_password("pat123"), "Mohammed Ali", "ACTIVE", now, now),
            ("pat_4", "+919901234567", hash_password("pat123"), "Anjali Sengupta", "ACTIVE", now, now),
            ("pat_5", "+919448123456", hash_password("pat123"), "Venkatesh Murthy", "ACTIVE", now, now),
            ("pat_demo", "patient@demo.com", hash_password("pat123"), "Rajesh Kumar", "ACTIVE", now, now),
        ]
        cursor.executemany("INSERT INTO patient_accounts VALUES (?, ?, ?, ?, ?, ?, ?)", patient_accounts)
        conn.commit()

    conn.close()

def init_patient_identity_db_seedless():
    """Create patient identity tables without seeding demo records."""
    conn = get_patient_identity_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_accounts (
        patient_id TEXT PRIMARY KEY,
        login_id TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        account_status TEXT DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL,
        last_login TEXT
    );
    """)
    conn.commit()
    conn.close()

def init_staff_identity_db():
    """Initializes Database B: Staff Identity DB (Doctor, Radiologist, Admin)."""
    conn = get_staff_identity_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff_accounts (
        staff_id TEXT PRIMARY KEY,
        login_id TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL, -- DOCTOR, RADIOLOGIST, ADMIN
        full_name TEXT NOT NULL,
        email TEXT,
        department TEXT,
        specialization TEXT,
        account_status TEXT DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE
        must_change_password INTEGER DEFAULT 0, -- 1: Force password change on next login
        created_at TEXT NOT NULL,
        last_login TEXT
    );
    """)
    conn.commit()

    # Seed Staff Accounts if empty
    cursor.execute("SELECT COUNT(*) FROM staff_accounts")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        staff_accounts = [
            # Default Hackathon Administrator Account (SIH@2026 / SIH@2026, must_change_password=1)
            ("staff_admin_0", "SIH@2026", hash_password("SIH@2026"), "ADMIN", "Administrator (SIH Demo)", "admin.sih@cityhospital.in", "System Administration", "Hospital Management", "ACTIVE", 1, now, None),
            
            # Direct Login Admins (No password change required)
            ("staff_admin_1", "ADM-1001", hash_password("admin123"), "ADMIN", "Priya Nair", "admin@cityhospital.in", "System Administration", "Security & Compliance", "ACTIVE", 0, now, now),
            ("staff_admin_2", "admin", hash_password("admin123"), "ADMIN", "System Admin (Direct Login)", "root.admin@cityhospital.in", "System Administration", "Hospital Management", "ACTIVE", 0, now, now),
            
            # Doctors
            ("staff_doc_1", "DOC-1001", hash_password("doc123"), "DOCTOR", "Dr. Rajesh Sharma, MD", "sharma.internalmed@cityhospital.in", "General Medicine OPD", "Internal Medicine & Diabetology", "ACTIVE", 0, now, now),
            ("staff_doc_2", "DOC-1002", hash_password("doc123"), "DOCTOR", "Dr. Ananya Patel, MBBS, DNB", "ananya.patel@cityhospital.in", "Cardiology OPD", "Cardiology & General Health", "ACTIVE", 0, now, now),
            ("staff_doc_3", "DOC-1003", hash_password("doc123"), "DOCTOR", "Dr. K. S. Iyer, MD (Ayurveda)", "iyer.ayush@cityhospital.in", "AYUSH Integrated OPD", "Kayachikitsa & Holistic Medicine", "ACTIVE", 0, now, now),
            
            # Radiologists
            ("staff_rad_1", "RAD-1001", hash_password("rad123"), "RADIOLOGIST", "Dr. Sunita Rao, MD", "sunita.radiology@cityhospital.in", "Department of Radiology & Imaging", "Diagnostic Neuroradiology & Body Imaging", "ACTIVE", 0, now, now),
            ("staff_rad_2", "RAD-1002", hash_password("rad123"), "RADIOLOGIST", "Dr. Vikram Joshi, DMRD", "vikram.imaging@cityhospital.in", "Department of Radiology & Imaging", "Musculoskeletal & Chest Radiology", "ACTIVE", 0, now, now),
        ]
        cursor.executemany("INSERT INTO staff_accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", staff_accounts)
        conn.commit()

    conn.close()

def init_staff_identity_db_seedless():
    """Create staff identity tables without seeding demo records."""
    conn = get_staff_identity_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff_accounts (
        staff_id TEXT PRIMARY KEY,
        login_id TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT,
        department TEXT,
        specialization TEXT,
        account_status TEXT DEFAULT 'ACTIVE',
        must_change_password INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        last_login TEXT
    );
    """)
    conn.commit()
    conn.close()

def init_medical_db():
    """Initializes Database C: Medical / Clinical DB."""
    conn = get_medical_db()
    cursor = conn.cursor()

    # 1. PATIENTS (Clinical Profile / Pseudonymized reference)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        abha_id TEXT UNIQUE,
        name TEXT NOT NULL,
        date_of_birth TEXT NOT NULL,
        gender TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT,
        preferred_language TEXT DEFAULT 'en',
        blood_group TEXT DEFAULT 'Unknown',
        emergency_contact TEXT,
        registration_date TEXT NOT NULL
    );
    """)

    # 2. DOCTORS (Clinical reference mapped from staff_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        doctor_id TEXT PRIMARY KEY,
        staff_id TEXT NOT NULL,
        name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        department TEXT NOT NULL,
        room_no TEXT,
        qualification TEXT,
        registration_no TEXT,
        preferred_language TEXT DEFAULT 'en'
    );
    """)

    # 3. RADIOLOGISTS (Clinical reference mapped from staff_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radiologists (
        radiologist_id TEXT PRIMARY KEY,
        staff_id TEXT NOT NULL,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        qualification TEXT,
        registration_no TEXT,
        preferred_language TEXT DEFAULT 'en'
    );
    """)

    # Ensure older deployments get the preferred_language column if missing
    try:
        cursor.execute("PRAGMA table_info(doctors)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'preferred_language' not in cols:
            cursor.execute("ALTER TABLE doctors ADD COLUMN preferred_language TEXT DEFAULT 'en'")
    except Exception:
        pass

    try:
        cursor.execute("PRAGMA table_info(radiologists)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'preferred_language' not in cols:
            cursor.execute("ALTER TABLE radiologists ADD COLUMN preferred_language TEXT DEFAULT 'en'")
    except Exception:
        pass

    # 4. CONSULTATIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultations (
        consultation_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        doctor_id TEXT,
        date_time TEXT NOT NULL,
        status TEXT NOT NULL, -- IN_PROGRESS, SUBMITTED, DOCTOR_REVIEWING, VERIFIED, COMPLETED
        queue_number INTEGER,
        token_code TEXT,
        chief_complaint_summary TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );
    """)

    # 5. QUESTIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        question_id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        subcategory TEXT,
        question_text TEXT NOT NULL,
        language TEXT DEFAULT 'en',
        question_type TEXT NOT NULL,
        options_json TEXT,
        branching_rules_json TEXT
    );
    """)

    # 6. HISTORY RESPONSES (Sensitive responses encrypted at rest)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history_responses (
        response_id TEXT PRIMARY KEY,
        consultation_id TEXT NOT NULL,
        question_id TEXT,
        category TEXT NOT NULL,
        original_response TEXT NOT NULL,
        translated_response TEXT,
        input_method TEXT NOT NULL, -- VOICE, TOUCH, TEXT
        timestamp TEXT NOT NULL,
        FOREIGN KEY (consultation_id) REFERENCES consultations(consultation_id)
    );
    """)

    # 7. MEDICAL HISTORIES (Encrypted fields for sensitive history)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medical_histories (
        history_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        consultation_id TEXT NOT NULL UNIQUE,
        chief_complaint TEXT,
        hpi TEXT,
        past_medical_history TEXT,
        past_surgical_history TEXT,
        drug_history TEXT,
        allergies TEXT,
        family_history TEXT,
        personal_history TEXT,
        review_of_systems TEXT,
        ayush_pariksha TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY (consultation_id) REFERENCES consultations(consultation_id)
    );
    """)

    # 8. AI SUMMARIES (Draft and Verified records, encrypted narrative)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_summaries (
        summary_id TEXT PRIMARY KEY,
        consultation_id TEXT NOT NULL UNIQUE,
        generated_at TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        structured_data_json TEXT NOT NULL,
        status TEXT NOT NULL, -- DRAFT, EDITED, VERIFIED
        verified_by TEXT,
        verified_at TEXT,
        doctor_notes TEXT,
        FOREIGN KEY (consultation_id) REFERENCES consultations(consultation_id)
    );
    """)

    # 9. DOCUMENTS (Uploaded medical files & OCR links)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        consultation_id TEXT,
        document_type TEXT NOT NULL, -- PRESCRIPTION, LAB_REPORT, DISCHARGE_SUMMARY, IMAGING_REPORT, OTHER
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        document_date TEXT,
        language TEXT DEFAULT 'en',
        ocr_status TEXT DEFAULT 'COMPLETED',
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );
    """)

    # 10. OCR RESULTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ocr_results (
        ocr_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL UNIQUE,
        extracted_text TEXT NOT NULL,
        extracted_entities_json TEXT NOT NULL,
        confidence_score REAL DEFAULT 0.95,
        processed_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(document_id)
    );
    """)

    # 11. LAB REPORTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_reports (
        lab_report_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        consultation_id TEXT,
        document_id TEXT,
        test_date TEXT NOT NULL,
        test_type TEXT NOT NULL,
        status TEXT DEFAULT 'FINAL',
        doctor_alert INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );
    """)

    # 12. LAB RESULTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_results (
        result_id TEXT PRIMARY KEY,
        lab_report_id TEXT NOT NULL,
        test_name TEXT NOT NULL,
        value TEXT NOT NULL,
        unit TEXT NOT NULL,
        reference_range TEXT NOT NULL,
        flag TEXT DEFAULT 'NORMAL', -- NORMAL, HIGH, LOW, CRITICAL
        FOREIGN KEY (lab_report_id) REFERENCES lab_reports(lab_report_id)
    );
    """)

    # 13. RADIOLOGY REPORTS (Radiologist first-class diagnostic records)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radiology_reports (
        radiology_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        consultation_id TEXT,
        document_id TEXT,
        study_type TEXT NOT NULL, -- Chest X-Ray PA, Brain CT, Lumbar Spine MRI, Abdominal USG
        modality TEXT NOT NULL, -- XRAY, CT, MRI, USG
        clinical_indication TEXT,
        findings TEXT NOT NULL, -- Encrypted at rest
        impression TEXT NOT NULL, -- Encrypted at rest
        recommendation TEXT,
        radiologist_id TEXT,
        status TEXT DEFAULT 'FINAL', -- PRELIMINARY, FINAL, CRITICAL_ALERT
        alert_flag INTEGER DEFAULT 0,
        study_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );
    """)

    # 14. CONSENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consents (
        consent_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        consultation_id TEXT,
        consent_type TEXT NOT NULL,
        consent_status TEXT NOT NULL, -- GRANTED, REVOKED
        given_at TEXT NOT NULL,
        revoked_at TEXT,
        audio_guided INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );
    """)

    # 15. AUDIT LOGS (Immutable security audit stream)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id TEXT PRIMARY KEY,
        user_id TEXT,
        role TEXT,
        patient_id TEXT,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp TEXT NOT NULL
    );
    """)

    # 16. SYSTEM CONFIG
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    conn.commit()

    # Seed clinical records if empty
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] == 0:
        seed_medical_data(cursor, conn)

    conn.close()

def init_medical_db_seedless():
    """Create medical DB tables without seeding demo data."""
    conn = get_medical_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        abha_id TEXT UNIQUE,
        name TEXT NOT NULL,
        date_of_birth TEXT NOT NULL,
        gender TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT,
        preferred_language TEXT DEFAULT 'en',
        blood_group TEXT DEFAULT 'Unknown',
        emergency_contact TEXT,
        registration_date TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        doctor_id TEXT PRIMARY KEY,
        staff_id TEXT NOT NULL,
        name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        department TEXT NOT NULL,
        room_no TEXT,
        qualification TEXT,
        registration_no TEXT,
        preferred_language TEXT DEFAULT 'en'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radiologists (
        radiologist_id TEXT PRIMARY KEY,
        staff_id TEXT NOT NULL,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        qualification TEXT,
        registration_no TEXT,
        preferred_language TEXT DEFAULT 'en'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultations (
        consultation_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        doctor_id TEXT,
        created_at TEXT,
        status TEXT,
        queue_number INTEGER,
        display_id TEXT,
        chief_complaint TEXT
    );
    """)

    # Force init tokens table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS force_init_tokens (
        token TEXT PRIMARY KEY,
        created_at TEXT,
        expires_at TEXT,
        used INTEGER DEFAULT 0,
        created_by TEXT
    );
    """)

    # 8. Force Init Tokens (one-time tokens for admin-triggered forced initialization)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS force_init_tokens (
        token TEXT PRIMARY KEY,
        created_at TEXT,
        expires_at TEXT,
        used INTEGER DEFAULT 0,
        created_by TEXT
    );
    """)

    conn.commit()
    conn.close()

def force_init_db_if_allowed():
    """Performs a forced full initialization including seeding regardless of ENV, but safe-guards are enforced by caller."""
    # Caller must validate admin credentials and force_key; here we simply call full init
    init_patient_identity_db()
    init_staff_identity_db()
    init_medical_db()
    return True


def create_force_init_token(created_by_staff_id: str, ttl_minutes: int = 15):
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(minutes=ttl_minutes)
    conn = get_medical_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO force_init_tokens (token, created_at, expires_at, used, created_by) VALUES (?, ?, ?, ?, ?)", (
        token, now.isoformat(), expires.isoformat(), 0, created_by_staff_id
    ))
    conn.commit()
    conn.close()
    return token, expires.isoformat()


def consume_force_init_token(token: str):
    conn = get_medical_db()
    cur = conn.cursor()
    cur.execute("SELECT token, created_at, expires_at, used, created_by FROM force_init_tokens WHERE token = ?", (token,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "not_found"

    if row[3]:
        conn.close()
        return False, "already_used"

    expires_at = datetime.fromisoformat(row[2])
    if datetime.now() > expires_at:
        conn.close()
        return False, "expired"

    # mark used
    cur.execute("UPDATE force_init_tokens SET used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return True, "ok"

def seed_medical_data(cursor, conn):
    """Populates rich seed datasets with encrypted medical records."""
    now = datetime.now()
    t_now = now.isoformat()
    t_yesterday = (now - timedelta(days=1)).isoformat()
    t_last_week = (now - timedelta(days=7)).isoformat()
    t_last_month = (now - timedelta(days=30)).isoformat()

    # System Configs
    cursor.executemany("INSERT INTO system_config (key, value) VALUES (?, ?)", [
        ("mock_abdm", "true"),
        ("ayush_mode", "true"),
        ("retention_policy_days", "30"),
        ("auto_tts", "true")
    ])

    # 1. Seed Doctors
    doctors = [
        ("doc_1", "staff_doc_1", "Dr. Rajesh Sharma", "Internal Medicine & Diabetology", "General Medicine OPD", "OPD Room 104", "MD (General Medicine), FACP", "MCI-48291", "en"),
        ("doc_2", "staff_doc_2", "Dr. Ananya Patel", "Cardiology & General Health", "Cardiology OPD", "OPD Room 202", "MBBS, DNB (Cardiology)", "MCI-59102", "en"),
        ("doc_3", "staff_doc_3", "Dr. K. S. Iyer", "Kayachikitsa & Holistic Medicine", "AYUSH Integrated OPD", "AYUSH Wing Room 12", "BAMS, MD (Kayachikitsa)", "AYU-10943", "en"),
    ]
    cursor.executemany("INSERT INTO doctors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", doctors)

    # 2. Seed Radiologists
    radiologists = [
        ("rad_1", "staff_rad_1", "Dr. Sunita Rao", "Department of Radiology & Imaging", "MD (Radiodiagnosis), FRCR", "KMC-71928", "en"),
        ("rad_2", "staff_rad_2", "Dr. Vikram Joshi", "Department of Radiology & Imaging", "MBBS, DMRD", "DMC-82103", "en"),
    ]
    cursor.executemany("INSERT INTO radiologists VALUES (?, ?, ?, ?, ?, ?, ?)", radiologists)

    # 3. Seed Patients
    patients = [
        ("pat_1", "91-4820-9182-3841@abdm", "Rajesh Kumar", "1978-05-14", "Male", "+91 98765 43210", "H-42, Sector 15, New Delhi", "hi", "B+", "+91 98765 43211", t_last_month),
        ("pat_2", "82-1940-5829-1049@abdm", "Sunita Devi", "1965-11-20", "Female", "+91 98111 22334", "Village Rampur, Distt. Varanasi, UP", "hi", "O+", "+91 98111 22335", t_last_month),
        ("pat_3", "74-5029-4829-6192@abdm", "Mohammed Ali", "1988-03-08", "Male", "+91 97234 56789", "Flat 302, Green Avenue, Hyderabad", "te", "A+", "+91 97234 56780", t_last_week),
        ("pat_4", "63-8201-4920-1920@abdm", "Anjali Sengupta", "1995-09-12", "Female", "+91 99012 34567", "Block C, Salt Lake, Kolkata", "bn", "AB+", "+91 99012 34568", t_yesterday),
        ("pat_5", "55-9012-3481-9920@abdm", "Venkatesh Murthy", "1952-07-25", "Male", "+91 94481 23456", "14th Cross, Malleshwaram, Bengaluru", "kn", "O-", "+91 94481 23457", t_now),
    ]
    cursor.executemany("INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", patients)

    # 4. Seed Consultations
    consultations = [
        ("con_1", "pat_1", "doc_1", t_now, "SUBMITTED", 101, "AM-101", "Throbbing headache & blurred vision for 3 days"),
        ("con_2", "pat_2", "doc_1", t_now, "DOCTOR_REVIEWING", 102, "AM-102", "Chest tightness, breathlessness on exertion & fatigue"),
        ("con_3", "pat_3", "doc_2", t_yesterday, "VERIFIED", 103, "AM-103", "Persistent dry cough, mild fever & wheezing"),
        ("con_4", "pat_4", "doc_1", t_yesterday, "COMPLETED", 104, "AM-104", "Bilateral knee joint pain, morning stiffness for 6 months"),
        ("con_5", "pat_5", "doc_3", t_now, "IN_PROGRESS", 105, "AM-105", "Chronic indigestion, bloating (Ajeerna) and insomnia"),
    ]
    cursor.executemany("INSERT INTO consultations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", consultations)

    # 5. Seed History Responses
    responses = [
        ("resp_1", "con_1", "q_cc_1", "CHIEF_COMPLAINT", encrypt_clinical_data("सिरदर्द"), encrypt_clinical_data("Headache"), "VOICE", t_now),
        ("resp_2", "con_1", "q_hpi_headache_1", "HPI", encrypt_clinical_data("3 दिन से"), encrypt_clinical_data("For 3 days"), "VOICE", t_now),
        ("resp_3", "con_1", "q_hpi_headache_2", "HPI", encrypt_clinical_data("तेज धड़कन जैसा दर्द"), encrypt_clinical_data("Throbbing / Pulsing"), "TOUCH", t_now),
        ("resp_4", "con_2", "q_cc_1", "CHIEF_COMPLAINT", encrypt_clinical_data("सीने में दर्द या भारीपन"), encrypt_clinical_data("Chest pain or tightness"), "TOUCH", t_now),
    ]
    cursor.executemany("INSERT INTO history_responses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", responses)

    # 6. Seed Medical History
    med_histories = [
        (
            "hist_1", "pat_1", "con_1",
            encrypt_clinical_data("Severe throbbing headache in bilateral temporal regions and intermittent blurred vision."),
            encrypt_clinical_data("Symptoms started 3 days ago, progressive. Worsens with bright sunlight and screen usage; partially relieved by darkness and paracetamol. No nausea or vomiting."),
            encrypt_clinical_data("Known case of Essential Hypertension (diagnosed 2021) on irregular medication."),
            encrypt_clinical_data("Appendectomy in 2012 (uncomplicated)."),
            encrypt_clinical_data("Tab Amlodipine 5mg once daily (admits missing doses frequently)."),
            encrypt_clinical_data("No known drug allergies. Mild dust allergy."),
            encrypt_clinical_data("Father had ischemic heart disease; Mother has Type 2 Diabetes."),
            encrypt_clinical_data("Non-smoker, occasional alcohol, sedentary desk job, high work-related stress."),
            encrypt_clinical_data("CNS: Headaches, no seizures. CVS: No palpitations. Resp: Clear. GI: Normal."),
            encrypt_clinical_data(json.dumps({"prakriti": "Pitta-Vata", "agni": "Tikshnagni", "satva": "Madhyama"})),
            t_now
        ),
        (
            "hist_2", "pat_2", "con_2",
            encrypt_clinical_data("Substernal chest heaviness and shortness of breath (NYHA Class II) on climbing stairs."),
            encrypt_clinical_data("Began 2 weeks ago, noticeable during household chores. Relieved after 5-10 minutes of resting. Associated with generalized lethargy."),
            encrypt_clinical_data("Type 2 Diabetes Mellitus x 8 years, Hypertension x 5 years."),
            encrypt_clinical_data("Bilateral tubal ligation (1998)."),
            encrypt_clinical_data("Tab Metformin 500mg BD, Tab Telmisartan 40mg OD, Tab Atorvastatin 10mg HS."),
            encrypt_clinical_data("Allergic to Penicillin (developed urticarial rash in 2015)."),
            encrypt_clinical_data("Strong family history of CAD (brother underwent PTCA at age 52)."),
            encrypt_clinical_data("Vegetarian diet, post-menopausal, non-smoker, moderate physical activity."),
            encrypt_clinical_data("CVS: Exertional dyspnea. Resp: No orthopnea. Musculoskeletal: Mild lumbar ache."),
            encrypt_clinical_data(json.dumps({"prakriti": "Kapha-Vata", "agni": "Mandagni", "satva": "Pravara"})),
            t_now
        )
    ]
    cursor.executemany("INSERT INTO medical_histories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", med_histories)

    # 7. Seed AI Summaries
    summary_1_struct = {
        "patient_info": {"name": "Rajesh Kumar", "age": 48, "gender": "Male", "abha": "91-4820-9182-3841@abdm"},
        "chief_complaint": "Bilateral temporal throbbing headache x 3 days with intermittent visual blurring.",
        "hpi": "Progressive onset over 72 hours. Triggered by screen time & bright light. Partial relief with rest/paracetamol. Denies photophobia, fever, vomiting or neurological deficits.",
        "past_medical_history": "Hypertension (3 years, poor compliance).",
        "past_surgical_history": "Appendectomy (2012).",
        "medications": ["Tab Amlodipine 5mg OD (Irregular)"],
        "allergies": ["No known drug allergies (NKDA)"],
        "family_history": "Paternal IHD, Maternal T2DM.",
        "personal_history": "Desk job, high stress, non-smoker.",
        "review_of_systems": "CNS: Headache + visual blurring; CVS/RS/GI: Unremarkable.",
        "previous_investigations": "Old BP reading 150/94 mmHg recorded at pharmacy 1 week ago.",
        "timeline_summary": "1 historical prescription scanned showing Amlodipine prescription from 2023.",
        "ayush_notes": "Pitta-Vata imbalance noted with hyperacidity tendencies."
    }

    summary_2_struct = {
        "patient_info": {"name": "Sunita Devi", "age": 60, "gender": "Female", "abha": "82-1940-5829-1049@abdm"},
        "chief_complaint": "Exertional chest tightness & dyspnea (NYHA Class II) x 2 weeks.",
        "hpi": "Retrosternal discomfort occurring during moderate exertion, resolving with rest in 5-10 mins. Fatigue and lethargy present. Denies radiating pain to jaw/left arm.",
        "past_medical_history": "T2DM (8 yrs), Hypertension (5 yrs).",
        "past_surgical_history": "Tubal ligation (1998).",
        "medications": ["Tab Metformin 500mg BD", "Tab Telmisartan 40mg OD", "Tab Atorvastatin 10mg HS"],
        "allergies": ["PENICILLIN (causes rash/urticaria)"],
        "family_history": "Brother CAD (PTCA at 52 yrs).",
        "personal_history": "Sedentary, vegetarian diet.",
        "review_of_systems": "CVS: Exertional chest tightness; Endocrine: Polyuria on/off.",
        "previous_investigations": "Recent Fasting Blood Sugar: 148 mg/dL; HbA1c: 7.6% (1 month ago).",
        "timeline_summary": "Discharge summary & previous cardiology ECG scanned from local clinic.",
        "ayush_notes": "Kapha-Vata dominant, Mandagni with mild Ama symptoms."
    }

    summaries = [
        (
            "sum_1", "con_1", t_now,
            encrypt_clinical_data("PATIENT OVERVIEW:\n48yo Male presenting with 3-day history of throbbing bilateral temporal headaches and episodic visual blurriness.\n\nCLINICAL CONTEXT:\nKnown hypertensive with poor medication compliance on Tab Amlodipine 5mg. Visual disturbance and worsening headaches require urgent fundoscopy and BP monitoring.\n\nKEY MEDICAL HISTORY:\n- HTN (poor compliance)\n- Appendectomy (2012)\n- NKDA\n- Family history of premature coronary artery disease.\n\nRECOMMENDED REVIEW:\nConfirm current blood pressure, rule out hypertensive encephalopathy/urgency, check recent renal profile."),
            encrypt_clinical_data(json.dumps(summary_1_struct)),
            "DRAFT", None, None, None
        ),
        (
            "sum_2", "con_2", t_now,
            encrypt_clinical_data("PATIENT OVERVIEW:\n60yo Female presenting with 2-week history of exertional retrosternal chest heaviness and NYHA Class II dyspnea.\n\nCLINICAL CONTEXT:\nHigh cardiovascular risk profile (T2DM x 8yr, HTN x 5yr, positive family history CAD). Symptoms concerning for stable angina pectoris.\n\nKEY MEDICAL HISTORY:\n- T2DM on Metformin 500mg BD\n- HTN on Telmisartan 40mg OD\n- Dyslipidemia on Atorvastatin 10mg HS\n- ALLERGY: PENICILLIN (Urticaria)\n\nRECOMMENDED REVIEW:\nResting 12-lead ECG, Troponin I/T baseline, HbA1c, Echocardiogram, and Cardiology consult."),
            encrypt_clinical_data(json.dumps(summary_2_struct)),
            "DRAFT", None, None, None
        ),
        (
            "sum_3", "con_3", t_yesterday,
            encrypt_clinical_data("PATIENT OVERVIEW:\n38yo Male presenting with persistent dry cough and low-grade evening fevers for 10 days.\n\nDOCTOR VERIFIED NOTE:\nPatient evaluated. Chest X-ray PA view advised. Commenced on bronchodilator & inhaled corticosteroid. Summary accepted with minor medication dosage corrections."),
            encrypt_clinical_data(json.dumps({
                "chief_complaint": "Dry cough & evening fever x 10 days",
                "diagnoses": ["Reactive Airway Disease", "Post-viral bronchial hyperreactivity"],
                "allergies": ["Sulfa drugs (itching)"],
                "status": "VERIFIED"
            })),
            "VERIFIED", "doc_2", t_yesterday, "Patient reviewed in OPD. Prescribed Levosalbutamol + Budesonide inhaler. Follow-up in 1 week."
        )
    ]
    cursor.executemany("INSERT INTO ai_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", summaries)

    # 8. Seed Documents & OCR Results
    documents = [
        ("doc_file_1", "pat_1", "con_1", "PRESCRIPTION", "prescription_delhi_clinic_2023.jpg", "/static/sample_docs/prescription_sample_1.png", t_last_month, "2023-11-15", "en", "COMPLETED"),
        ("doc_file_2", "pat_2", "con_2", "LAB_REPORT", "lipid_and_sugar_panel_2024.pdf", "/static/sample_docs/lab_report_sample_1.png", t_last_week, "2024-07-10", "en", "COMPLETED"),
        ("doc_file_3", "pat_2", "con_2", "DISCHARGE_SUMMARY", "cardiac_opd_discharge_summary.pdf", "/static/sample_docs/discharge_summary_sample.png", t_last_month, "2024-01-20", "en", "COMPLETED")
    ]
    cursor.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", documents)

    ocr_results = [
        (
            "ocr_1", "doc_file_1",
            encrypt_clinical_data("Dr. V. K. Aggarwal, MD (Med)\nApollo Clinic, Saket\nPatient: Rajesh Kumar, 46M\nRx:\n1. Tab Amlodipine 5mg - 1 tab once daily in morning\n2. Tab Paracetamol 650mg - SOS for body ache\nAdvise: Low salt diet, regular BP charting, lipid profile."),
            encrypt_clinical_data(json.dumps({
                "diagnoses": ["Essential Hypertension - Grade 1"],
                "medications": [
                    {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once Daily (OD)", "duration": "30 days"},
                    {"name": "Paracetamol", "dosage": "650mg", "frequency": "SOS / As needed", "duration": "5 days"}
                ],
                "investigations": [{"name": "Blood Pressure", "value": "148/92", "unit": "mmHg"}],
                "confidence_score": 0.94
            })),
            0.94, t_last_month
        ),
        (
            "ocr_2", "doc_file_2",
            encrypt_clinical_data("METROPOLIS HEALTHCARE LAB\nPatient: Sunita Devi, 59F\nTEST REPORT:\nFasting Blood Glucose: 154 mg/dL (Ref: 70-100)\nPost Prandial Glucose: 210 mg/dL (Ref: <140)\nHbA1c (Glycated Hemoglobin): 7.8 % (Ref: 4.0-5.6)\nSerum Cholesterol: 218 mg/dL (Ref: <200)\nSerum Triglycerides: 195 mg/dL (Ref: <150)\nSerum HDL: 42 mg/dL (Ref: >50)\nSerum LDL: 137 mg/dL (Ref: <100)"),
            encrypt_clinical_data(json.dumps({
                "diagnoses": ["Uncontrolled Type 2 Diabetes Mellitus", "Mixed Dyslipidemia"],
                "investigations": [
                    {"name": "Fasting Blood Glucose", "value": "154", "unit": "mg/dL", "reference": "70-100", "flag": "HIGH"},
                    {"name": "Post Prandial Glucose", "value": "210", "unit": "mg/dL", "reference": "<140", "flag": "HIGH"},
                    {"name": "HbA1c", "value": "7.8", "unit": "%", "reference": "4.0-5.6", "flag": "HIGH"},
                    {"name": "Total Cholesterol", "value": "218", "unit": "mg/dL", "reference": "<200", "flag": "HIGH"},
                    {"name": "Serum LDL", "value": "137", "unit": "mg/dL", "reference": "<100", "flag": "HIGH"}
                ],
                "confidence_score": 0.98
            })),
            0.98, t_last_week
        )
    ]
    cursor.executemany("INSERT INTO ocr_results VALUES (?, ?, ?, ?, ?, ?)", ocr_results)

    # 9. Seed Lab Reports & Results
    lab_reports = [
        ("lab_rep_1", "pat_1", "con_1", "doc_file_1", t_now, "Complete Blood Count & Renal Panel", "FINAL", 0, encrypt_clinical_data("Routine pre-op checkup panel"), t_now),
        ("lab_rep_2", "pat_2", "con_2", "doc_file_2", t_yesterday, "Comprehensive Diabetes & Lipid Profile", "FINAL", 1, encrypt_clinical_data("Alert: High HbA1c & Fasting Glucose"), t_yesterday)
    ]
    cursor.executemany("INSERT INTO lab_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", lab_reports)

    lab_results = [
        ("lr_1", "lab_rep_1", "Hemoglobin", "14.2", "g/dL", "13.0 - 17.0", "NORMAL"),
        ("lr_2", "lab_rep_1", "Total Leukocyte Count", "7,400", "/cu.mm", "4,000 - 11,000", "NORMAL"),
        ("lr_3", "lab_rep_1", "Platelet Count", "2.4", "Lakhs/cu.mm", "1.5 - 4.5", "NORMAL"),
        ("lr_4", "lab_rep_1", "Serum Creatinine", "0.9", "mg/dL", "0.7 - 1.2", "NORMAL"),
        ("lr_5", "lab_rep_1", "Blood Urea", "24", "mg/dL", "15 - 40", "NORMAL"),
        ("lr_6", "lab_rep_2", "Fasting Blood Sugar", "154", "mg/dL", "70 - 100", "HIGH"),
        ("lr_7", "lab_rep_2", "HbA1c", "7.8", "%", "4.0 - 5.6", "HIGH"),
        ("lr_8", "lab_rep_2", "Total Cholesterol", "218", "mg/dL", "< 200", "HIGH"),
        ("lr_9", "lab_rep_2", "Serum Triglycerides", "195", "mg/dL", "< 150", "HIGH"),
        ("lr_10", "lab_rep_2", "Serum HDL", "42", "mg/dL", "> 50", "LOW"),
        ("lr_11", "lab_rep_2", "Serum LDL", "137", "mg/dL", "< 100", "HIGH"),
        ("lr_12", "lab_rep_2", "Serum Creatinine", "1.1", "mg/dL", "0.6 - 1.1", "NORMAL"),
    ]
    cursor.executemany("INSERT INTO lab_results VALUES (?, ?, ?, ?, ?, ?, ?)", lab_results)

    # 10. Seed Radiology Reports (Radiologist First-Class Role Data)
    radiology_reports = [
        (
            "rad_rep_1", "pat_1", "con_1", None,
            "Brain MRI without Contrast", "MRI",
            "Persistent bilateral temporal headache and visual blurring for 3 days.",
            encrypt_clinical_data("Brain parenchyma demonstrates normal signal intensity. No acute intracranial hemorrhage, major territorial infarction, or mass effect. Ventricles and sulci are within normal limits for age. Major intracranial flow voids preserved."),
            encrypt_clinical_data("Normal Brain MRI study. No acute intracranial pathology or space-occupying lesion identified."),
            "Clinical correlation with blood pressure control and ophthalmological evaluation for visual blurring advised.",
            "rad_1", "FINAL", 0, t_yesterday, t_yesterday
        ),
        (
            "rad_rep_2", "pat_2", "con_2", None,
            "Chest X-Ray PA View", "XRAY",
            "Exertional dyspnea and retrosternal tightness x 2 weeks.",
            encrypt_clinical_data("Cardiomegaly noted with LV configuration. Prominent bronchovascular markings in bilateral perihilar regions. Costophrenic angles clear. No focal consolidation or pneumothorax."),
            encrypt_clinical_data("Cardiomegaly with mild pulmonary venous congestion. Correlate with 2D Echocardiogram and cardiac biomarkers."),
            "Urgent 2D Echocardiogram and Cardiology consultation recommended.",
            "rad_1", "FINAL", 1, t_now, t_now
        ),
        (
            "rad_rep_3", "pat_3", "con_3", None,
            "High-Resolution Chest CT (HRCT)", "CT",
            "Chronic cough and low-grade evening fever x 10 days.",
            encrypt_clinical_data("Bilateral lung fields demonstrate clear parenchyma with no centrilobular nodules, tree-in-bud opacities, or pleural effusion. Tracheobronchial tree is patent."),
            encrypt_clinical_data("Unremarkable HRCT Chest. No radiological evidence of active pulmonary infection or bronchiectasis."),
            "Recommend spirometry / PFT to evaluate reactive airway disease.",
            "rad_2", "FINAL", 0, t_last_week, t_last_week
        )
    ]
    cursor.executemany("INSERT INTO radiology_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", radiology_reports)

    # 11. Seed Consents
    consents = [
        ("con_sent_1", "pat_1", "con_1", "PRE_CONSULTATION_AI_INTAKE", "GRANTED", t_now, None, 1),
        ("con_sent_2", "pat_2", "con_2", "PRE_CONSULTATION_AI_INTAKE", "GRANTED", t_now, None, 1),
        ("con_sent_3", "pat_3", "con_3", "PRE_CONSULTATION_AI_INTAKE", "GRANTED", t_yesterday, None, 0),
    ]
    cursor.executemany("INSERT INTO consents VALUES (?, ?, ?, ?, ?, ?, ?, ?)", consents)

    # 12. Seed Audit Logs
    audit_logs = [
        ("log_1", "staff_admin_0", "ADMIN", None, "LOGIN", "Default demo admin logged in", "127.0.0.1", t_now),
        ("log_2", "pat_1", "PATIENT", "pat_1", "GRANT_CONSENT", "Patient granted explicit AI intake consent with audio guidance", "127.0.0.1", t_now),
        ("log_3", "pat_1", "PATIENT", "pat_1", "SUBMIT_INTAKE", "Completed voice and touch health history interview in Hindi", "127.0.0.1", t_now),
        ("log_4", "staff_doc_1", "DOCTOR", "pat_1", "VIEW_PATIENT_DOSSIER", "Doctor opened pre-consultation dossier for Rajesh Kumar", "192.168.1.104", t_now),
        ("log_5", "staff_rad_1", "RADIOLOGIST", "pat_2", "RADIOLOGY_REPORT_UPLOADED", "Radiologist uploaded Chest X-Ray PA report with Alert", "192.168.1.150", t_now),
        ("log_6", "staff_doc_2", "DOCTOR", "pat_3", "VERIFY_SUMMARY", "Doctor verified AI summary for Mohammed Ali", "192.168.1.202", t_yesterday),
    ]
    cursor.executemany("INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", audit_logs)

    # 13. Seed Clinical Intake Questions
    questions = [
        # Chief Complaint
        ("q_cc_1", "CHIEF_COMPLAINT", "primary", "What is your main health problem today?", "en", "single_choice",
         json.dumps(["Headache", "Chest pain or tightness", "Fever & Chills", "Cough & Breathlessness", "Stomach ache / Digestion", "Joint or Back pain", "Diabetes / Sugar check", "High Blood Pressure", "Other symptom"]),
         json.dumps({"Headache": "q_hpi_headache_1", "Chest pain or tightness": "q_hpi_chest_1", "Fever & Chills": "q_hpi_fever_1", "Stomach ache / Digestion": "q_hpi_gi_1"})),

        # HPI - Headache branch
        ("q_hpi_headache_1", "HPI", "onset", "When did your headache start?", "en", "single_choice",
         json.dumps(["Today morning", "1-3 days ago", "1-2 weeks ago", "More than a month ago"]),
         json.dumps({"default": "q_hpi_headache_2"})),
        ("q_hpi_headache_2", "HPI", "nature", "What does the headache feel like?", "en", "single_choice",
         json.dumps(["Throbbing / Pulsing", "Dull continuous ache", "Sharp stabbing pain", "Heavy pressure around forehead"]),
         json.dumps({"default": "q_hpi_headache_3"})),
        ("q_hpi_headache_3", "HPI", "triggers", "What makes the pain worse or better?", "en", "single_choice",
         json.dumps(["Worse with bright light or screens", "Worse with physical activity", "Better after resting in dark room", "Better after taking painkiller"]),
         json.dumps({"default": "q_pmh_1"})),

        # HPI - Chest Pain branch
        ("q_hpi_chest_1", "HPI", "onset", "When did you first notice the chest discomfort?", "en", "single_choice",
         json.dumps(["Just now / today", "Past 2-3 days", "Past 2 weeks", "On and off for months"]),
         json.dumps({"default": "q_hpi_chest_2"})),
        ("q_hpi_chest_2", "HPI", "exertion", "Does the discomfort increase when walking or climbing stairs?", "en", "single_choice",
         json.dumps(["Yes, increases on exertion and relieves with rest", "No, it occurs even while resting", "Worse while taking deep breaths", "Worse after heavy meals"]),
         json.dumps({"default": "q_pmh_1"})),

        # HPI - Fever & Chills branch
        ("q_hpi_fever_1", "HPI", "fever_onset", "How long have you had the fever and are there chills?", "en", "single_choice",
         json.dumps(["Started today with mild chills", "2-3 days with high body temperature", "More than a week with night sweats", "Intermittent fever on and off"]),
         json.dumps({"default": "q_pmh_1"})),

        # HPI - GI branch
        ("q_hpi_gi_1", "HPI", "gi_onset", "Where is the stomach discomfort and when does it occur?", "en", "single_choice",
         json.dumps(["Upper stomach burning after meals", "Lower abdomen cramping", "Generalized bloating and gas", "Continuous severe pain"]),
         json.dumps({"default": "q_pmh_1"})),

        # General Past Medical History
        ("q_pmh_1", "PAST_MEDICAL_HISTORY", "conditions", "Do you have any existing long-term medical conditions?", "en", "multi_choice",
         json.dumps(["High Blood Pressure (Hypertension)", "Diabetes (High Blood Sugar)", "Thyroid Disorder", "Heart Condition", "Asthma / Breathing problem", "Kidney Disease", "None of these"]),
         json.dumps({"default": "q_psh_1"})),

        # Past Surgical History
        ("q_psh_1", "PAST_SURGICAL_HISTORY", "surgeries", "Have you had any surgeries or major hospital admissions in the past?", "en", "single_choice",
         json.dumps(["No previous surgeries", "Yes, minor surgery", "Yes, major surgery", "Hospitalized for illness in past"]),
         json.dumps({"default": "q_med_1"})),

        # Medication History
        ("q_med_1", "MEDICATIONS", "current_drugs", "Are you currently taking any regular medicines or supplements?", "en", "single_choice",
         json.dumps(["Yes, for Blood Pressure", "Yes, for Diabetes / Sugar", "Yes, multiple daily medicines", "Only occasional medicines / None", "I brought my prescriptions to scan"]),
         json.dumps({"default": "q_all_1"})),

        # Allergy History
        ("q_all_1", "ALLERGIES", "drug_allergies", "Do you have any known allergies to medicines or food?", "en", "single_choice",
         json.dumps(["No known allergies", "Allergic to Penicillin / Antibiotics", "Allergic to Painkillers (NSAIDs)", "Allergic to Sulfa drugs", "Dust / Pollen allergy", "Food allergy"]),
         json.dumps({"default": "q_fam_1"})),

        # Family History
        ("q_fam_1", "FAMILY_HISTORY", "hereditary", "Is there any history of major illnesses in your immediate family?", "en", "multi_choice",
         json.dumps(["Diabetes in parents/siblings", "High Blood Pressure", "Heart Disease / Heart Attack", "Cancer history", "Asthma / Allergies", "No major family illness"]),
         json.dumps({"default": "q_pers_1"})),

        # Personal / Lifestyle History
        ("q_pers_1", "PERSONAL_HISTORY", "lifestyle", "Tell us briefly about your daily lifestyle and diet:", "en", "single_choice",
         json.dumps(["Vegetarian diet, non-smoker", "Non-vegetarian diet, non-smoker", "Desk job with high daily stress", "Active physical routine", "Smoker / Tobacco user", "Occasional alcohol"]),
         json.dumps({"default": "q_ros_1"})),

        # Review of Systems
        ("q_ros_1", "REVIEW_OF_SYSTEMS", "systemic_check", "Are you experiencing any other symptoms currently?", "en", "multi_choice",
         json.dumps(["Dizziness / Lightheadedness", "Blurry vision", "Fatigue / Weakness", "Loss of appetite", "Difficulty sleeping", "Weight loss / gain", "None of the above"]),
         json.dumps({"default": "q_ayush_1"})),

        # AYUSH Pariksha (Optional)
        ("q_ayush_1", "AYUSH_PARIKSHA", "agni_prakriti", "[AYUSH Assessment] How is your general appetite and digestion (Agni)?", "en", "single_choice",
         json.dumps(["Normal and regular (Samagni)", "Irregular / bloated (Vishamagni)", "Very sharp / burning sensation (Tikshnagni)", "Sluggish / slow digestion (Mandagni)", "Skip AYUSH section"]),
         json.dumps({"default": "q_complete"}))
    ]
    cursor.executemany("INSERT INTO questions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", questions)

    conn.commit()
