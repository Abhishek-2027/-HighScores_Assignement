from pydantic import BaseModel, Field
from typing import Optional


# ── Request Schemas ──────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)


class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str


# ── Response Schemas ─────────────────────────────────────────────────────────

class QuestionResponse(BaseModel):
    question_id: str
    question: str
    options: list[str]
    topic: str
    difficulty: float
    question_number: int
    total_questions: int
    ability_score: float


class AnswerFeedbackResponse(BaseModel):
    correct: bool
    correct_answer: str
    ability_score: float
    question_number: int
    is_test_complete: bool
    session_id: str


class StudyPlanStep(BaseModel):
    step: int
    title: str
    description: str
    resources: list[str]


class PerformanceAnalysis(BaseModel):
    total_questions: int
    correct_answers: int
    accuracy_rate: float
    max_ability_reached: float
    final_ability: float
    topics_attempted: list[str]
    weak_topics: list[str]
    strong_topics: list[str]


class StudyPlanResponse(BaseModel):
    session_id: str
    performance: PerformanceAnalysis
    study_plan: list[StudyPlanStep]
    summary: str


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    ability_score: float
    questions_answered: int
    is_complete: bool


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
