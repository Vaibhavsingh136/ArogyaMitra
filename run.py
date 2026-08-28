"""
ArogyaMitra Application Launcher
Runs Uvicorn ASGI server with live reloading.
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("Starting ArogyaMitra Pre-Consultation Clinical Intake Platform")
    print("Source of truth: systemdesign.md & brandguideline.md")
    print("=" * 70)
    print("Serving on http://localhost:8000")
    print("=" * 70)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
