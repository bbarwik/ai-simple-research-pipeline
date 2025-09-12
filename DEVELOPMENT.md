# Development Guide

A production-ready template for building sophisticated AI-powered pipelines using the ai-pipeline-core framework.

## Introduction

This template demonstrates how to build production AI pipelines using ai-pipeline-core. The framework provides a robust foundation for orchestrating multi-agent AI workflows with type safety, immutability, and comprehensive observability.

### Key Framework Features

- **Document-centric architecture** with immutable Pydantic models
- **Type-safe workflow definitions** through FlowConfig validation
- **Built-in retry logic and cost tracking** for LLM operations
- **Unified logging and tracing** with LMNR integration
- **Async-first design** for maximum performance
- **Flow-centric organization** with colocated tasks

### Technology Stack

- **Python 3.12+** (required for modern type hints)
- **ai-pipeline-core>=0.2.0** as the core framework
- **Prefect** for workflow orchestration
- **Pydantic** for data validation
- **httpx** for async HTTP operations

### Project Policy

- **FILES enum**: Use FILES enum when filename identity matters across steps. Documents that accept any file don't need FILES enum since filenames aren't pre-defined.
- **Models**: Always use type `ModelName` for model parameters and variables; always pass models from flow_options (e.g., `flow_options.core_model`).
- **Vision and structured-output**: Assume all models support documents/vision; search models (`*-search`) do not support structured output.

## Quick Start

### Installation

```bash
# Install the package
pip install -e .

# For development
make install-dev
```

### Running the Pipeline

```bash
# Full pipeline with defaults
python -m ai_pipeline ./projects/my_project

# Specific flows (by index, 1-based)
python -m ai_pipeline ./projects/my_project --start 2 --end 3
# Note: --start/--end indices are 1-based in this template's runner
# Example: --start 2 --end 3 runs the 2nd and 3rd flows

# With custom models
python -m ai_pipeline ./projects/my_project \
    --core-model "gpt-5" \
    --small-model "gpt-5-mini"

# Debug mode
LMNR_DEBUG=true python -m ai_pipeline ./projects/my_project
```

## Project Structure

### Flow-Centric Organization

The template follows a flow-centric architecture where each workflow is self-contained:

**Note**: The examples below show the general structure. Actual implementations may vary based on project needs.

```
ai_pipeline/
├── documents/                      # Document type definitions
│   ├── flow/                      # Flow documents (persistent across flows)
│   │   └── example_document.py    # ExampleDocument(FlowDocument)
│   └── task/                      # Task documents (temporary within tasks)
│       └── draft_document.py      # DraftDocument(TaskDocument)
│
├── flows/                          # Pipeline flows with colocated tasks
│   ├── __init__.py                # Exports FLOWS lists
│   └── step_01_example/           # Example flow
│       ├── __init__.py
│       ├── example_flow.py        # Flow definition with FlowConfig
│       └── tasks/                 # Flow-specific tasks
│           ├── __init__.py
│           ├── process_task.py    # Task implementation
│           └── process_task.jinja2 # Colocated prompt template (matching name)
│
├── tasks/                         # Shared tasks (used by multiple flows)
│   └── validate/                  # Task category folder
│       ├── validate.py            # Example shared task
│       └── validate.jinja2        # Prompt template for validate task
│
├── prompts/                        # Shared prompt templates
│   └── common.jinja2
│
├── flow_options.py                # ProjectFlowOptions configuration
└── __main__.py                    # CLI entry point
```

### Key Organizational Rules

1. **Flow-specific tasks** live in `flows/{flow_name}/tasks/`
2. **Jinja2 templates** are colocated with their task files and MUST have matching names
3. **Shared tasks** (used by 2+ flows) go in `tasks/{task_category}/` directory
4. **Shared prompts** go in `prompts/` directory
5. **Each flow** is self-contained with all dependencies
6. **flows/__init__.py** must export FLOWS list
7. **One file = one document class** in `documents/` directory
8. **Pydantic models** used by documents should be defined in the same file

## Core Development Patterns

### Flow Definition Pattern

Every flow follows this exact pattern:

