# AI Simple Research Pipeline

An AI-powered pipeline for analyzing startup pitch decks and whitepapers to generate comprehensive due diligence reports for investors. Built with **ai-pipeline-core** for robust async workflows and type-safe document processing.

## Features

* **Four-stage analysis pipeline**: Summary → Standardization → Review → Report
* **Multi-format support**: Analyzes pitch decks, whitepapers, blog posts, and other startup documents
* **Structured insights**: Identifies 5 risks, 5 opportunities, and 5 investor questions
* **Professional reports**: Generates 10-15 page due diligence reports in Markdown
* **Type-safe architecture**: Built on ai-pipeline-core with Pydantic models
* **Async processing**: Efficient document processing with provider caching
* **Full observability**: LMNR tracing and Prefect workflow orchestration

## Prerequisites

* Python **3.12+**
* Access to a LiteLLM proxy (or any OpenAI‑compatible endpoint)
* Optional: Prefect server/cloud if you want remote orchestration

## Install

```bash
# Clone and install
pip install -e .

# Dev setup (ruff, basedpyright, pre-commit, pytest)
make install-dev
```

### DevContainer Setup (Optional)

For VS Code DevContainer users who need overrides:

```bash
# Copy the example file and customize it
cp .devcontainer/docker-compose.override.yml.example .devcontainer/docker-compose.override.yml

# Edit devcontainer.json to include the override file
# Change: "dockerComposeFile": "docker-compose.yml",
# To: "dockerComposeFile": ["docker-compose.yml", "docker-compose.override.yml"],
```

The `docker-compose.override.yml` file is gitignored and can contain user-specific mounts and network configurations.

## Quick start

```bash
# Set up your project directory structure
mkdir -p projects/my_project/user_input
# Place your pitch decks, whitepapers, and other documents in projects/my_project/user_input/

# Run the full pipeline
python -m ai_simple_research_pipeline projects/my_project

# Select specific flows (indices are 1-based)
python -m ai_simple_research_pipeline projects/my_project --start 2 --end 3

# Choose models from FlowOptions (default: google/gemini-2.5-flash)
python -m ai_simple_research_pipeline projects/my_project \
  --core-model "google/gemini-2.5-flash" \
  --small-model "google/gemini-2.5-flash-lite"

# Debug traces
LMNR_DEBUG=true python -m ai_simple_research_pipeline projects/my_project
```

## Pipeline Stages

1. **Summary** (Flow 1): Analyzes all input documents to create an initial summary with key claims, data points, and per-source descriptions
2. **Standardization** (Flow 2): Converts each document to English Markdown with structured YAML front-matter
3. **Review** (Flow 3): Identifies 5 risks, 5 opportunities, and 5 investor questions with evidence citations
4. **Report** (Flow 4): Generates a comprehensive 10-15 page due diligence report

### Performance

The pipeline processes documents efficiently with typical execution times:
- Flow 1 (Summary): ~24 seconds
- Flow 2 (Standardization): <1 second per document
- Flow 3 (Review): ~46 seconds (structured output generation)
- Flow 4 (Report): ~47 seconds (comprehensive report writing)
- **Total**: ~2 minutes for complete analysis

## Output Structure

```
projects/my_project/
├── user_input/                    # Your input documents (pitch decks, whitepapers, etc.)
│   └── *.pdf, *.docx, etc.
├── initial_summary/               # Initial summary from Flow 1
│   └── initial_summary.json
├── standardized_file/             # English Markdown versions from Flow 2
│   └── *.md
├── review_finding/                # Structured findings from Flow 3
│   ├── risks.json
│   ├── opportunities.json
│   └── questions.json
└── final_report/                  # Final due diligence report from Flow 4
    └── final_report.md
```

Note: The framework automatically creates output directories based on document types. Document names cannot contain path separators.

## Configuration

### Default Models

The pipeline uses Google Gemini models by default (configured in `flow_options.py`):
- **Core model**: `google/gemini-2.5-flash` (for analysis and report generation)
- **Small model**: `google/gemini-2.5-flash-lite` (for standardization)

### Environment Variables

Set these environment variables (typically in a `.env` file):

```bash
# Required for LLM operations (OpenAI-compatible via LiteLLM proxy)
OPENAI_BASE_URL=http://localhost:4000
OPENAI_API_KEY=sk-...

# Optional services
PREFECT_API_URL=http://localhost:4200
PREFECT_API_KEY=pnu_...
LMNR_PROJECT_API_KEY=lmnr_...
LMNR_DEBUG=true
```

## Project layout

```
ai_simple_research_pipeline/
├── documents/                    # Document type definitions
│   ├── flow/                     # Flow documents (persistent across flows)
│   │   ├── user_input_document.py
│   │   ├── initial_summary_document.py
│   │   ├── standardized_file_document.py
│   │   ├── findings_document.py
│   │   └── final_report_document.py
│   └── task/                     # Task documents (temporary)
├── flows/                        # Four-stage pipeline flows
│   ├── step_01_summary/          # Creates initial summary
│   ├── step_02_standardization/  # Converts to English Markdown
│   ├── step_03_review/           # Generates findings
│   └── step_04_report/           # Writes final report
├── prompts/                      # Shared prompt templates
│   └── document_formatting_rules.jinja2
├── flow_options.py               # Model configuration
└── __main__.py                   # CLI entry point
```

## Everyday commands

```bash
make lint        # Ruff
make format      # Formatting
make typecheck   # basedpyright (must be 0 errors)
make test        # Unit tests
make test-cov    # Tests with coverage
make clean       # Remove build artifacts
```

## Development handbook

For detailed patterns (flows, tasks, documents, testing, prompts, logging, etc.), see **DEVELOPMENT.md**.

If you’re an AI assistant working in this repo, see **CLAUDE.md** for rules and navigation tips.

## License

MIT
