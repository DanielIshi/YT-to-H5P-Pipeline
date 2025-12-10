// MÜHELOSE KI: H5P ENHANCED v4.0
// Dark Mode + TTS (Text-to-Speech) für Dialogcards
// Supports: Dialogcards, Accordion, MultiChoice, TrueFalse, Blanks, DragText, Summary, ImageHotspots

(function() {
    'use strict';

    // ========== DARK MODE CSS ==========
    var H5P_DARK_CSS = `
        /* ========== GLOBAL BACKGROUND & TEXT ========== */
        body,
        .h5p-content,
        .h5p-container,
        .h5p-question-content,
        .h5p-standalone {
            background-color: #141414 !important;
            color: #f0f0f0 !important;
            font-family: sans-serif !important;
        }

        /* ========== DIALOGCARDS ========== */
        .h5p-dialogcards-card-content {
            background-color: #1a1a2e !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
            box-shadow: 0 4px 15px rgba(0, 165, 183, 0.3) !important;
        }
        .h5p-dialogcards-card-text,
        .h5p-dialogcards-card-text-inner,
        .h5p-dialogcards-card-text-inner-content,
        .h5p-dialogcards-card-text-area {
            background-color: transparent !important;
            color: #f0f0f0 !important;
        }
        .h5p-dialogcards-cardwrap {
            background-color: transparent !important;
        }
        .h5p-dialogcards-description {
            color: #b0b0b0 !important;
        }
        .h5p-dialogcards-card-footer {
            background-color: #1a1a2e !important;
            border-top: 1px solid #333 !important;
        }
        .h5p-dialogcards .h5p-joubelui-button {
            background: linear-gradient(135deg, #00A5B7, #8A2BE2) !important;
            color: #fff !important;
            border: none !important;
        }
        .h5p-dialogcards .h5p-joubelui-button:hover {
            background: linear-gradient(135deg, #8A2BE2, #00FFFF) !important;
        }

        /* ========== ACCORDION ========== */
        .h5p-accordion,
        .h5p-accordion-container {
            background-color: #141414 !important;
        }
        .h5p-accordion .h5p-panel-title {
            background-color: #1a1a2e !important;
            color: #00FFFF !important;
            border: 1px solid #333 !important;
        }
        .h5p-accordion .h5p-panel-title:hover {
            background-color: #252547 !important;
            border-color: #00A5B7 !important;
        }
        .h5p-accordion .h5p-panel-content {
            background-color: #1a1a2e !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
        }

        /* ========== QUIZ BUTTONS ========== */
        .h5p-true-false-answer,
        .h5p-answer,
        .h5p-alternative-container,
        .h5p-multichoice-answer {
            background-color: #222 !important;
            color: #fff !important;
            border: 1px solid #444 !important;
            transition: all 0.2s ease !important;
            border-radius: 4px !important;
        }
        .h5p-true-false-answer:hover,
        .h5p-answer:hover,
        .h5p-alternative-container:hover,
        .h5p-multichoice-answer:hover {
            background-color: #333 !important;
            border-color: #00FFFF !important;
            cursor: pointer !important;
        }
        .h5p-true-false-answer[aria-checked="true"],
        .h5p-answer[aria-checked="true"],
        .h5p-alternative-container.h5p-selected {
            border-left: 5px solid #bd66ff !important;
            background-color: #2a2a2a !important;
        }

        /* ========== BLANKS ========== */
        .h5p-blanks {
            background-color: #141414 !important;
        }
        .h5p-blanks .h5p-text-input {
            background-color: #1a1a2e !important;
            color: #fff !important;
            border: 2px solid #00A5B7 !important;
            border-radius: 4px !important;
        }
        .h5p-blanks .h5p-text-input:focus {
            border-color: #00FFFF !important;
            box-shadow: 0 0 8px rgba(0, 255, 255, 0.5) !important;
        }

        /* ========== DRAG TEXT ========== */
        .h5p-drag-text {
            background-color: #141414 !important;
            color: #f0f0f0 !important;
        }
        .h5p-drag-text .h5p-drag-droppable-words {
            background-color: #1a1a2e !important;
        }
        .h5p-drag-text .h5p-drag-draggable {
            background-color: #00A5B7 !important;
            color: #000 !important;
            border-radius: 4px !important;
        }

        /* ========== SUMMARY ========== */
        .h5p-summary {
            background-color: #141414 !important;
        }
        .h5p-summary .h5p-summary-statement {
            background-color: #1a1a2e !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
        }
        .h5p-summary .h5p-summary-statement:hover {
            background-color: #252547 !important;
            border-color: #00A5B7 !important;
        }

        /* ========== IMAGE HOTSPOTS ========== */
        .h5p-image-hotspots {
            background-color: #141414 !important;
        }
        .h5p-image-hotspot-popup {
            background-color: #1a1a2e !important;
            color: #f0f0f0 !important;
            border: 1px solid #00A5B7 !important;
        }

        /* ========== BUTTONS ========== */
        button.h5p-question-check-answer,
        .h5p-question-buttons button,
        .h5p-joubelui-button {
            background: linear-gradient(135deg, #8A2BE2, #00FFFF) !important;
            color: #000 !important;
            border: none !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
        }
        button.h5p-question-check-answer:hover,
        .h5p-question-buttons button:hover,
        .h5p-joubelui-button:hover {
            background: linear-gradient(135deg, #00FFFF, #8A2BE2) !important;
        }

        /* ========== FOOTER ========== */
        .h5p-controls,
        .h5p-actions {
            background-color: #0a0a0a !important;
            border-top: 1px solid #333 !important;
        }
        .h5p-footer {
            background-color: #0a0a0a !important;
        }

        /* ========== TTS CONTROLS ========== */
        .h5p-tts-btn {
            position: absolute !important;
            top: 10px !important;
            right: 10px !important;
            width: 40px !important;
            height: 40px !important;
            border-radius: 50% !important;
            border: none !important;
            background: linear-gradient(135deg, #00A5B7, #8A2BE2) !important;
            color: white !important;
            font-size: 18px !important;
            cursor: pointer !important;
            z-index: 1000 !important;
            transition: transform 0.2s, box-shadow 0.2s !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        }
        .h5p-tts-btn:hover {
            transform: scale(1.1) !important;
            box-shadow: 0 4px 12px rgba(0,165,183,0.5) !important;
        }
        .h5p-tts-btn.speaking {
            background: linear-gradient(135deg, #ff4444, #ff8800) !important;
            animation: pulse 1s infinite !important;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .h5p-tts-controls {
            position: absolute !important;
            top: 10px !important;
            right: 60px !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            z-index: 1000 !important;
        }
        .h5p-tts-toggle {
            display: flex !important;
            align-items: center !important;
            gap: 6px !important;
            cursor: pointer !important;
            font-size: 12px !important;
            color: #00FFFF !important;
            background: rgba(0,0,0,0.5) !important;
            padding: 6px 10px !important;
            border-radius: 15px !important;
            user-select: none !important;
        }
        .h5p-tts-toggle input {
            width: 16px !important;
            height: 16px !important;
            cursor: pointer !important;
            accent-color: #00A5B7 !important;
        }
        .h5p-tts-speed {
            position: absolute !important;
            bottom: 60px !important;
            right: 10px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            gap: 4px !important;
            z-index: 1000 !important;
            background: rgba(0,0,0,0.5) !important;
            padding: 8px !important;
            border-radius: 8px !important;
        }
        .h5p-tts-speed input {
            width: 60px !important;
            height: 4px !important;
            cursor: pointer !important;
            accent-color: #00A5B7 !important;
        }
        .h5p-tts-speed span {
            font-size: 11px !important;
            color: #00FFFF !important;
        }

        /* ========== SCROLLBARS ========== */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        ::-webkit-scrollbar-thumb {
            background: #00A5B7;
            border-radius: 4px;
        }
    `;

    // ========== TTS MODULE ==========
    var TTS = {
        config: {
            lang: 'de-DE',
            rate: 1.0,
            pitch: 1.0,
            volume: 1.0
        },
        isSpeaking: false,
        autoReadEnabled: false,
        lastCardText: '',

        getSynth: function() {
            return window.speechSynthesis || null;
        },

        getVoice: function() {
            var synth = this.getSynth();
            if (!synth) return null;
            var voices = synth.getVoices();
            var german = voices.filter(function(v) { return v.lang.indexOf('de') === 0; });
            var preferred = german.find(function(v) {
                return v.name.indexOf('Google') > -1 || v.name.indexOf('Microsoft') > -1;
            });
            return preferred || german[0] || voices[0];
        },

        speak: function(text, callback) {
            var self = this;
            var synth = this.getSynth();
            if (!synth || !text) return;

            if (this.isSpeaking) synth.cancel();

            var utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = this.config.lang;
            utterance.rate = this.config.rate;
            utterance.pitch = this.config.pitch;
            utterance.volume = this.config.volume;

            var voice = this.getVoice();
            if (voice) utterance.voice = voice;

            utterance.onstart = function() {
                self.isSpeaking = true;
                self.updateUI(true);
            };
            utterance.onend = function() {
                self.isSpeaking = false;
                self.updateUI(false);
                if (callback) callback();
            };
            utterance.onerror = function() {
                self.isSpeaking = false;
                self.updateUI(false);
            };

            synth.speak(utterance);
        },

        stop: function() {
            var synth = this.getSynth();
            if (synth) {
                synth.cancel();
                this.isSpeaking = false;
                this.updateUI(false);
            }
        },

        updateUI: function(speaking) {
            var btns = document.querySelectorAll('.h5p-tts-btn');
            btns.forEach(function(btn) {
                btn.classList.toggle('speaking', speaking);
                btn.innerHTML = speaking ? '⏹' : '🔊';
                btn.title = speaking ? 'Stop' : 'Vorlesen';
            });
        },

        loadSettings: function() {
            var saved = localStorage.getItem('h5p-tts-autoread');
            if (saved !== null) this.autoReadEnabled = saved === 'true';
            var rate = localStorage.getItem('h5p-tts-rate');
            if (rate !== null) this.config.rate = parseFloat(rate);
        }
    };

    // ========== CARD TEXT EXTRACTION ==========
    function getCardText(cardElement) {
        var selectors = [
            '.h5p-dialogcards-card-text-inner-content',
            '.h5p-dialogcards-card-text-inner',
            '.h5p-dialogcards-card-text',
            '.h5p-dialogcards-card-content'
        ];
        for (var i = 0; i < selectors.length; i++) {
            var el = cardElement.querySelector(selectors[i]);
            if (el && el.textContent.trim()) {
                return el.textContent.trim();
            }
        }
        return cardElement.textContent.trim();
    }

    function readCurrentCard(doc) {
        var currentCard = doc.querySelector('.h5p-dialogcards-cardwrap.h5p-dialogcards-current');
        if (!currentCard) {
            currentCard = doc.querySelector('.h5p-dialogcards-card-content');
        }
        if (currentCard) {
            var text = getCardText(currentCard);
            if (text && text !== TTS.lastCardText) {
                TTS.lastCardText = text;
                TTS.speak(text);
                return true;
            }
        }
        return false;
    }

    // ========== UI INJECTION ==========
    function injectTTSControls(doc) {
        var container = doc.querySelector('.h5p-dialogcards');
        if (!container || doc.querySelector('.h5p-tts-btn')) return;

        container.style.position = 'relative';

        // TTS Button
        var btn = doc.createElement('button');
        btn.className = 'h5p-tts-btn';
        btn.innerHTML = '🔊';
        btn.title = 'Vorlesen (Leertaste)';
        btn.onclick = function() {
            if (TTS.isSpeaking) {
                TTS.stop();
            } else {
                readCurrentCard(doc);
            }
        };
        container.appendChild(btn);

        // Controls Container
        var controls = doc.createElement('div');
        controls.className = 'h5p-tts-controls';

        // Auto-Read Toggle
        var toggle = doc.createElement('label');
        toggle.className = 'h5p-tts-toggle';
        var checkbox = doc.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = TTS.autoReadEnabled;
        checkbox.onchange = function() {
            TTS.autoReadEnabled = this.checked;
            localStorage.setItem('h5p-tts-autoread', TTS.autoReadEnabled);
            if (TTS.autoReadEnabled) readCurrentCard(doc);
        };
        toggle.appendChild(checkbox);
        toggle.appendChild(doc.createTextNode(' Auto'));
        controls.appendChild(toggle);
        container.appendChild(controls);

        // Speed Control
        var speed = doc.createElement('div');
        speed.className = 'h5p-tts-speed';
        var slider = doc.createElement('input');
        slider.type = 'range';
        slider.min = '0.5';
        slider.max = '2.0';
        slider.step = '0.1';
        slider.value = TTS.config.rate;
        var label = doc.createElement('span');
        label.textContent = TTS.config.rate.toFixed(1) + 'x';
        slider.oninput = function() {
            TTS.config.rate = parseFloat(this.value);
            label.textContent = TTS.config.rate.toFixed(1) + 'x';
            localStorage.setItem('h5p-tts-rate', TTS.config.rate);
        };
        speed.appendChild(slider);
        speed.appendChild(label);
        container.appendChild(speed);

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

        // Click handlers for next/prev buttons
        var buttons = doc.querySelectorAll('.h5p-dialogcards-footer button, .h5p-joubelui-button');
        buttons.forEach(function(b) {
            b.addEventListener('click', function() {
                if (TTS.autoReadEnabled) {
                    setTimeout(function() { readCurrentCard(doc); }, 500);
                }
            });
        });

        console.log('H5P TTS: Controls injected');
    }

    // ========== INJECTION LOGIC ==========
    function injectAll(doc, depth) {
        if (!doc) return;
        depth = depth || 0;
        if (depth > 5) return;

        try {
            // Inject Dark Mode CSS
            if (!doc.getElementById('h5p-enhanced-v4')) {
                var style = doc.createElement('style');
                style.id = 'h5p-enhanced-v4';
                style.textContent = H5P_DARK_CSS;
                (doc.head || doc.documentElement).appendChild(style);
                console.log('H5P Enhanced v4.0: Dark Mode injected (depth ' + depth + ')');
            }

            // Inject TTS Controls (nur für Dialogcards)
            if (doc.querySelector('.h5p-dialogcards')) {
                injectTTSControls(doc);
            }

            // Recursively inject into iframes
            var iframes = doc.getElementsByTagName('iframe');
            for (var i = 0; i < iframes.length; i++) {
                try {
                    var iframeDoc = iframes[i].contentDocument ||
                                   (iframes[i].contentWindow ? iframes[i].contentWindow.document : null);
                    if (iframeDoc) {
                        injectAll(iframeDoc, depth + 1);
                    }
                } catch (e) {
                    // Cross-origin
                }
            }
        } catch (e) {
            console.log('H5P Enhanced injection error:', e);
        }
    }

    function runInjection() {
        injectAll(document, 0);
    }

    // ========== KEYBOARD SHORTCUTS ==========
    document.addEventListener('keydown', function(e) {
        // Space = Play/Stop (wenn kein Input fokussiert)
        if (e.code === 'Space' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            // Prüfe ob wir in einer H5P-Seite sind
            var hasDialogcards = document.querySelector('iframe');
            if (hasDialogcards) {
                e.preventDefault();
                if (TTS.isSpeaking) {
                    TTS.stop();
                } else {
                    // Finde Dialogcards in iframes
                    var frames = document.querySelectorAll('iframe');
                    for (var i = 0; i < frames.length; i++) {
                        try {
                            var doc = frames[i].contentDocument || frames[i].contentWindow.document;
                            if (doc.querySelector('.h5p-dialogcards')) {
                                readCurrentCard(doc);
                                break;
                            }
                        } catch (err) {}
                    }
                }
            }
        }

        // Alt+A = Toggle Auto-Read
        if (e.code === 'KeyA' && e.altKey) {
            TTS.autoReadEnabled = !TTS.autoReadEnabled;
            localStorage.setItem('h5p-tts-autoread', TTS.autoReadEnabled);
            document.querySelectorAll('.h5p-tts-toggle input').forEach(function(cb) {
                cb.checked = TTS.autoReadEnabled;
            });
            console.log('H5P TTS: Auto-Read', TTS.autoReadEnabled ? 'aktiviert' : 'deaktiviert');
        }
    });

    // ========== INITIALIZATION ==========
    function init() {
        // Load TTS settings
        TTS.loadSettings();

        // Load voices
        if (window.speechSynthesis) {
            window.speechSynthesis.onvoiceschanged = function() {
                var voice = TTS.getVoice();
                if (voice) console.log('H5P TTS: Using voice:', voice.name);
            };
            window.speechSynthesis.getVoices();
        }

        // Run injection
        if (document.readyState === 'complete') {
            runInjection();
        } else {
            window.addEventListener('load', runInjection);
        }
        setTimeout(runInjection, 500);
        setTimeout(runInjection, 1500);
        setTimeout(runInjection, 3000);
        setTimeout(runInjection, 6000);

        // MutationObserver for dynamic iframes
        var observer = new MutationObserver(function(mutations) {
            var shouldInject = false;
            mutations.forEach(function(m) {
                if (m.addedNodes.length) {
                    for (var i = 0; i < m.addedNodes.length; i++) {
                        if (m.addedNodes[i].tagName === 'IFRAME') {
                            shouldInject = true;
                            break;
                        }
                    }
                }
            });
            if (shouldInject) setTimeout(runInjection, 500);
        });
        observer.observe(document.body || document.documentElement, { childList: true, subtree: true });

        console.log('H5P Enhanced v4.0 initialized (Dark Mode + TTS)');
    }

    init();
})();