```python
from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow
from ai_pipeline.flow_options import ProjectFlowOptions
from ai_pipeline.documents.flow import InputDocument, OutputDocument
from .tasks import process_task

class MyFlowConfig(FlowConfig):
    """Configuration for my flow."""

    # CRITICAL: Each flow MUST have a unique OUTPUT_DOCUMENT_TYPE!
    # The OUTPUT_DOCUMENT_TYPE should NOT be in INPUT_DOCUMENT_TYPES
    # to prevent circular dependencies between flows.
    INPUT_DOCUMENT_TYPES = [InputDocument]
    OUTPUT_DOCUMENT_TYPE = OutputDocument  # Must be a different class

@pipeline_flow(config=MyFlowConfig)  # config parameter is required in v0.2.0+
async def my_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    """Process documents through my flow."""

    # Step 1: Get input documents (validates types automatically)
    input_docs = documents.filter_by(MyFlowConfig.INPUT_DOCUMENT_TYPES)

    # Step 2: Process with tasks
    # If task returns a document, use it directly
    result_doc = await process_task(
        documents=input_docs,
        model=flow_options.core_model,
    )

    # Step 3: MUST use create_and_validate_output
    # If task returns the correct document type, pass it directly
    return MyFlowConfig.create_and_validate_output([result_doc])
```

### Task Implementation Pattern

Every task follows this structure:

```python
from ai_pipeline_core import (
    AIMessages, DocumentList, ModelName,
    PromptManager, get_pipeline_logger,
    llm, pipeline_task
)

# Module-level initialization (NOT inside functions!)
prompt_manager = PromptManager(__file__)  # Must be at module scope
logger = get_pipeline_logger(__name__)  # Must be at module scope

@pipeline_task  # No parameters!
async def process_task(
    documents: DocumentList,
    model: ModelName,  # NO DEFAULTS! Must come from FlowOptions
) -> AnalysisDocument:
    """Process documents using LLM."""

    # For multi-line prompts, use Jinja2 file with matching name
    prompt = prompt_manager.get(
        "process_task",  # Extension optional, MUST match task file name!
        task="analyze and summarize"
    )

    # For single-line prompts, use inline string
    # prompt = "Analyze this document and provide a summary."

    # Option 1: Simple case - everything in messages
    messages = AIMessages(list(documents) + [prompt])

    # Option 2: Use context for documents (when asking multiple questions)
    # context = AIMessages(list(documents))  # Documents in context (cached)
    # messages = AIMessages([prompt])  # Question in messages
    # result = await llm.generate(
    #     model=model,
    #     context=context,  # Static documents (cached)
    #     messages=messages  # Dynamic prompt
    # )

    # Call LLM (simple case)
    # IMPORTANT: Never use the 'options' parameter - framework defaults are optimal
    result = await llm.generate(
        model=model,
        messages=messages  # Documents + prompt
    )

    # Create and return document
    # Note: Omit 'description' parameter - it's rarely needed
    return AnalysisDocument.create(
        name="analysis.json",  # Plain string OK when not used for routing
        content=result.content
    )
```

### Structured Output Pattern

**Two-Step Pattern for Complex Tasks**: For complex analysis or research tasks, it's often more reliable to use a two-step approach:
1. First use `generate()` with a capable model to perform the analysis
2. Then use `generate_structured()` to format the results

```python
# Step 1: Complex analysis with generate()
analysis_result = await llm.generate(
    model=flow_options.core_model,
    messages=AIMessages(list(documents) + ["Perform deep analysis..."])
)

# Step 2: Structure the results
structured = await llm.generate_structured(
    flow_options.small_model,  # Smaller model is fine for formatting
    AnalysisResult,
    messages=AIMessages([f"Extract key information: {analysis_result.content}"])
)
```

For simpler tasks requiring structured data:

