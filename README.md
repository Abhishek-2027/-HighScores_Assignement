# AI-Driven Adaptive Diagnostic Engine

A production-grade **1-Dimension Adaptive Testing System** using **Item Response Theory (IRT)** for dynamic question selection and **Gemini AI** for personalized study plan generation.

---

## Architecture

```
HTML/CSS/JS Frontend  (no build step — open index.html)
         │  REST API (fetch)
         ▼
FastAPI Backend
    ├── Adaptive Engine  ← IRT / Maximum Fisher Information
    ├── Gemini Service   ← Personalized study plan
    └── MongoDB Atlas    ← Questions + UserSessions
```

---

## Tech Stack

| Layer    | Technology                               |
|----------|------------------------------------------|
| Frontend | HTML5, CSS3, Vanilla JavaScript (ES2020) |
| Backend  | FastAPI, Python 3.10+ (3.10 safer), Motor (async)     |
| Database | MongoDB Atlas                            |
| AI       | Google Gemini 1.5 Flash                  |
| IRT      | 1-Parameter Logistic Model (Rasch)       |

---

## Project Structure

```
adaptive-testing-system/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI app + lifespan
│       ├── config.py                # Settings via pydantic-settings + .env
│       ├── api/routes.py            # All API endpoint handlers
│       ├── models/                  # MongoDB document models
│       ├── schemas/schemas.py       # Request / response Pydantic schemas
│       ├── services/
│       │   ├── adaptive_engine.py   # Max-info question selection (IRT)
│       │   └── gemini_service.py    # Gemini study plan generation
│       ├── database/mongodb.py      # Async Motor connection pool
│       └── utils/irt.py             # IRT math — 1PL logistic model
│       |--── .env                   # please config you env file with google api key and mongoosAtlas string
|
├── frontend/
│   ├── index.html        # All 3 pages (home / test / plan) in one file
│   ├── css/style.css     # Complete dark-theme stylesheet
│   └── js/
│       ├── api.js        # All fetch() calls to the backend
│       ├── state.js      # Global state object
│       ├── ui.js         # DOM rendering functions
│       └── app.js        # Event handlers / app controller
│
├
└── README.md
```

---

## Setup & Running

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in MONGODB_URI and GEMINI_API_KEY
```

### 2. Start Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Open Frontend

No build step needed — just open `frontend/index.html` in your browser,
**or** serve it with any static server:

```bash
cd frontend
python -m http.server 3000
# then visit http://localhost:3000
```

### 4. Seed the database

Click **"Seed Database"** on the home page, or:

```bash
curl -X POST http://localhost:8000/api/v1/seed
```

---

## API Endpoints

| Method | Endpoint                          | Description                          |
|--------|-----------------------------------|--------------------------------------|
| POST   | `/api/v1/sessions/start`          | Start a new test session             |
| GET    | `/api/v1/sessions/{id}`           | Get session state                    |
| GET    | `/api/v1/sessions/{id}/question`  | Get next adaptive question           |
| POST   | `/api/v1/sessions/{id}/answer`    | Submit answer + update ability score |
| POST   | `/api/v1/sessions/{id}/plan`      | Generate Gemini AI study plan        |
| POST   | `/api/v1/seed`                    | Seed DB with 25 GRE questions        |
| GET    | `/health`                         | Health check                         |

Interactive docs: `http://localhost:8000/docs`

---

## Adaptive Algorithm

### 1PL / Rasch Model

**Probability of correct response:**
```
P(θ, b) = 1 / (1 + exp(-(θ - b)))
```
`θ` = student ability, `b` = question difficulty (both scaled to [0,1])

**Ability update after each response:**
```
θ_new = θ_old + α × (response - P(θ_old, b))
```
`α` = learning rate (0.3), `response` = 1 if correct, 0 if incorrect

**Question selection — Maximum Fisher Information:**
```
I(θ) = P(θ) × (1 - P(θ))
```
Selects the question with highest information from a difficulty band centred on current ability. Band widens progressively (±0.15 → ±0.25 → ±0.40 → full) if no candidates found.

---

## MongoDB Schema

### `questions`
```json
{
  "question": "If 3x + 7 = 22, what is x?",
  "options": ["3","5","7","9"],
  "correct_answer": "5",
  "difficulty": 0.2,
  "topic": "Algebra",
  "tags": ["linear","equation"]
}
```

### `user_sessions`
```json
{
  "user_id": "alex",
  "ability_score": 0.63,
  "questions_answered": 7,
  "is_complete": false,
  "asked_question_ids": ["id1","id2"],
  "history": [
    { "question_id":"id1", "topic":"Algebra", "difficulty":0.4,
      "correct":true, "ability_before":0.5, "ability_after":0.63 }
  ]
}
```

---

## AI Log

**AI tools used for:**
- Scaffolding the IRT math module with docstrings and academic references
- Generating 25 realistic GRE questions with calibrated difficulty scores
- Writing the Gemini prompt template for strict JSON output
- MongoDB aggregation pipeline for adaptive question selection

**Challenges requiring human judgment:**
- Learning rate calibration (0.3) — needed iterative testing to prevent oscillation
- Difficulty band tolerance progression — required IRT domain knowledge
- Gemini prompt engineering for reliable JSON schema compliance


**working example **
<img width="1486" height="816" alt="image" src="https://github.com/user-attachments/assets/33ca42f1-4c23-4d86-a666-c2ac4dc37169" />


<img width="1220" height="794" alt="image" src="https://github.com/user-attachments/assets/a5b387b7-914d-4be3-989c-828aebd3ea8a" />


<img width="696" height="820" alt="image" src="https://github.com/user-attachments/assets/6ba3bf69-2008-4b33-9ad5-54820035710b" />
