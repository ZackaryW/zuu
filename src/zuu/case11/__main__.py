"""Run a small dependency-free demonstration of case11 selection."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import Choice, CliSelector, SelectionError

AGENTS = ("codex", "claude", "pi", "kimi")


def build_parser() -> argparse.ArgumentParser:
    """Create the demonstration argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m zuu.case11",
        description="Try case11 explicit-or-interactive terminal selection.",
    )
    parser.add_argument(
        "--agent",
        action="append",
        choices=AGENTS,
        help="Select an agent explicitly; repeat to select several.",
    )
    parser.add_argument(
        "--optional",
        action="store_true",
        help="Allow confirmation or noninteractive execution with no selection.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the example and return a conventional process status."""
    arguments = build_parser().parse_args(argv)
    selector = CliSelector(
        "Configure agent applications",
        choices=(
            Choice("Codex", "codex"),
            Choice("Claude Code", "claude"),
            Choice("Pi", "pi"),
            Choice("Kimi", "kimi"),
        ),
    )
    try:
        selection = selector.select(
            tuple(arguments.agent or ()),
            required=not arguments.optional,
        )
    except SelectionError as error:
        print(f"Selection error: {error}", file=sys.stderr)
        return 2
    if selection.cancelled:
        print("Selection cancelled.", file=sys.stderr)
        return 130
    selected = ", ".join(selection.values) or "none"
    print(f"Selected: {selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
