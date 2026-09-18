from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

from database.connection import SessionLocal, Base, engine
from models.workspace import Workspace
from models.opportunity import Opportunity
from models.research_session import ResearchSession
from models.product import Product
from models.transformation_map import TransformationMap
from models.product_summary import ProductSummary
from models.product_outline import ProductOutline
from models.section import Section
from models.section_brief import SectionBrief
from models.content_blueprint import ContentBlueprint
from models.manuscript_section import ManuscriptSection
from models.product_package import ProductPackage
from models.brand_kit import BrandKit
from models.problem_discovery import ProblemDiscovery
from models.problem_evidence import ProblemEvidence
from models.problem_evidence_profile import ProblemEvidenceProfile
from models.intent_brief import IntentBrief
from models.intent_evidence import IntentEvidence
from models.reader_experience import ReaderExperience
from models.product_intent_link import ProductIntentLink
from ai_service import (
    generate_transformation_map,
    generate_product_summary,
    generate_product_outline,
    generate_section_briefs,
    generate_content_blueprints,
    generate_manuscript_section,
    generate_problem_discovery,
    generate_intent_validation,
    generate_reader_experiences,
)
from packaging_service import generate_product_pdf
from branding_service import generate_brand_kit, normalize_brand, build_assets


Base.metadata.create_all(bind=engine)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def mark_package_stale(db, product_id: int):
    package = (
        db.query(ProductPackage)
        .filter(ProductPackage.product_id == product_id)
        .first()
    )
    if package is not None:
        package.status = "stale"


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class OpportunityResponse(BaseModel):
    id: int
    title: str
    industry: str
    niche: str
    problem: str
    pain_score: float
    worsening_score: float
    purchasing_power_score: float
    speed_score: float
    overall_score: float

    class Config:
        from_attributes = True


class ProblemEvidenceResponse(BaseModel):
    id: int
    source_title: str
    source_url: str
    source_type: str | None
    signal_type: str | None
    excerpt: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


class ProblemEvidenceProfileResponse(BaseModel):
    pain_summary: str | None
    economic_consequence: str | None
    existing_attempts: str | None
    solution_seeking: str | None
    spending_signal: str | None
    repeated_pattern: str | None
    evidence_confidence: str
    evidence_summary: str | None

    class Config:
        from_attributes = True


class ProblemDiscoveryResponse(BaseModel):
    id: int
    market_direction: str | None
    customer_group: str
    situation: str
    problem: str
    trigger: str | None
    current_behavior: str | None
    initial_signal: str | None
    investigation_reason: str | None
    status: str
    created_at: datetime | None
    evidence_profile: ProblemEvidenceProfileResponse | None = None
    evidence: list[ProblemEvidenceResponse] = []


class IntentEvidenceResponse(BaseModel):
    id: int
    source_title: str
    source_url: str
    source_type: str | None
    signal_type: str | None
    excerpt: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


class IntentBriefResponse(BaseModel):
    id: int
    problem_discovery_id: int
    target_customer: str | None
    problem_context: str | None
    trigger: str | None
    current_behavior: str | None
    failed_alternatives: str | None
    desired_outcome: str | None
    constraints: str | None
    objections: str | None
    customer_language: str | None
    existing_solutions: str | None
    solution_gap: str | None
    potential_solution: str | None
    recommended_format: str | None
    why_format: str | None
    validation_questions: str | None
    evidence_confidence: str
    evidence_summary: str | None
    source_count: int
    domain_count: int
    customer_signal_count: int
    solution_seeking_count: int
    spending_signal_count: int
    failed_attempt_count: int
    status: str
    created_at: datetime | None
    updated_at: datetime | None
    evidence: list[IntentEvidenceResponse] = []

    class Config:
        from_attributes = True


class IntentProductCreate(BaseModel):
    format: str


class ProductCreate(BaseModel):
    opportunity_id: int
    format: str


class ProductResponse(BaseModel):
    id: int
    opportunity_id: int
    format: str
    status: str

    class Config:
        from_attributes = True


class TransformationMapCreate(BaseModel):
    before_emotional_state: str | None = None
    before_core_fear: str | None = None
    before_daily_experience: str | None = None
    before_identity: str | None = None
    after_emotional_state: str | None = None
    after_core_fear: str | None = None
    after_daily_experience: str | None = None
    after_identity: str | None = None


class TransformationMapResponse(BaseModel):
    id: int
    product_id: int
    before_emotional_state: str | None
    before_core_fear: str | None
    before_daily_experience: str | None
    before_identity: str | None
    after_emotional_state: str | None
    after_core_fear: str | None
    after_daily_experience: str | None
    after_identity: str | None

    class Config:
        from_attributes = True


class ProductSummaryCreate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    about: str | None = None
    what_youll_learn: str | None = None
    estimated_reading_time: int | None = None
    section_count: int | None = None
    bonus_materials: str | None = None


class ProductSummaryResponse(BaseModel):
    id: int
    product_id: int
    title: str | None
    subtitle: str | None
    about: str | None
    what_youll_learn: str | None
    estimated_reading_time: int | None
    section_count: int | None
    bonus_materials: str | None

    class Config:
        from_attributes = True


class GeneratedProductSummaryResponse(BaseModel):
    title: str
    subtitle: str
    about: str
    what_youll_learn: str
    estimated_reading_time: int
    section_count: int
    bonus_materials: str


class BrandKitCreate(BaseModel):
    brand_name: str | None = None
    tagline: str | None = None
    visual_direction: str | None = None
    palette_name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    text_color: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    cover_layout: str | None = None
    status: str | None = "reviewed"


class BrandKitResponse(BaseModel):
    id: int | None = None
    product_id: int
    brand_name: str
    tagline: str
    visual_direction: str
    palette_name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    text_color: str
    heading_font: str
    body_font: str
    cover_layout: str
    cover_svg: str
    social_card_svg: str
    thumbnail_svg: str
    status: str


class GeneratedBrandKitResponse(BrandKitResponse):
    pass


class ProductOutlineCreate(BaseModel):
    status: str | None = "draft"


class ProductOutlineResponse(BaseModel):
    id: int
    product_id: int
    status: str

    class Config:
        from_attributes = True


class SectionCreate(BaseModel):
    position: int
    title: str
    purpose: str | None = None
    status: str | None = "draft"


class SectionResponse(BaseModel):
    id: int
    outline_id: int
    position: int
    title: str
    purpose: str | None
    status: str

    class Config:
        from_attributes = True


class GeneratedProductOutlineSectionResponse(BaseModel):
    title: str
    purpose: str


class GeneratedProductOutlineResponse(BaseModel):
    sections: list[GeneratedProductOutlineSectionResponse]


class SectionBriefCreate(BaseModel):
    objective: str | None = None
    key_concepts: str | None = None
    practical_steps: str | None = None
    example_scenario: str | None = None
    common_mistakes: str | None = None
    reader_outcome: str | None = None
    status: str | None = "draft"


class SectionBriefResponse(BaseModel):
    id: int
    section_id: int
    objective: str | None
    key_concepts: str | None
    practical_steps: str | None
    example_scenario: str | None
    common_mistakes: str | None
    reader_outcome: str | None
    status: str

    class Config:
        from_attributes = True


