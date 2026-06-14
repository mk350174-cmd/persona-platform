"""HPEP-100 Quiz Router — 50-question persona extraction protocol."""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.db import get_db, User, QuizSubmission, UserPersona
from api.auth import get_current_user
from api.quiz_questions import QUESTION_BANK, public_question_bank
from api.quiz_service import extract_persona

router = APIRouter(prefix="/api/v1/quiz", tags=["quiz"])


# ── Request/Response Models ────────────────────────────────────────────────────

class QuestionResponse(BaseModel):
    """Public question bank (no rubric/layers exposed)."""
    id: str
    phase: int
    type: str
    text: str


class SubmitAnswersRequest(BaseModel):
    """Quiz submission: answers for all 50 questions."""
    answers: dict[str, float] = Field(
        ...,
        description="Dict mapping question ID (S1-S50) to 0-3 score"
    )


class CEIDScores(BaseModel):
    """CEID axis scores (0-3 each)."""
    C: float
    E: float
    I: float
    D: float


class PersonaResponse(BaseModel):
    """User's extracted persona."""
    k_layer: list[float] = Field(..., description="100-element K-layer vector (0-1 range)")
    ceid_scores: CEIDScores
    tier: str | None = None
    created_at: str


class SubmitAnswersResponse(BaseModel):
    """Response after quiz submission (before checkout)."""
    persona: PersonaResponse
    checkout_url: str


class ResultsResponse(BaseModel):
    """Latest persona extraction results."""
    persona: PersonaResponse
    submission_count: int


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/questions", response_model=list[QuestionResponse])
async def get_questions() -> list[QuestionResponse]:
    """Get all 50 HPEP-100 questions (public view, no scoring rubric/layers)."""
    return public_question_bank()


@router.post("/submit", response_model=SubmitAnswersResponse)
async def submit_quiz(
    request: SubmitAnswersRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmitAnswersResponse:
    """
    Submit quiz answers and extract persona.
    Returns persona vector + checkout URL for $5 HPEP-100 purchase.
    """
    # Extract persona from answers
    answers_dict = {qid: score for qid, score in request.answers.items()}
    k_layer, ceid_scores = extract_persona(answers_dict)

    # Create submission record
    submission = QuizSubmission(
        user_id=user.id,
        answers=answers_dict,
        k_layer=k_layer.tolist() if hasattr(k_layer, 'tolist') else k_layer,
        ceid_scores=ceid_scores,
    )
    db.add(submission)
    db.flush()  # Get the ID without committing yet

    # Create or update user persona cache
    persona = db.query(UserPersona).filter(UserPersona.user_id == user.id).first()
    if not persona:
        persona = UserPersona(
            user_id=user.id,
            k_layer=k_layer.tolist() if hasattr(k_layer, 'tolist') else k_layer,
            ceid_scores=ceid_scores,
            submission_id=submission.id,
        )
        db.add(persona)
    else:
        persona.k_layer = k_layer.tolist() if hasattr(k_layer, 'tolist') else k_layer
        persona.ceid_scores = ceid_scores
        persona.submission_id = submission.id

    db.commit()

    # Build persona response
    persona_resp = PersonaResponse(
        k_layer=persona.k_layer,
        ceid_scores=CEIDScores(**persona.ceid_scores),
        tier=persona.tier,
        created_at=submission.created_at.isoformat(),
    )

    # TODO: Generate Stripe checkout URL for $5 HPEP-100 SKU
    # For now, return placeholder
    checkout_url = "/checkout/hpep100?session_id=test"

    return SubmitAnswersResponse(
        persona=persona_resp,
        checkout_url=checkout_url,
    )


@router.get("/results", response_model=ResultsResponse)
async def get_results(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResultsResponse:
    """Get user's latest extracted persona and submission count."""
    persona = db.query(UserPersona).filter(UserPersona.user_id == user.id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="No persona extracted yet. Submit the quiz first.")

    submission_count = db.query(QuizSubmission).filter(QuizSubmission.user_id == user.id).count()

    persona_resp = PersonaResponse(
        k_layer=persona.k_layer,
        ceid_scores=CEIDScores(**persona.ceid_scores),
        tier=persona.tier,
        created_at=persona.updated_at.isoformat(),
    )

    return ResultsResponse(
        persona=persona_resp,
        submission_count=submission_count,
    )
