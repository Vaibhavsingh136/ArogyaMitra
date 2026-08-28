# ArogyaMitra (आरोग्यमित्र) — AI-Powered Pre-Consultation Clinical Intake Platform

> **Better History. Better Preparation. Better Conversations.**  
> *ArogyaMitra prepares the patient before the consultation so the doctor can focus on the patient during the consultation.*

ArogyaMitra is a multilingual, AI-powered clinical intake and medical document digitization platform designed for hospital Outpatient Departments (OPD) and kiosks. It allows patients to record a comprehensive medical history in their native language, scan prior prescriptions and lab reports, and prepare a structured, physician-ready summary prior to the doctor's consultation.

---

## 🌟 Core Product Purpose & Safety Principles

1. **Assists Clinical Workflow, Never Autonomous Diagnosis**: ArogyaMitra organizes patient history and extracts medical records; it does not replace the physician or autonomously diagnose conditions.
2. **Explicit Verification Lifecycle**: Every AI-generated clinical summary is visibly marked as an **AI-generated draft** until a licensed doctor reviews, edits if necessary, and digitally stamps it as **Doctor verified**.
3. **Multilingual Speech-First Accessibility**: Patients can speak or tap in 11 Indian languages (Hindi, Bengali, Telugu, Tamil, Marathi, Gujarati, Kannada, Odia, Malayalam, Punjabi, English) with voice recognition and text-to-speech audio guidance.
4. **Mock ABDM / ABHA Gateway Integration**: Interoperable with Ayushman Bharat Digital Mission (ABDM) standards, supporting ABHA ID identification and FHIR-ready resource exports.
5. **Future Priority Alert Detection**: Includes a dedicated "🚨 Priority Alert" feature with transparent non-diagnostic "Coming Soon" triage roadmap notices.

---

## 🎨 Brand Identity & Visual Design (`brandguideline.md`)

* **Primary Brand Color (`#7CA68D` - Arogya Green)**: Primary CTA buttons, navigation highlights, active states, progress indicators.
* **Secondary Brand Color (`#C0C3B9` - Soft Sage Gray)**: Subtle borders, secondary action buttons, muted panels.
* **Background (`#F3EFE3` - Calm Neutral)**: Kiosk screens, clean background, non-intimidating health companion theme.
* **Kiosk Touch Ergonomics**: Minimum 48px–56px touch targets, generous spacing, high-contrast typography, and minimal typing.

---

## 🏗️ System Architecture & Workflow

```text
               PATIENT ARRIVES AT KIOSK / WEB
                             │
                             ▼
                  Language Selection (11 Languages)
                             │
                             ▼
                ABHA ID Verification / Registration
                             │
                             ▼
              Granular Consent (Audio-Guided)
                             │
                             ▼
              Adaptive AI Health History Interview
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
   Voice Input (STT)                      Touch Chips / Text
        └────────────────────┬────────────────────┘
                             ▼
                 Speech-to-Text & Normalization
                             │
                             ▼
               Structured Clinical History
                             │
                             ▼
               Previous Medical Documents Upload
                             │
                             ▼
             Multilingual OCR & Entity Extraction
       (Medicines, Dosages, Investigations, Diagnoses)
                             │
                             ▼
                Chronological Medical Timeline
                             │
                             ▼
             AI Summary Generator (DRAFT State)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   Patient Copy & PDF Download        Doctor Dashboard Queue
                                              │
                                              ▼
                                   Physician Review & Edit
                                              │
                                              ▼
                                   Digital Doctor Verification
                                     (DOCTOR VERIFIED State)
                                              │
                                              ▼
                                   OPD Doctor Consultation
```

---

## 🚀 Quickstart & Running Instructions

### 1. Requirements
* Python 3.10+
* Packages: `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `pydantic`, `requests`, `reportlab`, `pillow`, `httpx`

### 2. Start the Application
```bash
python run.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

### 3. Run Automated Tests
```bash
python test_app.py
```

---

## 👥 Multi-Role Interactive Pitch Demo Guide

ArogyaMitra includes an instant **Role Switcher** in the top navigation bar:

### 1. 🧑‍🦽 Patient Kiosk Flow
1. **Choose Language**: Select from 11 languages (e.g. Hindi `हिन्दी`, Bengali `বাংলা`, Telugu `తెలుగు`). Listen to the audio greeting.
2. **Identification / ABHA**: Enter demo ABHA ID `91-4820-9182-3841@abdm` and click **Fetch ABHA** to autofill demographics.
3. **Privacy Consent**: Click **Listen in Audio** for audio guidance and accept consent.
4. **AI History Interview**:
   * Choose Chief Complaint (e.g. *Headache* or *Chest pain*).
   * Notice adaptive follow-up questions branching automatically (Onset, Nature, Triggers).
   * Use the **Speak** button or tap quick response chips.
   * Watch the **Live Structured Intake Record** update in real time.
