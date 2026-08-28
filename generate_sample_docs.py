"""
Generates realistic sample medical document images for ArogyaMitra OCR demo
"""
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent / "app" / "static" / "sample_docs"
os.makedirs(SAMPLE_DIR, exist_ok=True)

def create_prescription_image():
    img = Image.new('RGB', (800, 1100), color='#FAFAF8')
    draw = ImageDraw.Draw(img)
    
    # Border & Header
    draw.rectangle([(20, 20), (780, 1080)], outline='#C0C3B9', width=2)
    draw.rectangle([(20, 20), (780, 140)], fill='#7CA68D')
    
    # Header Text
    draw.text((40, 35), "APOLLO CLINIC & HEALTHCARE", fill='#FFFFFF')
    draw.text((40, 70), "Dr. V. K. Aggarwal, MD (Internal Medicine)", fill='#FFFFFF')
    draw.text((40, 100), "Reg No: MCI-48201 | Saket OPD, New Delhi | Ph: +91 11 2685 9900", fill='#E2E8F0')
    
    # Patient Info Bar
    draw.rectangle([(40, 160), (760, 220)], fill='#F3EFE3', outline='#C0C3B9')
    draw.text((60, 175), "Patient: Rajesh Kumar | Age: 46Y | Male | Date: 15-Nov-2023", fill='#1E293B')
    draw.text((60, 195), "ABHA ID: 91-4820-9182-3841@abdm | Vitals: BP 148/92 mmHg, PR 78 bpm", fill='#475569')
    
    # Rx Symbol & Content
    draw.text((60, 250), "Diagnosis: Essential Hypertension (Stage 1), Tension Headache", fill='#1E293B')
    draw.line([(60, 280), (740, 280)], fill='#CBD5E1', width=1)
    
    draw.text((60, 300), "Rx (Prescription Details):", fill='#7CA68D')
    
    meds = [
        "1. Tab. Amlodipine 5mg (Amlopres 5)",
        "   Sig: 1 Tablet OD (Once Daily in morning after breakfast) x 30 Days",
        "",
        "2. Tab. Paracetamol 650mg (Dolo 650)",
        "   Sig: 1 Tablet SOS (As needed for severe headache) x 5 Days",
        "",
        "3. Tab. Pantoprazole 40mg (Pan 40)",
        "   Sig: 1 Tablet OD (Before breakfast) x 14 Days"
    ]
    
    y = 340
    for line in meds:
        draw.text((80, y), line, fill='#1E293B')
        y += 26
        
    draw.line([(60, 560), (740, 560)], fill='#CBD5E1', width=1)
    draw.text((60, 580), "Clinical Advice & Follow-up:", fill='#7CA68D')
    draw.text((80, 610), "- Low salt diet (DASH diet), avoid processed food", fill='#334155')
    draw.text((80, 640), "- Regular 30 mins brisk walking, daily BP charting", fill='#334155')
    draw.text((80, 670), "- Review after 4 weeks with Fasting Lipid Profile & Serum Creatinine", fill='#334155')
    
    # Signature box
    draw.rectangle([(500, 920), (740, 1040)], outline='#94A3B8', width=1)
    draw.text((520, 935), "Dr. V. K. Aggarwal", fill='#0F172A')
    draw.text((520, 960), "MD, FACP (Senior Consultant)", fill='#64748B')
    draw.text((520, 1010), "[Verified Digital Signature]", fill='#059669')
    
    img.save(SAMPLE_DIR / "prescription_sample_1.png")