class GeneratedSectionBrief(BaseModel):
    position: int
    objective: str
    key_concepts: str
    practical_steps: str
    example_scenario: str
    common_mistakes: str
    reader_outcome: str


class GeneratedSectionBriefsResponse(BaseModel):
    briefs: list[GeneratedSectionBrief]


class ContentBlueprintCreate(BaseModel):
    hook_angle: str | None = None
    core_explanation: str | None = None
    supporting_points: str | None = None
    reader_action: str | None = None
    example_scenario: str | None = None
    misconception_or_objection: str | None = None
    transition_to_next: str | None = None
    avoid: str | None = None
    target_word_count: int | None = None
    status: str | None = "draft"


class ContentBlueprintResponse(BaseModel):
    id: int
    section_id: int
    hook_angle: str | None
    core_explanation: str | None
    supporting_points: str | None
    reader_action: str | None
    example_scenario: str | None
    misconception_or_objection: str | None
    transition_to_next: str | None
    avoid: str | None
    target_word_count: int | None
    status: str

    class Config:
        from_attributes = True


class GeneratedContentBlueprint(BaseModel):
    position: int
    hook_angle: str
    core_explanation: str
    supporting_points: str
    reader_action: str
    example_scenario: str
    misconception_or_objection: str
    transition_to_next: str
    avoid: str
    target_word_count: int


class GeneratedContentBlueprintsResponse(BaseModel):
    blueprints: list[GeneratedContentBlueprint]


class ReaderExperienceCreate(BaseModel):
    reader_job: str | None = None
    reader_question: str | None = None
    desired_reaction: str | None = None
    experience_type: str | None = None
    visual_decision: str | None = None
    interactive_element: str | None = None
    evidence_anchor: str | None = None
    claim_boundary: str | None = None
    reader_action: str | None = None
    transition_intent: str | None = None
    avoid: str | None = None
    status: str | None = "draft"


class ReaderExperienceResponse(BaseModel):
    id: int
    product_id: int
    section_id: int
    intent_brief_id: int | None
    reader_job: str | None
    reader_question: str | None
    desired_reaction: str | None
    experience_type: str | None
    visual_decision: str | None
    interactive_element: str | None
    evidence_anchor: str | None
    claim_boundary: str | None
    reader_action: str | None
    transition_intent: str | None
    avoid: str | None
    status: str
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class GeneratedReaderExperience(BaseModel):
    position: int
    reader_job: str
    reader_question: str
    desired_reaction: str
    experience_type: str
    visual_decision: str
    interactive_element: str
    evidence_anchor: str
    claim_boundary: str
    reader_action: str
    transition_intent: str
    avoid: str


class GeneratedReaderExperiencesResponse(BaseModel):
    experiences: list[GeneratedReaderExperience]


class ManuscriptSectionCreate(BaseModel):
    content: str | None = None
    word_count: int | None = None
    status: str | None = "draft"


class ManuscriptSectionResponse(BaseModel):
    id: int
    section_id: int
    content: str | None
    word_count: int
    status: str

    class Config:
        from_attributes = True


class GeneratedManuscriptSectionResponse(BaseModel):
    section_id: int
    position: int
    title: str
    content: str
    word_count: int


class ProductPackageResponse(BaseModel):
    id: int
    product_id: int
    title: str
    subtitle: str | None
    section_count: int
    total_word_count: int
    pdf_path: str | None
    status: str
    generated_at: str | None

    class Config:
        from_attributes = True


class BrandKitCreate(BaseModel):
    brand_name: str | None = None
    tagline: str | None = None
    visual_direction: str | None = None
    palette_name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    text_color: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    cover_layout: str | None = None
    status: str | None = "reviewed"


class BrandKitResponse(BaseModel):
    id: int | None = None
    product_id: int
    brand_name: str
    tagline: str
    visual_direction: str
    palette_name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    text_color: str
    heading_font: str
    body_font: str
    cover_layout: str
    cover_svg: str
    social_card_svg: str
    thumbnail_svg: str
    status: str


class GeneratedBrandKitResponse(BrandKitResponse):
    pass


class ProductOutlineCreate(BaseModel):
    status: str | None = "draft"


class ProductOutlineResponse(BaseModel):
    id: int
    product_id: int
    status: str

    class Config:
        from_attributes = True


class SectionCreate(BaseModel):
    position: int
    title: str
    purpose: str | None = None
    status: str | None = "draft"


class SectionResponse(BaseModel):
    id: int
    outline_id: int
    position: int
    title: str
    purpose: str | None
    status: str

    class Config:
        from_attributes = True


@app.get("/")
def home():
    return {"message": "Hello from NOVA!"}


@app.get("/workspaces", response_model=list[WorkspaceResponse])
def get_workspaces(db=Depends(get_db)):
    return db.query(Workspace).all()


@app.post("/workspaces", response_model=WorkspaceResponse)
def create_workspace(
    workspace: WorkspaceCreate,
    db=Depends(get_db),
):
    new_workspace = Workspace(
        name=workspace.name,
    )

    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    return new_workspace


@app.post("/problem-discovery/discover")
def discover_problem_candidates(db=Depends(get_db)):
    try:
        generated = generate_problem_discovery()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not discover evidence-backed customer problems: {exc}",
        ) from exc

    for item in generated.problems:
        record = ProblemDiscovery(
            market_direction=item.market_direction,
            customer_group=item.customer_group,
            situation=item.situation,
            problem=item.problem,
            trigger=item.trigger,
            current_behavior=item.current_behavior,
            initial_signal=item.solution_seeking,
            investigation_reason=item.evidence_summary,
            status="evidence_backed_candidate",
        )
        db.add(record)
        db.flush()

        profile = ProblemEvidenceProfile(
            problem_discovery_id=record.id,
            pain_summary=item.pain_summary,
            economic_consequence=item.economic_consequence,
            existing_attempts=item.existing_attempts,
            solution_seeking=item.solution_seeking,
            spending_signal=item.spending_signal,
            repeated_pattern=item.repeated_pattern,
            evidence_confidence=item.evidence_confidence,
            evidence_summary=item.evidence_summary,
        )
        db.add(profile)

        for evidence in item.evidence_items:
            db.add(
                ProblemEvidence(
                    problem_discovery_id=record.id,
                    source_title=evidence.source_title,
                    source_url=evidence.source_url,
                    source_type=evidence.source_type,
                    signal_type=evidence.signal_type,
                    excerpt=evidence.excerpt,
                )
            )

    db.commit()

    records = (
        db.query(ProblemDiscovery)
        .order_by(ProblemDiscovery.id.desc())
        .limit(len(generated.problems))
        .all()
    )

    return {
        "message": "Evidence-backed problem candidates discovered.",
        "problems": [_serialize_problem_discovery(db, record) for record in records],
    }


def _serialize_problem_discovery(db, problem):
    profile = (
        db.query(ProblemEvidenceProfile)
        .filter(ProblemEvidenceProfile.problem_discovery_id == problem.id)
        .first()
    )
    evidence = (
        db.query(ProblemEvidence)
        .filter(ProblemEvidence.problem_discovery_id == problem.id)
        .order_by(ProblemEvidence.id.asc())
        .all()
    )

    return {
        "id": problem.id,
        "market_direction": problem.market_direction,
        "customer_group": problem.customer_group,
        "situation": problem.situation,
        "problem": problem.problem,
        "trigger": problem.trigger,
        "current_behavior": problem.current_behavior,
        "initial_signal": problem.initial_signal,
        "investigation_reason": problem.investigation_reason,
        "status": problem.status,
        "created_at": problem.created_at,
        "evidence_profile": profile,
        "evidence": evidence,
    }