```python
from pydantic import BaseModel, Field
from ai_pipeline_core import (
    AIMessages, DocumentList, ModelName,
    get_pipeline_logger, llm, pipeline_task
)

logger = get_pipeline_logger(__name__)

class AnalysisResult(BaseModel):
    """Structured analysis output."""
    summary: str = Field(description="Executive summary")
    score: int = Field(ge=1, le=10, description="Score")

@pipeline_task
async def structured_analysis(
    documents: DocumentList,
    model: ModelName,  # Always use ModelName type
) -> AnalysisDocument:
    """Generate structured analysis."""

    # Build messages with documents and prompt
    prompt = "Analyze and score the following content."
    messages = AIMessages(list(documents) + [prompt])

    # Optional: Use context for documents if asking multiple questions
    # context = AIMessages(list(documents))  # Documents in context
    # messages = AIMessages([prompt])  # Question in messages

    # Use generate_structured for type-safe output
    # Note: Search models (*-search) do not support structured output
    # IMPORTANT: Never use the 'options' parameter - framework defaults are optimal
    result = await llm.generate_structured(
        model,  # First positional argument
        AnalysisResult,  # Second positional argument (response_format)
        # context=context,  # Optional keyword argument
        messages=messages  # Required keyword argument
    )

    # Access the parsed Pydantic model
    analysis = result.parsed
    logger.debug(f"Analysis score: {analysis.score}")  # Use debug for logging

    # Note: Omit 'description' parameter - it's rarely needed
    return AnalysisDocument.create(
        name="analysis.json",
        content=analysis  # Pass BaseModel directly, no model_dump()!
    )
```

## Document System

### Document Type Hierarchy

```python
from enum import StrEnum
from ai_pipeline_core import FlowDocument, TaskDocument

# Flow documents persist across flows
# One file = one document class rule
class AnalysisDocument(FlowDocument):
    """Analysis results that flow between pipeline stages."""

    class FILES(StrEnum):
        """Only add file names that are actually used."""
        ANALYSIS = "analysis.json"  # Only add what you need

# Task documents are temporary within tasks
class DraftDocument(TaskDocument):
    """Temporary draft used during processing."""
    pass
```

### Document Operations

```python
# PREFERRED: Use FILES enum when filename identity matters
doc = AnalysisDocument.create(
    name=AnalysisDocument.FILES.ANALYSIS,
    content=data
)

# ALSO OK: Plain strings when filename not used for routing
# Note: Omit 'description' parameter unless truly needed for metadata
doc = AnalysisDocument.create(
    name="analysis.json",  # OK if not referenced elsewhere
    content={"key": "value"}
)

# DocumentList operations
analysis_docs = documents.filter_by(AnalysisDocument)
specific_doc = documents.get_by(AnalysisDocument.FILES.ANALYSIS)

# Plain string OK when filename not used downstream for routing
optional_doc = documents.get_by("optional.txt", required=False)

# Parse back to original type (reverses create())
original_dict = doc.parse(dict)  # For JSON documents
original_str = doc.parse(str)  # For text documents

# Access Document properties
doc.id  # 6-char unique ID (e.g., "A7B2C9")
doc.sha256  # Full SHA256 hash (base32 encoded)
doc.size  # Content size in bytes
doc.mime_type  # MIME type (e.g., "application/json")
doc.is_text  # True if text-based document
doc.text  # UTF-8 text (only if is_text is True)

# IMPORTANT: AIMessages construction
# WRONG: AIMessages("text")  # NO! Iterates over characters!
# CORRECT: AIMessages(["text"]) or AIMessages().append("text")
```

## Configuration

### Flow Options

```python
# ai_pipeline/flow_options.py
from ai_pipeline_core import FlowOptions, ModelName
from pydantic import Field

class ProjectFlowOptions(FlowOptions):
    """Project-specific flow configuration."""

    # Override defaults from base class if needed
    core_model: ModelName = Field(default="gpt-5")
    small_model: ModelName = Field(default="gpt-5-mini")

    # ONLY add project-specific fields if explicitly required
    # Don't add fields unless the project needs them
```

### CLI Entry Point

The template includes a ready-to-use CLI:

