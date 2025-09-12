"""CLI entry point for the AI Simple Research Pipeline."""

from ai_pipeline_core.simple_runner import run_cli

from .flow_options import ProjectFlowOptions
from .flows import FLOWS

TRACE_NAME = (__package__ or __name__).split(".")[0].replace("_", "-")


def main():
    """Main CLI entry point."""
    run_cli(
        flows=FLOWS,
        options_cls=ProjectFlowOptions,
        trace_name=TRACE_NAME,
    )


if __name__ == "__main__":
    main()
