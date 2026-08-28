/**
 * ArogyaMitra Document Digitization & OCR Inspector
 * Source of truth: systemdesign.md Section 7 & brandguideline.md Section 10
 */

const OCRViewer = {
  activeDocument: null,
  uploadedDocuments: [],

  async init(patientId, consultationId) {
    this.patientId = patientId;
    this.consultationId = consultationId;
    // Localize page using App.currentLanguage when available
    try {
      const lang = window.App ? window.App.currentLanguage : 'en';
      const container = document.getElementById('kiosk-step-5');
      if (container) {
        const h2 = container.querySelector('h2');
        const p = container.querySelector('p');
        if (h2) h2.innerText = lang === 'hi' ? 'क्या आपके पास पिछले मेडिकल रिपोर्ट या प्रिस्क्रिप्शन हैं?' : 'Do you have previous medical reports or prescriptions?';
        if (p) p.innerText = lang === 'hi' ? 'पिछले रिकॉर्ड अपलोड करना वैकल्पिक है। यदि आपके पास दस्तावेज़ नहीं हैं, तो आप इस चरण को छोड़ सकते हैं।' : 'Uploading previous records is optional. If you don\'t have documents with you today, you can simply skip this step.';
      }
    } catch (err) {
      console.warn('OCRViewer localization failed:', err);
    }
    await this.loadPatientDocuments();
  },

  async loadSamplePresets() {
    try {
      const res = await fetch('/api/documents/samples');
      const data = await res.json();
      const container = document.getElementById('preset-samples-grid');
      if (!container) return;

      container.innerHTML = data.samples.map(s => `
        <div onclick="OCRViewer.selectPreset('${s.id}')" 
             class="cursor-pointer group p-4 rounded-xl border border-slate-200 bg-white hover:border-[#7CA68D] hover:shadow-md transition-all">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">${s.type}</span>
            <span class="text-xs text-slate-500">${s.date}</span>
          </div>
          <div class="font-semibold text-slate-900 text-sm group-hover:text-[#7CA68D] transition mb-1">${s.title}</div>
          <div class="text-xs text-slate-500 line-clamp-2">${s.description}</div>
          <div class="mt-3 flex items-center gap-1.5 text-xs text-[#7CA68D] font-medium">
            <i data-lucide="scan-line" class="w-3.5 h-3.5"></i>
            <span>Click to Scan & Read</span>
          </div>
        </div>
      `).join('');

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to load preset samples:', err);
    }
  },

  async loadPatientDocuments() {
    if (!this.patientId) return;
    try {
      const res = await fetch(`/api/documents/list/${this.patientId}`);
      const data = await res.json();
      this.uploadedDocuments = data.documents || [];
      this.renderDocumentList();
    } catch (err) {
      console.error('Failed to load patient documents:', err);
    }
  },

  renderDocumentList() {
    const listContainer = document.getElementById('uploaded-docs-list');
    if (!listContainer) return;

    if (this.uploadedDocuments.length === 0) {
      listContainer.innerHTML = `
        <div class="text-center py-8 text-slate-400 text-sm">
          No medical records scanned yet. Please upload your own medical record or prescription.
        </div>
      `;
      return;
    }

    listContainer.innerHTML = this.uploadedDocuments.map(d => `
      <div onclick="OCRViewer.viewDocumentDetails('${d.document_id}')" 
           class="cursor-pointer p-3.5 rounded-xl border border-slate-200 bg-white hover:border-[#7CA68D] flex items-center justify-between transition shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-[#7CA68D]/15 text-[#638d74] flex items-center justify-center">
            <i data-lucide="file-text" class="w-5 h-5"></i>
          </div>
          <div>
            <div class="font-semibold text-slate-900 text-sm">${d.file_name}</div>
            <div class="text-xs text-slate-500">${d.document_type} • ${d.document_date || d.upload_date.substring(0,10)}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">OCR Extracted</span>
          <i data-lucide="chevron-right" class="w-4 h-4 text-slate-400"></i>
        </div>
      </div>
    `).join('');

    if (window.lucide) window.lucide.createIcons();
  },

  async selectPreset(presetId) {
    this.showScanningAnimation();
    try {
      const formData = new FormData();
      formData.append('patient_id', this.patientId || 'pat_1');
      formData.append('consultation_id', this.consultationId || 'con_1');
      formData.append('preset_sample_id', presetId);

      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      setTimeout(() => {
        this.hideScanningAnimation();
        this.renderOCRResult(data);
        this.loadPatientDocuments();
      }, 1200);
    } catch (err) {
      this.hideScanningAnimation();
      console.error('Error processing preset OCR:', err);
    }
  },

  async uploadCustomFile(file) {
    if (!file) return;
    this.showScanningAnimation();
    try {
      const formData = new FormData();
      formData.append('patient_id', this.patientId || 'pat_1');
      formData.append('consultation_id', this.consultationId || 'con_1');
      formData.append('file', file);

      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      setTimeout(() => {
        this.hideScanningAnimation();
        this.renderOCRResult(data);
        this.loadPatientDocuments();
      }, 1500);
    } catch (err) {
      this.hideScanningAnimation();
      console.error('Upload failed:', err);
    }
  },

  showScanningAnimation() {
    const inspector = document.getElementById('ocr-inspector-modal');
    const loading = document.getElementById('ocr-scanning-overlay');
    if (inspector) inspector.classList.remove('hidden');
    if (loading) loading.classList.remove('hidden');
  },

  hideScanningAnimation() {
    const loading = document.getElementById('ocr-scanning-overlay');
    if (loading) loading.classList.add('hidden');
  },

  renderOCRResult(data) {
    const container = document.getElementById('ocr-inspector-content');
    if (!container) return;

    const entities = data.ocr.extracted_entities || {};
    const confidencePct = Math.round((data.ocr.confidence_score || 0.95) * 100);

    container.innerHTML = `
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Left: Document Preview -->
        <div class="bg-slate-900 rounded-xl overflow-hidden relative flex flex-col justify-center items-center p-4 min-h-[380px]">
          <img src="${data.file_path}" alt="Document Preview" class="max-h-[420px] object-contain rounded-lg shadow-lg border border-slate-700" />
          <div class="absolute bottom-3 left-3 bg-black/70 backdrop-blur-sm px-3 py-1 rounded text-xs text-slate-300">
            ${data.file_name} • Date: ${data.document_date || 'N/A'}
          </div>
        </div>

        <!-- Right: Extracted Structured Clinical Entities -->
        <div class="space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <span class="text-xs font-bold text-[#7CA68D] uppercase tracking-wider">Document AI Inspection</span>
              <h4 class="text-lg font-bold text-slate-900">${data.document_type}</h4>
            </div>
            <div class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold">
              <i data-lucide="check" class="w-3.5 h-3.5"></i>
              <span>OCR Confidence: ${confidencePct}%</span>
            </div>
          </div>

          <!-- Diagnoses -->
          ${entities.diagnoses && entities.diagnoses.length > 0 ? `
            <div>
              <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Identified Diagnoses / Indications</div>
              <div class="flex flex-wrap gap-2">
                ${entities.diagnoses.map(d => `<span class="px-2.5 py-1 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 text-xs font-medium">${d}</span>`).join('')}
              </div>
            </div>
          ` : ''}

          <!-- Medications -->
          ${entities.medications && entities.medications.length > 0 ? `
            <div>
              <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Prescribed Medicines & Dosages</div>
              <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                ${entities.medications.map(m => `
                  <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs flex items-center justify-between">
                    <div>
                      <span class="font-bold text-slate-900">${m.name}</span>
                      <span class="text-slate-600 ml-1">(${m.dosage || ''})</span>
                      <div class="text-slate-500 text-[11px]">${m.instructions || m.frequency || ''}</div>
                    </div>
                    <span class="px-2 py-0.5 bg-white rounded border border-slate-200 font-semibold text-slate-700">${m.duration || '30 days'}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          <!-- Investigations / Lab Values -->
          ${entities.investigations && entities.investigations.length > 0 ? `
            <div>
              <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Extracted Test Parameters & Ranges</div>
              <div class="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                ${entities.investigations.map(inv => `
                  <div class="p-2 rounded-lg ${inv.flag === 'HIGH' || inv.flag === 'LOW' ? 'bg-red-50/70 border border-red-200' : 'bg-slate-50 border border-slate-200'} text-xs flex items-center justify-between">
                    <span class="font-medium text-slate-800">${inv.name}</span>
                    <div class="flex items-center gap-2">
                      <span class="font-bold ${inv.flag === 'HIGH' || inv.flag === 'LOW' ? 'text-red-700' : 'text-slate-900'}">${inv.value} ${inv.unit || ''}</span>
                      ${inv.reference ? `<span class="text-slate-400 text-[10px]">Ref: ${inv.reference}</span>` : ''}
                      ${inv.flag && inv.flag !== 'NORMAL' ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-200 text-red-800">${inv.flag}</span>` : ''}
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          <!-- Raw Extracted OCR Text Collapsible -->
          <details class="text-xs border border-slate-200 rounded-lg p-2 bg-slate-50/50">
            <summary class="cursor-pointer font-semibold text-slate-600">View Raw Extracted Text</summary>
            <pre class="mt-2 p-2 bg-white rounded border border-slate-200 text-[11px] text-slate-700 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">${data.ocr.extracted_text}</pre>
          </details>
        </div>
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();
  },

  viewDocumentDetails(docId) {
    const doc = this.uploadedDocuments.find(d => d.document_id === docId);
    if (!doc) return;
    this.renderOCRResult({
      file_name: doc.file_name,
      file_path: doc.file_path,
      document_type: doc.document_type,
      document_date: doc.document_date,
      ocr: {
        extracted_text: doc.extracted_text || 'No raw text available',
        extracted_entities: doc.extracted_entities || {},
        confidence_score: doc.confidence_score || 0.95
      }
    });
    this.showScanningAnimation();
    this.hideScanningAnimation();
  },

  closeInspector() {
    const inspector = document.getElementById('ocr-inspector-modal');
    if (inspector) inspector.classList.add('hidden');
  }
};

window.OCRViewer = OCRViewer;
