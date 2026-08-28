/**
 * ArogyaMitra Core Application State & Role Router
 * Source of truth: systemdesign.md & User Requirements 1-30
 */

const App = {
  currentUser: null,
  currentRole: null,
  currentLanguage: 'en',
  kioskMode: false,
  activePatient: null,
  activeConsultationId: null,
  currentStep: 1,

  languages: [
    { code: 'en', name: 'English', native: 'English', flag: '' },
    { code: 'hi', name: 'Hindi', native: 'हिन्दी', flag: '' },
    { code: 'bn', name: 'Bengali', native: 'বাংলা', flag: '' },
    { code: 'te', name: 'Telugu', native: 'తెలుగు', flag: '' },
    { code: 'ta', name: 'Tamil', native: 'தமிழ்', flag: '' },
    { code: 'mr', name: 'Marathi', native: 'मराठी', flag: '' },
    { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', flag: '' },
    { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', flag: '' },
    { code: 'or', name: 'Odia', native: 'ଓଡ଼ିଆ', flag: '' },
    { code: 'ml', name: 'Malayalam', native: 'മലയാളം', flag: '' },
    { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ', flag: '' }
  ],

  async init() {
    VoiceEngine.init();
    AuthController.init();
    this.renderLanguageGrid();

    // If no active session, show pre-entry Landing Screen
    if (!this.currentUser) {
      this.showLandingScreen();
    }

    if (window.lucide) window.lucide.createIcons();
  },

  showLandingScreen() {
    this.currentRole = null;
    this.hideAllViews();
    const landing = document.getElementById('view-landing-role-select');
    if (landing) landing.classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  },

  selectRole(role) {
    AuthController.selectRole(role);
  },

  enterRoleView(role) {
    this.currentRole = role;
    this.hideAllViews();

    const viewPatient = document.getElementById('view-patient-kiosk');
    const viewDoctor = document.getElementById('view-doctor-dashboard');
    const viewRadiology = document.getElementById('view-radiology-portal');
    const viewLab = document.getElementById('view-lab-portal');
    const viewAdmin = document.getElementById('view-admin-portal');

    if (role === 'PATIENT') {
      if (viewPatient) viewPatient.classList.remove('hidden');
      // If we already have an active patient with saved preferences, use them
      if (this.activePatient && this.activePatient.preferred_language) {
        this.currentLanguage = this.activePatient.preferred_language;
        VoiceEngine.setLanguage(this.currentLanguage);
        // If latest consent exists and is GRANTED, skip consent step
        const latestConsent = this.activePatient.latest_consent || null;
        if (latestConsent && latestConsent.consent_status === 'GRANTED') {
          // proceed to intake directly
          this.goToStep(4);
        } else {
          this.goToStep(3);
        }
      } else {
        this.goToStep(1); // Start from language selection
      }
    } else if (role === 'DOCTOR') {
      if (viewDoctor) viewDoctor.classList.remove('hidden');
      DoctorDashboard.init();
    } else if (role === 'RADIOLOGIST') {
      if (viewRadiology) viewRadiology.classList.remove('hidden');
      RadiologistPortal.init();
    } else if (role === 'LAB') {
      if (viewLab) viewLab.classList.remove('hidden');
      LabPortal.init();
    } else if (role === 'ADMIN') {
      if (viewAdmin) viewAdmin.classList.remove('hidden');
      AdminPortal.init();
    }

    if (window.lucide) window.lucide.createIcons();
  },

  hideAllViews() {
    const views = [
      'view-landing-role-select',
      'view-patient-kiosk',
      'view-doctor-dashboard',
      'view-radiology-portal',
      'view-lab-portal',
      'view-admin-portal'
    ];
    views.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.add('hidden');
    });
  },

  renderLanguageGrid() {
    const grid = document.getElementById('language-selection-grid');
    if (!grid) return;

    grid.innerHTML = this.languages.map(l => `
      <button onclick="App.selectLanguage('${l.code}')" 
              class="lang-card group p-5 rounded-2xl border-2 ${this.currentLanguage === l.code ? 'border-[#7CA68D] bg-[#F3EFE3]/60 shadow-md' : 'border-slate-200 bg-white hover:border-[#7CA68D]/60 hover:shadow-sm'} flex flex-col items-center justify-center gap-2 transition-all">
        <span class="text-3xl">${l.flag}</span>
        <span class="text-xl font-bold text-slate-900 group-hover:text-[#7CA68D] transition">${l.native}</span>
        <span class="text-xs font-semibold text-slate-500">${l.name}</span>
      </button>
    `).join('');
  },

  selectLanguage(langCode) {
    this.currentLanguage = langCode;
    VoiceEngine.setLanguage(langCode);
    this.renderLanguageGrid();
    
    const selectedLangObj = this.languages.find(l => l.code === langCode);
    const audioMsg = langCode === 'hi' 
      ? 'आरोग्यमित्र में आपका स्वागत है। चलिए आपके डॉक्टर के लिए आपकी स्वास्थ्य जानकारी तैयार करते हैं।'
      : `Welcome to ArogyaMitra. Let's prepare your health history for your doctor.`;
    
    VoiceEngine.speak(audioMsg, langCode);
    this.showToast(`Language set to ${selectedLangObj?.name || 'English'}`);
    
    // Advance to Consent Step (Skipping re-registration if already logged in)
    this.goToStep(3);
  },

  toggleKioskMode() {
    this.kioskMode = !this.kioskMode;
    document.body.classList.toggle('kiosk-mode', this.kioskMode);
    
    const kioskBtn = document.getElementById('kiosk-toggle-btn');
    if (kioskBtn) {
      kioskBtn.classList.toggle('bg-[#7CA68D]', this.kioskMode);
      kioskBtn.classList.toggle('text-white', this.kioskMode);
    }
    this.showToast(this.kioskMode ? 'Kiosk Touch Mode Enabled (High-Contrast, Large Targets)' : 'Standard Responsive Web Mode Enabled');
  },

  goToStep(stepNumber) {
    this.currentStep = stepNumber;
    
    // Stepper Pills UI
    document.querySelectorAll('.kiosk-step-pill').forEach((pill, idx) => {
      const stepIdx = idx + 1;
      const numBadge = pill.querySelector('.step-num');
      if (stepIdx < stepNumber) {
        pill.classList.remove('opacity-50', 'text-slate-400');
        pill.classList.add('text-[#7CA68D]', 'font-bold');
        if (numBadge) numBadge.innerHTML = '✓';
      } else if (stepIdx === stepNumber) {
        pill.classList.remove('opacity-50', 'text-slate-400');
        pill.classList.add('text-slate-900', 'font-extrabold', 'border-b-2', 'border-[#7CA68D]');
        if (numBadge) numBadge.innerHTML = '●';
      } else {
        pill.classList.add('opacity-50', 'text-slate-400');
        pill.classList.remove('text-[#7CA68D]', 'text-slate-900', 'border-b-2');
        if (numBadge) numBadge.innerHTML = '○';
      }
    });

    for (let i = 1; i <= 6; i++) {
      const el = document.getElementById(`kiosk-step-${i}`);
      if (el) el.classList.add('hidden');
    }

    const activeSection = document.getElementById(`kiosk-step-${stepNumber}`);
    if (activeSection) {
      activeSection.classList.remove('hidden');
      activeSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (stepNumber === 4) {
      IntakeController.init(this.activeConsultationId || 'con_1', this.activePatient?.patient_id || 'pat_1', this.currentLanguage);
    } else if (stepNumber === 5) {
      OCRViewer.init(this.activePatient?.patient_id || 'pat_1', this.activeConsultationId || 'con_1');
    } else if (stepNumber === 6) {
      this.loadFinalPatientSummary();
    }

    if (window.lucide) window.lucide.createIcons();
  },

  async verifyABHA() {
    const input = document.getElementById('reg-abha-input');
    const abhaId = input ? input.value.trim() : '';
    if (!abhaId) {
      this.showToast('Please enter an ABHA ID (e.g. 91-4820-9182-3841@abdm)', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/abdm/verify-abha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ abha_id: abhaId })
      });
      const data = await res.json();

      if (data.success && data.profile) {
        document.getElementById('reg-name-input').value = data.profile.name || '';
        document.getElementById('reg-dob-input').value = data.profile.dob || '';
        document.getElementById('reg-phone-input').value = data.profile.phone || '';
        document.getElementById('reg-gender-select').value = data.profile.gender || 'Male';
        this.showToast('ABHA Identity verified! Demographic details autofilled.', 'success');
      } else {
        this.showToast(data.message || 'ABHA not found in sandbox.', 'warning');
      }
    } catch (err) {
      console.error('ABHA verification failed:', err);
    }
  },

  async submitRegistration() {
    const name = document.getElementById('reg-name-input')?.value.trim();
    const dob = document.getElementById('reg-dob-input')?.value || '1985-01-01';
    const gender = document.getElementById('reg-gender-select')?.value || 'Male';
    const phone = document.getElementById('reg-phone-input')?.value.trim();
    const abhaId = document.getElementById('reg-abha-input')?.value.trim();

    if (!name || !phone) {
      this.showToast('Please provide Patient Name and Contact Phone.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/patient/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          date_of_birth: dob,
          gender: gender,
          phone: phone,
          abha_id: abhaId,
          preferred_language: this.currentLanguage
        })
      });
      const data = await res.json();
      if (data.success) {
        this.activePatient = data.patient;
        this.activeConsultationId = data.consultation_id;
        this.showToast(`Patient profile identified. Token: ${data.token_code || 'AM-101'}`);
        this.goToStep(3); // Advance to Consent step
      }
    } catch (err) {
      console.error('Registration failed:', err);
    }
  },

  async grantConsent(audioGuided = false) {
    const patientId = this.activePatient?.patient_id || 'pat_1';
    const consultationId = this.activeConsultationId || 'con_1';

    try {
      await fetch('/api/patient/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          consultation_id: consultationId,
          consent_type: 'PRE_CONSULTATION_AI_INTAKE',
          consent_status: 'GRANTED',
          audio_guided: audioGuided
        })
      });
      this.showToast('Consent recorded securely. Starting clinical interview.');
      this.goToStep(4);
    } catch (err) {
      console.error('Failed to record consent:', err);
      this.goToStep(4);
    }
  },

  // Skippable document upload handler
  skipDocumentUpload() {
    this.showToast('Skipped document upload. Generating summary directly...');
    this.goToStep(6);
  },

  async loadFinalPatientSummary() {
    const consultationId = this.activeConsultationId || 'con_1';
    const container = document.getElementById('patient-summary-container');
    if (!container) return;

    const isHindi = this.currentLanguage === 'hi';
    const loadingText = isHindi 
      ? 'आपकी स्वास्थ्य जानकारी तैयार की जा रही है...'
      : 'Your health history is being prepared for your doctor...';

    container.innerHTML = `
      <div class="text-center py-12">
        <div class="w-12 h-12 border-4 border-[#7CA68D] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-600 font-semibold">${loadingText}</p>
      </div>
    `;

    try {
      const res = await fetch(`/api/intake/generate-summary/${consultationId}?language=${this.currentLanguage}`, { method: 'POST' });
      const data = await res.json();
      const s = data.structured_data || {};

      // Localized copy
      const t = {
        badge: isHindi ? 'एआई-जनरेटेड ड्राफ्ट (डॉक्टर सत्यापन प्रतीक्षारत)' : 'AI-Generated Draft (Pending Doctor Verification)',
        title: isHindi ? 'आपकी स्वास्थ्य जानकारी तैयार है' : 'Your Health Story is Ready',
        subtitle: isHindi ? 'आपके डॉक्टर परामर्श से पहले इस सारांश की समीक्षा करेंगे।' : 'Your doctor will review and verify this summary before your consultation.',
        downloadPdf: isHindi ? 'पीडीएफ प्रति डाउनलोड करें' : 'Download PDF Copy',
        cc: isHindi ? 'मुख्य समस्या' : 'Main Complaint',
        hpi: isHindi ? 'विस्तृत विवरण' : 'History Details',
        pmh: isHindi ? 'पुरानी बीमारियाँ व इतिहास' : 'Known Conditions & Past History',
        medsAll: isHindi ? 'वर्तमान दवाएं व एलर्जी' : 'Current Medicines & Allergies',
        whatNext: isHindi ? 'आगे क्या करें?' : 'What happens next?',
        whatNextDesc: isHindi 
          ? 'कृपया प्रतीक्षा कक्ष में बैठें। जब आपका टोकन बुलाया जाएगा, डॉक्टर के पास आपकी पूरी जानकारी तैयार होगी।' 
          : 'Please proceed to the waiting area. When your token is called, your doctor will have all your organized information open on their dashboard.',
        restart: isHindi ? 'नया मरीज़ सत्र शुरू करें' : 'Start New Patient Session'
      };

      container.innerHTML = `
        <div class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6 animate-fadeIn">
          <!-- Summary Header -->
          <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div>
              <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold mb-2">
                <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                <span>${t.badge}</span>
              </div>
              <h3 class="text-2xl font-bold text-slate-900">${t.title}</h3>
              <p class="text-slate-500 text-sm">${t.subtitle}</p>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="window.open('/api/export/summary-pdf/${consultationId}', '_blank')" 
                      class="btn-primary py-2.5 px-4 text-sm font-semibold rounded-xl flex items-center gap-2 shadow-sm">
                <i data-lucide="download" class="w-4 h-4"></i>
                <span>${t.downloadPdf}</span>
              </button>
            </div>
          </div>

          <!-- Summary Content Cards -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span class="text-xs font-bold text-[#7CA68D] uppercase tracking-wider">${t.cc}</span>
              <div class="font-bold text-slate-900 mt-1">${s.chief_complaint || 'General medical review'}</div>
            </div>

            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span class="text-xs font-bold text-[#7CA68D] uppercase tracking-wider">${t.hpi}</span>
              <div class="text-slate-800 mt-1 leading-relaxed">${s.history_of_present_illness || 'Detailed in record.'}</div>
            </div>

            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">${t.pmh}</span>
              <div class="text-slate-800 mt-1">${s.past_medical_history || 'None reported'}</div>
            </div>

            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span class="text-xs font-bold text-red-600 uppercase tracking-wider">${t.medsAll}</span>
              <div class="text-slate-800 mt-1">
                <div><b>Meds:</b> ${Array.isArray(s.medications) ? s.medications.join(', ') : s.medications}</div>
                <div><b>Allergies:</b> <span class="text-red-700 font-semibold">${Array.isArray(s.allergies) ? s.allergies.join(', ') : s.allergies}</span></div>
              </div>
            </div>
          </div>

          <!-- Informational Notice -->
          <div class="p-4 rounded-xl bg-[#F3EFE3] border border-[#C0C3B9] text-xs text-slate-700 flex items-start gap-3">
            <i data-lucide="info" class="w-5 h-5 text-[#7CA68D] flex-shrink-0 mt-0.5"></i>
            <div>
              <b>${t.whatNext}</b> ${t.whatNextDesc}
            </div>
          </div>

          <!-- Finished Button -->
          <div class="text-center pt-2">
            <button onclick="App.restartIntakeFlow()" class="btn-secondary px-6 py-3 rounded-xl text-sm font-semibold">
              <i data-lucide="refresh-cw" class="w-4 h-4"></i>
              <span>${t.restart}</span>
            </button>
          </div>
        </div>
      `;

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to generate summary:', err);
    }
  },

  restartIntakeFlow() {
    this.goToStep(1);
  },

  showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `p-4 rounded-xl shadow-lg text-sm font-semibold flex items-center gap-3 animate-slideIn ${type === 'warning' ? 'bg-amber-600 text-white' : 'bg-slate-900 text-white'}`;
    toast.innerHTML = `
      <i data-lucide="${type === 'warning' ? 'alert-circle' : 'check-circle-2'}" class="w-5 h-5 text-[#7CA68D]"></i>
      <span>${message}</span>
    `;
    container.appendChild(toast);
    if (window.lucide) window.lucide.createIcons();

    setTimeout(() => {
      toast.classList.add('opacity-0', 'transition-all');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
};

window.App = App;
document.addEventListener('DOMContentLoaded', () => App.init());