@app.get("/problem-discovery", response_model=list[ProblemDiscoveryResponse])
def get_problem_discoveries(db=Depends(get_db)):
    problems = (
        db.query(ProblemDiscovery)
        .filter(ProblemDiscovery.status == "evidence_backed_candidate")
        .order_by(ProblemDiscovery.id.desc())
        .all()
    )
    return [_serialize_problem_discovery(db, problem) for problem in problems]


@app.get("/problem-discovery/{problem_id}", response_model=ProblemDiscoveryResponse)
def get_problem_discovery(problem_id: int, db=Depends(get_db)):
    problem = db.get(ProblemDiscovery, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem candidate not found")
    return _serialize_problem_discovery(db, problem)


@app.post("/opportunities/discover")
def discover_opportunities(db=Depends(get_db)):
    opportunities = [
        Opportunity(
            title="Paycheck-to-Paycheck Budgeting",
            industry="Personal Finance",
            niche="Single-Income Households",
            problem="Helping single-income households stop running out of money before payday.",
            pain_score=9,
            worsening_score=9,
            purchasing_power_score=9,
            speed_score=8,
            overall_score=8.9,
        ),
        Opportunity(
            title="Competitive Gaming Improvement",
            industry="Gaming & Esports",
            niche="Adult Competitive Players",
            problem="Helping adult players win more close matches without grinding for long hours.",
            pain_score=9,
            worsening_score=8,
            purchasing_power_score=8,
            speed_score=8,
            overall_score=8.3,
        ),
        Opportunity(
            title="Household Chore Systems",
            industry="Home & Organization",
            niche="Busy Families",
            problem="Helping families turn recurring household chores into clear task systems.",
            pain_score=8,
            worsening_score=8,
            purchasing_power_score=8,
            speed_score=9,
            overall_score=8.2,
        ),
        Opportunity(
            title="Couples Responsibility Planning",
            industry="Relationships",
            niche="Long-Term Couples",
            problem="Helping couples resolve recurring household responsibility conflicts.",
            pain_score=9,
            worsening_score=8,
            purchasing_power_score=8,
            speed_score=7,
            overall_score=8.1,
        ),
        Opportunity(
            title="Independent Homework Systems",
            industry="Parenting",
            niche="Parents of Middle School Students",
            problem="Helping parents build independent homework habits without constant hovering.",
            pain_score=8,
            worsening_score=8,
            purchasing_power_score=9,
            speed_score=8,
            overall_score=8.2,
        ),
        Opportunity(
            title="Calm Alone-Time Training",
            industry="Pet Care",
            niche="First-Time Dog Owners",
            problem="Helping new dog owners keep dogs calm during short periods home alone.",
            pain_score=8,
            worsening_score=8,
            purchasing_power_score=8,
            speed_score=8,
            overall_score=8.0,
        ),
    ]

    db.add_all(opportunities)
    db.commit()

    for opportunity in opportunities:
        db.refresh(opportunity)

    return {
        "message": "Opportunities discovered!",
        "opportunities": opportunities,
    }


def _serialize_intent_brief(db, brief):
    evidence = (
        db.query(IntentEvidence)
        .filter(IntentEvidence.intent_brief_id == brief.id)
        .order_by(IntentEvidence.id.asc())
        .all()
    )
    return {
        "id": brief.id,
        "problem_discovery_id": brief.problem_discovery_id,
        "target_customer": brief.target_customer,
        "problem_context": brief.problem_context,
        "trigger": brief.trigger,
        "current_behavior": brief.current_behavior,
        "failed_alternatives": brief.failed_alternatives,
        "desired_outcome": brief.desired_outcome,
        "constraints": brief.constraints,
        "objections": brief.objections,
        "customer_language": brief.customer_language,
        "existing_solutions": brief.existing_solutions,
        "solution_gap": brief.solution_gap,
        "potential_solution": brief.potential_solution,
        "recommended_format": brief.recommended_format,
        "why_format": brief.why_format,
        "validation_questions": brief.validation_questions,
        "evidence_confidence": brief.evidence_confidence,
        "evidence_summary": brief.evidence_summary,
        "source_count": brief.source_count,
        "domain_count": brief.domain_count,
        "customer_signal_count": brief.customer_signal_count,
        "solution_seeking_count": brief.solution_seeking_count,
        "spending_signal_count": brief.spending_signal_count,
        "failed_attempt_count": brief.failed_attempt_count,
        "status": brief.status,
        "created_at": brief.created_at,
        "updated_at": brief.updated_at,
        "evidence": evidence,
    }


@app.post(
    "/intent-validation/{problem_id}",
    response_model=IntentBriefResponse,
)
def validate_intent(problem_id: int, db=Depends(get_db)):
    problem = db.get(ProblemDiscovery, problem_id)

    if problem is None:
        raise HTTPException(status_code=404, detail="Problem candidate not found")

    profile = (
        db.query(ProblemEvidenceProfile)
        .filter(ProblemEvidenceProfile.problem_discovery_id == problem.id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=409,
            detail="Problem evidence profile is missing. Run problem discovery again.",
        )

    class ProblemForIntent:
        pass

    problem_input = ProblemForIntent()
    for field in (
        "id",
        "market_direction",
        "customer_group",
        "situation",
        "problem",
        "trigger",
        "current_behavior",
    ):
        setattr(problem_input, field, getattr(problem, field))

    problem_input.evidence_profile = profile
    problem_input.existing_evidence = (
        db.query(ProblemEvidence)
        .filter(ProblemEvidence.problem_discovery_id == problem.id)
        .order_by(ProblemEvidence.id.asc())
        .all()
    )

    try:
        generated = generate_intent_validation(problem_input)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not complete INTENT validation: {exc}",
        ) from exc

    existing = (
        db.query(IntentBrief)
        .filter(IntentBrief.problem_discovery_id == problem.id)
        .first()
    )

    if existing is not None:
        db.query(IntentEvidence).filter(
            IntentEvidence.intent_brief_id == existing.id
        ).delete(synchronize_session=False)
        brief = existing
    else:
        brief = IntentBrief(problem_discovery_id=problem.id)
        db.add(brief)
        db.flush()

    evidence_items = generated.evidence_items
    domains = {
        urlparse(item.source_url).netloc.lower().removeprefix("www.")
        for item in evidence_items
        if urlparse(item.source_url).netloc
    }

    signal_types = [item.signal_type for item in evidence_items]
    customer_signals = sum(
        1
        for signal in signal_types
        if signal in {"customer_pain", "customer_language"}
    )
    solution_seeking = sum(
        1 for signal in signal_types if signal == "solution_seeking"
    )
    spending = sum(
        1 for signal in signal_types if signal == "spending"
    )
    failed_attempts = sum(
        1
        for signal in signal_types
        if signal in {"failed_attempt", "workaround"}
    )

    values = {
        "target_customer": generated.target_customer,
        "problem_context": generated.problem_context,
        "trigger": generated.trigger,
        "current_behavior": generated.current_behavior,
        "failed_alternatives": generated.failed_alternatives,
        "desired_outcome": generated.desired_outcome,
        "constraints": generated.constraints,
        "objections": generated.objections,
        "customer_language": generated.customer_language,
        "existing_solutions": generated.existing_solutions,
        "solution_gap": generated.solution_gap,
        "potential_solution": generated.potential_solution,
        "recommended_format": generated.recommended_format,
        "why_format": generated.why_format,
        "validation_questions": generated.validation_questions,
        "evidence_confidence": generated.evidence_confidence.lower(),
        "evidence_summary": generated.evidence_summary,
        "source_count": len(evidence_items),
        "domain_count": len(domains),
        "customer_signal_count": customer_signals,
        "solution_seeking_count": solution_seeking,
        "spending_signal_count": spending,
        "failed_attempt_count": failed_attempts,
        "status": "investigated",
    }

    for key, value in values.items():
        setattr(brief, key, value)

    for item in evidence_items:
        db.add(
            IntentEvidence(
                intent_brief_id=brief.id,
                source_title=item.source_title,
                source_url=item.source_url,
                source_type=item.source_type,
                signal_type=item.signal_type,
                excerpt=item.excerpt,
            )
        )

    db.commit()
    db.refresh(brief)

    return _serialize_intent_brief(db, brief)


@app.get(
    "/intent-validation/{problem_id}",
    response_model=IntentBriefResponse,
)
def get_intent_validation(problem_id: int, db=Depends(get_db)):
    problem = db.get(ProblemDiscovery, problem_id)

    if problem is None:
        raise HTTPException(status_code=404, detail="Problem candidate not found")

    brief = (
        db.query(IntentBrief)
        .filter(IntentBrief.problem_discovery_id == problem.id)
        .first()
    )

    if brief is None:
        raise HTTPException(status_code=404, detail="INTENT brief not found")

    return _serialize_intent_brief(db, brief)


@app.post(
    "/intent-validation/{problem_id}/create-product",
    response_model=dict,
)
def create_product_from_intent(
    problem_id: int,
    product_data: IntentProductCreate,
    db=Depends(get_db),
):
    problem = db.get(ProblemDiscovery, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem candidate not found")

    brief = (
        db.query(IntentBrief)
        .filter(IntentBrief.problem_discovery_id == problem.id)
        .first()
    )
    if brief is None:
        raise HTTPException(
            status_code=409,
            detail="Complete INTENT validation before creating a product.",
        )

    product_format = product_data.format.strip().lower()
    if not product_format:
        raise HTTPException(status_code=400, detail="Product format is required.")

    opportunity = Opportunity(
        title=(brief.potential_solution or problem.problem)[:200],
        industry=problem.market_direction or "Customer Problem",
        niche=brief.target_customer or problem.customer_group,
        problem=problem.problem,
        pain_score=0,
        worsening_score=0,
        purchasing_power_score=0,
        speed_score=0,
        overall_score=0,
    )
    db.add(opportunity)
    db.flush()

    product = Product(
        opportunity_id=opportunity.id,
        format=product_format,
        status="draft",
    )
    db.add(product)
    db.commit()
    db.refresh(opportunity)
    db.refresh(product)

    db.add(
        ProductIntentLink(
            product_id=product.id,
            intent_brief_id=brief.id,
        )
    )
    db.commit()

    return {
        "opportunity": {
            "id": opportunity.id,
            "title": opportunity.title,
            "industry": opportunity.industry,
            "niche": opportunity.niche,
            "problem": opportunity.problem,
            "pain_score": opportunity.pain_score,
            "worsening_score": opportunity.worsening_score,
            "purchasing_power_score": opportunity.purchasing_power_score,
            "speed_score": opportunity.speed_score,
            "overall_score": opportunity.overall_score,
        },
        "product": {
            "id": product.id,
            "opportunity_id": product.opportunity_id,
            "format": product.format,
            "status": product.status,
        },
    }


def _resolve_product_intent_brief(db, product):
    link = (
        db.query(ProductIntentLink)
        .filter(ProductIntentLink.product_id == product.id)
        .first()
    )

    if link is not None:
        return db.get(IntentBrief, link.intent_brief_id)

    opportunity = db.get(Opportunity, product.opportunity_id)
    if opportunity is None:
        return None

    # Backfill traceability for products created before the ProductIntentLink
    # table existed. The original INTENT product creation copied the validated
    # problem and target customer into the opportunity, so those fields provide
    # a deterministic bridge for existing products.
    candidate = (
        db.query(IntentBrief)
        .join(ProblemDiscovery, ProblemDiscovery.id == IntentBrief.problem_discovery_id)
        .filter(
            ProblemDiscovery.problem == opportunity.problem,
            IntentBrief.target_customer == opportunity.niche,
        )
        .order_by(IntentBrief.id.desc())
        .first()
    )

    if candidate is not None:
        db.add(
            ProductIntentLink(
                product_id=product.id,
                intent_brief_id=candidate.id,
            )
        )
        db.commit()

    return candidate


@app.get("/opportunities", response_model=list[OpportunityResponse])
def get_opportunities(db=Depends(get_db)):
    return db.query(Opportunity).all()


@app.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(
    opportunity_id: int,
    db=Depends(get_db),
):
    opportunity = db.get(Opportunity, opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    return opportunity


@app.get("/products", response_model=list[ProductResponse])
def get_products(db=Depends(get_db)):
    return db.query(Product).all()


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@app.post("/products", response_model=ProductResponse)
def create_product(
    product_data: ProductCreate,
    db=Depends(get_db),
):
    opportunity = db.get(Opportunity, product_data.opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    product = Product(
        opportunity_id=product_data.opportunity_id,
        format=product_data.format,
        status="draft",
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@app.get(
    "/products/{product_id}/transformation",
    response_model=TransformationMapResponse,
)
def get_transformation_map(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if transformation is None:
        raise HTTPException(
            status_code=404,
            detail="Transformation map not found",
        )

    return transformation


@app.post(
    "/products/{product_id}/transformation",
    response_model=TransformationMapResponse,
)
def create_transformation_map(
    product_id: int,
    transformation_data: TransformationMapCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    existing_transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if existing_transformation is not None:
        raise HTTPException(
            status_code=400,
            detail="Transformation map already exists for this product",
        )

    transformation = TransformationMap(
        product_id=product_id,
        **transformation_data.model_dump(),
    )

    db.add(transformation)
    db.commit()
    db.refresh(transformation)

    return transformation


@app.put(
    "/products/{product_id}/transformation",
    response_model=TransformationMapResponse,
)
def update_transformation_map(
    product_id: int,
    transformation_data: TransformationMapCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if transformation is None:
        raise HTTPException(
            status_code=404,
            detail="Transformation map not found",
        )

    data = transformation_data.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(transformation, field, value)

    db.commit()
    db.refresh(transformation)

    return transformation


class GeneratedTransformationResponse(BaseModel):
    before_emotional_state: str
    before_core_fear: str
    before_daily_experience: str
    before_identity: str
    after_emotional_state: str
    after_core_fear: str
    after_daily_experience: str
    after_identity: str


@app.post(
    "/products/{product_id}/transformation/generate",
    response_model=GeneratedTransformationResponse,
)
def generate_product_transformation(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    opportunity = db.get(Opportunity, product.opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    try:
        generated = generate_transformation_map(opportunity)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate transformation map: {exc}",
        ) from exc

    return generated


@app.post(
    "/products/{product_id}/summary/generate",
    response_model=GeneratedProductSummaryResponse,
)
def generate_product_summary_endpoint(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    opportunity = db.get(Opportunity, product.opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if transformation is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product transformation before generating the product summary.",
        )

    try:
        generated = generate_product_summary(
            opportunity,
            transformation,
            product.format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate product summary: {exc}",
        ) from exc

    return generated


@app.get(
    "/products/{product_id}/summary",
    response_model=ProductSummaryResponse,
)
def get_product_summary(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Product summary not found",
        )

    return summary


@app.post(
    "/products/{product_id}/summary",
    response_model=ProductSummaryResponse,
)
def create_product_summary(
    product_id: int,
    summary_data: ProductSummaryCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    existing_summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )

    if existing_summary is not None:
        raise HTTPException(
            status_code=400,
            detail="Product summary already exists for this product",
        )

    summary = ProductSummary(
        product_id=product_id,
        **summary_data.model_dump(),
    )

    db.add(summary)
    mark_package_stale(db, product_id)
    db.commit()
    db.refresh(summary)

    return summary


@app.put(
    "/products/{product_id}/summary",
    response_model=ProductSummaryResponse,
)
def update_product_summary(
    product_id: int,
    summary_data: ProductSummaryCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Product summary not found",
        )

    data = summary_data.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(summary, field, value)

    db.commit()
    db.refresh(summary)

    return summary





@app.post(
    "/products/{product_id}/outline/generate",
    response_model=GeneratedProductOutlineResponse,
)
def generate_product_outline_endpoint(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    opportunity = db.get(Opportunity, product.opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if transformation is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product transformation before generating the product outline.",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )

    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product summary before generating the product outline.",
        )

    try:
        generated = generate_product_outline(
            opportunity,
            transformation,
            summary,
            product.format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate product outline: {exc}",
        ) from exc

    return generated



@app.get(
    "/products/{product_id}/outline",
    response_model=ProductOutlineResponse,
)
def get_product_outline(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    return outline


@app.post(
    "/products/{product_id}/outline",
    response_model=ProductOutlineResponse,
)
def create_product_outline(
    product_id: int,
    outline_data: ProductOutlineCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    existing_outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if existing_outline is not None:
        raise HTTPException(
            status_code=400,
            detail="Product outline already exists for this product",
        )

    outline = ProductOutline(
        product_id=product_id,
        status=outline_data.status or "draft",
    )

    db.add(outline)
    db.commit()
    db.refresh(outline)

    return outline


@app.put(
    "/products/{product_id}/outline",
    response_model=ProductOutlineResponse,
)
def update_product_outline(
    product_id: int,
    outline_data: ProductOutlineCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    outline.status = outline_data.status or "draft"

    db.commit()
    db.refresh(outline)

    return outline


@app.get(
    "/products/{product_id}/outline/sections",
    response_model=list[SectionResponse],
)
def get_product_sections(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    return (
        db.query(Section)
        .filter(Section.outline_id == outline.id)
        .order_by(Section.position)
        .all()
    )


@app.post(
    "/products/{product_id}/outline/sections",
    response_model=SectionResponse,
)
def create_product_section(
    product_id: int,
    section_data: SectionCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    section = Section(
        outline_id=outline.id,
        position=section_data.position,
        title=section_data.title,
        purpose=section_data.purpose,
        status=section_data.status or "draft",
    )

    db.add(section)
    db.commit()
    db.refresh(section)

    return section


@app.put(
    "/products/{product_id}/outline/sections/{section_id}",
    response_model=SectionResponse,
)
def update_product_section(
    product_id: int,
    section_id: int,
    section_data: SectionCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    section = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.outline_id == outline.id,
        )
        .first()
    )

    if section is None:
        raise HTTPException(
            status_code=404,
            detail="Section not found",
        )

    section.position = section_data.position
    section.title = section_data.title
    section.purpose = section_data.purpose
    section.status = section_data.status or "draft"

    db.commit()
    db.refresh(section)

    return section


@app.post(
    "/products/{product_id}/outline/briefs/generate",
    response_model=GeneratedSectionBriefsResponse,
)
def generate_section_briefs_endpoint(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    opportunity = db.get(Opportunity, product.opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if transformation is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product transformation before generating section briefs.",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )

    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product summary before generating section briefs.",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product outline before generating section briefs.",
        )

    sections = (
        db.query(Section)
        .filter(Section.outline_id == outline.id)
        .order_by(Section.position)
        .all()
    )

    if len(sections) < 7 or len(sections) > 12:
        raise HTTPException(
            status_code=400,
            detail=(
                "The saved product outline must contain between 7 and 12 "
                "sections before generating section briefs."
            ),
        )

    try:
        generated = generate_section_briefs(
            opportunity,
            transformation,
            summary,
            sections,
            product.format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate section briefs: {exc}",
        ) from exc

    return generated


@app.get(
    "/products/{product_id}/outline/briefs",
    response_model=list[SectionBriefResponse],
)
def get_section_briefs(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    section_ids = [
        section.id
        for section in (
            db.query(Section)
            .filter(Section.outline_id == outline.id)
            .all()
        )
    ]

    if not section_ids:
        return []

    return (
        db.query(SectionBrief)
        .filter(SectionBrief.section_id.in_(section_ids))
        .join(Section, Section.id == SectionBrief.section_id)
        .order_by(Section.position)
        .all()
    )


@app.post(
    "/products/{product_id}/outline/sections/{section_id}/brief",
    response_model=SectionBriefResponse,
)
def create_section_brief(
    product_id: int,
    section_id: int,
    brief_data: SectionBriefCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    section = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.outline_id == outline.id,
        )
        .first()
    )

    if section is None:
        raise HTTPException(
            status_code=404,
            detail="Section not found",
        )

    existing = (
        db.query(SectionBrief)
        .filter(SectionBrief.section_id == section_id)
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Section brief already exists for this section",
        )

    brief = SectionBrief(
        section_id=section_id,
        objective=brief_data.objective,
        key_concepts=brief_data.key_concepts,
        practical_steps=brief_data.practical_steps,
        example_scenario=brief_data.example_scenario,
        common_mistakes=brief_data.common_mistakes,
        reader_outcome=brief_data.reader_outcome,
        status=brief_data.status or "draft",
    )

    db.add(brief)
    db.commit()
    db.refresh(brief)

    return brief


@app.put(
    "/products/{product_id}/outline/sections/{section_id}/brief",
    response_model=SectionBriefResponse,
)
def update_section_brief(
    product_id: int,
    section_id: int,
    brief_data: SectionBriefCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    section = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.outline_id == outline.id,
        )
        .first()
    )

    if section is None:
        raise HTTPException(
            status_code=404,
            detail="Section not found",
        )

    brief = (
        db.query(SectionBrief)
        .filter(SectionBrief.section_id == section_id)
        .first()
    )

    if brief is None:
        raise HTTPException(
            status_code=404,
            detail="Section brief not found",
        )

    data = brief_data.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(brief, field, value)

    db.commit()
    db.refresh(brief)

    return brief


@app.post(
    "/products/{product_id}/outline/blueprints/generate",
    response_model=GeneratedContentBlueprintsResponse,
)
def generate_content_blueprints_endpoint(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    opportunity = db.get(Opportunity, product.opportunity_id)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )

    if transformation is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product transformation before generating content blueprints.",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )

    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product summary before generating content blueprints.",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product outline before generating content blueprints.",
        )

    sections = (
        db.query(Section)
        .filter(Section.outline_id == outline.id)
        .order_by(Section.position)
        .all()
    )

    if len(sections) < 7 or len(sections) > 12:
        raise HTTPException(
            status_code=400,
            detail=(
                "The saved product outline must contain between 7 and 12 "
                "sections before generating content blueprints."
            ),
        )

    section_ids = [section.id for section in sections]
    saved_briefs = (
        db.query(SectionBrief)
        .filter(SectionBrief.section_id.in_(section_ids))
        .all()
    )

    brief_by_section_id = {
        brief.section_id: brief
        for brief in saved_briefs
    }

    missing_briefs = [
        section.position
        for section in sections
        if section.id not in brief_by_section_id
    ]

    if missing_briefs:
        raise HTTPException(
            status_code=400,
            detail=(
                "Save section briefs for every outline section before generating "
                "content blueprints. Missing sections: "
                + ", ".join(str(position) for position in missing_briefs)
            ),
        )

    try:
        generated = generate_content_blueprints(
            opportunity,
            transformation,
            summary,
            sections,
            saved_briefs,
            product.format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate content blueprints: {exc}",
        ) from exc

    return generated


@app.get(
    "/products/{product_id}/outline/blueprints",
    response_model=list[ContentBlueprintResponse],
)
def get_content_blueprints(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(
            status_code=404,
            detail="Product outline not found",
        )

    section_ids = [
        section.id
        for section in (
            db.query(Section)
            .filter(Section.outline_id == outline.id)
            .all()
        )
    ]

    if not section_ids:
        return []

    return (
        db.query(ContentBlueprint)
        .filter(ContentBlueprint.section_id.in_(section_ids))
        .join(Section, Section.id == ContentBlueprint.section_id)
        .order_by(Section.position)
        .all()
    )


@app.post(
    "/products/{product_id}/outline/sections/{section_id}/blueprint",
    response_model=ContentBlueprintResponse,
)
def create_content_blueprint(
    product_id: int,
    section_id: int,
    blueprint_data: ContentBlueprintCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    section = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.outline_id == outline.id,
        )
        .first()
    )

    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    existing = (
        db.query(ContentBlueprint)
        .filter(ContentBlueprint.section_id == section_id)
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Content blueprint already exists for this section",
        )

    blueprint = ContentBlueprint(
        section_id=section_id,
        **blueprint_data.model_dump(),
    )

    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)

    return blueprint


@app.put(
    "/products/{product_id}/outline/sections/{section_id}/blueprint",
    response_model=ContentBlueprintResponse,
)
def update_content_blueprint(
    product_id: int,
    section_id: int,
    blueprint_data: ContentBlueprintCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )

    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    section = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.outline_id == outline.id,
        )
        .first()
    )

    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    blueprint = (
        db.query(ContentBlueprint)
        .filter(ContentBlueprint.section_id == section_id)
        .first()
    )

    if blueprint is None:
        raise HTTPException(
            status_code=404,
            detail="Content blueprint not found",
        )

    data = blueprint_data.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(blueprint, field, value)

    db.commit()
    db.refresh(blueprint)

    return blueprint


@app.post(
    "/products/{product_id}/reader-experience/generate",
    response_model=GeneratedReaderExperiencesResponse,
)
def generate_reader_experience_endpoint(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    opportunity = db.get(Opportunity, product.opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    intent_brief = _resolve_product_intent_brief(db, product)
    if intent_brief is None:
        raise HTTPException(
            status_code=400,
            detail="This product is not linked to a validated INTENT brief.",
        )

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )
    if transformation is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product transformation before generating reader experience plans.",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )
    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product summary before generating reader experience plans.",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product outline before generating reader experience plans.",
        )

    sections = (
        db.query(Section)
        .filter(Section.outline_id == outline.id)
        .order_by(Section.position)
        .all()
    )

    if len(sections) < 7 or len(sections) > 12:
        raise HTTPException(
            status_code=400,
            detail="The saved product outline must contain between 7 and 12 sections.",
        )

    section_ids = [section.id for section in sections]
    section_briefs = (
        db.query(SectionBrief)
        .filter(SectionBrief.section_id.in_(section_ids))
        .all()
    )
    content_blueprints = (
        db.query(ContentBlueprint)
        .filter(ContentBlueprint.section_id.in_(section_ids))
        .all()
    )

    if len(section_briefs) != len(sections):
        raise HTTPException(
            status_code=400,
            detail="Save section briefs for every outline section before generating reader experience plans.",
        )

    if len(content_blueprints) != len(sections):
        raise HTTPException(
            status_code=400,
            detail="Save content blueprints for every outline section before generating reader experience plans.",
        )

    evidence = (
        db.query(IntentEvidence)
        .filter(IntentEvidence.intent_brief_id == intent_brief.id)
        .order_by(IntentEvidence.id.asc())
        .all()
    )

    try:
        generated = generate_reader_experiences(
            opportunity,
            intent_brief,
            evidence,
            transformation,
            summary,
            sections,
            section_briefs,
            content_blueprints,
            product.format,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate reader experience plans: {exc}",
        ) from exc

    return generated


@app.get(
    "/products/{product_id}/reader-experience",
    response_model=list[ReaderExperienceResponse],
)
def get_reader_experiences(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    return (
        db.query(ReaderExperience)
        .join(Section, Section.id == ReaderExperience.section_id)
        .filter(
            ReaderExperience.product_id == product_id,
            Section.outline_id == outline.id,
        )
        .order_by(Section.position)
        .all()
    )


@app.post(
    "/products/{product_id}/reader-experience/sections/{section_id}",
    response_model=ReaderExperienceResponse,
)
def create_reader_experience(
    product_id: int,
    section_id: int,
    experience_data: ReaderExperienceCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    section = (
        db.query(Section)
        .filter(Section.id == section_id, Section.outline_id == outline.id)
        .first()
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    existing = (
        db.query(ReaderExperience)
        .filter(ReaderExperience.section_id == section_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Reader experience already exists for this section",
        )

    intent_brief = _resolve_product_intent_brief(db, product)

    experience = ReaderExperience(
        product_id=product_id,
        section_id=section_id,
        intent_brief_id=intent_brief.id if intent_brief else None,
        **experience_data.model_dump(),
    )
    db.add(experience)
    db.commit()
    db.refresh(experience)
    return experience


@app.put(
    "/products/{product_id}/reader-experience/sections/{section_id}",
    response_model=ReaderExperienceResponse,
)
def update_reader_experience(
    product_id: int,
    section_id: int,
    experience_data: ReaderExperienceCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    section = (
        db.query(Section)
        .filter(Section.id == section_id, Section.outline_id == outline.id)
        .first()
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    experience = (
        db.query(ReaderExperience)
        .filter(
            ReaderExperience.product_id == product_id,
            ReaderExperience.section_id == section_id,
        )
        .first()
    )
    if experience is None:
        raise HTTPException(status_code=404, detail="Reader experience not found")

    data = experience_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(experience, field, value)

    db.commit()
    db.refresh(experience)
    return experience


@app.post(
    "/products/{product_id}/manuscript/sections/{section_id}/generate",
    response_model=GeneratedManuscriptSectionResponse,
)
def generate_manuscript_section_endpoint(
    product_id: int,
    section_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    opportunity = db.get(Opportunity, product.opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    transformation = (
        db.query(TransformationMap)
        .filter(TransformationMap.product_id == product_id)
        .first()
    )
    if transformation is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product transformation before generating the manuscript.",
        )

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )
    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product summary before generating the manuscript.",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(
            status_code=400,
            detail="Save the product outline before generating the manuscript.",
        )

    section = (
        db.query(Section)
        .filter(Section.id == section_id, Section.outline_id == outline.id)
        .first()
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    section_brief = (
        db.query(SectionBrief)
        .filter(SectionBrief.section_id == section_id)
        .first()
    )
    if section_brief is None:
        raise HTTPException(
            status_code=400,
            detail="Save the section brief before generating the manuscript section.",
        )

    content_blueprint = (
        db.query(ContentBlueprint)
        .filter(ContentBlueprint.section_id == section_id)
        .first()
    )
    if content_blueprint is None:
        raise HTTPException(
            status_code=400,
            detail="Save the content blueprint before generating the manuscript section.",
        )

    reader_experience = (
        db.query(ReaderExperience)
        .filter(
            ReaderExperience.product_id == product_id,
            ReaderExperience.section_id == section_id,
        )
        .first()
    )
    if reader_experience is None:
        raise HTTPException(
            status_code=400,
            detail="Save the Reader Experience plan for this section before generating the manuscript.",
        )

    intent_brief = _resolve_product_intent_brief(db, product)
    if intent_brief is None:
        raise HTTPException(
            status_code=400,
            detail="The product is missing its validated INTENT context.",
        )

    previous_section = (
        db.query(Section)
        .filter(
            Section.outline_id == outline.id,
            Section.position == section.position - 1,
        )
        .first()
    )
    next_section = (
        db.query(Section)
        .filter(
            Section.outline_id == outline.id,
            Section.position == section.position + 1,
        )
        .first()
    )

    try:
        generated = generate_manuscript_section(
            opportunity,
            transformation,
            summary,
            section,
            section_brief,
            content_blueprint,
            product_format=product.format,
            previous_section=previous_section,
            next_section=next_section,
            reader_experience=reader_experience,
            intent_brief=intent_brief,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate manuscript section: {exc}",
        ) from exc

    content = generated.content.strip()
    word_count = len(content.split())

    return GeneratedManuscriptSectionResponse(
        section_id=section.id,
        position=section.position,
        title=section.title,
        content=content,
        word_count=word_count,
    )


@app.get(
    "/products/{product_id}/manuscript",
    response_model=list[ManuscriptSectionResponse],
)
def get_manuscript(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    return (
        db.query(ManuscriptSection)
        .join(Section, Section.id == ManuscriptSection.section_id)
        .filter(Section.outline_id == outline.id)
        .order_by(Section.position)
        .all()
    )


@app.post(
    "/products/{product_id}/manuscript/sections/{section_id}",
    response_model=ManuscriptSectionResponse,
)
def create_manuscript_section(
    product_id: int,
    section_id: int,
    manuscript_data: ManuscriptSectionCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    section = (
        db.query(Section)
        .filter(Section.id == section_id, Section.outline_id == outline.id)
        .first()
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    existing = (
        db.query(ManuscriptSection)
        .filter(ManuscriptSection.section_id == section_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Manuscript section already exists for this section",
        )

    content = (manuscript_data.content or "").strip()
    manuscript = ManuscriptSection(
        section_id=section_id,
        content=content,
        word_count=len(content.split()),
        status=manuscript_data.status or "draft",
    )

    db.add(manuscript)
    mark_package_stale(db, product_id)
    db.commit()
    db.refresh(manuscript)
    return manuscript


@app.put(
    "/products/{product_id}/manuscript/sections/{section_id}",
    response_model=ManuscriptSectionResponse,
)
def update_manuscript_section(
    product_id: int,
    section_id: int,
    manuscript_data: ManuscriptSectionCreate,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=404, detail="Product outline not found")

    section = (
        db.query(Section)
        .filter(Section.id == section_id, Section.outline_id == outline.id)
        .first()
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    manuscript = (
        db.query(ManuscriptSection)
        .filter(ManuscriptSection.section_id == section_id)
        .first()
    )
    if manuscript is None:
        raise HTTPException(status_code=404, detail="Manuscript section not found")

    content = (manuscript_data.content or "").strip()
    manuscript.content = content
    manuscript.word_count = len(content.split())
    manuscript.status = manuscript_data.status or manuscript.status or "draft"

    mark_package_stale(db, product_id)
    db.commit()
    db.refresh(manuscript)
    return manuscript


def _brand_response(product_id: int, brand: dict, record: BrandKit | None = None):
    return BrandKitResponse(
        id=record.id if record else None,
        product_id=product_id,
        brand_name=brand["brand_name"],
        tagline=brand["tagline"],
        visual_direction=brand["visual_direction"],
        palette_name=brand["palette_name"],
        primary_color=brand["primary_color"],
        secondary_color=brand["secondary_color"],
        accent_color=brand["accent_color"],
        background_color=brand["background_color"],
        text_color=brand["text_color"],
        heading_font=brand["heading_font"],
        body_font=brand["body_font"],
        cover_layout=brand["cover_layout"],
        cover_svg=brand["cover_svg"],
        social_card_svg=brand["social_card_svg"],
        thumbnail_svg=brand["thumbnail_svg"],
        status=brand.get("status", "draft"),
    )


@app.get("/products/{product_id}/branding", response_model=BrandKitResponse)
def get_product_branding(product_id: int, db=Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    brand = db.query(BrandKit).filter(BrandKit.product_id == product_id).first()
    if brand is None:
        raise HTTPException(status_code=404, detail="Product branding not found")

    data = {column.name: getattr(brand, column.name) for column in BrandKit.__table__.columns}
    return _brand_response(product_id, data, brand)


@app.post("/products/{product_id}/branding/generate", response_model=GeneratedBrandKitResponse)
def generate_product_branding(product_id: int, db=Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    opportunity = db.get(Opportunity, product.opportunity_id)
    summary = db.query(ProductSummary).filter(ProductSummary.product_id == product_id).first()
    transformation = db.query(TransformationMap).filter(TransformationMap.product_id == product_id).first()

    if opportunity is None or summary is None or not (summary.title or "").strip():
        raise HTTPException(status_code=400, detail="Save the product summary before generating branding.")
    if transformation is None:
        raise HTTPException(status_code=400, detail="Save the product transformation before generating branding.")

    try:
        generated = generate_brand_kit(opportunity, transformation, summary, product.format)
        brand = normalize_brand(generated)
        assets = build_assets(summary.title, summary.subtitle or "", brand)
        brand.update(assets)
        brand["status"] = "draft"
        return _brand_response(product_id, brand)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not generate product branding: {exc}") from exc


@app.post("/products/{product_id}/branding", response_model=BrandKitResponse)
def create_product_branding(product_id: int, branding: BrandKitCreate, db=Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    summary = db.query(ProductSummary).filter(ProductSummary.product_id == product_id).first()
    if summary is None or not (summary.title or "").strip():
        raise HTTPException(status_code=400, detail="Save the product summary before saving branding.")

    existing = db.query(BrandKit).filter(BrandKit.product_id == product_id).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Product branding already exists")

    source = normalize_brand(branding.model_dump(exclude_none=True))
    source.pop("status", None)
    source.update(build_assets(summary.title, summary.subtitle or "", source))
    record = BrandKit(product_id=product_id, **source, status=branding.status or "reviewed")
    db.add(record)
    mark_package_stale(db, product_id)
    db.commit()
    db.refresh(record)
    data = {column.name: getattr(record, column.name) for column in BrandKit.__table__.columns}
    return _brand_response(product_id, data, record)


@app.put("/products/{product_id}/branding", response_model=BrandKitResponse)
def update_product_branding(product_id: int, branding: BrandKitCreate, db=Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    summary = db.query(ProductSummary).filter(ProductSummary.product_id == product_id).first()
    if summary is None or not (summary.title or "").strip():
        raise HTTPException(status_code=400, detail="Save the product summary before saving branding.")

    record = db.query(BrandKit).filter(BrandKit.product_id == product_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Product branding not found")

    source = normalize_brand(branding.model_dump(exclude_none=True))
    for key in [
        "brand_name", "tagline", "visual_direction", "palette_name",
        "primary_color", "secondary_color", "accent_color", "background_color",
        "text_color", "heading_font", "body_font", "cover_layout"
    ]:
        setattr(record, key, source[key])

    assets = build_assets(summary.title, summary.subtitle or "", source)
    record.cover_svg = assets["cover_svg"]
    record.social_card_svg = assets["social_card_svg"]
    record.thumbnail_svg = assets["thumbnail_svg"]
    record.status = branding.status or "reviewed"

    mark_package_stale(db, product_id)
    db.commit()
    db.refresh(record)
    data = {column.name: getattr(record, column.name) for column in BrandKit.__table__.columns}
    return _brand_response(product_id, data, record)


@app.get("/products/{product_id}/branding/assets/{asset_type}")
def get_product_brand_asset(product_id: int, asset_type: str, db=Depends(get_db)):
    record = db.query(BrandKit).filter(BrandKit.product_id == product_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Product branding not found")

    field_map = {
        "cover": "cover_svg",
        "social": "social_card_svg",
        "thumbnail": "thumbnail_svg",
    }
    field = field_map.get(asset_type)
    if field is None:
        raise HTTPException(status_code=404, detail="Unknown branding asset")

    svg = getattr(record, field) or ""
    if not svg:
        raise HTTPException(status_code=404, detail="Branding asset not found")

    return Response(content=svg, media_type="image/svg+xml")


@app.get(
    "/products/{product_id}/package",
    response_model=ProductPackageResponse,
)
def get_product_package(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    package = (
        db.query(ProductPackage)
        .filter(ProductPackage.product_id == product_id)
        .first()
    )
    if package is None:
        raise HTTPException(status_code=404, detail="Product package not found")

    return package


@app.post(
    "/products/{product_id}/package/generate",
    response_model=ProductPackageResponse,
)
def generate_product_package(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    summary = (
        db.query(ProductSummary)
        .filter(ProductSummary.product_id == product_id)
        .first()
    )
    if summary is None or not (summary.title or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Save the product summary before packaging the product.",
        )

    outline = (
        db.query(ProductOutline)
        .filter(ProductOutline.product_id == product_id)
        .first()
    )
    if outline is None:
        raise HTTPException(status_code=400, detail="Save the product outline before packaging the product.")

    sections = (
        db.query(Section)
        .filter(Section.outline_id == outline.id)
        .order_by(Section.position)
        .all()
    )
    if not sections:
        raise HTTPException(status_code=400, detail="The product outline has no sections.")

    manuscripts = (
        db.query(ManuscriptSection)
        .join(Section, Section.id == ManuscriptSection.section_id)
        .filter(Section.outline_id == outline.id)
        .all()
    )
    manuscript_by_section_id = {item.section_id: item for item in manuscripts}

    missing = [
        section.title
        for section in sections
        if section.id not in manuscript_by_section_id
        or not (manuscript_by_section_id[section.id].content or "").strip()
        or manuscript_by_section_id[section.id].status != "reviewed"
    ]
    if missing:
        preview = ", ".join(missing[:3])
        if len(missing) > 3:
            preview += ", and more"
        raise HTTPException(
            status_code=400,
            detail=f"Save every manuscript section before packaging. Missing or unsaved: {preview}",
        )

    total_word_count = sum(
        len((manuscript_by_section_id[section.id].content or "").split())
        for section in sections
    )

    package_dir = Path("storage") / "products" / str(product_id)
    pdf_path = package_dir / "product.pdf"
    section_payload = [
        (
            section.position,
            section.title,
            manuscript_by_section_id[section.id].content or "",
        )
        for section in sections
    ]

    brand_record = db.query(BrandKit).filter(BrandKit.product_id == product_id).first()
    brand_data = None
    if brand_record is not None:
        brand_data = {
            "brand_name": brand_record.brand_name,
            "tagline": brand_record.tagline,
            "primary_color": brand_record.primary_color,
            "secondary_color": brand_record.secondary_color,
            "accent_color": brand_record.accent_color,
            "background_color": brand_record.background_color,
            "text_color": brand_record.text_color,
            "heading_font": brand_record.heading_font,
            "body_font": brand_record.body_font,
        }

    try:
        generate_product_pdf(
            str(pdf_path),
            summary.title or "Untitled Product",
            summary.subtitle or "",
            summary.about or "",
            summary.bonus_materials or "",
            section_payload,
            branding=brand_data,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not create the product PDF: {exc}",
        ) from exc

    package = (
        db.query(ProductPackage)
        .filter(ProductPackage.product_id == product_id)
        .first()
    )
    now = datetime.now().isoformat(timespec="seconds")
    if package is None:
        package = ProductPackage(
            product_id=product_id,
            title=summary.title or "Untitled Product",
            subtitle=summary.subtitle or "",
            section_count=len(sections),
            total_word_count=total_word_count,
            pdf_path=str(pdf_path),
            status="packaged",
            generated_at=now,
        )
        db.add(package)
    else:
        package.title = summary.title or "Untitled Product"
        package.subtitle = summary.subtitle or ""
        package.section_count = len(sections)
        package.total_word_count = total_word_count
        package.pdf_path = str(pdf_path)
        package.status = "packaged"
        package.generated_at = now

    db.commit()
    db.refresh(package)
    return package


@app.get("/products/{product_id}/package/pdf")
def get_product_package_pdf(
    product_id: int,
    db=Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    package = (
        db.query(ProductPackage)
        .filter(ProductPackage.product_id == product_id)
        .first()
    )
    if package is None or not package.pdf_path:
        raise HTTPException(status_code=404, detail="Product PDF not found")

    pdf_path = Path(package.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Product PDF file not found")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="nova-product.pdf",
    )
