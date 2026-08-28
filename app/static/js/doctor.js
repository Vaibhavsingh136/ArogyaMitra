/**
 * ArogyaMitra Doctor Dashboard & Verification Controller
 * Source of truth: systemdesign.md Section 8, 9, 11 & brandguideline.md Section 12
 */

const DoctorDashboard = {
  currentDoctorId: 'doc_1',
  activeConsultationId: null,
  activeDossier: null,
  queueFilter: 'ALL',

  async init() {
    await this.loadStats();
    await this.loadQueue();
  },

  async loadStats() {
    try {
      const res = await fetch(`/api/doctor/dashboard-stats?doctor_id=${this.currentDoctorId}`);
      const stats = await res.json();
      
      const elTotal = document.getElementById('stat-total-patients');
      const elPending = document.getElementById('stat-pending-verify');
      const elVerified = document.getElementById('stat-verified-today');
      const elLabs = document.getElementById('stat-lab-alerts');

      if (elTotal) elTotal.innerText = stats.total_patients || 0;
      if (elPending) elPending.innerText = stats.pending_verification || 0;
      if (elVerified) elVerified.innerText = stats.verified_today || 0;
      if (elLabs) elLabs.innerText = stats.abnormal_lab_alerts || 0;
    } catch (err) {
      console.error('Failed to load doctor dashboard stats:', err);
    }
  },

  async loadQueue() {
    try {
      const res = await fetch('/api/doctor/queue');
      const data = await res.json();
      const queueContainer = document.getElementById('doctor-patient-queue');
      if (!queueContainer) return;

      const queue = data.queue || [];
      const filtered = queue.filter(item => {
        if (this.queueFilter === 'PENDING') return item.status === 'SUBMITTED' || item.status === 'DOCTOR_REVIEWING';
        if (this.queueFilter === 'VERIFIED') return item.status === 'VERIFIED';
        return true;
      });

      if (filtered.length === 0) {
        queueContainer.innerHTML = `
          <tr>
            <td colspan="6" class="text-center py-10 text-slate-400 font-medium">
              No patients found matching the selected filter.
            </td>
          </tr>
        `;
        return;
      }

      queueContainer.innerHTML = filtered.map(p => {
        let badgeClass = 'badge-draft';
        let badgeText = 'AI-Generated Draft';
        if (p.status === 'VERIFIED') {
          badgeClass = 'badge-verified';
          badgeText = 'Doctor Verified';
        } else if (p.status === 'DOCTOR_REVIEWING') {
          badgeClass = 'bg-blue-50 text-blue-800 border border-blue-200';
          badgeText = 'In Review';
        }

        return `
          <tr class="hover:bg-slate-50/80 transition border-b border-slate-100">
            <td class="px-5 py-4 whitespace-nowrap">
              <span class="font-bold text-slate-900">#${p.queue_number || '101'}</span>
              <span class="text-xs text-slate-500 block">${p.token_code || ''}</span>
            </td>
            <td class="px-5 py-4">
              <div class="font-bold text-slate-900 text-sm">${p.patient_name}</div>
              <div class="text-xs text-slate-500">${p.gender}, DOB: ${p.date_of_birth} • ${p.phone}</div>
            </td>
            <td class="px-5 py-4">
              <span class="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                <i data-lucide="shield-check" class="w-3 h-3 text-[#7CA68D]"></i>
                ${p.abha_id || 'Not Linked'}
              </span>
            </td>
            <td class="px-5 py-4">
              <div class="text-xs text-slate-700 font-medium max-w-xs truncate">${p.chief_complaint_summary || 'Intake recorded'}</div>
            </td>
            <td class="px-5 py-4 whitespace-nowrap">
              <span class="px-2.5 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1 ${badgeClass}">
                ${badgeText}
              </span>
            </td>
            <td class="px-5 py-4 whitespace-nowrap text-right">
              <button onclick="DoctorDashboard.openPatientDossier('${p.consultation_id}')" 
                      class="btn-primary py-2 px-4 text-xs font-semibold rounded-lg shadow-sm">
                <span>Open Dossier</span>
                <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to load queue:', err);
    }
  },

  setQueueFilter(filter) {
    this.queueFilter = filter;
    document.querySelectorAll('.queue-filter-btn').forEach(b => {
      if (b.dataset.filter === filter) {
        b.classList.add('bg-[#7CA68D]', 'text-white');
        b.classList.remove('bg-white', 'text-slate-600');
      } else {
        b.classList.remove('bg-[#7CA68D]', 'text-white');
        b.classList.add('bg-white', 'text-slate-600');
      }
    });
    this.loadQueue();
  },

  async openPatientDossier(consultationId) {
    this.activeConsultationId = consultationId;
    try {
      const res = await fetch(`/api/doctor/patient-dossier/${consultationId}?lang=${App.currentLanguage}`);
      const dossier = await res.json();
      this.activeDossier = dossier;

      const modal = document.getElementById('doctor-dossier-modal');
      if (modal) modal.classList.remove('hidden');

      this.renderDossierHeader(dossier);
      this.renderDossierSummaryTab(dossier);
      this.renderDossierHistoryTab(dossier);
      this.renderDossierTimelineTab(dossier);
      this.renderDossierDocsTab(dossier);
      this.renderDossierLabsTab(dossier);
      this.renderDossierRadiologyTab(dossier);

      this.switchDossierTab('summary');
    } catch (err) {
      console.error('Error fetching dossier:', err);
    }
  },

  renderDossierHeader(dossier) {
    const c = dossier.consultation;
    const s = dossier.ai_summary || {};
    const isVerified = s.status === 'VERIFIED';

    const header = document.getElementById('dossier-header-info');
    if (!header) return;

    header.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-3">
            <h2 class="text-2xl font-bold text-slate-900">${c.patient_name}</h2>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${isVerified ? 'badge-verified' : 'badge-draft'}">
              ${isVerified ? 'Doctor Verified' : 'AI-Generated Draft'}
            </span>
          </div>
          <div class="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-3">
            <span><b>Age/Gender:</b> ${c.date_of_birth} (${c.gender})</span>
            <span>•</span>
            <span><b>ABHA ID:</b> <code class="bg-slate-100 px-1 py-0.5 rounded text-slate-700">${c.abha_id || 'Unlinked'}</code></span>
            <span>•</span>
            <span><b>Blood Group:</b> ${c.blood_group || 'Unknown'}</span>
            <span>•</span>
            <span><b>Token:</b> ${c.token_code}</span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button onclick="DoctorDashboard.downloadSummaryPDF()" class="btn-secondary py-2 px-3 text-xs rounded-lg flex items-center gap-1.5">
            <i data-lucide="download" class="w-4 h-4 text-slate-600"></i>
            <span>Export Summary PDF</span>
          </button>
          <button onclick="DoctorDashboard.closeDossier()" class="p-2 text-slate-400 hover:text-slate-600 rounded-lg">
            <i data-lucide="x" class="w-6 h-6"></i>
          </button>
        </div>
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();
  },

  renderDossierSummaryTab(dossier) {
    const s = dossier.ai_summary || {};
    const isVerified = s.status === 'VERIFIED';
    const container = document.getElementById('dossier-tab-summary');
    if (!container) return;

    container.innerHTML = `
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main AI Narrative & Editing Panel -->
        <div class="lg:col-span-2 space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold uppercase tracking-wider text-[#7CA68D]">Clinical Narrative & Synthesis</span>
              <span class="px-2 py-0.5 rounded text-[11px] font-bold ${isVerified ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
                ${isVerified ? 'Doctor Verified' : 'AI-Generated Draft (Physician Review Required)'}
              </span>
            </div>
          </div>

          <textarea id="doctor-summary-text" rows="14" 
                    class="w-full p-4 rounded-xl border border-slate-300 font-mono text-xs leading-relaxed text-slate-800 bg-slate-50/50 focus:bg-white focus:border-[#7CA68D] focus:ring-2 focus:ring-[#7CA68D]/20 outline-none transition">${s.summary_text || 'No summary generated yet.'}</textarea>

          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Physician Clinical Notes / OPD Remarks:</label>
            <input type="text" id="doctor-notes-input" value="${s.doctor_notes || ''}" 
                   placeholder="Add your physician review notes or follow-up instructions..." 
                   class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:border-[#7CA68D] outline-none" />
          </div>

          <div class="flex items-center justify-between pt-2">
            <button onclick="DoctorDashboard.saveSummaryEdits()" class="btn-secondary py-2.5 px-5 text-sm font-semibold rounded-xl">
              <i data-lucide="save" class="w-4 h-4"></i>
              <span>Save Edits Only</span>
            </button>

            <button onclick="DoctorDashboard.verifySummary()" 
                    class="btn-primary py-2.5 px-6 text-sm font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 shadow-sm">
              <i data-lucide="check-circle" class="w-4 h-4"></i>
              <span>Accept & Verify Summary</span>
            </button>
          </div>
        </div>

        <!-- Right Quick Insights Sidebar -->
        <div class="space-y-4">
          <div class="p-4 rounded-xl bg-[#F3EFE3]/50 border border-[#C0C3B9]/50">
            <h4 class="font-bold text-slate-900 text-xs uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <i data-lucide="shield-alert" class="w-4 h-4 text-amber-600"></i>
              <span>Safety & AI Disclaimer</span>
            </h4>
            <p class="text-xs text-slate-600 leading-relaxed">
              This summary is prepared to streamline pre-consultation workflow. ArogyaMitra does not replace clinical examination or make autonomous medical decisions.
            </p>
          </div>

          <div class="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
            <div class="text-xs font-bold text-slate-700 uppercase tracking-wider">Summary Metadata</div>
            <div class="text-xs space-y-2 text-slate-600">
              <div><b>Generated At:</b> ${s.generated_at ? s.generated_at.substring(0, 16).replace('T', ' ') : 'N/A'}</div>
              <div><b>Current Status:</b> <span class="font-bold text-slate-900">${s.status || 'DRAFT'}</span></div>
              <div><b>Verified By:</b> ${s.verified_by || 'Pending Verification'}</div>
              <div><b>Verified At:</b> ${s.verified_at ? s.verified_at.substring(0, 16).replace('T', ' ') : 'Not yet'}</div>
            </div>
          </div>
        </div>
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();
  },

  renderDossierHistoryTab(dossier) {
    const h = dossier.medical_history || {};
    const resp = dossier.responses || [];
    const container = document.getElementById('dossier-tab-history');
    if (!container) return;

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Structured Clinical History Sections -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs font-bold text-[#7CA68D] uppercase tracking-wider">Chief Complaint</span>
            <div class="font-semibold text-slate-900 text-sm mt-1">${h.chief_complaint || 'General evaluation'}</div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs font-bold text-[#7CA68D] uppercase tracking-wider">History of Present Illness (HPI)</span>
            <div class="text-slate-800 text-sm mt-1 leading-relaxed">${h.hpi || 'Detailed above.'}</div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Past Medical & Surgical History</span>
            <div class="text-slate-800 text-xs mt-1 space-y-1">
              <div><b>Medical:</b> ${h.past_medical_history || 'None reported'}</div>
              <div><b>Surgical:</b> ${h.past_surgical_history || 'None reported'}</div>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs font-bold text-red-600 uppercase tracking-wider">Current Medicines & Allergies</span>
            <div class="text-slate-800 text-xs mt-1 space-y-1">
              <div><b>Medicines:</b> ${h.drug_history || 'None reported'}</div>
              <div><b class="text-red-700">Allergies:</b> <span class="font-semibold text-red-700">${h.allergies || 'NKDA'}</span></div>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Family & Personal/Lifestyle History</span>
            <div class="text-slate-800 text-xs mt-1 space-y-1">
              <div><b>Family:</b> ${h.family_history || 'Non-contributory'}</div>
              <div><b>Personal:</b> ${h.personal_history || 'Standard routine'}</div>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Review of Systems & AYUSH Pariksha</span>
            <div class="text-slate-800 text-xs mt-1 space-y-1">
              <div><b>ROS:</b> ${h.review_of_systems || 'Unremarkable'}</div>
              ${h.ayush_pariksha ? `<div><b>AYUSH Assessment:</b> <code class="text-[11px] bg-white px-1 rounded">${h.ayush_pariksha}</code></div>` : ''}
            </div>
          </div>
        </div>

        <!-- Conversational Dialogue Transcript -->
        <div class="mt-6">
          <h4 class="font-bold text-slate-900 text-sm mb-3">Original Conversational Dialogue Transcript (Source Traceability)</h4>
          <div class="space-y-2 max-h-60 overflow-y-auto pr-1">
            ${resp.map(r => `
              <div class="p-3 bg-white rounded-lg border border-slate-200 text-xs flex items-start justify-between">
                <div>
                  <span class="font-bold text-slate-700">${r.question_text || r.category}</span>
                  <div class="text-slate-900 font-medium mt-0.5">"${r.original_response}"</div>
                  ${r.translated_response && r.translated_response !== r.original_response ? `
                    <div class="text-slate-500 text-[11px] italic mt-0.5">Normalized: ${r.translated_response}</div>
                  ` : ''}
                </div>
                <span class="px-2 py-0.5 bg-slate-100 rounded text-[10px] font-bold text-slate-600">${r.input_method}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  },

  renderDossierTimelineTab(dossier) {
    const timeline = dossier.timeline || [];
    const container = document.getElementById('dossier-tab-timeline');
    if (!container) return;

    if (timeline.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-slate-400 text-sm">No historical events recorded on timeline.</div>`;
      return;
    }

    container.innerHTML = `
      <div class="relative pl-6 border-l-2 border-[#7CA68D]/40 space-y-6">
        ${timeline.map(item => `
          <div class="relative group">
            <div class="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-[#7CA68D] border-4 border-white shadow-sm"></div>
            <div class="p-4 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-[#7CA68D] transition">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-bold text-slate-500">${item.date}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${item.badge_color === 'red' ? 'bg-red-100 text-red-700' : (item.badge_color === 'emerald' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700')}">
                  ${item.badge}
                </span>
              </div>
              <h4 class="font-bold text-slate-900 text-sm">${item.title}</h4>
              <p class="text-xs text-slate-600 mt-1">${item.details}</p>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  },

  renderDossierDocsTab(dossier) {
    const docs = dossier.documents || [];
    const container = document.getElementById('dossier-tab-docs');
    if (!container) return;

    if (docs.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-slate-400 text-sm">No medical records uploaded for this patient.</div>`;
      return;
    }

    container.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        ${docs.map(d => `
          <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3">
            <div class="flex items-center justify-between">
              <span class="px-2 py-0.5 bg-slate-100 rounded text-xs font-bold text-slate-700">${d.document_type}</span>
              <span class="text-xs text-slate-500">${d.document_date || d.upload_date.substring(0,10)}</span>
            </div>
            <div class="font-bold text-slate-900 text-sm">${d.file_name}</div>
            <div class="p-2.5 rounded bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700 max-h-32 overflow-y-auto whitespace-pre-wrap">${d.extracted_text || 'OCR in progress'}</div>
            <div class="text-xs font-semibold text-emerald-700 flex items-center gap-1">
              <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
              <span>Confidence: ${(d.confidence_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();
  },

  renderDossierLabsTab(dossier) {
    const labs = dossier.lab_reports || [];
    const container = document.getElementById('dossier-tab-labs');
    if (!container) return;

    if (labs.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-slate-400 text-sm">No lab reports associated with this record.</div>`;
      return;
    }

    container.innerHTML = labs.map(lr => `
      <div class="p-5 rounded-xl border border-slate-200 bg-white shadow-sm mb-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
          <div>
            <h4 class="font-bold text-slate-900 text-sm">${lr.test_type}</h4>
            <div class="text-xs text-slate-500">Date: ${lr.test_date}</div>
          </div>
          ${lr.doctor_alert ? `
            <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 flex items-center gap-1">
              <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>
              <span>Abnormal Flag Detected</span>
            </span>
          ` : '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Normal Range</span>'}
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-600 font-semibold">
              <tr>
                <th class="p-2">Test Parameter</th>
                <th class="p-2">Result</th>
                <th class="p-2">Unit</th>
                <th class="p-2">Reference Range</th>
                <th class="p-2">Flag</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${lr.results.map(r => `
                <tr class="${r.flag === 'HIGH' || r.flag === 'LOW' || r.flag === 'CRITICAL' ? 'bg-red-50/60 font-semibold' : ''}">
                  <td class="p-2 text-slate-900">${r.test_name}</td>
                  <td class="p-2 ${r.flag !== 'NORMAL' ? 'text-red-700' : 'text-slate-900'}">${r.value}</td>
                  <td class="p-2 text-slate-500">${r.unit}</td>
                  <td class="p-2 text-slate-500">${r.reference_range}</td>
                  <td class="p-2">
                    <span class="px-1.5 py-0.5 rounded text-[10px] ${r.flag === 'NORMAL' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-200 text-red-800'}">
                      ${r.flag}
                    </span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `).join('');

    if (window.lucide) window.lucide.createIcons();
  },

  renderDossierRadiologyTab(dossier) {
    const rads = dossier.radiology_reports || [];
    const container = document.getElementById('dossier-tab-radiology');
    if (!container) return;

    if (rads.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-slate-400 text-sm">No radiology or imaging studies associated with this patient.</div>`;
      return;
    }

    container.innerHTML = rads.map(rr => `
      <div class="p-5 rounded-xl border border-slate-200 bg-white shadow-sm mb-4 space-y-3">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <div class="text-xs font-bold text-purple-700 uppercase tracking-wider">${rr.modality} Study</div>
            <h4 class="font-bold text-slate-900 text-sm">${rr.study_type}</h4>
            <div class="text-xs text-slate-500">Date: ${rr.study_date} • Indication: ${rr.clinical_indication || 'Clinical evaluation'}</div>
          </div>
          ${rr.alert_flag ? `
            <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 flex items-center gap-1">
              <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>
              <span>Critical Alert Finding</span>
            </span>
          ` : '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">Final Report</span>'}
        </div>

        <div>
          <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Radiologist Findings:</div>
          <div class="p-3 bg-slate-50 rounded-xl text-xs font-mono text-slate-800 whitespace-pre-wrap">${rr.findings}</div>
        </div>

        <div>
          <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Diagnostic Impression:</div>
          <div class="p-3 bg-amber-50/70 border border-amber-200/50 rounded-xl text-xs font-bold text-slate-900">${rr.impression}</div>
        </div>

        ${rr.recommendation ? `
          <div>
            <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Recommendation:</div>
            <div class="p-2.5 bg-slate-50 rounded-xl text-xs text-slate-700">${rr.recommendation}</div>
          </div>
        ` : ''}
      </div>
    `).join('');

    if (window.lucide) window.lucide.createIcons();
  },

  switchDossierTab(tabName) {
    const tabs = ['summary', 'history', 'timeline', 'docs', 'labs', 'radiology'];
    tabs.forEach(t => {
      const tabContent = document.getElementById(`dossier-tab-${t}`);
      const tabBtn = document.getElementById(`dossier-btn-${t}`);
      if (t === tabName) {
        if (tabContent) tabContent.classList.remove('hidden');
        if (tabBtn) {
          tabBtn.classList.add('border-[#7CA68D]', 'text-[#7CA68D]');
          tabBtn.classList.remove('border-transparent', 'text-slate-500');
        }
      } else {
        if (tabContent) tabContent.classList.add('hidden');
        if (tabBtn) {
          tabBtn.classList.remove('border-[#7CA68D]', 'text-[#7CA68D]');
          tabBtn.classList.add('border-transparent', 'text-slate-500');
        }
      }
    });
  },

  async saveSummaryEdits() {
    const text = document.getElementById('doctor-summary-text')?.value;
    const notes = document.getElementById('doctor-notes-input')?.value;

    try {
      const res = await fetch('/api/doctor/edit-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          summary_id: this.activeDossier?.ai_summary?.summary_id || 'sum_1',
          consultation_id: this.activeConsultationId,
          summary_text: text,
          doctor_notes: notes
        })
      });
      const data = await res.json();
      if (data.success) {
        App.showToast('Clinical summary edits saved successfully.');
        this.loadStats();
        this.loadQueue();
      }
    } catch (err) {
      console.error('Failed to save summary edits:', err);
    }
  },

  async verifySummary() {
    const text = document.getElementById('doctor-summary-text')?.value;
    const notes = document.getElementById('doctor-notes-input')?.value;

    try {
      const res = await fetch('/api/doctor/verify-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          summary_id: this.activeDossier?.ai_summary?.summary_id || 'sum_1',
          consultation_id: this.activeConsultationId,
          doctor_id: this.currentDoctorId,
          doctor_notes: notes,
          verified_summary_text: text
        })
      });
      const data = await res.json();
      if (data.success) {
        App.showToast('Clinical summary verified and digitally signed by physician!');
        this.closeDossier();
        this.loadStats();
        this.loadQueue();
      }
    } catch (err) {
      console.error('Failed to verify summary:', err);
    }
  },

  downloadSummaryPDF() {
    if (!this.activeConsultationId) return;
    window.open(`/api/export/summary-pdf/${this.activeConsultationId}`, '_blank');
  },

  showRedFlagModal() {
    const modal = document.getElementById('red-flag-feature-modal');
    if (modal) modal.classList.remove('hidden');
  },

  closeRedFlagModal() {
    const modal = document.getElementById('red-flag-feature-modal');
    if (modal) modal.classList.add('hidden');
  },

  closeDossier() {
    const modal = document.getElementById('doctor-dossier-modal');
    if (modal) modal.classList.add('hidden');
    this.activeConsultationId = null;
    this.activeDossier = null;
  }
};

window.DoctorDashboard = DoctorDashboard;
