/**
 * state.js — Centralised application state.
 *
 * No framework needed: a plain object + subscriber pattern.
 * All UI reads from State.get(), all mutations call State.update().
 */

const State = (() => {
  /** @type {AppState} */
  const _state = {
    phase: "home",          // "home" | "testing" | "feedback" | "plan"
    sessionId: null,
    userId: null,
    abilityScore: 0.5,
    questionsAnswered: 0,
    isComplete: false,
    currentQuestion: null,  // question object from API
    lastFeedback: null,     // feedback object from API
    studyPlan: null,        // full plan response from API
    loading: false,
    error: null,
  };

  /** @type {Array<(state: AppState) => void>} */
  const _subscribers = [];

  /** Notify all subscribers after a state change. */
  function _notify() {
    _subscribers.forEach((fn) => fn({ ..._state }));
  }

  return {
    /** Read a snapshot of current state. */
    get() {
      return { ..._state };
    },

    /**
     * Merge partial updates into state and notify subscribers.
     * @param {Partial<AppState>} patch
     */
    update(patch) {
      Object.assign(_state, patch);
      _notify();
    },

    /**
     * Subscribe to state changes.
     * @param {(state: AppState) => void} fn
     */
    subscribe(fn) {
      _subscribers.push(fn);
    },

    /** Hard reset to initial values. */
    reset() {
      Object.assign(_state, {
        phase: "home",
        sessionId: null,
        userId: null,
        abilityScore: 0.5,
        questionsAnswered: 0,
        isComplete: false,
        currentQuestion: null,
        lastFeedback: null,
        studyPlan: null,
        loading: false,
        error: null,
      });
      _notify();
    },
  };
})();
