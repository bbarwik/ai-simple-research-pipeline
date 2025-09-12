from ai_pipeline_core import FlowDocument


class StandardizedFileDocument(FlowDocument):
    """English Markdown version of a single source with YAML front-matter.

    Filenames are dynamic (slugged), so no FILES enum.
    """