5. **Document OCR Digitization**:
   * Click one of the 3 realistic preset samples (e.g. *Prescription - Dr. V. K. Aggarwal* or *Diabetic & Lipid Panel*).
   * Watch the animated scanning line and inspect extracted medicines (Amlodipine 5mg, Paracetamol 650mg) and test values.
6. **Summary & PDF**: View your draft summary and click **Download PDF Copy**.

### 2. 🩺 Doctor Dashboard Flow
1. Click **Doctor Dashboard** in the top bar.
2. Review top OPD queue metrics: *Today's Patients*, *Pending Verification*, *Verified Today*, *Abnormal Lab Alerts*.
3. Click **Open Dossier** on any patient (e.g. Rajesh Kumar or Sunita Devi).
4. Review the multi-tab medical dossier:
   * **AI Summary & Verification**: Edit narrative text, add physician clinical notes, and click **Accept & Verify Summary** (changes state to **Doctor Verified** with digital stamp).
   * **Structured History & Transcript**: View categorized medical history alongside original spoken transcripts.
   * **Medical Timeline**: View chronological history of consultations, prescriptions, and lab tests.
   * **Scanned OCR Documents**: Inspect scanned images and OCR confidence.
   * **Lab Reports & Alerts**: View abnormal flag highlights (HIGH/LOW).
5. Click **Priority Alert** button in the header to view the safety triage roadmap notice.

### 3. 🧪 Lab Diagnostics Flow
1. Click **Lab Diagnostics** in the top bar.
2. Select a patient, fill in test parameters, and see abnormal flags (High/Low) auto-highlighted and linked to the patient's timeline.

### 4. 🛡️ Admin & Compliance Flow
1. Click **Admin & Audit** in the top bar.
2. Inspect the real-time **Security & Compliance Audit Log** tracking views, edits, verifications, and consent grants.
3. Toggle operational parameters (AYUSH Pariksha Mode, Mock ABDM Gateway, Audio retention days).

---

## 📁 Repository Structure

```
SIH/
├── app/
│   ├── config.py             # Brand colors (#7CA68D, #C0C3B9, #F3EFE3) & configuration
│   ├── db.py                 # SQLite database engine, schemas & rich seed datasets
│   ├── models.py             # Pydantic schemas (Intake, Summary, Lab, Consent, ABDM)
│   ├── main.py               # FastAPI application & static asset routers
│   ├── routes/
│   │   ├── auth.py           # Role-based auth & demo switcher
│   │   ├── patient.py        # Patient registration & consent management
│   │   ├── intake.py         # Conversational clinical dialogue & summary synthesis
│   │   ├── documents.py      # Medical document upload & OCR processing
│   │   ├── doctor.py         # Doctor dashboard, dossier, summary verification & timeline
│   │   ├── lab.py            # Laboratory diagnostic results & flag alerts
│   │   ├── abdm.py           # Mock ABDM / ABHA gateway & FHIR bundle export
│   │   ├── admin.py          # Admin controls & audit logs
│   │   └── export.py         # PDF download and print views
│   ├── services/
│   │   ├── ai_engine.py      # Adaptive dialogue branching & summary synthesizer
│   │   ├── ocr_engine.py     # OCR engine & clinical entity extraction
│   │   ├── abdm_service.py   # ABDM adapter & FHIR resource bundle builder
│   │   ├── pdf_service.py    # ReportLab branded pre-consultation PDF generator
│   │   └── audit_service.py  # Security audit logging engine
│   ├── static/
│   │   ├── css/app.css       # Brand styling, animations, waveform visualizer, kiosk mode
│   │   ├── js/
│   │   │   ├── app.js        # State machine, role router, toast manager
│   │   │   ├── voice.js      # Web Speech STT & TTS controller
│   │   │   ├── intake.js     # Conversational interview engine & touch chips
│   │   │   ├── ocr_viewer.js # Document scanner & split-view OCR inspector
│   │   │   ├── doctor.js     # Doctor queue, dossier, timeline, and verification
│   │   │   ├── lab.js        # Lab report management & flag calculations
│   │   │   └── admin.js      # System configuration & audit logs table
│   │   └── sample_docs/      # Realistic sample medical images for OCR demo
│   └── templates/
│       └── index.html        # Unified responsive & kiosk-ready single page application
├── run.py                    # Server launcher
├── test_app.py               # Comprehensive automated test suite
├── generate_sample_docs.py   # Sample medical document generator
├── requirements.txt          # Python dependencies
└── README.md                 # Full documentation
```

---

## ⚖️ Clinical Safety & Legal Disclaimer

ArogyaMitra is a pre-consultation clinical intake and organization platform. It is engineered to assist healthcare workflows by gathering patient history and digitizing historical documents prior to consultation. It does not provide autonomous clinical diagnosis, medical prescriptions, or emergency triage. All clinical records and medical judgments remain strictly under the authority of licensed healthcare professionals.
