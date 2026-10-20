/**
 * Git-Gud AI — Interactive Engine & UI Controller
 * Zero external dependencies. Fast, keyboard-accessible, WCAG AA compliant.
 */

(function () {
  'use strict';

  // --- State Store ---
  const state = {
    currentScenarioId: 'hardcoded-secrets',
    currentRoastLevel: 'spicy', // 'mild' | 'spicy' | 'savage'
    isTyping: false,
    typingTimeoutId: null,
    skipAnimation: false,
    reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
  };

  // --- Theme Management ---
  function initTheme() {
    const savedTheme = localStorage.getItem('gitgud-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'dark'); // default dark hacker
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);

    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('gitgud-theme', next);
        updateThemeIcon(next);
      });
    }
  }

  function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;
    btn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
    btn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
  }

  // --- Diff Syntax Highlighting ---
  function renderDiff(diffText) {
    const lines = diffText.trim().split('\n');
    return lines.map(line => {
      const escaped = escapeHtml(line);
      if (line.startsWith('+') && !line.startsWith('+++')) {
        return `<span class="d-add">${escaped}</span>`;
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        return `<span class="d-del">${escaped}</span>`;
      } else if (line.startsWith('@@') || line.startsWith('diff ') || line.startsWith('---') || line.startsWith('+++')) {
        return `<span class="d-meta">${escaped}</span>`;
      }
      return `<span>${escaped}</span>`;
    }).join('\n');
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // --- Visual Score Meter Generator ---
  function renderScoreMeter(score) {
    const clamped = Math.max(0, Math.min(10, score));
    const filled = Math.round(clamped);
    const empty = 10 - filled;
    let colorClass = 't-red';
    if (clamped >= 7.5) colorClass = 't-green';
    else if (clamped >= 5.0) colorClass = 't-amber';

    const bar = `[${'='.repeat(filled)}${'.'.repeat(empty)}]`;
    return `<span class="${colorClass} t-bold">${bar}</span> <span class="t-bold">${score.toFixed(1)}/10.0</span>`;
  }

  // --- Judgment Report HTML Builder ---
  function buildJudgmentReport(scenario, roastLevel) {
    const roast = scenario.roasts[roastLevel] || scenario.roasts.spicy;
    const isApproved = scenario.badge === 'APPROVED' || scenario.score >= 7.5;

    let html = '';
    // Header
    html += `<div class="t-bold">⚖️  GIT-GUD AI (Pre-Commit Judge &amp; Jury) <span class="t-gray">[Model: phi3 | Roast: ${roastLevel.toUpperCase()}]</span></div>`;
    html += `<div class="t-gray">--------------------------------------------------------------------------------</div>\n`;

    // Roast Box
    html += `<div class="t-magenta" style="border: 1px solid #c084fc; border-radius: 6px; padding: 0.75rem 1rem; margin: 0.75rem 0; background: rgba(192, 132, 252, 0.05);">`;
    html += `  <div class="t-bold t-amber" style="margin-bottom: 0.35rem;">🔥 THE JUDGE'S ROAST:</div>`;
    html += `  <div class="t-italic" style="color: #f1f5f9; line-height: 1.55;">"${escapeHtml(roast)}"</div>`;
    html += `</div>\n`;

    // Health Score
    html += `<div style="margin: 0.75rem 0;"><span class="t-bold">Code Health Score:</span> ${renderScoreMeter(scenario.score)}</div>\n`;

    // Issues
    if (scenario.issues && scenario.issues.length > 0) {
      html += `<div class="t-bold" style="margin-top: 1rem;">📋 DEFECTS &amp; REQUIRED ACTION (${scenario.issues.length}):</div>`;
      scenario.issues.forEach((iss, idx) => {
        let badge = `<span class="t-red t-bold">[HIGH CRITICAL]</span>`;
        if (iss.severity === 'MED') badge = `<span class="t-amber t-bold">[MED SMELL]</span>`;
        else if (iss.severity === 'LOW') badge = `<span class="t-cyan t-bold">[LOW NITPICK]</span>`;

        html += `<div style="margin: 0.65rem 0 0.65rem 1rem;">`;
        html += `  <div><span class="t-bold">${idx + 1}.</span> ${badge} <span class="t-cyan t-bold">${escapeHtml(iss.file)}:${iss.line}</span></div>`;
        html += `  <div style="margin-left: 1.5rem;"><span class="t-gray">Problem:</span> ${escapeHtml(iss.problem)}</div>`;
        html += `  <div style="margin-left: 1.5rem;"><span class="t-green t-bold">Fix:</span>     ${escapeHtml(iss.fix)}</div>`;
        html += `</div>`;
      });
    } else {
      html += `<div class="t-green" style="margin: 0.75rem 0;">✨ No technical defects detected. Pure craftsmanship.</div>`;
    }

    // Verdict Banner
    html += `\n<div class="t-gray">================================================================================</div>`;
    if (isApproved) {
      html += `<div class="t-green t-bold" style="font-size: 1rem; padding: 0.35rem 0;">  ⚖️  COMMIT APPROVED: PROCEED WITH CAUTION</div>`;
    } else {
      html += `<div class="t-red t-bold" style="font-size: 1rem; padding: 0.35rem 0;">  🚫 COMMIT REJECTED: GIT GUD OR GET OUT</div>`;
      html += `<div class="t-gray" style="font-size: 0.78rem;">(Bypass via: \`git commit --no-verify\` or \`GITGUD_SKIP=1 git commit\`)</div>`;
    }
    html += `<div class="t-gray">================================================================================</div>`;

    return html;
  }

  // --- Typing Simulation Engine ---
  function typeTextToTerminal(targetElement, fullHtml, onComplete) {
    if (state.reducedMotion || state.skipAnimation) {
      targetElement.innerHTML = fullHtml;
      if (onComplete) onComplete();
      return;
    }

    // Clear previous timeout
    if (state.typingTimeoutId) {
      clearTimeout(state.typingTimeoutId);
      state.typingTimeoutId = null;
    }

    state.isTyping = true;
    targetElement.innerHTML = `<span class="t-cyan">⠋</span> <span class="t-bold">Git-Gud AI is reviewing staged changes with Ollama...</span><span class="terminal-cursor"></span>`;

    // Brief realistic spinner delay (400ms)
    state.typingTimeoutId = setTimeout(() => {
      // Chunk-based typing for performance & authentic feel
      targetElement.innerHTML = '';
      const chunks = fullHtml.split(/(<div[^>]*>|<\/div>|<span[^>]*>|<\/span>|<br>|\n)/g).filter(Boolean);
      let idx = 0;
      let buffer = '';

      function step() {
        if (!state.isTyping) return;
        if (state.skipAnimation) {
          targetElement.innerHTML = fullHtml;
          state.isTyping = false;
          if (onComplete) onComplete();
          return;
        }

        if (idx < chunks.length) {
          buffer += chunks[idx];
          targetElement.innerHTML = buffer + '<span class="terminal-cursor"></span>';
          targetElement.scrollTop = targetElement.scrollHeight;
          idx++;
          state.typingTimeoutId = setTimeout(step, 18);
        } else {
          targetElement.innerHTML = fullHtml;
          state.isTyping = false;
          if (onComplete) onComplete();
        }
      }
      step();
    }, 450);
  }

  // --- Interactive Demo Controller ---
  function initDemo() {
    const diffContainer = document.getElementById('demo-diff-content');
    const outputContainer = document.getElementById('demo-terminal-output');
    const skipBtn = document.getElementById('demo-skip-animation-btn');
    const terminalInput = document.getElementById('demo-terminal-input');

    if (!diffContainer || !outputContainer) return;

    function loadScenario(scenarioId, roastLevel) {
      const scenario = SCENARIOS.find(s => s.id === scenarioId) || SCENARIOS[0];
      diffContainer.innerHTML = renderDiff(scenario.diff);
      const reportHtml = buildJudgmentReport(scenario, roastLevel);
      typeTextToTerminal(outputContainer, reportHtml);
    }

    // Scenario Pill Clicks
    const pills = document.querySelectorAll('.scenario-pill');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        pills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.currentScenarioId = pill.getAttribute('data-scenario');
        loadScenario(state.currentScenarioId, state.currentRoastLevel);
      });
    });

    // Roast Level Toggle Clicks
    const roastBtns = document.querySelectorAll('.roast-level-btn');
    roastBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        roastBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.currentRoastLevel = btn.getAttribute('data-level');
        loadScenario(state.currentScenarioId, state.currentRoastLevel);
      });
    });

    // Skip Animation Button
    if (skipBtn) {
      skipBtn.addEventListener('click', () => {
        state.skipAnimation = true;
        const scenario = SCENARIOS.find(s => s.id === state.currentScenarioId) || SCENARIOS[0];
        outputContainer.innerHTML = buildJudgmentReport(scenario, state.currentRoastLevel);
        state.isTyping = false;
        setTimeout(() => { state.skipAnimation = false; }, 300);
      });
    }

    // Terminal Input (Easter Egg trigger: type "git gud")
    if (terminalInput) {
      terminalInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const val = terminalInput.value.trim().toLowerCase();
          if (val === 'git gud' || val === 'git-gud') {
            diffContainer.innerHTML = renderDiff(EASTER_EGG_SCENARIO.diff);
            const reportHtml = buildJudgmentReport(EASTER_EGG_SCENARIO, 'savage');
            typeTextToTerminal(outputContainer, reportHtml);
            terminalInput.value = '';
          } else if (val === 'clear' || val === 'cls') {
            outputContainer.innerHTML = '<span class="t-gray">Terminal output cleared. Select a scenario above to test.</span>';
            terminalInput.value = '';
          } else {
            terminalInput.value = '';
            // Run default
            loadScenario(state.currentScenarioId, state.currentRoastLevel);
          }
        }
      });
    }

    // Initial load
    loadScenario(state.currentScenarioId, state.currentRoastLevel);
  }

  // --- Hero Section Animated Terminal ---
  function initHeroTerminal() {
    const heroOutput = document.getElementById('hero-terminal-body');
    const heroSkipBtn = document.getElementById('hero-skip-btn');
    if (!heroOutput) return;

    const heroScript = [
      `<span class="t-gray">$</span> <span class="t-green">git add</span> services/payment.py`,
      `<span class="t-gray">$</span> <span class="t-green">git commit</span> -m <span class="t-cyan">"feat: hotfix payment timeout"</span>`,
      `\n<span class="t-cyan">⠋</span> <span class="t-bold">Git-Gud AI is reviewing staged changes with Ollama (model: phi3)...</span>`,
      `\n<div class="t-bold">⚖️  GIT-GUD AI (Pre-Commit Judge &amp; Jury) [Model: phi3]</div>`,
      `<div class="t-gray">--------------------------------------------------------------------------------</div>`,
      `<div class="t-magenta" style="border: 1px solid #c084fc; border-radius: 4px; padding: 0.6rem; margin: 0.5rem 0; background: rgba(192, 132, 252, 0.05);">`,
      `  <div class="t-bold t-amber">🔥 THE JUDGE'S ROAST:</div>`,
      `  <div class="t-italic" style="color: #f1f5f9;">"A bare except block that silently swallows KeyboardInterrupt and returns null? Did you write this during an earthquake or are you actively trying to make debugging an extreme sport? Also, hardcoding production credentials in 2026 is a bold career move."</div>`,
      `</div>`,
      `<div><span class="t-bold">Code Health Score:</span> <span class="t-red t-bold">[===.......]</span> <span class="t-bold">3.2/10.0</span></div>`,
      `\n<div class="t-bold">📋 DEFECTS &amp; REQUIRED ACTION:</div>`,
      `  <span class="t-bold">1.</span> <span class="t-red t-bold">[HIGH CRITICAL]</span> <span class="t-cyan">services/payment.py:88</span>`,
      `     <span class="t-gray">Problem:</span> Bare except silently swallowing all exceptions including system signals.`,
      `     <span class="t-green t-bold">Fix:</span>     Catch specific exceptions: \`except (PaymentGatewayError, NetworkTimeout):\``,
      `  <span class="t-bold">2.</span> <span class="t-red t-bold">[HIGH CRITICAL]</span> <span class="t-cyan">services/payment.py:95</span>`,
      `     <span class="t-gray">Problem:</span> Hardcoded production API secret key committed to source control.`,
      `     <span class="t-green t-bold">Fix:</span>     Load credentials from os.environ or an external secret vault.`,
      `\n<div class="t-gray">================================================================================</div>`,
      `<div class="t-red t-bold">  🚫 COMMIT REJECTED: GIT GUD OR GET OUT</div>`,
      `<div class="t-gray">================================================================================</div>`,
      `<div class="t-gray" style="font-size: 0.78rem;">(Bypass via: \`git commit --no-verify\` or \`GITGUD_SKIP=1 git commit\`)</div>`
    ].join('\n');

    if (state.reducedMotion) {
      heroOutput.innerHTML = heroScript;
      return;
    }

    let isHeroSkipped = false;
    if (heroSkipBtn) {
      heroSkipBtn.addEventListener('click', () => {
        isHeroSkipped = true;
        heroOutput.innerHTML = heroScript;
      });
    }

    // Step typing for hero
    let currentLine = 0;
    const lines = [
      `<span class="t-gray">$</span> <span class="t-green">git add</span> services/payment.py`,
      `<span class="t-gray">$</span> <span class="t-green">git commit</span> -m <span class="t-cyan">"feat: hotfix payment timeout"</span>`,
      `<span class="t-cyan">⠋</span> <span class="t-bold">Git-Gud AI is reviewing staged changes with Ollama (model: phi3)...</span>`
    ];

    heroOutput.innerHTML = lines[0] + '<span class="terminal-cursor"></span>';

    setTimeout(() => {
      if (isHeroSkipped) return;
      heroOutput.innerHTML = lines[0] + '\n' + lines[1] + '<span class="terminal-cursor"></span>';

      setTimeout(() => {
        if (isHeroSkipped) return;
        heroOutput.innerHTML = lines[0] + '\n' + lines[1] + '\n' + lines[2] + '<span class="terminal-cursor"></span>';

        setTimeout(() => {
          if (isHeroSkipped) return;
          heroOutput.innerHTML = heroScript;
        }, 600);
      }, 500);
    }, 400);
  }

  // --- Installation Tabs Controller ---
  function initInstallTabs() {
    const tabBtns = document.querySelectorAll('.install-tab-btn');
    const tabPanes = document.querySelectorAll('.install-tab-pane');

    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-tab');
        tabBtns.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add('active');
      });
    });
  }

  // --- Copy to Clipboard Controller ---
  function initCopyButtons() {
    const copyBtns = document.querySelectorAll('.copy-btn');
    copyBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const textToCopy = btn.getAttribute('data-copy') || 
          (targetId ? document.getElementById(targetId)?.innerText : '');

        if (!textToCopy) return;

        navigator.clipboard.writeText(textToCopy).then(() => {
          const originalText = btn.innerHTML;
          btn.innerHTML = '✓ Copied!';
          btn.classList.add('copied');
          setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('copied');
          }, 2000);
        }).catch(err => {
          console.error('Failed to copy: ', err);
        });
      });
    });
  }

  // --- FAQ Accordion Controller ---
  function initFaqAccordion() {
    const questions = document.querySelectorAll('.faq-question');
    questions.forEach(btn => {
      btn.addEventListener('click', () => {
        const item = btn.closest('.faq-item');
        const isActive = item.classList.contains('active');

        // Optional: close other accordions
        document.querySelectorAll('.faq-item').forEach(other => {
          if (other !== item) other.classList.remove('active');
        });

        if (isActive) {
          item.classList.remove('active');
          btn.setAttribute('aria-expanded', 'false');
        } else {
          item.classList.add('active');
          btn.setAttribute('aria-expanded', 'true');
        }
      });
    });
  }

  // --- Sticky Quick-Install Bar Controller ---
  function initStickyBar() {
    const stickyBar = document.getElementById('sticky-install-bar');
    const heroSection = document.getElementById('hero');
    if (!stickyBar || !heroSection) return;

    window.addEventListener('scroll', () => {
      const heroBottom = heroSection.getBoundingClientRect().bottom;
      if (heroBottom < 0) {
        stickyBar.classList.add('visible');
      } else {
        stickyBar.classList.remove('visible');
      }
    }, { passive: true });
  }

  // --- Keyboard Shortcuts & Accessibility ---
  function initKeyboard() {
    window.addEventListener('keydown', (e) => {
      // Toggle theme on Ctrl + Alt + T
      if (e.ctrlKey && e.altKey && (e.key === 't' || e.key === 'T')) {
        document.getElementById('theme-toggle-btn')?.click();
      }
    });
  }

  // --- Mobile Menu Toggle ---
  function initMobileMenu() {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const navLinks = document.getElementById('nav-links');
    if (!menuBtn || !navLinks) return;

    menuBtn.addEventListener('click', () => {
      const isVisible = navLinks.style.display === 'flex';
      navLinks.style.display = isVisible ? 'none' : 'flex';
      navLinks.style.flexDirection = 'column';
      navLinks.style.position = 'absolute';
      navLinks.style.top = '68px';
      navLinks.style.left = '0';
      navLinks.style.right = '0';
      navLinks.style.background = 'var(--bg-secondary)';
      navLinks.style.padding = '1.5rem';
      navLinks.style.borderBottom = '1px solid var(--border-subtle)';
    });
  }

  // --- Master Initialization ---
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initHeroTerminal();
    initDemo();
    initInstallTabs();
    initCopyButtons();
    initFaqAccordion();
    initStickyBar();
    initKeyboard();
    initMobileMenu();
  });

})();
