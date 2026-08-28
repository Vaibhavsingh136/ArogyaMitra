/**
 * ArogyaMitra Voice & Audio Engine
 * Provides Multilingual Text-to-Speech (TTS), Speech-to-Text (STT),
 * and audio waveform visualization.
 * Source of truth: systemdesign.md Section 6 & brandguideline.md Section 10
 */

const VoiceEngine = {
  isListening: false,
  recognition: null,
  speechSynth: window.speechSynthesis || null,
  currentLanguage: 'en',
  onResultCallback: null,
  onStatusChangeCallback: null,

  init() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.maxAlternatives = 1;

      this.recognition.onstart = () => {
        this.isListening = true;
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(true);
      };

      this.recognition.onresult = (event) => {
        try {
          const transcript = Array.from(event.results)
            .map(result => result[0].transcript)
            .join('');
          const last = event.results[event.results.length - 1];
          const isFinal = last.isFinal;
          if (this.onResultCallback) {
            this.onResultCallback(transcript, isFinal);
          }
        } catch (err) {
          console.warn('Error processing recognition result:', err);
        }
      };

      this.recognition.onerror = (event) => {
        console.warn('Speech recognition error/warning:', event.error);
        this.isListening = false;
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(false);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(false);
      };
    } else {
      console.info('Web Speech API STT not natively supported in this browser. Fallback simulation available.');
    }
  },

  setLanguage(langCode) {
    this.currentLanguage = langCode;
    if (this.recognition) {
      const localeMap = {
        'en': 'en-IN',
        'hi': 'hi-IN',
        'bn': 'bn-IN',
        'te': 'te-IN',
        'ta': 'ta-IN',
        'mr': 'mr-IN',
        'gu': 'gu-IN',
        'kn': 'kn-IN',
        'or': 'or-IN',
        'ml': 'ml-IN',
        'pa': 'pa-IN'
      };
      this.recognition.lang = localeMap[langCode] || 'en-IN';
    }
  },

  startListening(onResult, onStatusChange) {
    this.onResultCallback = onResult;
    this.onStatusChangeCallback = onStatusChange;

    if (this.recognition) {
      try {
        this.recognition.start();
      } catch (err) {
        console.warn('Recognition start exception:', err);
      }
    } else {
      // Simulate speech input if browser mic is unavailable or blocked
      this.isListening = true;
      if (onStatusChange) onStatusChange(true);
      setTimeout(() => {
        if (this.isListening && onResult) {
          onResult("Headache for past 3 days and slight dizziness.", true);
          this.stopListening();
        }
      }, 2500);
    }
  },

  stopListening() {
    this.isListening = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (err) {
        console.warn(err);
      }
    }
    if (this.onStatusChangeCallback) this.onStatusChangeCallback(false);
  },
  speak(text, langCode = 'en') {
  speak(text, langCode = 'en', onStart = null, onEnd = null) {
    if (!this.speechSynth) {
      if (onStart) onStart();
      if (onEnd) onEnd();
      return;
    }
    this.speechSynth.cancel(); // Cancel any ongoing speech

    const utterance = new SpeechSynthesisUtterance(text);
    const localeMap = {
      'en': 'en-IN',
      'hi': 'hi-IN',
      'bn': 'bn-IN',
      'te': 'te-IN',
      'ta': 'ta-IN',
      'mr': 'mr-IN',
      'gu': 'gu-IN',
      'kn': 'kn-IN',
      'ml': 'ml-IN'
    };
    utterance.lang = localeMap[langCode] || 'en-IN';
    utterance.rate = 0.95; // Calm, clear, measured pace
    utterance.pitch = 1.0;

    // Pick Indian English/Hindi voice if available in system
    const voices = this.speechSynth.getVoices();
    const preferredVoice = voices.find(v => v.lang.includes(langCode) || v.lang.includes('IN'));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => {
      if (onStart) onStart();
    };
    utterance.onend = () => {
      if (onEnd) onEnd();
    };

    this.speechSynth.speak(utterance);
  }
};

window.VoiceEngine = VoiceEngine;
