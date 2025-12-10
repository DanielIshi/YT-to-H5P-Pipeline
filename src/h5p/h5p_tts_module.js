// MÜHELOSE KI: H5P TTS MODULE v1.0
// Text-to-Speech für Dialogcards mit Auto-Read Modus
// Integriert sich in bestehendes H5P Dark Mode Script

(function() {
    'use strict';

    // ========== CONFIGURATION ==========
    const TTS_CONFIG = {
        lang: 'de-DE',           // Sprache
        rate: 1.0,               // Geschwindigkeit (0.5 - 2.0)
        pitch: 1.0,              // Tonhöhe (0 - 2)
        volume: 1.0,             // Lautstärke (0 - 1)
        autoReadEnabled: false,  // Auto-Read standardmäßig aus
        voicePreference: null    // Wird automatisch gewählt
    };

    // State
    let currentUtterance = null;
    let isSpeaking = false;
    let autoReadEnabled = false;
    let lastCardText = '';

    // ========== SPEECH SYNTHESIS SETUP ==========

    function getSpeechSynthesis() {
        if ('speechSynthesis' in window) {
            return window.speechSynthesis;
        }
        console.warn('H5P TTS: Web Speech API nicht verfügbar');
        return null;
    }

    function getGermanVoice() {
        const synth = getSpeechSynthesis();
        if (!synth) return null;

        const voices = synth.getVoices();
        // Priorität: Google Deutsch > Microsoft > Andere
        const germanVoices = voices.filter(v => v.lang.startsWith('de'));

        // Bevorzuge Google oder Microsoft Stimmen
        const preferred = germanVoices.find(v =>
            v.name.includes('Google') ||
            v.name.includes('Microsoft') ||
            v.name.includes('Anna') ||
            v.name.includes('Hedda')
        );

        return preferred || germanVoices[0] || voices[0];
    }

    function speak(text, callback) {
        const synth = getSpeechSynthesis();
        if (!synth || !text) return;

        // Stoppe aktuelle Sprache
        if (isSpeaking) {
            synth.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = TTS_CONFIG.lang;
        utterance.rate = TTS_CONFIG.rate;
        utterance.pitch = TTS_CONFIG.pitch;
        utterance.volume = TTS_CONFIG.volume;

        const voice = getGermanVoice();
        if (voice) {
            utterance.voice = voice;
        }

        utterance.onstart = () => {
            isSpeaking = true;
            updateSpeakingState(true);
        };

        utterance.onend = () => {
            isSpeaking = false;
            updateSpeakingState(false);
            if (callback) callback();
        };

        utterance.onerror = (e) => {
            console.error('H5P TTS Error:', e);
            isSpeaking = false;
            updateSpeakingState(false);
        };

        currentUtterance = utterance;
        synth.speak(utterance);
    }

    function stopSpeaking() {
        const synth = getSpeechSynthesis();
        if (synth) {
            synth.cancel();
            isSpeaking = false;
            updateSpeakingState(false);
        }
    }

    function updateSpeakingState(speaking) {
        // Update UI buttons
        document.querySelectorAll('.h5p-tts-btn').forEach(btn => {
            btn.classList.toggle('speaking', speaking);
            btn.innerHTML = speaking ? '⏹️' : '🔊';
            btn.title = speaking ? 'Stop' : 'Vorlesen';
        });
    }

    // ========== UI COMPONENTS ==========

    function createTTSButton() {
        const btn = document.createElement('button');
        btn.className = 'h5p-tts-btn';
        btn.innerHTML = '🔊';
        btn.title = 'Vorlesen';
        btn.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, #00A5B7, #8A2BE2);
            color: white;
            font-size: 18px;
            cursor: pointer;
            z-index: 1000;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;

        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.1)';
            btn.style.boxShadow = '0 4px 12px rgba(0,165,183,0.5)';
        });

        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
        });

        return btn;
    }

    function createAutoReadToggle() {
        const container = document.createElement('div');
        container.className = 'h5p-tts-autoread-container';
        container.style.cssText = `
            position: absolute;
            top: 10px;
            right: 60px;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 1000;
        `;

        const toggle = document.createElement('label');
        toggle.className = 'h5p-tts-toggle';
        toggle.style.cssText = `
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            font-size: 12px;
            color: #00FFFF;
            background: rgba(0,0,0,0.5);
            padding: 6px 10px;
            border-radius: 15px;
            user-select: none;
        `;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'h5p-tts-autoread-checkbox';
        checkbox.checked = autoReadEnabled;
        checkbox.style.cssText = `
            width: 16px;
            height: 16px;
            cursor: pointer;
            accent-color: #00A5B7;
        `;

        const label = document.createElement('span');
        label.textContent = 'Auto';

        checkbox.addEventListener('change', (e) => {
            autoReadEnabled = e.target.checked;
            localStorage.setItem('h5p-tts-autoread', autoReadEnabled);
            console.log('H5P TTS: Auto-Read', autoReadEnabled ? 'aktiviert' : 'deaktiviert');

            // Wenn aktiviert, lese aktuelle Karte vor
            if (autoReadEnabled) {
                readCurrentCard();
            }
        });

        toggle.appendChild(checkbox);
        toggle.appendChild(label);
        container.appendChild(toggle);

        return container;
    }

    function createSpeedControl() {
        const container = document.createElement('div');
        container.className = 'h5p-tts-speed-container';
        container.style.cssText = `
            position: absolute;
            bottom: 60px;
            right: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            z-index: 1000;
            background: rgba(0,0,0,0.5);
            padding: 8px;
            border-radius: 8px;
        `;

        const label = document.createElement('span');
        label.textContent = '1.0x';
        label.className = 'h5p-tts-speed-label';
        label.style.cssText = `
            font-size: 11px;
            color: #00FFFF;
        `;

        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = '0.5';
        slider.max = '2.0';
        slider.step = '0.1';
        slider.value = TTS_CONFIG.rate;
        slider.className = 'h5p-tts-speed-slider';
        slider.style.cssText = `
            width: 60px;
            height: 4px;
            cursor: pointer;
            accent-color: #00A5B7;
        `;

        slider.addEventListener('input', (e) => {
            TTS_CONFIG.rate = parseFloat(e.target.value);
            label.textContent = TTS_CONFIG.rate.toFixed(1) + 'x';
            localStorage.setItem('h5p-tts-rate', TTS_CONFIG.rate);
        });

        container.appendChild(slider);
        container.appendChild(label);

        return container;
    }

    // ========== DIALOGCARDS INTEGRATION ==========

    function getCardText(cardElement) {
        // Suche nach Text-Content in der Karte
        const textSelectors = [
            '.h5p-dialogcards-card-text-inner-content',
            '.h5p-dialogcards-card-text-inner',
            '.h5p-dialogcards-card-text',
            '.h5p-dialogcards-card-content'
        ];

        for (const selector of textSelectors) {
            const el = cardElement.querySelector(selector);
            if (el && el.textContent.trim()) {
                return el.textContent.trim();
            }
        }

        return cardElement.textContent.trim();
    }

    function readCurrentCard() {
        const frames = document.querySelectorAll('iframe');

        for (const iframe of frames) {
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

                // Finde aktuelle Karte (die sichtbare)
                const currentCard = iframeDoc.querySelector('.h5p-dialogcards-cardwrap.h5p-dialogcards-current');
                if (currentCard) {
                    const text = getCardText(currentCard);
                    if (text && text !== lastCardText) {
                        lastCardText = text;
                        speak(text);
                        return true;
                    }
                }

                // Fallback: Erste sichtbare Karte
                const anyCard = iframeDoc.querySelector('.h5p-dialogcards-card-content');
                if (anyCard) {
                    const text = getCardText(anyCard);
                    if (text && text !== lastCardText) {
                        lastCardText = text;
                        speak(text);
                        return true;
                    }
                }
            } catch (e) {
                // Cross-origin - ignorieren
            }
        }

        return false;
    }

    function injectTTSControls(doc) {
        if (!doc || doc.querySelector('.h5p-tts-injected')) return;

        // Finde Dialogcards Container
        const dialogcardsContainer = doc.querySelector('.h5p-dialogcards');
        if (!dialogcardsContainer) return;

        // Markiere als injiziert
        const marker = doc.createElement('div');
        marker.className = 'h5p-tts-injected';
        marker.style.display = 'none';
        doc.body.appendChild(marker);

        // Mache Container relativ positioniert
        dialogcardsContainer.style.position = 'relative';

        // Füge TTS Button hinzu
        const ttsBtn = createTTSButton();
        ttsBtn.addEventListener('click', () => {
            if (isSpeaking) {
                stopSpeaking();
            } else {
                readCurrentCard();
            }
        });
        dialogcardsContainer.appendChild(ttsBtn);

        // Füge Auto-Read Toggle hinzu
        const autoToggle = createAutoReadToggle();
        dialogcardsContainer.appendChild(autoToggle);

        // Füge Speed Control hinzu
        const speedControl = createSpeedControl();
        dialogcardsContainer.appendChild(speedControl);

        // Beobachte Kartenwechsel für Auto-Read
        observeCardChanges(doc);

        console.log('H5P TTS: Controls injected into Dialogcards');
    }

    function observeCardChanges(doc) {
        const cardHolder = doc.querySelector('.h5p-dialogcards-cardwrap-set');
        if (!cardHolder) return;

        const observer = new MutationObserver((mutations) => {
            // Prüfe ob sich die aktuelle Karte geändert hat
            const currentCard = doc.querySelector('.h5p-dialogcards-cardwrap.h5p-dialogcards-current');
            if (currentCard && autoReadEnabled) {
                const text = getCardText(currentCard);
                if (text && text !== lastCardText) {
                    // Kleine Verzögerung für Animation
                    setTimeout(() => {
                        lastCardText = text;
                        speak(text);
                    }, 300);
                }
            }
        });

        observer.observe(cardHolder, {
            attributes: true,
            attributeFilter: ['class'],
            subtree: true
        });

        // Beobachte auch Klicks auf Next/Prev Buttons
        const buttons = doc.querySelectorAll('.h5p-dialogcards-footer button, .h5p-joubelui-button');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                if (autoReadEnabled) {
                    setTimeout(readCurrentCard, 500);
                }
            });
        });
    }

    // ========== INITIALIZATION ==========

    function loadSettings() {
        // Lade gespeicherte Einstellungen
        const savedAutoRead = localStorage.getItem('h5p-tts-autoread');
        if (savedAutoRead !== null) {
            autoReadEnabled = savedAutoRead === 'true';
        }

        const savedRate = localStorage.getItem('h5p-tts-rate');
        if (savedRate !== null) {
            TTS_CONFIG.rate = parseFloat(savedRate);
        }
    }

    function injectIntoAllFrames(doc, depth) {
        if (!doc) return;
        depth = depth || 0;
        if (depth > 5) return;

        // Injiziere in aktuelles Dokument
        injectTTSControls(doc);

        // Rekursiv in iframes
        const iframes = doc.getElementsByTagName('iframe');
        for (let i = 0; i < iframes.length; i++) {
            try {
                const iframeDoc = iframes[i].contentDocument ||
                                 (iframes[i].contentWindow ? iframes[i].contentWindow.document : null);
                if (iframeDoc) {
                    injectIntoAllFrames(iframeDoc, depth + 1);
                }
            } catch (e) {
                // Cross-origin
            }
        }
    }

    function init() {
        // Warte auf Voices (werden asynchron geladen)
        if ('speechSynthesis' in window) {
            window.speechSynthesis.onvoiceschanged = () => {
                const voice = getGermanVoice();
                if (voice) {
                    console.log('H5P TTS: Verwende Stimme:', voice.name);
                }
            };
            // Trigger voice loading
            window.speechSynthesis.getVoices();
        }

        loadSettings();

        // Injiziere in alle Frames
        function runInjection() {
            injectIntoAllFrames(document, 0);
        }

        // Mehrfach versuchen (H5P lädt langsam)
        if (document.readyState === 'complete') {
            runInjection();
        } else {
            window.addEventListener('load', runInjection);
        }
        setTimeout(runInjection, 1000);
        setTimeout(runInjection, 3000);
        setTimeout(runInjection, 5000);

        // MutationObserver für dynamisch geladene iframes
        const observer = new MutationObserver((mutations) => {
            let shouldInject = false;
            mutations.forEach(mutation => {
                if (mutation.addedNodes.length) {
                    for (let i = 0; i < mutation.addedNodes.length; i++) {
                        if (mutation.addedNodes[i].tagName === 'IFRAME') {
                            shouldInject = true;
                            break;
                        }
                    }
                }
            });
            if (shouldInject) {
                setTimeout(runInjection, 500);
            }
        });
        observer.observe(document.body || document.documentElement, {childList: true, subtree: true});

        console.log('H5P TTS Module v1.0 initialized');
    }

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        // Space = Play/Stop (nur wenn kein Input fokussiert)
        if (e.code === 'Space' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            if (isSpeaking) {
                stopSpeaking();
            } else {
                readCurrentCard();
            }
        }

        // A = Toggle Auto-Read
        if (e.code === 'KeyA' && e.altKey) {
            autoReadEnabled = !autoReadEnabled;
            localStorage.setItem('h5p-tts-autoread', autoReadEnabled);

            // Update checkboxes
            document.querySelectorAll('.h5p-tts-autoread-checkbox').forEach(cb => {
                cb.checked = autoReadEnabled;
            });

            console.log('H5P TTS: Auto-Read', autoReadEnabled ? 'aktiviert' : 'deaktiviert');
        }
    });

    // Start
    init();

})();
