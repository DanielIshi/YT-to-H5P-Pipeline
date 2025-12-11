/**
 * H5P Auto-Advance Script for Moodle
 * Issue #3: UX - Auto-Weiter nach korrekter Antwort
 *
 * Listens to H5P xAPI events and automatically advances to the next activity
 * when the user completes a quiz correctly.
 *
 * Installation: Add to Moodle's Site Administration → Appearance → Additional HTML → Footer
 */
(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        autoAdvanceDelay: 1500,      // ms before auto-advance (1.5 seconds)
        showSuccessOverlay: true,     // Show green success overlay
        enableOnCorrectOnly: true,    // Only auto-advance on correct answers
        debugMode: false              // Set to true for console logging
    };

    // Check if we're on an H5P activity page
    function isH5PActivityPage() {
        return window.location.href.includes('/mod/h5pactivity/view.php');
    }

    // Get the next activity URL from the course navigation
    function getNextActivityUrl() {
        // Try multiple selectors for next activity link
        const selectors = [
            '.activity-navigation .nav-link[data-direction="next"]',
            '.activity-navigation a[href*="view.php"]:last-child',
            '#page-content .next-activity a',
            '.courseindex-item.pageitem + .courseindex-item a'
        ];

        for (const selector of selectors) {
            const nextLink = document.querySelector(selector);
            if (nextLink && nextLink.href) {
                return nextLink.href;
            }
        }

        // Fallback: Try to find next activity in course index
        const courseIndex = document.querySelectorAll('.courseindex-item a.courseindex-link');
        let foundCurrent = false;
        for (const link of courseIndex) {
            if (foundCurrent) {
                return link.href;
            }
            if (link.closest('.pageitem')) {
                foundCurrent = true;
            }
        }

        return null;
    }

    // Show success overlay before advancing
    function showSuccessOverlay(callback) {
        if (!CONFIG.showSuccessOverlay) {
            callback();
            return;
        }

        const overlay = document.createElement('div');
        overlay.id = 'h5p-success-overlay';
        overlay.innerHTML = `
            <div class="success-content">
                <div class="success-icon">✓</div>
                <div class="success-text">Richtig! Weiter zum nächsten Modul...</div>
            </div>
        `;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 180, 100, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            animation: fadeIn 0.3s ease;
        `;

        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            #h5p-success-overlay .success-content {
                text-align: center;
                color: white;
            }
            #h5p-success-overlay .success-icon {
                font-size: 80px;
                margin-bottom: 20px;
            }
            #h5p-success-overlay .success-text {
                font-size: 24px;
                font-weight: bold;
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(overlay);

        setTimeout(callback, CONFIG.autoAdvanceDelay);
    }

    // Navigate to next activity
    function advanceToNextActivity() {
        const nextUrl = getNextActivityUrl();

        if (nextUrl) {
            if (CONFIG.debugMode) {
                console.log('[H5P Auto-Advance] Navigating to:', nextUrl);
            }
            showSuccessOverlay(() => {
                window.location.href = nextUrl;
            });
        } else {
            if (CONFIG.debugMode) {
                console.log('[H5P Auto-Advance] No next activity found');
            }
            // Show completion message instead
            showCompletionMessage();
        }
    }

    // Show course completion message
    function showCompletionMessage() {
        const overlay = document.createElement('div');
        overlay.id = 'h5p-completion-overlay';
        overlay.innerHTML = `
            <div class="completion-content">
                <div class="completion-icon">🎉</div>
                <div class="completion-text">Lernpfad abgeschlossen!</div>
                <button onclick="document.getElementById('h5p-completion-overlay').remove()">Schließen</button>
            </div>
        `;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(138, 43, 226, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
        `;

        const style = document.createElement('style');
        style.textContent = `
            #h5p-completion-overlay .completion-content {
                text-align: center;
                color: white;
            }
            #h5p-completion-overlay .completion-icon {
                font-size: 80px;
                margin-bottom: 20px;
            }
            #h5p-completion-overlay .completion-text {
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 30px;
            }
            #h5p-completion-overlay button {
                background: white;
                color: #8A2BE2;
                border: none;
                padding: 15px 40px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 8px;
                cursor: pointer;
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(overlay);
    }

    // Handle xAPI events from H5P
    function handleXAPIEvent(event) {
        const statement = event.data.statement;

        if (CONFIG.debugMode) {
            console.log('[H5P Auto-Advance] xAPI Event:', statement);
        }

        // Check if this is a completion event
        if (!statement.result || statement.result.completion !== true) {
            return;
        }

        // Check if this is the root activity (not a sub-question)
        const hasParent = statement.context &&
                         statement.context.contextActivities &&
                         statement.context.contextActivities.parent &&
                         statement.context.contextActivities.parent.length > 0;

        if (hasParent) {
            if (CONFIG.debugMode) {
                console.log('[H5P Auto-Advance] Skipping sub-question completion');
            }
            return;
        }

        // Check if answer was correct (if we're only advancing on correct)
        if (CONFIG.enableOnCorrectOnly) {
            const score = statement.result.score;
            if (score) {
                const percentage = (score.raw / score.max) * 100;
                if (percentage < 100) {
                    if (CONFIG.debugMode) {
                        console.log('[H5P Auto-Advance] Score not 100%, not advancing:', percentage);
                    }
                    return;
                }
            }
        }

        if (CONFIG.debugMode) {
            console.log('[H5P Auto-Advance] Activity completed successfully, advancing...');
        }

        advanceToNextActivity();
    }

    // Initialize the script
    function init() {
        if (!isH5PActivityPage()) {
            return;
        }

        if (CONFIG.debugMode) {
            console.log('[H5P Auto-Advance] Initializing on H5P activity page');
        }

        // Wait for H5P to load
        const checkH5P = setInterval(() => {
            if (window.H5P && window.H5P.externalDispatcher) {
                clearInterval(checkH5P);

                if (CONFIG.debugMode) {
                    console.log('[H5P Auto-Advance] H5P loaded, attaching event listener');
                }

                H5P.externalDispatcher.on('xAPI', handleXAPIEvent);
            }
        }, 500);

        // Timeout after 30 seconds
        setTimeout(() => clearInterval(checkH5P), 30000);
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
