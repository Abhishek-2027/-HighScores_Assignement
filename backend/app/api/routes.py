"""
API Routes — all endpoints for the adaptive testing system.

Endpoints:
    POST /sessions/start          — start a new test session
    GET  /sessions/{id}           — get session info
    GET  /sessions/{id}/question  — get next adaptive question
    POST /sessions/{id}/answer    — submit an answer
    POST /sessions/{id}/plan      — generate AI study plan
    POST /seed                    — seed DB with GRE questions (dev only)
"""

import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.database.mongodb import get_db
from app.models.session_model import AnswerRecord, UserSessionModel
from app.schemas.schemas import (
    AnswerFeedbackResponse,
    QuestionResponse,
    SessionResponse,
    StartSessionRequest,
    StudyPlanResponse,
    PerformanceAnalysis,
    SubmitAnswerRequest,
)
from app.services.adaptive_engine import AdaptiveEngine
from app.services.gemini_service import GeminiService
from app.utils.irt import update_ability

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ── Session Management ────────────────────────────────────────────────────────

@router.post("/sessions/start", response_model=SessionResponse, status_code=201)
async def start_session(
    body: StartSessionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a new adaptive testing session for a user."""
    session = UserSessionModel(
        user_id=body.user_id,
        ability_score=settings.BASELINE_ABILITY,
    )
    result = await db["user_sessions"].insert_one(
        session.model_dump(by_alias=True, exclude={"id"})
    )
    return SessionResponse(
        session_id=str(result.inserted_id),
        user_id=body.user_id,
        ability_score=session.ability_score,
        questions_answered=0,
        is_complete=False,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Retrieve current session state."""
    doc = await db["user_sessions"].find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        session_id=str(doc["_id"]),
        user_id=doc["user_id"],
        ability_score=doc["ability_score"],
        questions_answered=doc["questions_answered"],
        is_complete=doc["is_complete"],
    )


# ── Adaptive Question Selection ───────────────────────────────────────────────

@router.get("/sessions/{session_id}/question", response_model=QuestionResponse)
async def get_next_question(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Select the next question using Maximum Fisher Information.
    Returns 404 if session is complete or no questions available.
    """
    doc = await db["user_sessions"].find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if doc["is_complete"]:
        raise HTTPException(status_code=400, detail="Test already completed")
    if doc["questions_answered"] >= settings.MAX_QUESTIONS:
        raise HTTPException(status_code=400, detail="Maximum questions reached")

    engine = AdaptiveEngine(db)
    question = await engine.get_next_question(
        ability=doc["ability_score"],
        asked_ids=doc.get("asked_question_ids", []),
    )
    if not question:
        raise HTTPException(status_code=404, detail="No suitable questions found")

    return QuestionResponse(
        question_id=str(question.id),
        question=question.question,
        options=question.options,
        topic=question.topic,
        difficulty=question.difficulty,
        question_number=doc["questions_answered"] + 1,
        total_questions=settings.MAX_QUESTIONS,
        ability_score=doc["ability_score"],
    )


# ── Answer Submission ─────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/answer", response_model=AnswerFeedbackResponse)
async def submit_answer(
    session_id: str,
    body: SubmitAnswerRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Process a submitted answer, update IRT ability score, and save to session.
    """
    # Validate session
    session_doc = await db["user_sessions"].find_one({"_id": ObjectId(session_id)})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_doc["is_complete"]:
        raise HTTPException(status_code=400, detail="Test already completed")

    # Validate question
    question_doc = await db["questions"].find_one({"_id": ObjectId(body.question_id)})
    if not question_doc:
        raise HTTPException(status_code=404, detail="Question not found")

    # Score the answer
    is_correct = body.answer.strip().lower() == question_doc["correct_answer"].strip().lower()

    # IRT ability update
    old_ability = session_doc["ability_score"]
    new_ability = update_ability(
        ability=old_ability,
        difficulty=question_doc["difficulty"],
        is_correct=is_correct,
        learning_rate=settings.LEARNING_RATE,
    )

    # Build answer record
    record = AnswerRecord(
        question_id=body.question_id,
        topic=question_doc["topic"],
        difficulty=question_doc["difficulty"],
        correct=is_correct,
        ability_before=old_ability,
        ability_after=new_ability,
    )

    new_count = session_doc["questions_answered"] + 1
    is_complete = new_count >= settings.MAX_QUESTIONS

    # Persist update
    await db["user_sessions"].update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "ability_score": new_ability,
                "questions_answered": new_count,
                "is_complete": is_complete,
                "updated_at": datetime.utcnow(),
            },
            "$push": {
                "history": record.model_dump(),
                "asked_question_ids": body.question_id,
            },
        },
    )

    return AnswerFeedbackResponse(
        correct=is_correct,
        correct_answer=question_doc["correct_answer"],
        ability_score=new_ability,
        question_number=new_count,
        is_test_complete=is_complete,
        session_id=session_id,
    )


