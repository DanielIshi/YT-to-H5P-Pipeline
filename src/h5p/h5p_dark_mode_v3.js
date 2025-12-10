// MÜHELOSE KI: H5P DARK MODE INJECTOR v3.0
// Supports: Dialogcards, Accordion, MultiChoice, TrueFalse, Blanks, DragText, Summary, ImageHotspots
// Fixed: Nested iframe injection for H5P embed frames
(function() {
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
        /* Turn Button */
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

        /* ========== QUIZ BUTTONS (MultiChoice, TrueFalse) ========== */
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

        /* ========== BLANKS (Fill in) ========== */
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

        /* ========== CHECK BUTTON (All Types) ========== */
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

        /* ========== FOOTER & PROGRESS ========== */
        .h5p-controls,
        .h5p-actions {
            background-color: #0a0a0a !important;
            border-top: 1px solid #333 !important;
        }
        .h5p-footer {
            background-color: #0a0a0a !important;
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

    function injectDarkMode(doc, depth) {
        if (!doc) return;
        depth = depth || 0;
        var maxDepth = 5;

        try {
            // Inject into current document if not already done
            if (!doc.getElementById("h5p-dark-mode-v3")) {
                var style = doc.createElement("style");
                style.id = "h5p-dark-mode-v3";
                style.textContent = H5P_DARK_CSS;
                (doc.head || doc.documentElement).appendChild(style);
                console.log("Effortless AI: H5P Dark Mode v3.0 injected (depth " + depth + ")");
            }

            // Recursively inject into nested iframes
            if (depth < maxDepth) {
                var iframes = doc.getElementsByTagName("iframe");
                for (var i = 0; i < iframes.length; i++) {
                    try {
                        var iframe = iframes[i];
                        var iframeDoc = iframe.contentDocument || (iframe.contentWindow ? iframe.contentWindow.document : null);
                        if (iframeDoc) {
                            injectDarkMode(iframeDoc, depth + 1);
                        }
                    } catch (e) {
                        // Cross-origin blocked - normal for external content
                    }
                }
            }
        } catch (e) {
            console.log("H5P Dark Mode injection error: " + e);
        }
    }

    function runInjection() {
        injectDarkMode(document, 0);
    }

    // Run multiple times to catch dynamically loaded iframes
    if (document.readyState === "complete") {
        runInjection();
    } else {
        window.addEventListener("load", runInjection);
    }
    setTimeout(runInjection, 500);
    setTimeout(runInjection, 1500);
    setTimeout(runInjection, 3000);
    setTimeout(runInjection, 6000);

    // MutationObserver for dynamically added iframes
    var observer = new MutationObserver(function(mutations) {
        var shouldInject = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                for (var i = 0; i < mutation.addedNodes.length; i++) {
                    if (mutation.addedNodes[i].tagName === "IFRAME") {
                        shouldInject = true;
                        break;
                    }
                }
            }
        });
        if (shouldInject) {
            setTimeout(runInjection, 300);
        }
    });
    observer.observe(document.body || document.documentElement, {childList: true, subtree: true});
})();
