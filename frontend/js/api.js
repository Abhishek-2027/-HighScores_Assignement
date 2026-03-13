/**
 * api.js — All HTTP calls to the FastAPI backend.
 * Uses the native fetch API. No external dependencies.
 */

const BASE_URL = "http://localhost:8000/api/v1";

/**
 * Central fetch wrapper with error normalisation.
 * @param {string} path
 * @param {RequestInit} options
 * @returns {Promise<any>}
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };
  const res = await fetch(url, config);
  const data = await res.json();
  if (!res.ok) {
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// ── Session ──────────────────────────────────────────────────────────────────

/**
 * Start a new adaptive test session.
 * @param {string} userId
 * @returns {Promise<{session_id, user_id, ability_score, questions_answered, is_complete}>}
 */
function startSession(userId) {
  return request("/sessions/start", {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

/**
 * Get current session state.
 * @param {string} sessionId
 */
function getSession(sessionId) {
  return request(`/sessions/${sessionId}`);
}

// ── Questions ─────────────────────────────────────────────────────────────────

/**
 * Fetch the next adaptive question for a session.
 * @param {string} sessionId
 * @returns {Promise<{question_id, question, options, topic, difficulty, question_number, total_questions, ability_score}>}
 */
function getNextQuestion(sessionId) {
  return request(`/sessions/${sessionId}/question`);
}

/**
 * Submit an answer for a question.
 * @param {string} sessionId
 * @param {string} questionId
 * @param {string} answer
 * @returns {Promise<{correct, correct_answer, ability_score, question_number, is_test_complete, session_id}>}
 */
function submitAnswer(sessionId, questionId, answer) {
  return request(`/sessions/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      question_id: questionId,
      answer: answer,
    }),
  });
}

// ── Study Plan ────────────────────────────────────────────────────────────────

/**
 * Request Gemini AI study plan generation.
 * Session must be complete (10 questions answered).
 * @param {string} sessionId
 */
function generateStudyPlan(sessionId) {
  return request(`/sessions/${sessionId}/plan`, { method: "POST" });
}

// ── Seed (Dev Only) ───────────────────────────────────────────────────────────

/**
 * Seed MongoDB with 25 GRE questions. Run once.
 */
function seedDatabase() {
  return request("/seed", { method: "POST" });
}