# ── AI Study Plan Generation ──────────────────────────────────────────────────

@router.post("/sessions/{session_id}/plan", response_model=StudyPlanResponse)
async def generate_study_plan(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Analyze session history and call Gemini to generate a personalized study plan.
    Session must be complete (10 questions answered).
    """
    doc = await db["user_sessions"].find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if not doc["is_complete"]:
        raise HTTPException(
            status_code=400,
            detail="Complete the test before generating a study plan",
        )

    history = doc.get("history", [])
    correct_count = sum(1 for h in history if h["correct"])
    all_topics = list({h["topic"] for h in history})

    # Identify weak topics (answered incorrectly more than once)
    topic_errors: dict[str, int] = {}
    topic_correct: dict[str, int] = {}
    for h in history:
        if h["correct"]:
            topic_correct[h["topic"]] = topic_correct.get(h["topic"], 0) + 1
        else:
            topic_errors[h["topic"]] = topic_errors.get(h["topic"], 0) + 1

    weak_topics = [t for t, cnt in topic_errors.items() if cnt >= 1]
    strong_topics = [t for t in topic_correct if t not in topic_errors]
    max_ability = max((h["ability_after"] for h in history), default=0.5)

    performance = PerformanceAnalysis(
        total_questions=len(history),
        correct_answers=correct_count,
        accuracy_rate=correct_count / len(history) if history else 0,
        max_ability_reached=max_ability,
        final_ability=doc["ability_score"],
        topics_attempted=all_topics,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
    )

    gemini = GeminiService()
    steps, summary = await gemini.generate_study_plan(performance)

    return StudyPlanResponse(
        session_id=session_id,
        performance=performance,
        study_plan=steps,
        summary=summary,
    )


# ── Dev / Seeding ─────────────────────────────────────────────────────────────

@router.post("/seed", status_code=201, tags=["dev"])
async def seed_questions(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Seed the DB with 25 GRE-style questions. Run once during setup."""
    questions = [
        # ── Algebra ──────────────────────────────────────────────────────────
        {"question": "If 3x + 7 = 22, what is x?", "options": ["3", "5", "7", "9"], "correct_answer": "5", "difficulty": 0.2, "topic": "Algebra", "tags": ["linear", "equation"]},
        {"question": "Solve: 2x² - 8 = 0", "options": ["x = ±2", "x = ±4", "x = 2", "x = -2"], "correct_answer": "x = ±2", "difficulty": 0.4, "topic": "Algebra", "tags": ["quadratic", "equation"]},
        {"question": "If f(x) = 3x² - 2x + 1, what is f(3)?", "options": ["22", "24", "28", "30"], "correct_answer": "22", "difficulty": 0.5, "topic": "Algebra", "tags": ["functions", "polynomial"]},
        {"question": "Factor completely: x² - 5x + 6", "options": ["(x-2)(x-3)", "(x+2)(x+3)", "(x-1)(x-6)", "(x+1)(x-6)"], "correct_answer": "(x-2)(x-3)", "difficulty": 0.45, "topic": "Algebra", "tags": ["factoring", "quadratic"]},
        {"question": "If |2x - 6| = 10, find all values of x.", "options": ["x = 8 or x = -2", "x = 8 or x = 2", "x = -8 or x = 2", "x = 4 or x = -2"], "correct_answer": "x = 8 or x = -2", "difficulty": 0.6, "topic": "Algebra", "tags": ["absolute_value"]},

        # ── Geometry ─────────────────────────────────────────────────────────
        {"question": "A rectangle has length 12 and width 5. What is its diagonal?", "options": ["13", "14", "15", "17"], "correct_answer": "13", "difficulty": 0.3, "topic": "Geometry", "tags": ["pythagorean", "rectangle"]},
        {"question": "What is the area of a circle with radius 7?", "options": ["14π", "49π", "21π", "7π"], "correct_answer": "49π", "difficulty": 0.25, "topic": "Geometry", "tags": ["circle", "area"]},
        {"question": "Two angles of a triangle are 45° and 75°. What is the third angle?", "options": ["60°", "70°", "80°", "90°"], "correct_answer": "60°", "difficulty": 0.2, "topic": "Geometry", "tags": ["triangle", "angles"]},
        {"question": "A cube has volume 125. What is its surface area?", "options": ["100", "120", "150", "175"], "correct_answer": "150", "difficulty": 0.55, "topic": "Geometry", "tags": ["cube", "3d"]},
        {"question": "In a circle, an inscribed angle is 40°. What is the central angle subtending the same arc?", "options": ["20°", "40°", "80°", "160°"], "correct_answer": "80°", "difficulty": 0.7, "topic": "Geometry", "tags": ["circle", "angles", "inscribed"]},

        # ── Arithmetic / Number Theory ────────────────────────────────────────
        {"question": "What is the LCM of 12 and 18?", "options": ["24", "36", "48", "72"], "correct_answer": "36", "difficulty": 0.25, "topic": "Arithmetic", "tags": ["lcm", "number_theory"]},
        {"question": "What is 15% of 240?", "options": ["32", "36", "40", "48"], "correct_answer": "36", "difficulty": 0.15, "topic": "Arithmetic", "tags": ["percentage"]},
        {"question": "If a number is increased by 20% and then decreased by 20%, the net change is:", "options": ["-4%", "0%", "+4%", "-1%"], "correct_answer": "-4%", "difficulty": 0.55, "topic": "Arithmetic", "tags": ["percentage", "net_change"]},
        {"question": "How many prime numbers are between 20 and 40?", "options": ["3", "4", "5", "6"], "correct_answer": "4", "difficulty": 0.4, "topic": "Arithmetic", "tags": ["prime", "number_theory"]},
        {"question": "What is the remainder when 2^10 is divided by 7?", "options": ["1", "2", "4", "6"], "correct_answer": "2", "difficulty": 0.75, "topic": "Arithmetic", "tags": ["modular_arithmetic", "powers"]},

        # ── Vocabulary / Verbal ──────────────────────────────────────────────
        {"question": "Choose the word most similar to EPHEMERAL:", "options": ["Permanent", "Transient", "Substantial", "Ancient"], "correct_answer": "Transient", "difficulty": 0.5, "topic": "Vocabulary", "tags": ["synonym", "gre_vocab"]},
        {"question": "Choose the word most opposite to LOQUACIOUS:", "options": ["Verbose", "Garrulous", "Taciturn", "Eloquent"], "correct_answer": "Taciturn", "difficulty": 0.6, "topic": "Vocabulary", "tags": ["antonym", "gre_vocab"]},
        {"question": "PALLIATE most nearly means:", "options": ["Aggravate", "Alleviate", "Intensify", "Diagnose"], "correct_answer": "Alleviate", "difficulty": 0.65, "topic": "Vocabulary", "tags": ["synonym", "gre_vocab"]},
        {"question": "Which word best completes: 'Her argument was so ___ that even her opponents were convinced.'", "options": ["Specious", "Cogent", "Nebulous", "Banal"], "correct_answer": "Cogent", "difficulty": 0.7, "topic": "Vocabulary", "tags": ["sentence_completion"]},
        {"question": "OBFUSCATE most nearly means:", "options": ["Clarify", "Obscure", "Simplify", "Illuminate"], "correct_answer": "Obscure", "difficulty": 0.55, "topic": "Vocabulary", "tags": ["synonym", "gre_vocab"]},

        # ── Data Analysis ────────────────────────────────────────────────────
        {"question": "The average of 5 numbers is 18. If four of them are 12, 15, 20, and 25, what is the fifth?", "options": ["16", "18", "20", "22"], "correct_answer": "18", "difficulty": 0.35, "topic": "Data Analysis", "tags": ["average", "statistics"]},
        {"question": "In a set {4, 7, 7, 9, 12, 15}, what is the median?", "options": ["7", "8", "9", "10"], "correct_answer": "8", "difficulty": 0.3, "topic": "Data Analysis", "tags": ["median", "statistics"]},
        {"question": "A bag has 3 red and 5 blue marbles. What is P(drawing 2 red in a row without replacement)?", "options": ["3/28", "9/64", "3/14", "1/8"], "correct_answer": "3/28", "difficulty": 0.75, "topic": "Data Analysis", "tags": ["probability", "combinatorics"]},
        {"question": "The standard deviation of {2, 2, 2, 2} is:", "options": ["0", "1", "2", "4"], "correct_answer": "0", "difficulty": 0.4, "topic": "Data Analysis", "tags": ["standard_deviation", "statistics"]},
        {"question": "If P(A) = 0.4, P(B) = 0.5, and A and B are independent, what is P(A and B)?", "options": ["0.1", "0.2", "0.45", "0.9"], "correct_answer": "0.2", "difficulty": 0.5, "topic": "Data Analysis", "tags": ["probability", "independence"]},
    ]

    # Clear existing and re-seed
    await db["questions"].delete_many({})
    result = await db["questions"].insert_many(questions)
    
    # Create indexes for efficient querying
    await db["questions"].create_index([("difficulty", 1)])
    await db["questions"].create_index([("topic", 1)])
    await db["user_sessions"].create_index([("user_id", 1)])

    return {
        "message": f"✅ Seeded {len(result.inserted_ids)} questions successfully",
        "count": len(result.inserted_ids),
    }
