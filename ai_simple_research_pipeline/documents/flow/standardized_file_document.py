from ai_pipeline_core import FlowDocument


class StandardizedFileDocument(FlowDocument):
    """Standardized document with separate metadata and content files.

    Generates two files per source document:
    - {slug}.yaml: Structured metadata
    - {slug}.md: Clean English markdown content

    Filenames are dynamic (slugged from source), so no FILES enum.
    """
