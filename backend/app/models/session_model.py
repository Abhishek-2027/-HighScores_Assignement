from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime
from app.models.question_model import PyObjectId


class AnswerRecord(BaseModel):
    question_id: str
    topic: str
    difficulty: float
    correct: bool
    ability_before: float
    ability_after: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserSessionModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    ability_score: float = 0.5
    questions_answered: int = 0
    history: list[AnswerRecord] = []
    asked_question_ids: list[str] = []
    is_complete: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
