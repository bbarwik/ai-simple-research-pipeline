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

### API Server

The pipeline includes a FastAPI server that provides REST endpoints for triggering pipeline runs via Prefect:

```bash
# Start the API server (requires Prefect server running)
python -m ai_simple_research_pipeline.server

# The server will be available at http://localhost:4080
# API documentation at http://localhost:4080/docs
```

### Local Usage

```bash
# Set up your project directory structure
mkdir -p projects/my_project/user_input
# Place your pitch decks, whitepapers, and other documents in projects/my_project/user_input/

# Run the full pipeline
python -m ai_simple_research_pipeline projects/my_project

# Select specific flows (indices are 1-based)
python -m ai_simple_research_pipeline projects/my_project --start 2 --end 3

# Choose execution mode (test, quick, or full)
python -m ai_simple_research_pipeline projects/my_project --mode quick

# Choose models from FlowOptions (default: gemini-2.5-flash)
python -m ai_simple_research_pipeline projects/my_project \
  --core-model "gemini-2.5-flash" \
  --small-model "gemini-2.5-flash-lite"

# Debug traces
LMNR_DEBUG=true python -m ai_simple_research_pipeline projects/my_project
```

### Docker Compose Deployment

The pipeline can be deployed using Docker Compose for production environments with Prefect server and API middleware:

```bash
# 1. Create a .env file with your configuration
cat > .env << 'EOF'
# Required: LLM API configuration (recommended: OpenRouter)
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-your-key-here

# Required: API middleware authentication
PREFECT_MIDDLEWARE_API_KEY=your-secure-api-key-here

# Optional: Observability with Laminar (free account at laminar.sh)
LMNR_PROJECT_API_KEY=lmnr_your_key_here

# Optional: Google Cloud Storage configuration
# Place your GCS service account key.json in the project root
# The pipeline will use GCS if a gs:// URL is provided
EOF

# 2. (Optional) Add Google Cloud Storage credentials
# Download your service account key from Google Cloud Console
# Save it as key.json in the project root
cp /path/to/your/gcs-service-account-key.json ./key.json

# 3. Run with Docker Compose (includes Prefect server and API middleware)
docker compose up -d

# 4. Access the services:
# - Prefect UI: http://localhost:4200
# - API Server: http://localhost:4080
# - API Docs: http://localhost:4080/docs

# 5. Execute pipeline with local storage
docker compose exec app python -m ai_simple_research_pipeline projects/my_project

# 6. Execute pipeline with Google Cloud Storage
# Ensure your bucket has a user_input/ directory with your documents
docker compose exec app python -m ai_simple_research_pipeline gs://your-bucket-name/

# Example with actual GCS bucket:
docker compose exec app python -m ai_simple_research_pipeline gs://ai-research-pipeline-1757702160/
```

### Google Cloud Storage Setup

To use Google Cloud Storage as your storage backend:

1. **Create a GCS bucket** in your Google Cloud Console
2. **Create a service account** with Storage Admin permissions for the bucket
3. **Download the service account key** as `key.json` and place it in the project root
4. **Prepare your bucket structure**:
   ```bash
   # Your bucket should have this structure:
   gs://your-bucket-name/
   └── user_input/
       ├── pitch_deck.pdf
       ├── whitepaper.pdf
       └── other_documents...
   ```
5. **Run the pipeline** pointing to your GCS bucket:
   ```bash
   docker compose exec app python -m ai_simple_research_pipeline gs://your-bucket-name/
   ```

All pipeline outputs (initial_summary, standardized_file, review_finding, final_report) will be automatically saved to the GCS bucket alongside your input documents.

## Pipeline Stages

1. **Summary** (Flow 1): Analyzes all input documents to create:
   - Initial structured summary (JSON)
   - Short description (50-100 words)
   - Long description (500-1000 words)
2. **Standardization** (Flow 2): Converts each document to:
   - Structured metadata (YAML)
   - Clean English content (Markdown)
