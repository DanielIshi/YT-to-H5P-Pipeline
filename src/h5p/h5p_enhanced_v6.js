// MÜHELOSE KI: H5P ENHANCED v6.0
// Dark Mode + TTS + STT + LLM Answer Matching für Dialogcards
// Mobile-optimiert mit Web Speech API + GPT-4o-mini Backend

(function() {
    'use strict';

    // ========== CONFIGURATION ==========
    var CONFIG = {
        autoReadDefault: true,  // Auto-Read standardmäßig AN
        lang: 'de-DE',
        ttsRate: 1.0,
        sttContinuous: true,    // Dauerhaftes Zuhören
        sttInterimResults: true, // Zwischenergebnisse anzeigen
        matcherApiUrl: 'https://moodle.srv947487.hstgr.cloud:8085/api/match', // LLM Matcher API
        matcherFallbackUrl: 'http://148.230.71.150:8085/api/match' // Fallback ohne SSL
    };

    // ========== DARK MODE CSS + BRANDING ==========
    var H5P_DARK_CSS = `
        /* ========== GLOBAL BRANDING ========== */
        body, .h5p-content, .h5p-container, .h5p-question-content, .h5p-standalone {
            background-color: #141414 !important;
            color: #f0f0f0 !important;
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important;
        }

        /* ========== QUESTION TITLES - ACCENT COLOR ========== */
        .h5p-question-introduction,
        .h5p-multichoice .h5p-question-content > p:first-child,
        .h5p-true-false .h5p-question-content > p:first-child,
        .h5p-blanks .h5p-question-content > p:first-child,
        .h5p-summary-intro,
        .h5p-drag-task-description {
            color: #00FFFF !important;
            font-size: 1.3rem !important;
            font-weight: 600 !important;
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.2) !important;
        }

        /* ========== DIALOGCARDS ========== */
        .h5p-dialogcards-card-content {
            background: linear-gradient(145deg, #1a1a2e 0%, #252538 100%) !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
            box-shadow: 0 4px 20px rgba(0, 165, 183, 0.25), 0 0 40px rgba(138, 43, 226, 0.1) !important;
            border-radius: 12px !important;
        }
        .h5p-dialogcards-card-text, .h5p-dialogcards-card-text-inner,
        .h5p-dialogcards-card-text-inner-content, .h5p-dialogcards-card-text-area {
            background-color: transparent !important;
            color: #f0f0f0 !important;
        }
        .h5p-dialogcards-cardwrap { background-color: transparent !important; }
        .h5p-dialogcards-description {
            color: #00FFFF !important;
            font-size: 1.1rem !important;
            font-weight: 500 !important;
        }
        .h5p-dialogcards-card-footer {
            background: linear-gradient(145deg, #1a1a2e 0%, #252538 100%) !important;
            border-top: 1px solid rgba(0, 165, 183, 0.3) !important;
        }
        .h5p-dialogcards .h5p-joubelui-button {
            background: linear-gradient(135deg, #00A5B7, #8A2BE2) !important;
            color: #fff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        .h5p-dialogcards .h5p-joubelui-button:hover {
            background: linear-gradient(135deg, #8A2BE2, #00FFFF) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(0, 255, 255, 0.3) !important;
        }
        /* Card front (question) styling */
        .h5p-dialogcards-card-side.h5p-dialogcards-card-side-front .h5p-dialogcards-card-text-inner-content {
            color: #00FFFF !important;
        }
        /* Card back (answer) styling */
        .h5p-dialogcards-card-side.h5p-dialogcards-card-side-back .h5p-dialogcards-card-text-inner-content {
            color: #f0f0f0 !important;
        }

        /* ========== DIALOGCARDS TERM HIGHLIGHTING ========== */
        .h5p-dialogcards .h5p-term,
        .h5p-dialogcards-card-text .h5p-term,
        .h5p-term {
            color: #00FFFF !important;
            font-weight: bold !important;
            text-shadow: 0 0 8px rgba(0, 255, 255, 0.4) !important;
        }
        .h5p-dialogcards-card-text-inner-content {
            font-size: 1.3rem !important;
            line-height: 1.6 !important;
            text-align: center !important;
        }

        /* ========== ACCORDION ========== */
        .h5p-accordion, .h5p-accordion-container { background-color: #141414 !important; }
        .h5p-accordion .h5p-panel-title {
            background: linear-gradient(145deg, #1a1a2e 0%, #252538 100%) !important;
            color: #00FFFF !important;
            border: 1px solid #333 !important;
            border-left: 4px solid #00A5B7 !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            transition: all 0.3s ease !important;
        }
        .h5p-accordion .h5p-panel-title:hover {
            background: linear-gradient(145deg, #252538 0%, #2a2a4a 100%) !important;
            border-color: #00A5B7 !important;
            border-left-color: #00FFFF !important;
        }
        .h5p-accordion .h5p-panel-title[aria-expanded="true"] {
            border-left: 4px solid #8A2BE2 !important;
            background: linear-gradient(145deg, #252538 0%, #2a2a4a 100%) !important;
        }
        .h5p-accordion .h5p-panel-content {
            background-color: #1a1a2e !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
            border-left: 4px solid rgba(138, 43, 226, 0.5) !important;
            font-size: 1.05rem !important;
            line-height: 1.6 !important;
        }

        /* ========== QUIZ ANSWER OPTIONS ========== */
        .h5p-true-false-answer, .h5p-answer, .h5p-alternative-container, .h5p-multichoice-answer {
            background: linear-gradient(145deg, #1e1e2e 0%, #252538 100%) !important;
            color: #fff !important;
            border: 1px solid #444 !important;
            border-left: 3px solid transparent !important;
            transition: all 0.25s ease !important;
            border-radius: 8px !important;
            font-size: 1.1rem !important;
            padding: 14px 18px !important;
            margin-bottom: 8px !important;
        }
        .h5p-true-false-answer:hover, .h5p-answer:hover,
        .h5p-alternative-container:hover, .h5p-multichoice-answer:hover {
            background: linear-gradient(145deg, #252538 0%, #2a2a4a 100%) !important;
            border-color: #00A5B7 !important;
            border-left: 3px solid #00FFFF !important;
            transform: translateX(4px) !important;
        }
        .h5p-true-false-answer[aria-checked="true"], .h5p-answer[aria-checked="true"],
        .h5p-alternative-container.h5p-selected {
            border-left: 4px solid #bd66ff !important;
            background: linear-gradient(145deg, #2a2a4a 0%, #353560 100%) !important;
            box-shadow: 0 0 15px rgba(189, 102, 255, 0.2) !important;
        }

        /* ========== QUIZ FONTS & QUESTIONS ========== */
        .h5p-multichoice .h5p-question-content,
        .h5p-question-content p,
        .h5p-question-content,
        .h5p-multichoice-answer div,
        .h5p-true-false .h5p-question-content {
            font-size: 1.15rem !important;
            line-height: 1.6 !important;
        }
        .h5p-question-introduction {
            font-size: 1.3rem !important;
            color: #00FFFF !important;
            font-weight: 600 !important;
            margin-bottom: 1rem !important;
        }

        /* ========== BLANKS ========== */
        .h5p-blanks { background-color: #141414 !important; }
        .h5p-blanks .h5p-question-content {
            color: #f0f0f0 !important;
            font-size: 1.15rem !important;
            line-height: 1.8 !important;
        }
        .h5p-blanks .h5p-text-input {
            background-color: #1a1a2e !important;
            color: #00FFFF !important;
            border: 2px solid #00A5B7 !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        .h5p-blanks .h5p-text-input:focus {
            border-color: #00FFFF !important;
            box-shadow: 0 0 12px rgba(0, 255, 255, 0.4) !important;
            background-color: #252538 !important;
        }
        .h5p-blanks .h5p-correct { border-color: #00A5B7 !important; color: #00FFFF !important; }
        .h5p-blanks .h5p-wrong { border-color: #ff6b6b !important; }

        /* ========== DRAG TEXT ========== */
        .h5p-drag-text { background-color: #141414 !important; color: #f0f0f0 !important; }
        .h5p-drag-text .h5p-drag-task-description {
            color: #00FFFF !important;
            font-size: 1.2rem !important;
            font-weight: 600 !important;
        }
        .h5p-drag-text .h5p-drag-droppable-words {
            background-color: #1a1a2e !important;
            border-radius: 8px !important;
            padding: 16px !important;
        }
        .h5p-drag-text .h5p-drag-draggable {
            background: linear-gradient(135deg, #00A5B7, #8A2BE2) !important;
            color: #fff !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 8px 14px !important;
            box-shadow: 0 2px 8px rgba(0, 165, 183, 0.3) !important;
            transition: all 0.2s ease !important;
        }
        .h5p-drag-text .h5p-drag-draggable:hover {
            transform: scale(1.05) !important;
            box-shadow: 0 4px 15px rgba(0, 255, 255, 0.4) !important;
        }
        .h5p-drag-text .h5p-drag-dropzone {
            background-color: #252538 !important;
            border: 2px dashed #00A5B7 !important;
            border-radius: 6px !important;
        }
        .h5p-drag-text .h5p-drag-dropzone-has-draggable {
            background-color: #1a1a2e !important;
            border: 2px solid #8A2BE2 !important;
        }

        /* ========== SUMMARY ========== */
        .h5p-summary { background-color: #141414 !important; }
        .h5p-summary .h5p-summary-intro {
            color: #00FFFF !important;
            font-size: 1.2rem !important;
            font-weight: 600 !important;
            margin-bottom: 1rem !important;
        }
        .h5p-summary .h5p-summary-statement {
            background: linear-gradient(145deg, #1a1a2e 0%, #252538 100%) !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
            border-left: 3px solid transparent !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
            margin-bottom: 8px !important;
            transition: all 0.25s ease !important;
        }
        .h5p-summary .h5p-summary-statement:hover {
            background: linear-gradient(145deg, #252538 0%, #2a2a4a 100%) !important;
            border-color: #00A5B7 !important;
            border-left: 3px solid #00FFFF !important;
            transform: translateX(4px) !important;
        }
        .h5p-summary .h5p-summary-statement.h5p-summary-correct {
            border-left: 4px solid #00A5B7 !important;
            background: linear-gradient(145deg, #1a2a2e 0%, #253538 100%) !important;
        }

        /* ========== IMAGE HOTSPOTS ========== */
        .h5p-image-hotspots { background-color: #141414 !important; }
        .h5p-image-hotspot-popup {
            background: linear-gradient(145deg, #1a1a2e 0%, #252538 100%) !important;
            color: #f0f0f0 !important;
            border: 1px solid #00A5B7 !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 40px rgba(0, 165, 183, 0.2) !important;
        }
        .h5p-image-hotspot-popup-header {
            color: #00FFFF !important;
            font-size: 1.2rem !important;
            font-weight: 600 !important;
            border-bottom: 1px solid rgba(0, 165, 183, 0.3) !important;
        }
        .h5p-image-hotspot-popup-body { color: #f0f0f0 !important; line-height: 1.6 !important; }
        .h5p-image-hotspots-overlay { background-color: rgba(0, 0, 0, 0.7) !important; }
        .h5p-image-hotspot {
            background: linear-gradient(135deg, #00A5B7, #8A2BE2) !important;
            border: 2px solid #fff !important;
            box-shadow: 0 2px 10px rgba(0, 165, 183, 0.5) !important;
            transition: all 0.3s ease !important;
        }
        .h5p-image-hotspot:hover {
            transform: scale(1.2) !important;
            box-shadow: 0 4px 20px rgba(0, 255, 255, 0.6) !important;
        }

        /* ========== BUTTONS ========== */
        button.h5p-question-check-answer, .h5p-question-buttons button, .h5p-joubelui-button {
            background: linear-gradient(135deg, #8A2BE2, #00FFFF) !important;
            color: #000 !important;
            border: none !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
        }
        button.h5p-question-check-answer:hover, .h5p-question-buttons button:hover,
        .h5p-joubelui-button:hover {
            background: linear-gradient(135deg, #00FFFF, #8A2BE2) !important;
        }

        /* ========== FOOTER ========== */
        .h5p-controls, .h5p-actions {
            background-color: #0a0a0a !important;
            border-top: 1px solid #333 !important;
        }
        .h5p-footer { background-color: #0a0a0a !important; }

        /* ========== TTS/STT CONTROLS ========== */
        .h5p-voice-controls {
            position: absolute !important;
            top: 8px !important;
            right: 8px !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            z-index: 1000 !important;
        }
        .h5p-tts-btn, .h5p-stt-btn {
            width: 36px !important;
            height: 36px !important;
            border-radius: 50% !important;
            border: none !important;
            color: white !important;
            font-size: 16px !important;
            cursor: pointer !important;
            transition: transform 0.2s, box-shadow 0.2s !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        .h5p-tts-btn {
            background: linear-gradient(135deg, #00A5B7, #8A2BE2) !important;
        }
        .h5p-stt-btn {
            background: linear-gradient(135deg, #8A2BE2, #00A5B7) !important;
        }
        .h5p-tts-btn:hover, .h5p-stt-btn:hover {
            transform: scale(1.1) !important;
            box-shadow: 0 4px 12px rgba(0,165,183,0.5) !important;
        }
        .h5p-tts-btn.speaking, .h5p-stt-btn.listening {
            background: linear-gradient(135deg, #ff4444, #ff8800) !important;
            animation: pulse 1s infinite !important;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .h5p-voice-toggle {
            display: flex !important;
            align-items: center !important;
            gap: 4px !important;
            font-size: 11px !important;
            color: #00FFFF !important;
            background: rgba(0,0,0,0.6) !important;
            padding: 4px 8px !important;
            border-radius: 12px !important;
            cursor: pointer !important;
        }
        .h5p-voice-toggle input {
            width: 14px !important;
            height: 14px !important;
            accent-color: #00A5B7 !important;
        }
        .h5p-stt-transcript {
            position: absolute !important;
            bottom: 70px !important;
            left: 10px !important;
            right: 10px !important;
            background: rgba(0,0,0,0.8) !important;
            color: #00FFFF !important;
            padding: 10px 15px !important;
            border-radius: 8px !important;
            font-size: 14px !important;
            text-align: center !important;
            z-index: 1000 !important;
            border: 1px solid #00A5B7 !important;
            display: none !important;
        }
        .h5p-stt-transcript.visible { display: block !important; }
        .h5p-stt-transcript.interim { color: #888 !important; font-style: italic !important; }
        .h5p-stt-transcript.final { color: #00FFFF !important; font-style: normal !important; }
        .h5p-speed-control {
            position: absolute !important;
            bottom: 70px !important;
            right: 10px !important;
            background: rgba(0,0,0,0.6) !important;
            padding: 6px !important;
            border-radius: 8px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            gap: 2px !important;
            z-index: 1000 !important;
        }
        .h5p-speed-control input {
            width: 50px !important;
            accent-color: #00A5B7 !important;
        }
        .h5p-speed-control span {
            font-size: 10px !important;
            color: #00FFFF !important;
        }

        /* ========== MOBILE OPTIMIERUNG ========== */
        @media (max-width: 768px) {
            .h5p-voice-controls { top: 5px !important; right: 5px !important; gap: 5px !important; }
            .h5p-tts-btn, .h5p-stt-btn { width: 32px !important; height: 32px !important; font-size: 14px !important; }
            .h5p-voice-toggle { font-size: 10px !important; padding: 3px 6px !important; }
            .h5p-stt-transcript { font-size: 12px !important; bottom: 60px !important; }
        }

        /* ========== SCROLLBARS ========== */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a1a; }
        ::-webkit-scrollbar-thumb { background: #00A5B7; border-radius: 4px; }
    `;

    // ========== TTS MODULE ==========
    var TTS = {
        isSpeaking: false,
        autoReadEnabled: CONFIG.autoReadDefault,
        lastCardText: '',
        rate: CONFIG.ttsRate,

        getSynth: function() { return window.speechSynthesis || null; },

        getVoice: function() {
            var synth = this.getSynth();
            if (!synth) return null;
            var voices = synth.getVoices();
            var german = voices.filter(function(v) { return v.lang.indexOf('de') === 0; });
            var preferred = german.find(function(v) {
                return v.name.indexOf('Google') > -1 || v.name.indexOf('Microsoft') > -1 || v.name.indexOf('Anna') > -1;
            });
            return preferred || german[0] || voices[0];
        },

        speak: function(text, callback) {
            var self = this;
            var synth = this.getSynth();
            if (!synth || !text) return;
            if (this.isSpeaking) synth.cancel();

            var utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = CONFIG.lang;
            utterance.rate = this.rate;
            var voice = this.getVoice();
            if (voice) utterance.voice = voice;

            utterance.onstart = function() { self.isSpeaking = true; self.updateUI(true); };
            utterance.onend = function() { self.isSpeaking = false; self.updateUI(false); if (callback) callback(); };
            utterance.onerror = function() { self.isSpeaking = false; self.updateUI(false); };
            synth.speak(utterance);
        },

        stop: function() {
            var synth = this.getSynth();
            if (synth) { synth.cancel(); this.isSpeaking = false; this.updateUI(false); }
        },

        updateUI: function(speaking) {
            document.querySelectorAll('.h5p-tts-btn').forEach(function(btn) {
                btn.classList.toggle('speaking', speaking);
                btn.textContent = speaking ? '⏹' : '🔊';
            });
        },

        loadSettings: function() {
            var saved = localStorage.getItem('h5p-tts-autoread');
            this.autoReadEnabled = saved !== null ? saved === 'true' : CONFIG.autoReadDefault;
            var rate = localStorage.getItem('h5p-tts-rate');
            if (rate) this.rate = parseFloat(rate);
        }
    };

    // ========== STT MODULE ==========
    var STT = {
        recognition: null,
        isListening: false,
        transcript: '',
        onResult: null,

        init: function() {
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                console.warn('H5P STT: Speech Recognition nicht verfügbar');
                return false;
            }

            this.recognition = new SpeechRecognition();
            this.recognition.lang = CONFIG.lang;
            this.recognition.continuous = CONFIG.sttContinuous;
            this.recognition.interimResults = CONFIG.sttInterimResults;

            var self = this;

            this.recognition.onstart = function() {
                self.isListening = true;
                self.updateUI(true);
                console.log('H5P STT: Listening...');
            };

            this.recognition.onend = function() {
                self.isListening = false;
                self.updateUI(false);
                // Auto-restart if continuous mode
                if (self.shouldRestart) {
                    setTimeout(function() { self.start(); }, 100);
                }
            };

            this.recognition.onresult = function(event) {
                var interim = '';
                var final = '';

                for (var i = event.resultIndex; i < event.results.length; i++) {
                    var transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        final += transcript;
                    } else {
                        interim += transcript;
                    }
                }

                self.showTranscript(interim || final, !final);

                if (final && self.onResult) {
                    self.onResult(final.trim());
                }
            };

            this.recognition.onerror = function(event) {
                console.log('H5P STT Error:', event.error);
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    self.isListening = false;
                    self.updateUI(false);
                }
            };

            return true;
        },

        start: function() {
            if (!this.recognition) {
                if (!this.init()) return;
            }
            if (!this.isListening) {
                this.shouldRestart = true;
                try {
                    this.recognition.start();
                } catch (e) {
                    console.log('H5P STT: Already started');
                }
            }
        },

        stop: function() {
            this.shouldRestart = false;
            if (this.recognition && this.isListening) {
                this.recognition.stop();
            }
            this.hideTranscript();
        },

        toggle: function() {
            if (this.isListening) {
                this.stop();
            } else {
                this.start();
            }
        },

        updateUI: function(listening) {
            document.querySelectorAll('.h5p-stt-btn').forEach(function(btn) {
                btn.classList.toggle('listening', listening);
                btn.textContent = listening ? '⏹' : '🎤';
            });
        },

        showTranscript: function(text, isInterim) {
            document.querySelectorAll('.h5p-stt-transcript').forEach(function(el) {
                el.textContent = text || '...';
                el.classList.add('visible');
                el.classList.toggle('interim', isInterim);
                el.classList.toggle('final', !isInterim);
            });
        },

        hideTranscript: function() {
            document.querySelectorAll('.h5p-stt-transcript').forEach(function(el) {
                el.classList.remove('visible');
            });
        }
    };

    // ========== CARD FUNCTIONS ==========
    function getCardText(cardElement) {
        var selectors = ['.h5p-dialogcards-card-text-inner-content', '.h5p-dialogcards-card-text-inner',
                        '.h5p-dialogcards-card-text', '.h5p-dialogcards-card-content'];
        for (var i = 0; i < selectors.length; i++) {
            var el = cardElement.querySelector(selectors[i]);
            if (el && el.textContent.trim()) return el.textContent.trim();
        }
        return cardElement.textContent.trim();
    }

    function readCurrentCard(doc) {
        var card = doc.querySelector('.h5p-dialogcards-cardwrap.h5p-dialogcards-current') ||
                   doc.querySelector('.h5p-dialogcards-card-content');
        if (card) {
            var text = getCardText(card);
            if (text && text !== TTS.lastCardText) {
                TTS.lastCardText = text;
                TTS.speak(text);
                return true;
            }
        }
        return false;
    }

    function getExpectedAnswer(doc) {
        // Hole die Rückseite der aktuellen Karte (die Antwort)
        var card = doc.querySelector('.h5p-dialogcards-cardwrap.h5p-dialogcards-current');
        if (card) {
            var backText = card.querySelector('.h5p-dialogcards-card-back .h5p-dialogcards-card-text-inner-content');
            if (backText) return backText.textContent.trim();
        }
        return null;
    }

    // ========== LLM API MATCHING ==========
    function matchWithLLM(spoken, expected, context) {
        return new Promise(function(resolve, reject) {
            var apiUrl = CONFIG.matcherFallbackUrl; // Use direct IP for now

            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    spoken: spoken,
                    expected: expected,
                    context: context || 'Dialogkarte',
                    lang: 'de'
                })
            })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('API Error: ' + response.status);
                }
                return response.json();
            })
            .then(function(data) {
                resolve({
                    match_score: data.match_score || 0,
                    is_correct: data.is_correct || false,
                    feedback: data.feedback || ''
                });
            })
            .catch(function(err) {
                console.error('LLM Match API error:', err);
                reject(err);
            });
        });
    }

    // ========== UI INJECTION ==========
    function injectVoiceControls(doc) {
        var container = doc.querySelector('.h5p-dialogcards');
        if (!container || doc.querySelector('.h5p-voice-controls')) return;
        container.style.position = 'relative';

        // Voice Controls Container
        var controls = doc.createElement('div');
        controls.className = 'h5p-voice-controls';

        // Auto-Read Toggle
        var autoToggle = doc.createElement('label');
        autoToggle.className = 'h5p-voice-toggle';
        var autoCheckbox = doc.createElement('input');
        autoCheckbox.type = 'checkbox';
        autoCheckbox.checked = TTS.autoReadEnabled;
        autoCheckbox.onchange = function() {
            TTS.autoReadEnabled = this.checked;
            localStorage.setItem('h5p-tts-autoread', TTS.autoReadEnabled);
            if (TTS.autoReadEnabled) readCurrentCard(doc);
        };
        autoToggle.appendChild(autoCheckbox);
        autoToggle.appendChild(doc.createTextNode(' Auto'));
        controls.appendChild(autoToggle);

        // TTS Button
        var ttsBtn = doc.createElement('button');
        ttsBtn.className = 'h5p-tts-btn';
        ttsBtn.textContent = '🔊';
        ttsBtn.title = 'Vorlesen (Leertaste)';
        ttsBtn.onclick = function() {
            if (TTS.isSpeaking) TTS.stop();
            else readCurrentCard(doc);
        };
        controls.appendChild(ttsBtn);

        // STT Button (nur wenn unterstützt)
        if (window.SpeechRecognition || window.webkitSpeechRecognition) {
            var sttBtn = doc.createElement('button');
            sttBtn.className = 'h5p-stt-btn';
            sttBtn.textContent = '🎤';
            sttBtn.title = 'Spracheingabe (M)';
            sttBtn.onclick = function() { STT.toggle(); };
            controls.appendChild(sttBtn);
        }

        container.appendChild(controls);

        // Transcript Display
        var transcript = doc.createElement('div');
        transcript.className = 'h5p-stt-transcript';
        transcript.textContent = '...';
        container.appendChild(transcript);

        // Speed Control
        var speedControl = doc.createElement('div');
        speedControl.className = 'h5p-speed-control';
        var slider = doc.createElement('input');
        slider.type = 'range';
        slider.min = '0.5';
        slider.max = '2.0';
        slider.step = '0.1';
        slider.value = TTS.rate;
        var label = doc.createElement('span');
        label.textContent = TTS.rate.toFixed(1) + 'x';
        slider.oninput = function() {
            TTS.rate = parseFloat(this.value);
            label.textContent = TTS.rate.toFixed(1) + 'x';
            localStorage.setItem('h5p-tts-rate', TTS.rate);
        };
        speedControl.appendChild(slider);
        speedControl.appendChild(label);
        container.appendChild(speedControl);

        // STT Result Handler - LLM-basiertes Matching
        STT.onResult = function(spokenText) {
            var expected = getExpectedAnswer(doc);
            var question = getCardText(doc.querySelector('.h5p-dialogcards-cardwrap.h5p-dialogcards-current') || doc.querySelector('.h5p-dialogcards-card-content'));

            if (expected) {
                console.log('H5P STT: Gesprochen:', spokenText);
                console.log('H5P STT: Erwartet:', expected);
                STT.showTranscript('⏳ Prüfe Antwort...', true);

                // LLM-basiertes Matching via API
                matchWithLLM(spokenText, expected, question)
                    .then(function(result) {
                        console.log('H5P STT: LLM Score:', result.match_score + '%');
                        if (result.is_correct) {
                            STT.showTranscript('✓ ' + result.feedback + ' (' + result.match_score + '%)', false);
                            // Optional: Auto-advance zur nächsten Karte
                        } else {
                            STT.showTranscript('✗ ' + result.feedback, false);
                        }
                    })
                    .catch(function(err) {
                        console.error('H5P STT: API Error:', err);
                        // Fallback auf lokales Matching
                        var similarity = calculateSimilarity(spokenText.toLowerCase(), expected.toLowerCase());
                        if (similarity > 0.6) {
                            STT.showTranscript('✓ ' + spokenText + ' (' + (similarity * 100).toFixed(0) + '%)', false);
                        } else {
                            STT.showTranscript('✗ ' + spokenText, false);
                        }
                    });
            }
        };

        // Observe card changes for auto-read
        var cardHolder = doc.querySelector('.h5p-dialogcards-cardwrap-set');
        if (cardHolder) {
            var observer = new MutationObserver(function() {
                if (TTS.autoReadEnabled) {
                    setTimeout(function() { readCurrentCard(doc); }, 300);
                }
            });
            observer.observe(cardHolder, { attributes: true, attributeFilter: ['class'], subtree: true });
        }

        // Button click handlers for auto-read
        doc.querySelectorAll('.h5p-dialogcards-footer button, .h5p-joubelui-button').forEach(function(btn) {
            btn.addEventListener('click', function() {
                if (TTS.autoReadEnabled) setTimeout(function() { readCurrentCard(doc); }, 500);
            });
        });

        console.log('H5P Voice Controls injected (TTS + STT)');
    }

    // Simple string similarity (Dice coefficient)
    function calculateSimilarity(str1, str2) {
        if (str1 === str2) return 1;
        if (str1.length < 2 || str2.length < 2) return 0;

        var bigrams1 = new Set();
        for (var i = 0; i < str1.length - 1; i++) {
            bigrams1.add(str1.substring(i, i + 2));
        }

        var intersection = 0;
        for (var j = 0; j < str2.length - 1; j++) {
            var bigram = str2.substring(j, j + 2);
            if (bigrams1.has(bigram)) {
                intersection++;
                bigrams1.delete(bigram);
            }
        }

        return (2 * intersection) / (str1.length + str2.length - 2);
    }

    // ========== STT FOR TEXT INPUTS (Issue #4) ==========
    function injectSTTForTextInputs(doc) {
        // Find all text inputs in H5P content types
        var selectors = [
            '.h5p-blanks .h5p-text-input',           // Blanks/Fill-in
            '.h5p-drag-text input[type="text"]',     // Drag Text (if any)
            '.h5p-essay textarea',                    // Essay
            '.h5p-free-text-question textarea',       // Free Text
            'input.h5p-textinput',                    // Generic H5P text input
            '.h5p-question input[type="text"]'        // Any question text input
        ];

        var inputs = [];
        selectors.forEach(function(sel) {
            var found = doc.querySelectorAll(sel);
            found.forEach(function(el) { inputs.push(el); });
        });

        inputs.forEach(function(input) {
            // Skip if already has mic button
            if (input.parentElement && input.parentElement.querySelector('.h5p-stt-input-btn')) return;

            // Create mic button
            var micBtn = doc.createElement('button');
            micBtn.className = 'h5p-stt-input-btn';
            micBtn.textContent = '🎤';
            micBtn.title = 'Spracheingabe';
            micBtn.type = 'button';
            micBtn.style.cssText = 'position:absolute;right:5px;top:50%;transform:translateY(-50%);width:28px;height:28px;border-radius:50%;border:none;background:linear-gradient(135deg,#8A2BE2,#00A5B7);color:#fff;font-size:14px;cursor:pointer;z-index:100;display:flex;align-items:center;justify-content:center;';

            // Wrap input if needed
            var wrapper = input.parentElement;
            if (!wrapper.style.position || wrapper.style.position === 'static') {
                wrapper.style.position = 'relative';
            }
            input.style.paddingRight = '35px';

            // Insert button after input
            input.parentElement.insertBefore(micBtn, input.nextSibling);

            // STT for this specific input
            var inputRecognition = null;
            var isRecording = false;

            micBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();

                if (isRecording) {
                    // Stop recording
                    if (inputRecognition) inputRecognition.stop();
                    isRecording = false;
                    micBtn.textContent = '🎤';
                    micBtn.style.background = 'linear-gradient(135deg,#8A2BE2,#00A5B7)';
                    return;
                }

                // Start recording
                var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert('Spracheingabe wird in diesem Browser nicht unterstützt. Bitte Chrome oder Edge verwenden.');
                    return;
                }

                inputRecognition = new SpeechRecognition();
                inputRecognition.lang = CONFIG.lang;
                inputRecognition.continuous = false;
                inputRecognition.interimResults = true;

                inputRecognition.onstart = function() {
                    isRecording = true;
                    micBtn.textContent = '⏹';
                    micBtn.style.background = 'linear-gradient(135deg,#ff4444,#ff8800)';
                    input.placeholder = 'Sprechen Sie jetzt...';
                };

                inputRecognition.onresult = function(event) {
                    var transcript = '';
                    for (var i = 0; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    input.value = transcript;
                    // Trigger input event for H5P validation
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                };

                inputRecognition.onend = function() {
                    isRecording = false;
                    micBtn.textContent = '🎤';
                    micBtn.style.background = 'linear-gradient(135deg,#8A2BE2,#00A5B7)';
                    input.placeholder = '';
                };

                inputRecognition.onerror = function(event) {
                    console.log('STT Input Error:', event.error);
                    isRecording = false;
                    micBtn.textContent = '🎤';
                    micBtn.style.background = 'linear-gradient(135deg,#8A2BE2,#00A5B7)';
                };

                try {
                    inputRecognition.start();
                } catch (err) {
                    console.log('STT already running');
                }
            };
        });

        if (inputs.length > 0) {
            console.log('H5P STT: Injected mic buttons for ' + inputs.length + ' text inputs');
        }
    }

    // ========== INJECTION LOGIC ==========
    function injectAll(doc, depth) {
        if (!doc || depth > 5) return;

        try {
            if (!doc.getElementById('h5p-enhanced-v5')) {
                var style = doc.createElement('style');
                style.id = 'h5p-enhanced-v5';
                style.textContent = H5P_DARK_CSS;
                (doc.head || doc.documentElement).appendChild(style);
                console.log('H5P Enhanced v6.0: Injected (depth ' + depth + ')');
            }

            if (doc.querySelector('.h5p-dialogcards')) {
                injectVoiceControls(doc);
            }

            // Inject STT for all text inputs (Issue #4)
            injectSTTForTextInputs(doc);

            var iframes = doc.getElementsByTagName('iframe');
            for (var i = 0; i < iframes.length; i++) {
                try {
                    var iframeDoc = iframes[i].contentDocument ||
                                   (iframes[i].contentWindow ? iframes[i].contentWindow.document : null);
                    if (iframeDoc) injectAll(iframeDoc, depth + 1);
                } catch (e) {}
            }
        } catch (e) {
            console.log('H5P injection error:', e);
        }
    }

    function runInjection() { injectAll(document, 0); }

    // ========== KEYBOARD SHORTCUTS ==========
    document.addEventListener('keydown', function(e) {
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;

        // Space = TTS Play/Stop
        if (e.code === 'Space') {
            e.preventDefault();
            if (TTS.isSpeaking) TTS.stop();
            else {
                document.querySelectorAll('iframe').forEach(function(iframe) {
                    try {
                        var doc = iframe.contentDocument || iframe.contentWindow.document;
                        if (doc.querySelector('.h5p-dialogcards')) readCurrentCard(doc);
                    } catch (err) {}
                });
            }
        }

        // M = Mikrofon Toggle
        if (e.code === 'KeyM') {
            e.preventDefault();
            STT.toggle();
        }

        // A = Auto-Read Toggle
        if (e.code === 'KeyA' && e.altKey) {
            TTS.autoReadEnabled = !TTS.autoReadEnabled;
            localStorage.setItem('h5p-tts-autoread', TTS.autoReadEnabled);
            document.querySelectorAll('.h5p-voice-toggle input').forEach(function(cb) {
                cb.checked = TTS.autoReadEnabled;
            });
        }
    });

    // ========== INITIALIZATION ==========
    function init() {
        TTS.loadSettings();

        if (window.speechSynthesis) {
            window.speechSynthesis.onvoiceschanged = function() {
                var voice = TTS.getVoice();
                if (voice) console.log('H5P TTS: Voice:', voice.name);
            };
            window.speechSynthesis.getVoices();
        }

        STT.init();

        if (document.readyState === 'complete') runInjection();
        else window.addEventListener('load', runInjection);

        setTimeout(runInjection, 500);
        setTimeout(runInjection, 1500);
        setTimeout(runInjection, 3000);
        setTimeout(runInjection, 6000);

        var observer = new MutationObserver(function(mutations) {
            var shouldInject = mutations.some(function(m) {
                return Array.from(m.addedNodes).some(function(n) { return n.tagName === 'IFRAME'; });
            });
            if (shouldInject) setTimeout(runInjection, 500);
        });
        observer.observe(document.body || document.documentElement, { childList: true, subtree: true });

        console.log('H5P Enhanced v6.0 initialized (Dark Mode + TTS + STT + LLM Matching)');
    }

    init();
})();
