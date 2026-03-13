/**
 * ui.js — All DOM manipulation lives here.
 *
 * Single entry point: UI.render(state) is called whenever state changes.
 * Helper functions update individual sections.
 * No logic here — only presentation.
 */

const UI = (() => {
  // ── Element cache ──────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  const pages = {
    home:    $("page-home"),
    test:    $("page-test"),
    plan:    $("page-plan"),
  };

  const PHASE_TO_PAGE = {
    home:     "home",
    testing:  "test",
    feedback: "test",
    plan:     "plan",
  };

  const LETTERS = ["A", "B", "C", "D"];

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Main render function. Called on every state change.
   * @param {AppState} state
   */
  function render(state) {
    _showPage(PHASE_TO_PAGE[state.phase] || "home");

    if (state.phase === "home") return; // home page is static HTML

    if (state.phase === "testing" || state.phase === "feedback") {
      _renderTestPage(state);
    }

    if (state.phase === "plan") {
      _renderPlanPage(state);
    }
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  /** Show a named page, hide others. */
  function _showPage(name) {
    Object.entries(pages).forEach(([key, el]) => {
      el.classList.toggle("active", key === name);
    });
  }

  /** Update the test page (question + feedback states). */
  function _renderTestPage(state) {
    const {
      phase, loading, error, currentQuestion, lastFeedback,
      abilityScore, questionsAnswered,
    } = state;

    // Counter & progress
    $("test-counter").textContent = `${questionsAnswered} / 10`;
    $("progress-label").textContent = `${questionsAnswered} / 10 questions`;
    $("progress-bar").style.width = `${(questionsAnswered / 10) * 100}%`;

    // Ability meter
    _renderAbility(abilityScore);

    // Error
    const errEl = $("test-error");
    if (error) {
      errEl.textContent = `⚠️ ${error}`;
      errEl.classList.remove("hidden");
    } else {
      errEl.classList.add("hidden");
    }

    // Loading spinner
    _toggle("test-loading", loading && !currentQuestion);

    // Question card
    _toggle("question-card", !loading && !!currentQuestion && phase === "testing");
    if (!loading && currentQuestion && phase === "testing") {
      _renderQuestion(currentQuestion);
    }

    // Feedback card
    _toggle("feedback-card", phase === "feedback" && !!lastFeedback);
    if (phase === "feedback" && lastFeedback) {
      _renderFeedback(lastFeedback);
    }
  }

  /** Update the ability score display. */
  function _renderAbility(score) {
    const pct = Math.round(score * 100);
    const { label, cls, color } = _abilityMeta(score);

    $("ability-pct").textContent = `${pct}%`;
    $("ability-bar").style.width = `${pct}%`;
    $("ability-bar").style.background = color;
    $("ability-raw").textContent = `${score.toFixed(3)} θ`;

    const lvlEl = $("ability-level");
    lvlEl.textContent = label;
    lvlEl.className = `ability-level ${cls}`;
  }

  /** Render question card content. */
  function _renderQuestion(q) {
    $("q-topic").textContent = q.topic;

    const tier = q.difficulty <= 0.4 ? "easy" : q.difficulty <= 0.65 ? "medium" : "hard";
    const diffEl = $("q-difficulty");
    diffEl.textContent = tier.charAt(0).toUpperCase() + tier.slice(1);
    diffEl.className = `diff-badge ${tier}`;

    $("q-text").textContent = q.question;

    // Options
    const list = $("options-list");
    list.innerHTML = "";
    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.dataset.index = i;
      btn.innerHTML = `
        <span class="option-letter">${LETTERS[i]}</span>
        <span>${opt}</span>
      `;
      btn.addEventListener("click", () => _selectOption(i, q.options.length));
      list.appendChild(btn);
    });

    // Disable submit until selection
    $("btn-submit").disabled = true;
  }

  /** Highlight selected option, enable submit. */
  function _selectOption(selectedIndex, count) {
    const btns = document.querySelectorAll(".option-btn");
    btns.forEach((btn, i) => {
      btn.classList.toggle("selected", i === selectedIndex);
    });
    $("btn-submit").disabled = false;
    $("btn-submit").dataset.selectedIndex = selectedIndex;
  }

  /** Render feedback after answer submission. */
  function _renderFeedback(fb) {
    const card = $("feedback-card");
    card.className = `feedback-card ${fb.correct ? "correct" : "incorrect"}`;

    $("feedback-icon").textContent = fb.correct ? "✅" : "❌";
    $("feedback-title").textContent = fb.correct ? "Correct!" : "Incorrect";

    const ansEl = $("feedback-correct-answer");
    if (!fb.correct) {
      ansEl.innerHTML = `Correct answer: <strong>${fb.correct_answer}</strong>`;
      ansEl.classList.remove("hidden");
    } else {
      ansEl.classList.add("hidden");
    }

    $("feedback-ability").innerHTML =
      `Ability updated to <span>${(fb.ability_score * 100).toFixed(1)}%</span>`;
    $("feedback-qnum").textContent =
      `Question ${fb.question_number} of 10 complete`;

    _toggle("btn-next", !fb.is_test_complete);
    _toggle("btn-plan", fb.is_test_complete);
  }

  /** Render the study plan page. */
  function _renderPlanPage(state) {
    const { studyPlan, loading } = state;

    _toggle("plan-loading", loading);

    if (!studyPlan) return;

    const { performance, study_plan, summary } = studyPlan;

    $("plan-summary").textContent = summary;

    // Stats grid
    const statsData = [
      { emoji: "🎯", value: `${(performance.accuracy_rate * 100).toFixed(0)}%`, label: "Accuracy" },
      { emoji: "✅", value: `${performance.correct_answers}/${performance.total_questions}`, label: "Correct" },
      { emoji: "📈", value: `${(performance.max_ability_reached * 100).toFixed(0)}%`, label: "Peak Ability" },
      { emoji: "⚡", value: `${(performance.final_ability * 100).toFixed(0)}%`, label: "Final Ability" },
    ];
    $("stats-grid").innerHTML = statsData.map((s) => `
      <div class="stat-card">
        <span class="stat-emoji">${s.emoji}</span>
        <span class="stat-value">${s.value}</span>
        <span class="stat-label">${s.label}</span>
      </div>
    `).join("");

    // Topic breakdown
    let topicHTML = "";
    if (performance.weak_topics.length) {
      topicHTML += `
        <div class="topic-card weak">
          <h3>⚠️ Needs Work</h3>
          <ul>${performance.weak_topics.map((t) => `<li>• ${t}</li>`).join("")}</ul>
        </div>`;
    }
    if (performance.strong_topics.length) {
      topicHTML += `
        <div class="topic-card strong">
          <h3>💪 Strong Areas</h3>
          <ul>${performance.strong_topics.map((t) => `<li>• ${t}</li>`).join("")}</ul>
        </div>`;
    }
    $("topic-grid").innerHTML = topicHTML;

    // Study plan steps
    const stepColors = ["s1", "s2", "s3"];
    $("steps-list").innerHTML = study_plan.map((step, i) => `
      <div class="step-card">
        <div class="step-number ${stepColors[i % 3]}">${step.step}</div>
        <div class="step-body">
          <div class="step-title">${step.title}</div>
          <div class="step-desc">${step.description}</div>
          <div class="step-resources">
            ${step.resources.map((r) => `<div class="step-resource">${r}</div>`).join("")}
          </div>
        </div>
      </div>
    `).join("");
  }

  // ── Utility helpers ────────────────────────────────────────────────────────

  function _toggle(id, visible) {
    $(id).classList.toggle("hidden", !visible);
  }

  function _abilityMeta(score) {
    if (score < 0.35) return { label: "Beginner",   cls: "beginner",   color: "#f43f5e" };
    if (score < 0.55) return { label: "Developing",  cls: "developing",  color: "#f59e0b" };
    if (score < 0.75) return { label: "Proficient",  cls: "proficient",  color: "#10b981" };
    return               { label: "Advanced",    cls: "advanced",    color: "#818cf8" };
  }

  return { render };
})();
