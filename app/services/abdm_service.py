"""
ArogyaMitra ABDM / ABHA Adapter Service (Mock)
Provides an integration boundary for Ayushman Bharat Digital Mission (ABDM),
ABHA ID verification, Health Record Linking, and FHIR-ready resource exports.
Source of truth: systemdesign.md Section 15
"""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# In-memory mock registry of ABDM health IDs
MOCK_ABHA_REGISTRY = {
    "91-4820-9182-3841@abdm": {
        "name": "Rajesh Kumar",
        "gender": "Male",
        "dob": "1978-05-14",
        "phone": "+91 98765 43210",
        "address": "New Delhi, Delhi",
        "kyc_status": "VERIFIED",
        "linked_hip": "HIP-DELHI-OPD-104"
    },
    "82-1940-5829-1049@abdm": {
        "name": "Sunita Devi",
        "gender": "Female",
        "dob": "1965-11-20",
        "phone": "+91 98111 22334",
        "address": "Varanasi, Uttar Pradesh",
        "kyc_status": "VERIFIED",
        "linked_hip": "HIP-UP-VARANASI-202"
    },
    "74-5029-4829-6192@abdm": {
        "name": "Mohammed Ali",
        "gender": "Male",
        "dob": "1988-03-08",
        "phone": "+91 97234 56789",
        "address": "Hyderabad, Telangana",
        "kyc_status": "VERIFIED",
        "linked_hip": "HIP-TEL-HYD-501"
    }
}

class ABDMAdapter:
    """Mock ABDM Service Adapter representing NDHM/ABDM Gateway."""
    
    @staticmethod
    def verify_abha(abha_id: str) -> Dict[str, Any]:
        """Verifies ABHA ID format or fetches demographic profile."""
        clean_id = abha_id.strip()
        if clean_id in MOCK_ABHA_REGISTRY:
            profile = MOCK_ABHA_REGISTRY[clean_id]
            return {
                "success": True,
                "status": "VERIFIED",
                "message": "ABHA ID successfully authenticated via mock ABDM gateway.",
                "profile": profile,
                "token": f"abdm_token_{uuid.uuid4().hex[:12]}"
            }
        
        # If not pre-seeded, generate a valid mock profile if format looks like ABHA
        if "@abdm" in clean_id or len(clean_id) >= 10:
            mock_profile = {
                "name": "Ayushman Beneficiary",
                "gender": "Other",
                "dob": "1990-01-01",
                "phone": "+91 98000 11111",
                "address": "India",
                "kyc_status": "VERIFIED",
                "linked_hip": f"HIP-GATEWAY-{uuid.uuid4().hex[:6]}"
            }
            return {
                "success": True,
                "status": "VERIFIED",
                "message": "ABHA ID verified via mock ABDM Sandbox.",
                "profile": mock_profile,
                "token": f"abdm_token_{uuid.uuid4().hex[:12]}"
            }
        
        return {
            "success": False,
            "status": "NOT_FOUND",
            "message": "ABHA ID not recognized in ABDM sandbox registry. Format: XX-XXXX-XXXX-XXXX@abdm"
        }

    @staticmethod
    def generate_fhir_bundle(patient: Dict[str, Any], summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds a standard FHIR (Fast Healthcare Interoperability Resources)
        Document Bundle representation for ABDM health information exchange.
        """
        bundle_id = str(uuid.uuid4())
        fhir_bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "lastUpdated": datetime.now().isoformat(),
                "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/ClinicalArtifact"]
            },
            "identifier": {
                "system": "https://arogyamitra.health/records",
                "value": f"DOC-{bundle_id[:8]}"
            },
            "type": "document",
            "timestamp": datetime.now().isoformat(),
            "entry": [
                {
                    "resource": {
                        "resourceType": "Composition",
                        "id": f"comp-{bundle_id[:6]}",
                        "status": "preliminary" if summary.get("status") == "DRAFT" else "final",
                        "type": {
                            "coding": [{"system": "http://loinc.org", "code": "11488-4", "display": "Consultation note"}]
                        },
                        "title": "ArogyaMitra Pre-Consultation Intake Record",
                        "subject": {
                            "reference": f"Patient/{patient.get('patient_id')}",
                            "display": patient.get("name")
                        },
                        "date": datetime.now().isoformat(),
                        "section": [
                            {"title": "Chief Complaint", "text": {"status": "generated", "div": summary.get("chief_complaint", "")}},
                            {"title": "History of Present Illness", "text": {"status": "generated", "div": summary.get("history_of_present_illness", "")}},
                            {"title": "Allergies", "text": {"status": "generated", "div": str(summary.get("allergies", []))}},
                            {"title": "Medications", "text": {"status": "generated", "div": str(summary.get("medications", []))}}
                        ]
                    }
                },
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": patient.get("patient_id"),
                        "identifier": [
                            {"system": "https://healthid.ndhm.gov.in", "value": patient.get("abha_id", "")}
                        ],
                        "name": [{"text": patient.get("name")}],
                        "gender": str(patient.get("gender", "")).lower(),
                        "birthDate": patient.get("date_of_birth")
                    }
                }
            ]
        }
        return fhir_bundle
