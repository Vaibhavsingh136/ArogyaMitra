"""
ArogyaMitra Medical Summary PDF Exporter
Generates standardized, branded pre-consultation reports using ReportLab.
Conforms strictly to brandguideline.md (Colors #7CA68D, #C0C3B9, #F3EFE3)
"""
import io
from typing import Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def hex_to_color(hex_str: str):
    hex_str = hex_str.lstrip('#')
    return colors.HexColor(f"#{hex_str}")

# Brand Colors
COLOR_PRIMARY = hex_to_color("7CA68D")    # Arogya Green
COLOR_SECONDARY = hex_to_color("C0C3B9")  # Soft Sage Gray
COLOR_BG_LIGHT = hex_to_color("F3EFE3")   # Calm Background
COLOR_TEXT = hex_to_color("1E293B")       # Dark Charcoal
COLOR_MUTED = hex_to_color("64748B")
COLOR_DRAFT = hex_to_color("D97706")      # Amber
COLOR_VERIFIED = hex_to_color("059669")   # Emerald Green

def generate_summary_pdf(
    patient: Dict[str, Any],
    consultation: Dict[str, Any],
    summary: Dict[str, Any],
    doctor: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Generates a high-quality, clinical pre-consultation intake PDF document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=COLOR_PRIMARY,
        alignment=TA_LEFT
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=COLOR_MUTED,
        alignment=TA_LEFT
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=COLOR_PRIMARY
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=COLOR_TEXT
    )

    badge_style = ParagraphStyle(
        'BadgeStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.white
    )

    story = []

    # 1. Header Banner with Brand Title & Status Badge
    is_verified = summary.get("status") == "VERIFIED"
    status_text = "DOCTOR VERIFIED" if is_verified else "AI-GENERATED DRAFT"
    status_bg = COLOR_VERIFIED if is_verified else COLOR_DRAFT

    header_table_data = [
        [
            Paragraph("<b>ArogyaMitra</b><br/><font size=8 color='#64748B'>Pre-Consultation Clinical Intake Summary</font>", title_style),
            Paragraph(f"<font color='white'><b>&nbsp;{status_text}&nbsp;</b></font>", badge_style)
        ]
    ]

    header_table = Table(header_table_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (1, 0), status_bg),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('TOPPADDING', (1, 0), (1, 0), 6),
        ('BOTTOMPADDING', (1, 0), (1, 0), 6),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (1, 0), (1, 0), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=8))

    # 2. Patient Demographics Box
    demo_data = [
        [
            Paragraph(f"<b>Patient Name:</b> {patient.get('name', 'N/A')}", body_style),
            Paragraph(f"<b>ABHA ID:</b> {patient.get('abha_id', 'Not Linked')}", body_style)
        ],
        [
            Paragraph(f"<b>Age / Gender:</b> {patient.get('date_of_birth', 'N/A')} ({patient.get('gender', 'N/A')})", body_style),
            Paragraph(f"<b>Contact:</b> {patient.get('phone', 'N/A')}", body_style)
        ],
        [
            Paragraph(f"<b>Consultation Token:</b> {consultation.get('token_code', 'AM-100')}", body_style),
            Paragraph(f"<b>Date / Time:</b> {consultation.get('date_time', datetime.now().strftime('%Y-%m-%d %H:%M'))[:16]}", body_style)
        ]
    ]
    demo_table = Table(demo_data, colWidths=[270, 270])
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_SECONDARY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_SECONDARY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(demo_table)
    story.append(Spacer(1, 12))

    # 3. Clinical Sections
    sections = [
        ("1. Chief Complaint", summary.get("chief_complaint", "General medical review.")),
        ("2. History of Present Illness (HPI)", summary.get("history_of_present_illness", "Symptoms detailed as above.")),
        ("3. Past Medical & Surgical History", f"Medical: {summary.get('past_medical_history', 'None reported.')}\nSurgical: {summary.get('past_surgical_history', 'None reported.')}"),
        ("4. Current Medications & Allergies", f"Medications: {', '.join(summary.get('medications', ['None'])) if isinstance(summary.get('medications'), list) else summary.get('medications', 'None')}\nAllergies: {', '.join(summary.get('allergies', ['None'])) if isinstance(summary.get('allergies'), list) else summary.get('allergies', 'NKDA')}"),
        ("5. Family & Personal History", f"Family: {summary.get('family_history', 'Non-contributory.')}\nPersonal/Habits: {summary.get('personal_history', 'Non-smoker.')}"),
        ("6. Review of Systems & Prior Investigations", f"ROS: {summary.get('review_of_systems', 'Unremarkable.')}\nDigitized Records: {summary.get('previous_investigations_summary', 'None scanned.')}")
    ]

    if summary.get("ayush_notes"):
        sections.append(("7. AYUSH Assessment (Dashavidha Pariksha / Agni)", summary.get("ayush_notes")))

    for title, content in sections:
        story.append(Paragraph(title, section_header_style))
        story.append(Spacer(1, 2))
        clean_content = str(content).replace('\n', '<br/>')
        story.append(Paragraph(clean_content, body_style))
        story.append(Spacer(1, 8))

    # 4. Physician Verification Box
    story.append(Spacer(1, 8))
    verify_box_data = [
        [
            Paragraph("<b>Physician Verification & Sign-off</b>", section_header_style),
            Paragraph(f"<b>Status:</b> {status_text}", body_style)
        ],
        [
            Paragraph(f"<b>Attending Doctor:</b> {doctor.get('name', 'OPD Attending Physician') if doctor else 'OPD Attending Physician'}<br/>"
                      f"<b>Department:</b> {doctor.get('department', 'General Medicine') if doctor else 'General Medicine'}<br/>"
                      f"<b>Doctor Notes:</b> {summary.get('doctor_notes', 'Verified for pre-consultation OPD evaluation.')}", body_style),
            Paragraph(f"<b>Verification Timestamp:</b><br/>{summary.get('verified_at', 'Pending Doctor Verification')}<br/><br/>"
                      f"<i>Digital Record prepared via ArogyaMitra Platform</i>", body_style)
        ]
    ]
    verify_table = Table(verify_box_data, colWidths=[320, 220])
    verify_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, COLOR_PRIMARY),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(verify_table))

    # 5. Footer Disclaimer (systemdesign.md & brandguideline.md)
    story.append(Spacer(1, 10))
    disclaimer_text = (
        "<font size=7 color='#64748B'>"
        "<b>CLINICAL NOTICE:</b> ArogyaMitra prepares and organizes patient history before consultation. "
        "It assists the clinical workflow and does NOT autonomously diagnose conditions or prescribe treatments. "
        "The attending physician retains complete authority over diagnosis and patient care."
        "</font>"
    )
    story.append(Paragraph(disclaimer_text, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
