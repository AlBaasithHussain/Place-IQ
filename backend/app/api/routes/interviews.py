"""Mock interview endpoints (all protected, text answers only)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evaluation import AnswerEvaluation, InterviewEvaluation
from app.models.interview import Interview, InterviewQuestion
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.interview import (
    AnswerEvaluationDetail,
    AnswerRequest,
    EvaluationResult,
    InterviewDetail,
    InterviewStartRequest,
    InterviewStatus,
    InterviewSummary,
    QuestionCategory,
    QuestionDetail,
)
from app.schemas.job import JobAnalysisResult
from app.services.analysis import scorer
from app.services.interviews import evaluator, generator
from app.services.interviews.evaluator import (
    EvaluationError,
    EvaluationInput,
    EvaluationQuestion,
)
from app.services.interviews.generator import InterviewGenerationError, InterviewInput
from app.services.resume.skills import collect_resume_skills

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _detail(row: Interview) -> InterviewDetail:
    questions = sorted(row.questions, key=lambda item: item.position)
    answered = sum(1 for item in questions if item.answer)
    is_complete = bool(questions) and answered == len(questions)
    current = next((item.position for item in questions if not item.answer), None)
    percentage = int((answered / len(questions)) * 100 + 0.5) if questions else 0
    return InterviewDetail(
        id=row.id,
        user_id=row.user_id,
        resume_id=row.resume_id,
        job_id=row.job_id,
        job_title=row.job_title,
        question_count=row.question_count,
        generation_engine=row.generation_engine,
        status=InterviewStatus.COMPLETED if is_complete else InterviewStatus(row.status),
        created_at=row.created_at,
        completed_at=row.completed_at,
        questions=[QuestionDetail.model_validate(item) for item in questions],
        answered_count=answered,
        progress_percentage=percentage,
        current_question_number=current,
        is_complete=is_complete,
        has_evaluation=row.evaluation is not None,
    )


def _summary(row: Interview) -> InterviewSummary:
    answered = sum(1 for item in row.questions if item.answer)
    percentage = int((answered / len(row.questions)) * 100 + 0.5) if row.questions else 0
    return InterviewSummary(
        id=row.id,
        resume_id=row.resume_id,
        job_id=row.job_id,
        job_title=row.job_title,
        question_count=row.question_count,
        generation_engine=row.generation_engine,
        status=InterviewStatus.COMPLETED if answered == len(row.questions) else InterviewStatus(row.status),
        created_at=row.created_at,
        progress_percentage=percentage,
        has_evaluation=row.evaluation is not None,
    )


def _evaluation_detail(row: InterviewEvaluation) -> EvaluationResult:
    answers = sorted(row.answer_evaluations, key=lambda item: item.position)
    return EvaluationResult(
        id=row.id,
        interview_id=row.interview_id,
        job_title=row.interview.job_title,
        overall_score=row.overall_score,
        generation_engine=row.generation_engine,
        overall_summary=row.overall_summary,
        overall_strengths=row.overall_strengths,
        overall_weaknesses=row.overall_weaknesses,
        suggested_improvements=row.suggested_improvements,
        question_count=len(row.interview.questions),
        evaluated_answer_count=len(answers),
        answer_evaluations=[
            AnswerEvaluationDetail(
                id=item.id,
                evaluation_id=item.evaluation_id,
                question_id=item.question_id,
                position=item.position,
                category=QuestionCategory(item.question.category),
                question=item.question.question,
                answer=item.question.answer or "",
                focus_skill=item.question.focus_skill,
                score=item.score,
                technical_accuracy=item.technical_accuracy,
                relevance=item.relevance,
                completeness=item.completeness,
                clarity=item.clarity,
                strengths=item.strengths,
                weaknesses=item.weaknesses,
                suggested_improvement=item.suggested_improvement,
                model_answer=item.model_answer,
            )
            for item in answers
        ],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/start", response_model=InterviewDetail, status_code=status.HTTP_201_CREATED)
def start_interview(
    payload: InterviewStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewDetail:
    resume = (
        db.query(Resume)
        .filter(Resume.id == payload.resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    job = (
        db.query(Job)
        .filter(Job.id == payload.job_id, Job.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_data = JobAnalysisResult.model_validate(job, from_attributes=True).model_dump()
    parsed = resume.parsed_data or {}
    match_result = scorer.score_match(
        collect_resume_skills(resume),
        job_data,
        resume_experience=parsed.get("experience", []) or [],
        resume_projects=parsed.get("projects", []) or [],
    )

    data = InterviewInput(
        job_title=job.job_title,
        job_description=job.original_text,
        required_skills=job.required_skills or [],
        resume_skills=collect_resume_skills(resume),
        projects=list(parsed.get("projects", []) or []),
        missing_skills=match_result.missing_skills,
        match_score=match_result.score,
        question_count=payload.question_count,
    )
    try:
        plan, engine = generator.generate_questions(data)
    except InterviewGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed. Please try again.",
        ) from exc

    row = Interview(
        user_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        job_title=job.job_title,
        question_count=payload.question_count,
        generation_engine=engine,
        status=InterviewStatus.IN_PROGRESS.value,
    )
    for index, item in enumerate(plan.questions, start=1):
        row.questions.append(
            InterviewQuestion(
                position=index,
                category=item.category.value,
                question=item.question,
                focus_skill=item.focus_skill,
            )
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _detail(row)


@router.get("", response_model=list[InterviewSummary])
def list_interviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InterviewSummary]:
    rows = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc(), Interview.id.desc())
        .all()
    )
    return [_summary(row) for row in rows]


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewDetail:
    row = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return _detail(row)


@router.post("/{interview_id}/answer", response_model=InterviewDetail)
def answer_question(
    interview_id: int,
    payload: AnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewDetail:
    row = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == payload.question_id,
            InterviewQuestion.interview_id == row.id,
        )
        .first()
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if row.status == InterviewStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview is already completed",
        )

    question.answer = payload.answer
    question.answered_at = datetime.now(timezone.utc)
    if all(item.answer for item in row.questions):
        row.status = InterviewStatus.COMPLETED.value
        row.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return _detail(row)


@router.post("/{interview_id}/evaluate", response_model=EvaluationResult)
def evaluate_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationResult:
    row = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if not all(item.answer for item in row.questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview must be completed before evaluation",
        )

    existing = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.interview_id == row.id)
        .first()
    )
    if existing is not None:
        return _evaluation_detail(existing)

    questions = sorted(row.questions, key=lambda item: item.position)
    data = EvaluationInput(
        job_title=row.job_title,
        job_description=row.job.original_text,
        required_skills=row.job.required_skills or [],
        questions=[
            EvaluationQuestion(
                position=item.position,
                category=QuestionCategory(item.category),
                question=item.question,
                focus_skill=item.focus_skill,
                answer=item.answer or "",
            )
            for item in questions
        ],
    )
    try:
        draft, engine = evaluator.evaluate_answers(data)
    except EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed. Please try again.",
        ) from exc

    by_position = {item.position: item for item in questions}
    evaluation = InterviewEvaluation(
        interview=row,
        overall_score=draft.overall_score,
        generation_engine=engine,
        overall_summary=draft.overall_summary,
        overall_strengths=draft.overall_strengths,
        overall_weaknesses=draft.overall_weaknesses,
        suggested_improvements=draft.suggested_improvements,
    )
    for answer in draft.answer_evaluations:
        question = by_position[answer.position]
        evaluation.answer_evaluations.append(
            AnswerEvaluation(
                question=question,
                position=answer.position,
                score=answer.score,
                technical_accuracy=answer.technical_accuracy,
                relevance=answer.relevance,
                completeness=answer.completeness,
                clarity=answer.clarity,
                strengths=answer.strengths,
                weaknesses=answer.weaknesses,
                suggested_improvement=answer.suggested_improvement,
                model_answer=answer.model_answer,
            )
        )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _evaluation_detail(evaluation)


@router.get("/{interview_id}/results", response_model=EvaluationResult)
def get_interview_results(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationResult:
    evaluation = (
        db.query(InterviewEvaluation)
        .join(Interview)
        .filter(
            InterviewEvaluation.interview_id == interview_id,
            Interview.user_id == current_user.id,
        )
        .first()
    )
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation found for this interview",
        )
    return _evaluation_detail(evaluation)