3. **Review** (Flow 3): Identifies 5 risks, 5 opportunities, and 5 investor questions with evidence citations
4. **Report** (Flow 4): Generates:
   - Full report (15-20 pages comprehensive due diligence)
   - Short report (5 pages executive summary)

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
├── initial_summary/               # Initial analysis from Flow 1
│   ├── initial_summary.json      # Structured summary
│   ├── short_description.md      # 50-100 word description
│   └── long_description.md       # 500-1000 word description
├── standardized_file/             # Standardized documents from Flow 2
│   ├── {slug}.yaml               # Metadata for each document
│   └── {slug}.md                 # Content for each document
├── review_finding/                # Structured findings from Flow 3
│   ├── risks.json
│   ├── opportunities.json
│   └── questions.json
└── final_report/                  # Due diligence reports from Flow 4
    ├── full_report.md            # 15-20 page comprehensive report
    └── short_report.md           # 5 page executive summary
```

Note: The framework automatically creates output directories based on document types. Document names cannot contain path separators.

## Configuration

### Default Models

The pipeline uses Google Gemini models by default (configured in `flow_options.py`):
- **Core model**: `gemini-2.5-flash` (for analysis and report generation)
- **Small model**: `gemini-2.5-flash-lite` (for standardization)
- **Mode**: `quick` (default) - Controls analysis depth (test/quick/full)

### Environment Variables

Set these environment variables (typically in a `.env` file):

```bash
# Required: LLM API configuration
# Option 1: OpenRouter (recommended for ease of use)
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-your-key-here

# Option 2: Local LiteLLM proxy
# OPENAI_BASE_URL=http://localhost:4000
# OPENAI_API_KEY=sk-...

# Optional: Observability and monitoring
LMNR_PROJECT_API_KEY=lmnr_...  # Free account at laminar.sh
LMNR_DEBUG=true                # Enable debug traces

# Required for Docker Compose deployment:
PREFECT_MIDDLEWARE_API_KEY=your-secure-api-key  # API authentication

# Optional: Workflow orchestration (external Prefect)
PREFECT_API_URL=http://localhost:4200
PREFECT_API_KEY=pnu_...

# Optional: Google Cloud Storage
# Place your service account key.json in the project root
# No environment variable needed - detected automatically
```

## Project layout

```
ai_simple_research_pipeline/
├── documents/                      # Document type definitions
│   ├── flow/                       # Flow documents (persistent across flows)
│   │   ├── user_input_document.py
│   │   ├── initial_summary_document.py  # Summary + descriptions
│   │   ├── standardized_file_document.py # YAML + Markdown pairs
│   │   ├── findings_document.py         # Risks, opportunities, questions
│   │   └── final_report_document.py     # Full + short reports
│   └── task/                       # Task documents (temporary)
├── flows/                          # Four-stage pipeline flows
│   ├── step_01_summary/            # Creates initial summary
│   │   ├── summary_flow.py
│   │   └── tasks/
│   │       ├── create_summary.py           # Initial JSON summary
│   │       ├── create_summary.jinja2
│   │       ├── create_short_description.py # 50-100 word description
│   │       ├── create_short_description.jinja2
│   │       ├── create_long_description.py  # 500-1000 word description
│   │       └── create_long_description.jinja2
│   ├── step_02_standardization/    # Converts to English Markdown
│   │   ├── standardization_flow.py
│   │   └── tasks/
│   │       ├── extract_metadata.py         # Extract YAML metadata
│   │       ├── extract_metadata.jinja2
│   │       ├── standardize_content.py      # Convert to Markdown
│   │       ├── standardize_content.jinja2
│   │       ├── standardize_files.py        # Legacy combined task
│   │       └── standardize_files.jinja2
│   ├── step_03_review/             # Generates findings
│   │   ├── review_flow.py
│   │   └── tasks/
│   │       ├── generate_findings.py
│   │       └── generate_findings.jinja2
│   └── step_04_report/             # Writes final report
│       ├── report_flow.py
│       └── tasks/
│           ├── write_full_report.py        # 15-20 page report
│           ├── write_full_report.jinja2
│           ├── write_short_report.py       # 5 page summary
│           └── write_short_report.jinja2
├── prompts/                        # Shared prompt templates
│   └── document_formatting_rules.jinja2
├── cli.py                          # CLI interface for running pipelines
├── research_pipeline.py            # Main research pipeline with improved webhook progress tracking
├── flow_options.py                 # Model configuration with mode (test/quick/full) and webhook support
├── server.py                       # FastAPI server for REST API
├── http_server.py                  # Test HTTP server for development
└── __main__.py                     # Prefect deployment entry point
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
