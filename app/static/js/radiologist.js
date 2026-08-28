/**
 * ArogyaMitra Radiologist Portal Controller
 * Source of truth: User Requirement 11 & systemdesign.md Section 8
 */

const RadiologistPortal = {
  presets: [],
  selectedPreset: null,

  async init() {
    await this.loadStats();
    await this.loadQueue();
    await this.loadPresets();
    await this.loadPatientsDropdown();
  },

  async loadStats() {
    try {
      const res = await fetch('/api/radiology/stats');
      const stats = await res.json();

      const elTotal = document.getElementById('stat-rad-total');
      const elPending = document.getElementById('stat-rad-pending');
      const elCompleted = document.getElementById('stat-rad-completed');
      const elAlerts = document.getElementById('stat-rad-alerts');

      if (elTotal) elTotal.innerText = stats.total_studies || 0;
      if (elPending) elPending.innerText = stats.pending_reports || 0;
      if (elCompleted) elCompleted.innerText = stats.completed_today || 0;
      if (elAlerts) elAlerts.innerText = stats.critical_alerts || 0;
    } catch (err) {
      console.error('Failed to load radiology stats:', err);
    }
  },

  async loadQueue() {
    try {
      const res = await fetch('/api/radiology/queue');
      const data = await res.json();
      const container = document.getElementById('radiology-studies-queue');
      if (!container) return;

      const studies = data.queue || [];
      if (studies.length === 0) {
        container.innerHTML = `
          <tr>
            <td colspan="6" class="text-center py-10 text-slate-400 font-medium">
              No imaging studies currently registered.
            </td>
          </tr>
        `;
        return;
      }

      container.innerHTML = studies.map(st => {
        const isAlert = st.alert_flag == 1;
        return `
          <tr class="hover:bg-slate-50/80 transition border-b border-slate-100 text-xs">
            <td class="px-4 py-3.5 whitespace-nowrap font-mono text-slate-500">${st.study_date}</td>
            <td class="px-4 py-3.5">
              <div class="font-bold text-slate-900 text-sm">${st.patient_name || 'Patient'}</div>
              <div class="text-slate-500 text-[11px]">${st.gender || ''}, DOB: ${st.date_of_birth || ''}</div>
            </td>
            <td class="px-4 py-3.5 font-mono text-slate-700">
              <span class="px-2 py-0.5 rounded bg-slate-100 border border-slate-200">${st.modality}</span>
            </td>
            <td class="px-4 py-3.5 font-medium text-slate-800">${st.study_type}</td>
            <td class="px-4 py-3.5">
              ${isAlert 
                ? `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-red-100 text-red-800 border border-red-200 inline-flex items-center gap-1"><i data-lucide="alert-triangle" class="w-3 h-3"></i>CRITICAL ALERT</span>`
                : `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">NORMAL / FINAL</span>`
              }
            </td>
            <td class="px-4 py-3.5 text-right">
              <button onclick="RadiologistPortal.viewStudyDetails('${st.radiology_id}')" 
                      class="btn-secondary py-1.5 px-3 rounded-lg text-xs font-semibold">
                <span>View Report</span>
              </button>
            </td>
          </tr>
        `;
      }).join('');

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to load radiology queue:', err);
    }
  },

  async loadPresets() {
    try {
      const res = await fetch('/api/radiology/presets');
      const data = await res.json();
      this.presets = data.presets || [];
      
      const container = document.getElementById('rad-preset-chips');
      if (!container) return;

      container.innerHTML = this.presets.map((p, idx) => `
        <button type="button" onclick="RadiologistPortal.applyPreset(${idx})" 
                class="text-left p-3 rounded-xl border border-slate-200 bg-white hover:border-[#7CA68D] hover:bg-[#F3EFE3]/30 transition shadow-sm">
          <div class="flex items-center justify-between mb-1">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">${p.modality}</span>
            ${p.alert_flag ? '<span class="text-[10px] font-bold text-red-600 inline-flex items-center gap-1"><i data-lucide="alert-triangle" class="w-3 h-3"></i>Alert</span>' : ''}
          </div>
          <div class="font-bold text-xs text-slate-900 truncate">${p.study_type}</div>
        </button>
      `).join('');
    } catch (err) {
      console.error('Failed to load radiology presets:', err);
    }
  },

  applyPreset(index) {
    const p = this.presets[index];
    if (!p) return;

    const modSelect = document.getElementById('rad-input-modality');
    const typeInput = document.getElementById('rad-input-study-type');
    const indInput = document.getElementById('rad-input-indication');
    const findInput = document.getElementById('rad-input-findings');
    const impInput = document.getElementById('rad-input-impression');
    const recInput = document.getElementById('rad-input-recommendation');
    const alertToggle = document.getElementById('rad-input-alert');

    if (modSelect) modSelect.value = p.modality;
    if (typeInput) typeInput.value = p.study_type;
    if (indInput) indInput.value = p.clinical_indication;
    if (findInput) findInput.value = p.findings;
    if (impInput) impInput.value = p.impression;
    if (recInput) recInput.value = p.recommendation;
    if (alertToggle) alertToggle.checked = p.alert_flag;

    App.showToast(`Applied preset template for ${p.study_type}`);
  },

  async loadPatientsDropdown() {
    try {
      const res = await fetch('/api/patient/list');
      const data = await res.json();
      const select = document.getElementById('rad-patient-select');
      if (!select) return;

      select.innerHTML = (data.patients || []).map(p => `
        <option value="${p.patient_id}">${p.name} (${p.gender}, ${p.date_of_birth}) - ABHA: ${p.abha_id || 'N/A'}</option>
      `).join('');
    } catch (err) {
      console.error('Failed to load patients for radiology:', err);
    }
  },

  async submitRadiologyReport() {
    const patientId = document.getElementById('rad-patient-select')?.value;
    const modality = document.getElementById('rad-input-modality')?.value || 'XRAY';
    const studyType = document.getElementById('rad-input-study-type')?.value.trim();
    const indication = document.getElementById('rad-input-indication')?.value.trim();
    const findings = document.getElementById('rad-input-findings')?.value.trim();
    const impression = document.getElementById('rad-input-impression')?.value.trim();
    const recommendation = document.getElementById('rad-input-recommendation')?.value.trim();
    const isAlert = document.getElementById('rad-input-alert')?.checked || false;
    const studyDate = document.getElementById('rad-input-date')?.value || new Date().toISOString().substring(0, 10);

    if (!patientId || !studyType || !findings || !impression) {
      App.showToast('Please provide Patient, Study Type, Findings, and Impression.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/radiology/upload-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          study_type: studyType,
          modality: modality,
          clinical_indication: indication,
          findings: findings,
          impression: impression,
          recommendation: recommendation,
          alert_flag: isAlert,
          study_date: studyDate
        })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Failed to submit report', 'warning');
        return;
      }

      App.showToast('Radiology report saved and linked to patient timeline!', 'success');
      await this.loadStats();
      await this.loadQueue();
    } catch (err) {
      App.showToast('Error uploading radiology report.', 'warning');
    }
  },

  async viewStudyDetails(radiologyId) {
    try {
      const res = await fetch('/api/radiology/queue');
      const data = await res.json();
      const study = (data.queue || []).find(s => s.radiology_id === radiologyId);
      if (!study) return;

      const modal = document.getElementById('radiology-view-modal');
      const content = document.getElementById('radiology-view-content');
      if (!modal || !content) return;

      content.innerHTML = `
        <div class="space-y-4 text-sm">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <div class="text-xs font-bold text-[#7CA68D] uppercase tracking-wider">${study.modality} Study</div>
              <h3 class="text-lg font-bold text-slate-900">${study.study_type}</h3>
            </div>
            <span class="px-3 py-1 rounded-full text-xs font-bold ${study.alert_flag ? 'bg-red-100 text-red-800' : 'bg-purple-100 text-purple-800'}">
              ${study.alert_flag ? 'CRITICAL ALERT' : 'FINAL REPORT'}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <div><b>Patient:</b> ${study.patient_name}</div>
            <div><b>Study Date:</b> ${study.study_date}</div>
            <div><b>Demographics:</b> ${study.gender}, DOB: ${study.date_of_birth}</div>
            <div><b>ABHA ID:</b> ${study.abha_id || 'Not Linked'}</div>
          </div>

          <div>
            <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Clinical Indication:</div>
            <div class="p-3 bg-slate-50 rounded-xl text-slate-800">${study.clinical_indication || 'Standard evaluation'}</div>
          </div>

          <div>
            <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Detailed Findings:</div>
            <div class="p-3 bg-slate-50 rounded-xl text-slate-800 leading-relaxed font-mono text-xs whitespace-pre-wrap">${study.findings}</div>
          </div>

          <div>
            <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Impression & Opinion:</div>
            <div class="p-3.5 bg-amber-50/80 border border-amber-200/60 rounded-xl text-slate-900 font-bold leading-relaxed">${study.impression}</div>
          </div>

          ${study.recommendation ? `
            <div>
              <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Recommendation:</div>
              <div class="p-3 bg-slate-50 rounded-xl text-slate-700">${study.recommendation}</div>
            </div>
          ` : ''}
        </div>
      `;

      modal.classList.remove('hidden');
      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Error viewing study details:', err);
    }
  },

  closeStudyViewModal() {
    const modal = document.getElementById('radiology-view-modal');
    if (modal) modal.classList.add('hidden');
  }
};

window.RadiologistPortal = RadiologistPortal;
