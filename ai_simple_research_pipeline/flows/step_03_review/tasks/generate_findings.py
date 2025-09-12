from enum import StrEnum
from typing import Literal

from ai_pipeline_core import (
    AIMessages,
    DocumentList,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)
from pydantic import BaseModel, ConfigDict, Field

from ai_simple_research_pipeline.documents.flow import (
    InitialSummaryDocument,
    ReviewFindingDocument,
)

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


class Category(StrEnum):
    """Investment review category taxonomy."""

    TECH = "tech"
    PRODUCT = "product"
    MARKET = "market"
    TEAM = "team"
    LEGAL = "legal"
    FINANCE = "finance"
    GO_TO_MARKET = "go_to_market"
    COMPETITION = "competition"
    SECURITY = "security"
    REGULATORY = "regulatory"


class Severity(StrEnum):
    """Risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Horizon(StrEnum):
    """Time horizon for risks."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Citation(BaseModel):
    """Evidence citation from standardized documents."""

    model_config = ConfigDict(frozen=True)

    file: str = Field(description="standardized filename")
    quote: str = Field(description="verbatim short snippet or bullet")


class Risk(BaseModel):
    """Investment risk with severity and mitigation."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    category: Category
    severity: Severity
    horizon: Horizon
    description: str
    evidence: list[Citation]
    mitigation: list[str]
    confidence: float = Field(ge=0, le=1)


class Opportunity(BaseModel):
    """Investment opportunity with impact assessment."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    category: Category
    impact: Literal["moderate", "high", "transformational"]
    description: str
    prerequisites: list[str]
    evidence: list[Citation]
    confidence: float = Field(ge=0, le=1)


class Question(BaseModel):
    """Investor question for diligence."""

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    rationale: str
    expected_signal: str
    evidence: list[Citation]


class Findings(BaseModel):
    """Complete set of investment findings."""

    model_config = ConfigDict(frozen=True)

    risks: list[Risk] = Field(min_length=5, max_length=5)
    opportunities: list[Opportunity] = Field(min_length=5, max_length=5)
    questions: list[Question] = Field(min_length=5, max_length=5)


@pipeline_task
async def generate_findings(
    standardized_documents: DocumentList,
    initial_summary: InitialSummaryDocument,
    model: ModelName,
    project_name: str,
) -> tuple[ReviewFindingDocument, ReviewFindingDocument, ReviewFindingDocument]:
    """Generate investment findings: risks, opportunities, and questions."""
    prompt = prompt_manager.get("generate_findings", project_name=project_name)

    # Static context with all documents for caching
    context = AIMessages(list(standardized_documents) + [initial_summary])
    messages = AIMessages([prompt])

    result = await llm.generate_structured(
        model,
        Findings,
        context=context,
        messages=messages,
    )

    findings = result.parsed

    # Create three separate documents for each finding type
    risks_doc = ReviewFindingDocument.create(
        name=ReviewFindingDocument.FILES.RISKS,
        content={"risks": [risk.model_dump() for risk in findings.risks]},
    )

    opportunities_doc = ReviewFindingDocument.create(
        name=ReviewFindingDocument.FILES.OPPORTUNITIES,
        content={"opportunities": [opp.model_dump() for opp in findings.opportunities]},
    )

    questions_doc = ReviewFindingDocument.create(
        name=ReviewFindingDocument.FILES.QUESTIONS,
        content={"questions": [q.model_dump() for q in findings.questions]},
    )

    return risks_doc, opportunities_doc, questions_doc
