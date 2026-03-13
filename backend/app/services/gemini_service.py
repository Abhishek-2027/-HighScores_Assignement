"""
Gemini Service — generates personalized 3-step study plans.

Uses the Gemini 1.5 Flash model via the google-generativeai SDK.
Prompts are carefully structured for JSON-parseable output.
"""

import json
import logging
import re

import google.generativeai as genai

from app.config import get_settings
from app.schemas.schemas import StudyPlanStep, PerformanceAnalysis

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1500,
            ),
        )

    def _build_prompt(self, performance: PerformanceAnalysis) -> str:
        weak = ", ".join(performance.weak_topics) if performance.weak_topics else "None identified"
        strong = ", ".join(performance.strong_topics) if performance.strong_topics else "None identified"

        return f"""You are an expert GRE tutor generating a personalized study plan.

## Student Performance Report
- Questions answered: {performance.total_questions}
- Correct answers: {performance.correct_answers}
- Accuracy: {performance.accuracy_rate:.1%}
- Starting ability score: 0.50 (baseline)
- Final ability score: {performance.final_ability:.2f} (scale: 0.0–1.0)
- Peak ability reached: {performance.max_ability_reached:.2f}
- Weak topics (missed multiple questions): {weak}
- Strong topics (answered correctly): {strong}

## Your Task
Generate a structured, actionable 3-step study plan tailored to this student.
Each step must target their specific weaknesses.

## IMPORTANT: Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "summary": "2-sentence personalized overview of the student's performance",
  "steps": [
    {{
      "step": 1,
      "title": "Short action-oriented title",
      "description": "Detailed 2-3 sentence description of what to do and why",
      "resources": ["Specific resource 1", "Specific resource 2", "Specific resource 3"]
    }},
    {{
      "step": 2,
      "title": "Short action-oriented title",
      "description": "Detailed 2-3 sentence description",
      "resources": ["Resource 1", "Resource 2", "Resource 3"]
    }},
    {{
      "step": 3,
      "title": "Short action-oriented title",
      "description": "Detailed 2-3 sentence description",
      "resources": ["Resource 1", "Resource 2", "Resource 3"]
    }}
  ]
}}"""

    async def generate_study_plan(
        self, performance: PerformanceAnalysis
    ) -> tuple[list[StudyPlanStep], str]:
        """
        Call Gemini and parse the structured study plan response.

        Returns:
            (steps, summary) tuple
        """
        prompt = self._build_prompt(performance)

        try:
            response = await self.model.generate_content_async(prompt)
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            steps = [StudyPlanStep(**s) for s in data["steps"]]
            summary = data["summary"]
            logger.info("✅ Gemini study plan generated successfully")
            return steps, summary

        except json.JSONDecodeError as e:
            logger.error("Gemini returned non-JSON response: %s", e)
            return self._fallback_plan(performance), "Study plan generated with default template."

        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return self._fallback_plan(performance), "Study plan generated with default template."

    def _fallback_plan(self, performance: PerformanceAnalysis) -> list[StudyPlanStep]:
        """Fallback plan when Gemini is unavailable."""
        weak = performance.weak_topics[:2] if performance.weak_topics else ["core concepts"]
        return [
            StudyPlanStep(
                step=1,
                title=f"Review {weak[0]} Fundamentals",
                description=f"Start by revisiting the core concepts of {weak[0]}. Use official GRE prep materials and focus on understanding underlying principles.",
                resources=["ETS Official GRE Guide", "Khan Academy", "Magoosh GRE"],
            ),
            StudyPlanStep(
                step=2,
                title="Targeted Practice Problems",
                description="Complete 20–30 targeted practice questions daily, focusing exclusively on your weak topics. Track your progress after each session.",
                resources=["GRE Big Book", "Manhattan Prep Practice Tests", "Kaplan GRE Prep"],
            ),
            StudyPlanStep(
                step=3,
                title="Full-Length Timed Practice",
                description="Take two full-length timed GRE practice tests under real conditions. Analyze every mistake to reinforce your improvements.",
                resources=["ETS PowerPrep II", "Princeton Review", "Official GRE Practice Tests"],
            ),
        ]
