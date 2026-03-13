"""
Adaptive Engine — selects the next question using Maximum Fisher Information.

Selection strategy:
1. Filter out already-asked questions.
2. Find questions within the difficulty band around current ability.
3. Among those, pick the question with highest Fisher information I(θ, b).
4. If no questions in band, widen the search progressively.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.irt import information_function, difficulty_band
from app.models.question_model import QuestionModel

logger = logging.getLogger(__name__)


class AdaptiveEngine:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["questions"]

    async def get_next_question(
        self,
        ability: float,
        asked_ids: list[str],
    ) -> QuestionModel | None:
        """
        Select the next question using Maximum Information criterion.
        Progressively widens the search band if no questions are found.
        """
        tolerances = [0.15, 0.25, 0.40, 1.0]  # progressive widening

        for tolerance in tolerances:
            lower, upper = difficulty_band(ability, tolerance)

            pipeline = [
                {
                    "$match": {
                        "difficulty": {"$gte": lower, "$lte": upper},
                        "_id": {"$nin": asked_ids},
                    }
                },
                {"$sample": {"size": 10}},  # random sample to avoid always picking same questions
            ]

            candidates = await self.collection.aggregate(pipeline).to_list(10)

            if candidates:
                # Score each candidate by Fisher information
                best = max(
                    candidates,
                    key=lambda q: information_function(ability, q["difficulty"]),
                )
                best["_id"] = str(best["_id"])
                return QuestionModel(**best)

        logger.warning("No eligible questions found for ability=%.2f", ability)
        return None

    async def get_total_question_count(self) -> int:
        return await self.collection.count_documents({})
