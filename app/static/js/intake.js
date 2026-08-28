/**
 * ArogyaMitra Conversational Clinical Intake Engine
 * Source of truth: User Requirements 1, 2, 23, 24 & systemdesign.md Section 4, 5
 *
 * Enforces 100% language consistency throughout the patient interview.
 */

const IntakeController = {
  currentSessionId: null,
  currentPatientId: null,
  currentLanguage: 'en',
  currentQuestion: null,
  allQuestions: [],
  recordedResponses: [],
  selectedOptions: [],

  async init(consultationId, patientId, language = 'en') {
    this.currentSessionId = consultationId;
    this.currentPatientId = patientId;
    this.currentLanguage = language || App.currentLanguage || 'en';
    this.selectedOptions = [];
    this.recordedResponses = [];

    VoiceEngine.setLanguage(this.currentLanguage);
    await this.loadQuestions();
  },

  async loadQuestions() {
    try {
      const res = await fetch(`/api/intake/questions?lang=${this.currentLanguage}`);
      const data = await res.json();
      this.allQuestions = data.questions || [];
      
      // Start with Chief Complaint
      const initialQ = this.allQuestions.find(q => q.question_id === 'q_cc_1') || this.allQuestions[0];
      this.renderQuestion(initialQ);
    } catch (err) {
      console.error('Failed to load questions:', err);
    }
  },

  getLocalizedText(key, fallback) {
    const dict = {
      'hi': {
        'tap_speak': 'विकल्प चुनें या नीचे बोलकर बताएं:',
        'type_speak_placeholder': 'अपनी भाषा में सहजता से लिखें या बोलें...',
        'speak': 'बोलें',
        'listening': 'सुन रहे हैं...',
        'next': 'आगे बढ़ें',
        'skip_question': 'अभी छोड़ें',
        'take_time': '💡 "अपना समय लें। आप बोल या चुन सकते हैं।"',
        'history_recorded': 'स्वास्थ्य इतिहास दर्ज कर लिया गया है',
        'history_recorded_sub': 'धन्यवाद! अब आप अपने पुराने पर्चे या रिपोर्ट जोड़ सकते हैं (या सीधे आगे बढ़ सकते हैं)।',
        'continue_docs': 'दस्तावेज़ जोड़ें या छोड़ें',
        'live_title': 'स्वास्थ्य रिकॉर्ड (लाइव सिंक)',
        'live_empty': 'आपके द्वारा बोले गए या चुने गए उत्तर यहाँ रीयल-टाइम में दिखेंगे।'
      },
      'bn': {
        'tap_speak': 'বিকল্প নির্বাচন করুন বা কথা বলুন:',
        'type_speak_placeholder': 'আপনার ভাষায় লিখুন বা বলুন...',
        'speak': 'বলুন',
        'listening': 'শুনছি...',
        'next': 'পরবর্তী',
        'skip_question': 'এড়িয়ে যান',
        'take_time': '💡 "ধীরে সুস্থে উত্তর দিন।"',
        'history_recorded': 'স্বাস্থ্য ইতিহাস সংরক্ষিত হয়েছে',
        'history_recorded_sub': 'ধন্যবাদ! আপনার পুরানো রিপোর্ট থাকলে যুক্ত করতে পারেন।',
        'continue_docs': 'নথি আপলোড বা এড়িয়ে যান',
        'live_title': 'স্বাস্থ্য রেকর্ড (লাইভ সিঙ্ক)'
      },
      'te': {
        'tap_speak': 'ఎంపికను ఎంచుకోండి లేదా మాట్లాడండి:',
        'type_speak_placeholder': 'మీ భాషలో టైప్ చేయండి లేదా మాట్లాడండి...',
        'speak': 'మాట్లాడండి',
        'listening': 'వింటున్నాం...',
        'next': 'తదుపరి',
        'skip_question': 'దాటవేయి',
        'take_time': '💡 "నిదానంగా సమాధానం ఇవ్వండి."',
        'history_recorded': 'ఆరోగ్య వివరాలు నమోదు చేయబడ్డాయి',
        'history_recorded_sub': 'ధన్యవాదాలు! మీ పాత రిపోర్టులు ఉంటే జతచేయవచ్చు.',
        'continue_docs': 'డాక్యుమెంట్ స్కానింగ్ లేదా దాటవేయడం',
        'live_title': 'ఆరోగ్య రికార్డు (లైవ్ సింక్)'
      }
    };

    const langDict = dict[this.currentLanguage] || {};
    return langDict[key] || fallback;
  },

  renderQuestion(question) {
    if (!question) {
      this.finishIntakeInterview();
      return;
    }

    this.currentQuestion = question;
    this.selectedOptions = [];
    
    const container = document.getElementById('intake-question-container');
    if (!container) return;

    // Speak question aloud in selected language if autoTTS enabled
    if (window.autoTTS !== false) {
      VoiceEngine.speak(question.question_text, this.currentLanguage);
    }

    // Build Touch Option Chips
    let optionsHtml = '';
    if (question.options && question.options.length > 0) {
      optionsHtml = `
        <div class="mb-4">
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
            ${this.getLocalizedText('tap_speak', 'Tap an option or speak below:')}
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            ${question.options.map((opt) => `
              <button type="button" onclick="IntakeController.selectOption('${opt.replace(/'/g, "\\'")}', this)" 
                      class="intake-chip text-left px-4 py-3 rounded-xl border border-slate-200 bg-white hover:border-[#7CA68D] hover:bg-[#F3EFE3]/40 text-slate-800 font-medium transition-all shadow-sm flex items-center justify-between text-base">
                <span>${opt}</span>
                <i data-lucide="plus-circle" class="w-4 h-4 text-slate-400"></i>
              </button>
            `).join('')}
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/80 shadow-sm transition-all animate-fadeIn">
        <div class="flex items-center justify-between gap-4 mb-4">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#7CA68D]/15 text-[#638d74] text-xs font-semibold tracking-wide">
            <i data-lucide="stethoscope" class="w-3.5 h-3.5"></i>
            <span>${question.category ? question.category.replace(/_/g, ' ') : 'CLINICAL INTAKE'}</span>
          </div>
          <button onclick="IntakeController.playQuestionAudio(this, '${question.question_text.replace(/'/g, "\\'")}', '${this.currentLanguage}')" 
                  class="p-2 rounded-lg text-slate-500 hover:text-[#7CA68D] hover:bg-slate-50 transition" title="Listen again">
            <i data-lucide="volume-2" class="w-5 h-5"></i>
          </button>
        </div>

        <h3 class="text-xl sm:text-2xl font-bold text-slate-900 leading-snug mb-6">
          ${question.question_text}
        </h3>

        ${optionsHtml}

        <!-- Voice & Text Input Section -->
        <div class="mt-6 pt-5 border-t border-slate-100">
          <div class="flex flex-col sm:flex-row gap-3 items-stretch">
            <div class="relative flex-1">
              <input type="text" id="intake-text-input" 
                     placeholder="${this.getLocalizedText('type_speak_placeholder', 'Type or speak your answer naturally in your language...')}" 
                     class="w-full pl-4 pr-10 py-3.5 rounded-xl border border-slate-200 focus:border-[#7CA68D] focus:ring-2 focus:ring-[#7CA68D]/20 outline-none text-base text-slate-800 transition" 
                     onkeypress="if(event.key==='Enter') IntakeController.submitCurrentAnswer()" />
            </div>
            
            <button id="intake-mic-btn" onclick="IntakeController.toggleVoice()" 
                    class="btn-secondary px-5 py-3.5 flex items-center justify-center gap-2 rounded-xl transition font-medium" 
                    title="Speak in your language">
              <i data-lucide="mic" class="w-5 h-5 text-slate-700"></i>
              <span id="intake-mic-label">${this.getLocalizedText('speak', 'Speak')}</span>
            </button>

            <button onclick="IntakeController.submitCurrentAnswer()" 
                    class="btn-primary px-6 py-3.5 rounded-xl text-base font-semibold transition">
              <span>${this.getLocalizedText('next', 'Next')}</span>
              <i data-lucide="arrow-right" class="w-4 h-4"></i>
            </button>
          </div>

          <!-- Real-time Recording Status & Waveform Indicator -->
          <div id="voice-indicator" class="hidden mt-4 p-3 bg-red-50 border border-red-100 rounded-xl flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-3 h-3 rounded-full bg-red-500 animate-ping"></div>
              <span class="text-sm font-medium text-red-700">Listening to your voice... Speak naturally.</span>
            </div>
            <div class="waveform-container">
              <div class="waveform-bar"></div><div class="waveform-bar"></div><div class="waveform-bar"></div>
              <div class="waveform-bar"></div><div class="waveform-bar"></div><div class="waveform-bar"></div>
            </div>
          </div>

          <div class="mt-3 flex items-center justify-between text-xs text-slate-500">
            <span>${this.getLocalizedText('take_time', '💡 "Take your time. You can speak or tap."')}</span>
            <button onclick="IntakeController.skipQuestion()" class="text-slate-400 hover:text-slate-600 underline">
              ${this.getLocalizedText('skip_question', 'Skip for now')}
            </button>
          </div>
        </div>
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();
  },

  selectOption(optText, element) {
    const input = document.getElementById('intake-text-input');
    if (this.currentQuestion.question_type === 'multi_choice') {
      if (this.selectedOptions.includes(optText)) {
        this.selectedOptions = this.selectedOptions.filter(o => o !== optText);
        element.classList.remove('bg-[#7CA68D]', 'text-white', 'border-[#7CA68D]');
      } else {
        this.selectedOptions.push(optText);
        element.classList.add('bg-[#7CA68D]', 'text-white', 'border-[#7CA68D]');
      }
      if (input) input.value = this.selectedOptions.join(', ');
    } else {
      if (input) input.value = optText;
      this.submitAnswer(optText, 'TOUCH');
    }
  },

  toggleVoice() {
    const micBtn = document.getElementById('intake-mic-btn');
    const micLabel = document.getElementById('intake-mic-label');
    const indicator = document.getElementById('voice-indicator');
    const input = document.getElementById('intake-text-input');

    if (VoiceEngine.isListening) {
      VoiceEngine.stopListening();
      if (micBtn) micBtn.classList.remove('mic-recording');
      if (micLabel) micLabel.innerText = this.getLocalizedText('speak', 'Speak');
      if (indicator) indicator.classList.add('hidden');
    } else {
      if (micBtn) micBtn.classList.add('mic-recording');
      if (micLabel) micLabel.innerText = this.getLocalizedText('listening', 'Listening...');
      if (indicator) indicator.classList.remove('hidden');

      VoiceEngine.startListening(
        (transcript, isFinal) => {
          if (input) input.value = transcript;
          if (isFinal) {
            this.toggleVoice();
          }
        },
        (isRecording) => {
          if (!isRecording) {
            if (micBtn) micBtn.classList.remove('mic-recording');
            if (micLabel) micLabel.innerText = this.getLocalizedText('speak', 'Speak');
            if (indicator) indicator.classList.add('hidden');
          }
        }
      );
    }
  },

  submitCurrentAnswer() {
    const input = document.getElementById('intake-text-input');
    const text = input ? input.value.trim() : '';
    if (!text) {
      this.skipQuestion();
      return;
    }
    this.submitAnswer(text, 'TEXT');
  },

  async submitAnswer(answerText, inputMethod = 'TEXT') {
    if (!this.currentQuestion || !this.currentSessionId) return;

    try {
      const payload = {
        consultation_id: this.currentSessionId,
        question_id: this.currentQuestion.question_id,
        category: this.currentQuestion.category,
        original_response: answerText,
        input_method: inputMethod,
        current_language: this.currentLanguage
      };

      const res = await fetch('/api/intake/submit-response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      this.recordedResponses.push({
        category: this.currentQuestion.category,
        original: answerText,
        normalized: data.normalized_response
      });

      this.updateStructuredPreview();

      if (data.is_complete || !data.next_question) {
        this.finishIntakeInterview();
      } else {
        this.renderQuestion(data.next_question);
      }
    } catch (err) {
      console.error('Error submitting intake response:', err);
    }
  },

  skipQuestion() {
    const skipLabel = this.getLocalizedText('not_reported', 'Not reported / Skipped');
    this.submitAnswer(skipLabel, 'TOUCH');
  },

  updateStructuredPreview() {
    const container = document.getElementById('live-history-list');
    if (!container) return;

    container.innerHTML = this.recordedResponses.map(r => `
      <div class="p-3 bg-white rounded-xl border border-slate-100 shadow-sm text-sm animate-fadeIn">
        <div class="text-xs font-semibold text-[#7CA68D] uppercase tracking-wider">${r.category.replace(/_/g, ' ')}</div>
        <div class="text-slate-900 font-medium mt-0.5">${r.original}</div>
      </div>
    `).join('');
  },

  async finishIntakeInterview() {
    const container = document.getElementById('intake-question-container');
    if (container) {
      container.innerHTML = `
        <div class="bg-white rounded-2xl p-8 border border-slate-200 text-center shadow-sm animate-fadeIn">
          <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <i data-lucide="check-circle" class="w-8 h-8"></i>
          </div>
          <h3 class="text-2xl font-bold text-slate-900 mb-2">
            ${this.getLocalizedText('history_recorded', 'Health History Recorded')}
          </h3>
          <p class="text-slate-600 max-w-md mx-auto mb-6 text-sm">
            ${this.getLocalizedText('history_recorded_sub', 'Thank you! Now you can attach previous prescriptions or reports (or proceed directly to review).')}
          </p>
          <button onclick="App.goToStep(5)" class="btn-primary px-8 py-3.5 rounded-xl text-base font-semibold shadow-sm">
            <span>${this.getLocalizedText('continue_docs', 'Continue to Document Step')}</span>
            <i data-lucide="arrow-right" class="w-5 h-5"></i>
          </button>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
    }
  }
};

IntakeController.playQuestionAudio = function(btn, text, lang) {
  if (!btn) return;
  const icon = btn.querySelector('i');
  const original = btn.innerHTML;
  const setPlaying = () => {
    btn.classList.add('bg-slate-50');
    btn.innerHTML = '<i data-lucide="volume-2" class="w-5 h-5 text-[#7CA68D]"></i> Playing...';
    if (window.lucide) window.lucide.createIcons();
  };
  const clearPlaying = () => {
    btn.classList.remove('bg-slate-50');
    btn.innerHTML = original;
    if (window.lucide) window.lucide.createIcons();
  };

  try {
    VoiceEngine.speak(text, lang, setPlaying, clearPlaying);
  } catch (err) {
    console.error('TTS playback failed:', err);
    clearPlaying();
  }
};

window.IntakeController = IntakeController;
