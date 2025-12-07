"""
Amadeus Voice Assistant - Main Entry Point

Main entry point for launching the assistant.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from amadeus.app.pipeline import VoicePipeline, PipelineConfig


def setup_logging(verbose: bool = False) -> None:
    """Sets up logging."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def run_interactive(pipeline: VoicePipeline) -> None:
    """Runs the interactive text mode."""
    print("=" * 60)
    print("Amadeus Voice Assistant - Interactive Mode")
    print("=" * 60)
    print()
    print("Type commands to test the assistant.")
    print("Type 'help' for a list of example commands.")
    print("Type 'quit' or 'exit' to stop.")
    print()
    
    while True:
        try:
            command = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not command:
            continue
        
        if command.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        
        if command.lower() == "help":
            print_help()
            continue
        
        if command.lower() == "state":
            print(f"Current state: {pipeline.get_state().name}")
            continue

        # Process command
        print()
        result = pipeline.process_text(command)
        
        if result.success:
            print(f"✅ Success!")
            if result.plan:
                print(f"   Intent: {result.intent.intent_type.value}")
                print(f"   Actions: {len(result.plan.actions)}")
            for r in result.results:
                if r.output:
                    print(f"   Output: {r.output}")
        else:
            print(f"❌ Failed: {result.error}")
            if result.intent and result.intent.is_unknown:
                print("   Tip: Try rephrasing your command.")
        
        print()


def print_help() -> None:
    """Prints a list of example commands."""
    print()
    print("Example commands:")
    print("-" * 40)
    print("  open calculator")
    print("  open notepad")
    print("  search for python tutorials")
    print("  list files in ~/Documents")
    print("  system info")
    print("  create file ~/Documents/test.txt")
    print("  go to https://github.com")
    print("-" * 40)
    print()


def run_single_command(pipeline: VoicePipeline, command: str, dry_run: bool = False) -> int:
    """Executes a single command and returns the exit code."""
    result = pipeline.process_text(command, dry_run=dry_run)
    
    if result.success:
        print("✅ Command executed successfully")
        if result.plan:
            print(f"Intent: {result.intent.intent_type.value}")
        for r in result.results:
            if r.output:
                print(f"Output: {r.output}")
        return 0
    else:
        print(f"❌ Command failed: {result.error}")
        return 1


def main(args: Optional[list] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="amadeus",
        description="Amadeus Voice Assistant - Privacy-first local PC assistant",
    )
    
    parser.add_argument(
        "-c", "--command",
        type=str,
        help="Execute a single command and exit",
    )
    
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Simulate execution without making changes",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Amadeus Voice Assistant v0.1.0",
    )
    
    parsed = parser.parse_args(args)

    # Sets up logging
    setup_logging(parsed.verbose)

    # Creates the pipeline
    config = PipelineConfig(
        dry_run_by_default=parsed.dry_run,
        verbose_logging=parsed.verbose,
    )
    pipeline = VoicePipeline(config=config)

    # Execute command
    if parsed.command:
        return run_single_command(pipeline, parsed.command, parsed.dry_run)
    else:
        run_interactive(pipeline)
        return 0


if __name__ == "__main__":
    sys.exit(main())