def create_lab_report_image():
    img = Image.new('RGB', (800, 1100), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.rectangle([(20, 20), (780, 1080)], outline='#CBD5E1', width=2)
    draw.rectangle([(20, 20), (780, 130)], fill='#1E293B')
    draw.text((40, 35), "METROPOLIS HEALTHCARE & DIAGNOSTICS", fill='#FFFFFF')
    draw.text((40, 70), "NABL Accredited Reference Clinical Laboratory | ISO 15189 Certified", fill='#94A3B8')
    draw.text((40, 95), "Report ID: LAB-2024-84920 | Date: 10-Jul-2024", fill='#CBD5E1')
    
    # Demographics
    draw.rectangle([(40, 150), (760, 210)], fill='#F8FAFC', outline='#E2E8F0')
    draw.text((50, 160), "Patient: Sunita Devi | Age: 59 Yrs / Female | Ref by: Dr. Rajesh Sharma", fill='#0F172A')
    draw.text((50, 185), "Sample: Blood (Serum) | Collection Time: 10-Jul-2024 07:30 AM", fill='#475569')
    
    # Table Header
    draw.rectangle([(40, 230), (760, 265)], fill='#7CA68D')
    draw.text((50, 240), "TEST NAME", fill='#FFFFFF')
    draw.text((320, 240), "RESULT", fill='#FFFFFF')
    draw.text((440, 240), "UNIT", fill='#FFFFFF')
    draw.text((540, 240), "REFERENCE RANGE", fill='#FFFFFF')
    draw.text((690, 240), "FLAG", fill='#FFFFFF')
    
    tests = [
        ("Fasting Blood Glucose (FBS)", "154.0", "mg/dL", "70.0 - 100.0", "HIGH", True),
        ("Post Prandial Glucose (PPBS)", "210.0", "mg/dL", "< 140.0", "HIGH", True),
        ("HbA1c (Glycated Hemoglobin)", "7.8", "%", "4.0 - 5.6", "HIGH", True),
        ("Serum Total Cholesterol", "218.0", "mg/dL", "< 200.0", "HIGH", True),
        ("Serum Triglycerides", "195.0", "mg/dL", "< 150.0", "HIGH", True),
        ("Serum HDL (Good Cholesterol)", "42.0", "mg/dL", "> 50.0", "LOW", True),
        ("Serum LDL (Bad Cholesterol)", "137.0", "mg/dL", "< 100.0", "HIGH", True),
        ("Serum Creatinine", "0.95", "mg/dL", "0.60 - 1.10", "NORMAL", False),
        ("Blood Urea Nitrogen (BUN)", "16.2", "mg/dL", "7.0 - 20.0", "NORMAL", False)
    ]
    
    y = 280
    for name, res, unit, ref, flag, is_abnormal in tests:
        row_bg = '#FEF2F2' if is_abnormal else '#FFFFFF'
        draw.rectangle([(40, y-5), (760, y+25)], fill=row_bg)
        draw.text((50, y), name, fill='#0F172A')
        draw.text((320, y), res, fill='#DC2626' if is_abnormal else '#0F172A')
        draw.text((440, y), unit, fill='#64748B')
        draw.text((540, y), ref, fill='#64748B')
        draw.text((690, y), flag, fill='#DC2626' if is_abnormal else '#059669')
        draw.line([(40, y+25), (760, y+25)], fill='#E2E8F0', width=1)
        y += 35
        
    draw.text((50, 680), "Interpretation: Uncontrolled glycemic indices (Elevated HbA1c & FBS) with mixed dyslipidemia.", fill='#334155')
    draw.text((50, 710), "Physician Alert: Priority clinical review advised for medication titration.", fill='#DC2626')
    
    img.save(SAMPLE_DIR / "lab_report_sample_1.png")

def create_discharge_summary_image():
    img = Image.new('RGB', (800, 1100), color='#FAFAF8')
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([(20, 20), (780, 1080)], outline='#C0C3B9', width=2)
    draw.rectangle([(20, 20), (780, 130)], fill='#2563EB')
    draw.text((40, 35), "FORTIS HEART & MULTISPECIALTY HOSPITAL", fill='#FFFFFF')
    draw.text((40, 70), "CLINICAL DISCHARGE SUMMARY", fill='#FFFFFF')
    draw.text((40, 95), "IPD: IP-94021 | Admission: 18-Jan-2024 | Discharge: 20-Jan-2024", fill='#DBEAFE')
    
    draw.rectangle([(40, 150), (760, 210)], fill='#F3EFE3', outline='#C0C3B9')
    draw.text((50, 160), "Patient: Sunita Devi | 59F | Consultant: Dr. S. K. Roy, DM (Cardiology)", fill='#1E293B')
    draw.text((50, 185), "Allergies: PENICILLIN (Causes cutaneous urticaria)", fill='#DC2626')
    
    draw.text((50, 240), "FINAL CLINICAL DIAGNOSIS:", fill='#1E293B')
    draw.text((70, 270), "1. Stable Angina Pectoris (CCS Class II)", fill='#0F172A')
    draw.text((70, 295), "2. Type 2 Diabetes Mellitus x 8 Years", fill='#0F172A')
    draw.text((70, 320), "3. Essential Hypertension x 5 Years", fill='#0F172A')
    
    draw.line([(50, 360), (750, 360)], fill='#CBD5E1', width=1)
    draw.text((50, 380), "INVESTIGATIONS & HOSPITAL COURSE:", fill='#1E293B')
    draw.text((70, 410), "- 2D Echocardiography: LVEF 55%, Mild LVH, Grade 1 Diastolic Dysfunction.", fill='#334155')
    draw.text((70, 435), "- Resting ECG: Normal sinus rhythm, non-specific ST-T changes in lateral leads.", fill='#334155')
    
    draw.line([(50, 475), (750, 475)], fill='#CBD5E1', width=1)
    draw.text((50, 495), "DISCHARGE MEDICATIONS:", fill='#2563EB')
    meds = [
        "1. Tab Telmisartan 40mg - 1 Tab Once Daily in morning",
        "2. Tab Metformin 500mg - 1 Tab Twice Daily after meals",
        "3. Tab Atorvastatin 10mg - 1 Tab at Bedtime (HS)",
        "4. Tab Aspirin 75mg - 1 Tab Once Daily after lunch",
        "5. Sorbitrate 5mg - 1 Tab Sublingual SOS for acute chest pain"
    ]
    y = 525
    for m in meds:
        draw.text((70, y), m, fill='#0F172A')
        y += 28
        
    img.save(SAMPLE_DIR / "discharge_summary_sample.png")

if __name__ == "__main__":
    create_prescription_image()
    create_lab_report_image()
    create_discharge_summary_image()
    print("Sample document images created successfully in", SAMPLE_DIR)
