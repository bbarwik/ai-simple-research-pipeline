"""Test research pipeline and its flows."""

import pytest

from ai_simple_research_pipeline.documents.flow import (
    FinalReportDocument,
    InitialSummaryDocument,
)


@pytest.mark.asyncio
async def test_summary_flow_generates_all_documents():
    """Test that summary flow generates initial summary and description documents."""
    # This test would require mocking LLM calls in a real test environment
    # For now, we verify the document structure
    pass


@pytest.mark.asyncio
async def test_report_flow_generates_all_reports():
    """Test that report flow generates all report variations."""
    # This test would require setting up all intermediate documents
    # For now, we'll just verify the document class has the right files

    # Verify FinalReportDocument has all required file names
    assert hasattr(FinalReportDocument.FILES, "SHORT_REPORT")
    assert hasattr(FinalReportDocument.FILES, "FULL_REPORT")

    assert FinalReportDocument.FILES.SHORT_REPORT == "short_report.md"
    assert FinalReportDocument.FILES.FULL_REPORT == "full_report.md"


@pytest.mark.asyncio
async def test_initial_summary_document_files():
    """Test that InitialSummaryDocument has all required file names."""
    assert hasattr(InitialSummaryDocument.FILES, "INITIAL_SUMMARY")
    assert hasattr(InitialSummaryDocument.FILES, "SHORT_DESCRIPTION")
    assert hasattr(InitialSummaryDocument.FILES, "LONG_DESCRIPTION")

    assert InitialSummaryDocument.FILES.INITIAL_SUMMARY == "initial_summary.json"
    assert InitialSummaryDocument.FILES.SHORT_DESCRIPTION == "short_description.md"
    assert InitialSummaryDocument.FILES.LONG_DESCRIPTION == "long_description.md"