```python
# ai_pipeline/__main__.py
from ai_pipeline_core import DocumentList, FlowOptions
from ai_pipeline_core.simple_runner import run_cli
from .flow_options import ProjectFlowOptions
from .flows import FLOWS

TRACE_NAME = (__package__ or __name__).split(".")[0].replace("_", "-")

def initialize_project(options: FlowOptions) -> tuple[str, DocumentList]:
    # TODO: Implement project initialization
    return "", DocumentList([])

def main():
    run_cli(
        flows=FLOWS,
        options_cls=ProjectFlowOptions,
        initializer=initialize_project,
        trace_name=TRACE_NAME,
    )
```

## Development

### Essential Commands

```bash
# Development setup
make install-dev         # Install with dev dependencies and pre-commit hooks

# Code Quality
make lint               # Run ruff linting
make format            # Auto-format and fix code
make typecheck         # Run basedpyright type checking
make pre-commit        # Run all pre-commit hooks

# Testing
make test               # Run all tests
make test-cov          # Run tests with coverage report
pytest -m "not integration"  # Skip integration tests

# Cleanup
make clean             # Remove all build artifacts and caches
```

### Testing Strategy

```python
import pytest
from ai_pipeline_core import DocumentList
from ai_pipeline.documents.flow import SampleDocument
from ai_pipeline.flows.step_01_example.tasks import process_task

@pytest.mark.asyncio
async def test_process_task():
    """Test processing task."""
    # Arrange
    sample_doc = SampleDocument.create(
        name="sample.txt",
        content="Sample data"
    )
    documents = DocumentList([sample_doc])

    # Use FlowOptions for model selection
    from ai_pipeline.flow_options import ProjectFlowOptions
    options = ProjectFlowOptions()

    # Act
    result = await process_task(
        documents=documents,
        model=options.small_model,  # ModelName from FlowOptions
    )

    # Assert
    assert isinstance(result, SampleDocument)
    assert "processed" in result.content.lower()
```

## Best Practices

### Import Rules

```python
# CORRECT: Import from top-level ai_pipeline_core
from ai_pipeline_core import (
    FlowDocument, DocumentList,
    pipeline_task, pipeline_flow,
    llm, AIMessages
)

# WRONG: Never import from submodules
from ai_pipeline_core.llm import generate  # NO!
from ai_pipeline_core.documents import FlowDocument  # NO!

# NEVER use parent imports (..)
# NEVER use lazy imports or if TYPE_CHECKING
# NEVER use try/except for imports - no optional imports
```

### Context vs Messages Split

**Important**: Split static and dynamic content for caching benefits:
- **context**: Static content that can be cached (by LLM provider)
  - Documents being analyzed (when the same docs are used for multiple questions)
  - Examples, schemas, reference documentation
  - Content that remains constant across multiple calls
- **messages**: Dynamic per-call content (not cached)
  - The actual prompt/question/instruction
  - User queries that change with each call
  - Task-specific instructions

This pattern reduces token usage and costs through provider caching when you ask multiple questions about the same documents.

### Common Patterns

1. **Always use `create_and_validate_output()`** at the end of flows
2. **Never specify default models in tasks** - pass from FlowOptions
3. **Initialize PromptManager at module level**, not in functions
4. **Wrap documents in AIMessages** for LLM calls
5. **Use DocumentList default constructor** unless validation needed
6. **Colocate templates with tasks** with matching file names
7. **No 'Test' prefix for Document subclasses** - conflicts with pytest
8. **If task returns correct document type**, use it directly (don't recreate)
9. **Each flow must have unique OUTPUT_DOCUMENT_TYPE** class
10. **Use debug level for logging**, avoid meaningless logs
11. **Only add FlowOptions fields** that are explicitly needed

## Environment Variables

```bash
# Required for LLM operations
OPENAI_BASE_URL=http://localhost:4000  # API endpoint (eg. openrouter)
OPENAI_API_KEY=sk-...                  # API key

# Optional
PREFECT_API_URL=http://localhost:4200  # Prefect server
LMNR_PROJECT_API_KEY=lmnr_...          # Observability
LMNR_DEBUG=false                       # Debug tracing
```

## Getting Help

- Review `dependencies_docs/ai-pipeline-core.md` for framework details
- Check the test suite for usage examples
- Follow patterns in existing flows and tasks

## License

MIT
