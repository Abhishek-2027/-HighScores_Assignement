"""
Item Response Theory (IRT) — 1-Parameter Logistic Model (1PL / Rasch Model)

The 1PL model calculates the probability that a student with ability θ will
answer correctly a question with difficulty b:

    P(correct | θ, b) = 1 / (1 + exp(-(θ - b)))

After each response, we update ability via gradient ascent on the log-likelihood:

    θ_new = θ_old + α * (response - P(correct | θ, b))

where:
    α       = learning rate (controls update magnitude)
    response = 1 if correct, 0 if incorrect
    P(...)  = estimated probability of correct answer

References:
    Rasch, G. (1960). Probabilistic Models for Some Intelligence and Attainment Tests.
    van der Linden, W. J. (2016). Handbook of Item Response Theory.
"""

import math


def irt_probability(ability: float, difficulty: float) -> float:
    """
    Calculate P(correct) using the 1PL logistic model.

    Args:
        ability:    Student ability score θ ∈ [0, 1]
        difficulty: Question difficulty b ∈ [0.1, 1.0]

    Returns:
        Probability of correct response ∈ (0, 1)
    """
    # Rescale from [0,1] to logit space [-4, 4] for numerical stability
    theta = (ability - 0.5) * 8
    beta = (difficulty - 0.5) * 8
    return 1.0 / (1.0 + math.exp(-(theta - beta)))


def update_ability(
    ability: float,
    difficulty: float,
    is_correct: bool,
    learning_rate: float = 0.3,
) -> float:
    """
    Update ability score using IRT gradient ascent.

    Args:
        ability:       Current ability estimate θ
        difficulty:    Question difficulty b
        is_correct:    Whether the student answered correctly
        learning_rate: Step size α for the update

    Returns:
        Updated ability score, clamped to [0.05, 0.95]
    """
    response = 1.0 if is_correct else 0.0
    p = irt_probability(ability, difficulty)
    delta = learning_rate * (response - p)
    new_ability = ability + delta
    return max(0.05, min(0.95, new_ability))


def information_function(ability: float, difficulty: float) -> float:
    """
    Fisher information — measures how much info a question gives about ability.
    Higher info = question is better calibrated to student's level.

    I(θ) = P(θ) * (1 - P(θ))
    """
    p = irt_probability(ability, difficulty)
    return p * (1.0 - p)


def optimal_difficulty_for_ability(ability: float) -> float:
    """
    The question difficulty that maximizes Fisher information is the one
    that matches the student's ability (P = 0.5, i.e., difficulty = ability).
    Returns the target difficulty to use when selecting next question.
    """
    return ability


def difficulty_band(ability: float, tolerance: float = 0.15) -> tuple[float, float]:
    """
    Returns (min_difficulty, max_difficulty) band centered on ability.
    Used to find questions near the student's current level.
    """
    lower = max(0.1, ability - tolerance)
    upper = min(1.0, ability + tolerance)
    return lower, upper
