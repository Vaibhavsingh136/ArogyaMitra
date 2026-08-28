/**
 * ArogyaMitra Laboratory Technician Workflow Controller
 * Source of truth: systemdesign.md Section 8 & 12
 */

const LabPortal = {
  patients: [],
  testRows: [],

  async init() {
    await this.loadPatients();
    await this.loadRecentReports();
    this.addDefaultTestRow();
  },

  async loadPatients() {
    try {
      const res = await fetch('/api/patient/list');
      const data = await res.json();
      this.patients = data.patients || [];
      const select = document.getElementById('lab-patient-select');
      if (!select) return;

      select.innerHTML = `
        <option value="">-- Choose Patient for Lab Entry --</option>
        ${this.patients.map(p => `
          <option value="${p.patient_id}">${p.name} (ABHA: ${p.abha_id || 'Unlinked'}) - DOB: ${p.date_of_birth}</option>
        `).join('')}
      `;
    } catch (err) {
      console.error('Failed to load patients for lab:', err);
    }
  },

  async loadRecentReports() {
    try {
      const res = await fetch('/api/lab/reports');
      const data = await res.json();
      const container = document.getElementById('recent-lab-reports-list');
      if (!container) return;

      const reports = data.reports || [];
      container.innerHTML = reports.map(r => `
        <div class="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-900 text-sm">${r.patient_name}</span>
            <span class="text-xs text-slate-500">${r.test_date}</span>
          </div>
          <div class="text-xs text-slate-700 font-medium">${r.test_type}</div>
          <div class="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
            <span class="text-slate-500">${r.results ? r.results.length : 0} Parameters</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-bold ${r.doctor_alert ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}">
              ${r.doctor_alert ? 'Alert Flagged' : 'Normal'}
            </span>
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.error('Failed to load recent reports:', err);
    }
  },

  addDefaultTestRow() {
    this.addTestRow('Fasting Blood Glucose', '110', 'mg/dL', '70 - 100', 'HIGH');
  },

  addTestRow(name = '', val = '', unit = 'mg/dL', ref = '', flag = 'NORMAL') {
    const container = document.getElementById('lab-test-rows-container');
    if (!container) return;

    const rowId = `test_row_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;
    const rowHtml = `
      <div id="${rowId}" class="grid grid-cols-12 gap-2 p-2 bg-slate-50 rounded-lg border border-slate-200 items-center">
        <div class="col-span-4">
          <input type="text" class="row-name w-full px-2.5 py-1.5 rounded border border-slate-200 text-xs bg-white" placeholder="Test Name (e.g. HbA1c)" value="${name}" />
        </div>
        <div class="col-span-2">
          <input type="text" class="row-val w-full px-2.5 py-1.5 rounded border border-slate-200 text-xs bg-white font-bold" placeholder="Result Value" value="${val}" />
        </div>
        <div class="col-span-2">
          <input type="text" class="row-unit w-full px-2.5 py-1.5 rounded border border-slate-200 text-xs bg-white" placeholder="Unit (mg/dL)" value="${unit}" />
        </div>
        <div class="col-span-2">
          <input type="text" class="row-ref w-full px-2.5 py-1.5 rounded border border-slate-200 text-xs bg-white" placeholder="Reference" value="${ref}" />
        </div>
        <div class="col-span-1">
          <select class="row-flag w-full px-1 py-1.5 rounded border border-slate-200 text-xs bg-white font-semibold">
            <option value="NORMAL" ${flag === 'NORMAL' ? 'selected' : ''}>Normal</option>
            <option value="HIGH" ${flag === 'HIGH' ? 'selected' : ''}>High</option>
            <option value="LOW" ${flag === 'LOW' ? 'selected' : ''}>Low</option>
            <option value="CRITICAL" ${flag === 'CRITICAL' ? 'selected' : ''}>Critical</option>
          </select>
        </div>
        <div class="col-span-1 text-center">
          <button type="button" onclick="document.getElementById('${rowId}').remove()" class="p-1 text-red-500 hover:bg-red-50 rounded">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      </div>
    `;
    container.insertAdjacentHTML('beforeend', rowHtml);
    if (window.lucide) window.lucide.createIcons();
  },

  async submitReport() {
    const patientSelect = document.getElementById('lab-patient-select');
    const patientId = patientSelect ? patientSelect.value : '';
    const testType = document.getElementById('lab-test-type')?.value || 'Biochemistry Panel';
    const testDate = document.getElementById('lab-test-date')?.value || new Date().toISOString().substring(0, 10);
    const notes = document.getElementById('lab-notes')?.value || '';

    if (!patientId) {
      App.showToast('Please select a patient first.', 'warning');
      return;
    }

    const rowElements = document.querySelectorAll('#lab-test-rows-container > div');
    const results = [];
    rowElements.forEach(row => {
      const name = row.querySelector('.row-name')?.value.trim();
      const val = row.querySelector('.row-val')?.value.trim();
      const unit = row.querySelector('.row-unit')?.value.trim();
      const ref = row.querySelector('.row-ref')?.value.trim();
      const flag = row.querySelector('.row-flag')?.value || 'NORMAL';
      if (name && val) {
        results.push({
          test_name: name,
          value: val,
          unit: unit,
          reference_range: ref,
          flag: flag
        });
      }
    });

    if (results.length === 0) {
      App.showToast('Please add at least one test parameter result.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/lab/add-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          test_date: testDate,
          test_type: testType,
          notes: notes,
          results: results
        })
      });
      const data = await res.json();
      if (data.success) {
        App.showToast('Lab report successfully added to patient timeline!');
        this.loadRecentReports();
        // Clear rows
        document.getElementById('lab-test-rows-container').innerHTML = '';
        this.addDefaultTestRow();
      }
    } catch (err) {
      console.error('Failed to save lab report:', err);
    }
  }
};

window.LabPortal = LabPortal;
