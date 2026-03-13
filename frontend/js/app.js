/**
 * app.js — Event handlers & controller logic.
 *
 * Wires DOM events → API calls → State updates.
 * State changes automatically trigger UI.render() via subscription.
 */

// ── Subscribe UI to state ─────────────────────────────────────────────────────
State.subscribe(UI.render);

// ── DOM ready ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {

  // Render initial state (shows home page)
  UI.render(State.get());

  // ── Home: Start session ──────────────────────────────────────────────────
  document.getElementById("form-start").addEventListener("submit", async (e) => {
    e.preventDefault();
    const userId = document.getElementById("input-userid").value.trim();
    if (!userId) return;

    State.update({ loading: true, error: null });

    try {
      const data = await startSession(userId);
      State.update({
        sessionId: data.session_id,
        userId: data.user_id,
        abilityScore: data.ability_score,
        questionsAnswered: 0,
        isComplete: false,
        loading: false,
        phase: "testing",
      });
      // Immediately load first question
      await loadNextQuestion();
    } catch (err) {
      State.update({ loading: false, error: err.message });
    }
  });

  // ── Home: Seed database ──────────────────────────────────────────────────
  document.getElementById("btn-seed").addEventListener("click", async () => {
    const btn = document.getElementById("btn-seed");
    const msg = document.getElementById("seed-msg");
    btn.disabled = true;
    btn.textContent = "Seeding...";
    msg.classList.add("hidden");

    try {
      const res = await seedDatabase();
      msg.textContent = res.message;
      msg.style.color = "var(--emerald)";
    } catch (err) {
      msg.textContent = `Failed: ${err.message}`;
      msg.style.color = "var(--rose)";
    } finally {
      msg.classList.remove("hidden");
      btn.disabled = false;
      btn.textContent = "🌱 Seed Database (first-time setup)";
    }
  });

  // ── Test: Submit answer ───────────────────────────────────────────────────
  document.getElementById("btn-submit").addEventListener("click", async () => {
    const btn = document.getElementById("btn-submit");
    const selectedIndex = parseInt(btn.dataset.selectedIndex, 10);
    if (isNaN(selectedIndex)) return;

    const { sessionId, currentQuestion } = State.get();
    const selectedAnswer = currentQuestion.options[selectedIndex];

    State.update({ loading: true, error: null });

    try {
      const feedback = await submitAnswer(sessionId, currentQuestion.question_id, selectedAnswer);
      State.update({
        loading: false,
        lastFeedback: feedback,
        abilityScore: feedback.ability_score,
        questionsAnswered: feedback.question_number,
        isComplete: feedback.is_test_complete,
        phase: "feedback",
      });
    } catch (err) {
      State.update({ loading: false, error: err.message });
    }
  });

  // ── Test: Next question ───────────────────────────────────────────────────
  document.getElementById("btn-next").addEventListener("click", async () => {
    await loadNextQuestion();
  });

  // ── Test: Generate plan ───────────────────────────────────────────────────
  document.getElementById("btn-plan").addEventListener("click", async () => {
    State.update({ phase: "plan", loading: true, error: null });

    const { sessionId } = State.get();
    try {
      const planData = await generateStudyPlan(sessionId);
      State.update({ loading: false, studyPlan: planData });
    } catch (err) {
      State.update({ loading: false, error: err.message });
    }
  });

  // ── Plan: Restart ─────────────────────────────────────────────────────────
  document.getElementById("btn-restart").addEventListener("click", () => {
    document.getElementById("input-userid").value = "";
    State.reset();
  });

});

// ── Shared controller helpers ─────────────────────────────────────────────────

/**
 * Fetch the next question and update state.
 */
async function loadNextQuestion() {
  const { sessionId } = State.get();
  State.update({ loading: true, error: null, currentQuestion: null, phase: "testing" });

  try {
    const question = await getNextQuestion(sessionId);
    State.update({ loading: false, currentQuestion: question });
  } catch (err) {
    State.update({ loading: false, error: err.message });
  }
}
