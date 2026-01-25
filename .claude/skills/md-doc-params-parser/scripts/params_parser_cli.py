#!/usr/bin/env python3
"""
md-doc-params-parser CLI

Parses data interface parameters between phases in the doc-rag retrieval workflow.

Usage:
    # Single phase transition
    python params_parser_cli.py --from-phase 0a --to-phase 1 --input '<json>'

    # Merge mode (0a+0b -> 1): accepts array of outputs from both phases
    python params_parser_cli.py --from-phase 0a+0b --to-phase 1 --input '[{"phase": "0a", "output": {...}}, {"phase": "0b", "output": {...}}]'

Options:
    --from-phase:     Upstream phase (0a, 0b, 0a+0b, 1, 1.5, 2, 3)
    --to-phase:       Downstream phase (1, 1.5, 2, 3, 4)
    --input:          Upstream output as JSON string (or array for 0a+0b merge mode)
    --knowledge-base: Path to knowledge_base.json (for base_dir)
    --output:         Output file path (optional)
    --json:           Output JSON format (default, implicit)
    --no-validate:    Skip schema validation
"""

import argparse
import json
import sys
from pathlib import Path

from parser_factory import ParserFactory


def load_knowledge_base(kb_path: str) -> dict:
    """Load knowledge_base.json to get base_dir and other settings."""
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def enhance_with_knowledge_base(
    result: dict,
    from_phase: str,
    to_phase: str,
    kb_path: str
) -> dict:
    """
    Enhance parser output with knowledge base settings.

    Args:
        result: Parser output dict
        from_phase: Source phase
        to_phase: Target phase
        kb_path: Path to knowledge_base.json

    Returns:
        Enhanced result dict
    """
    kb = load_knowledge_base(kb_path)

    # Phase 0a/0b/0a+0b -> Phase 1: Add base_dir from knowledge base
    if from_phase in ["0a", "0b", "0a+0b"] and to_phase == "1":
        if "base_dir" not in result:
            result["base_dir"] = kb.get("knowledge_base", {}).get("base_dir", "")

        # Disable CLI reranking when using Phase 1.5 LLM reranker
        if "reranker" not in result:
            result["reranker"] = False

        if "json" not in result:
            result["json"] = True

    return result


def main():
    parser = argparse.ArgumentParser(
        description="md-doc-params-parser: Parse doc-rag phase data interface parameters"
    )
    parser.add_argument(
        "--from-phase",
        required=True,
        choices=["0a", "0b", "0a+0b", "1", "1.5", "2", "3"],
        help="Upstream phase identifier (use '0a+0b' to merge outputs from both phases)"
    )
    parser.add_argument(
        "--to-phase",
        required=True,
        choices=["1", "1.5", "2", "3", "4"],
        help="Downstream phase identifier"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Upstream output as JSON string (use '-' to read from stdin)"
    )
    parser.add_argument(
        "--knowledge-base",
        default=str(Path(__file__).resolve().parent.parent.parent.parent / "knowledge_base.json"),
        help="Path to knowledge_base.json (default: script_dir/knowledge_base.json)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (optional)"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation"
    )

    args = parser.parse_args()

    # Parse input
    if args.input == "-":
        try:
            input_str = sys.stdin.read()
            if args.from_phase == "0a+0b":
                upstream_output = json.loads(input_str)
                if not isinstance(upstream_output, list):
                    raise ValueError("For 0a+0b merge mode, input must be an array of outputs")
            else:
                upstream_output = json.loads(input_str)
        except (json.JSONDecodeError, ValueError) as e:
            error_result = {
                "error": f"Invalid JSON from stdin: {e}",
                "status": "failed"
            }
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
            sys.exit(1)
    else:
        try:
            if args.from_phase == "0a+0b":
                upstream_output = json.loads(args.input)
                if not isinstance(upstream_output, list):
                    raise ValueError("For 0a+0b merge mode, input must be an array of outputs")
            else:
                upstream_output = json.loads(args.input)
        except (json.JSONDecodeError, ValueError) as e:
            error_result = {
                "error": f"Invalid JSON input: {e}",
                "status": "failed"
            }
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
            sys.exit(1)

    try:
        # Validate transition and input format
        if not args.no_validate:
            # Special validation for 0a+0b merge mode
            if args.from_phase == "0a+0b":
                if not isinstance(upstream_output, list):
                    error_result = {
                        "error": "For 0a+0b merge mode, input must be an array of outputs",
                        "status": "failed"
                    }
                    print(json.dumps(error_result, ensure_ascii=False, indent=2))
                    sys.exit(1)

                # Validate each item in the array
                required_phases = set()
                for item in upstream_output:
                    if not isinstance(item, dict):
                        error_result = {
                            "error": "Each item in the array must be an object with 'phase' and 'output' keys",
                            "status": "failed"
                        }
                        print(json.dumps(error_result, ensure_ascii=False, indent=2))
                        sys.exit(1)

                    phase = item.get("phase")
                    if phase not in ["0a", "0b"]:
                        error_result = {
                            "error": f"Invalid phase '{phase}' in array. Expected '0a' or '0b'",
                            "status": "failed"
                        }
                        print(json.dumps(error_result, ensure_ascii=False, indent=2))
                        sys.exit(1)
                    required_phases.add(phase)

                if "0a" not in required_phases or "0b" not in required_phases:
                    error_result = {
                        "error": "0a+0b merge mode requires both '0a' and '0b' outputs in the array",
                        "status": "failed"
                    }
                    print(json.dumps(error_result, ensure_ascii=False, indent=2))
                    sys.exit(1)

            is_valid, errors = ParserFactory.validate_output(
                args.from_phase,
                args.to_phase,
                upstream_output
            )
            if not is_valid:
                error_result = {
                    "error": "Schema validation failed",
                    "details": errors,
                    "status": "failed"
                }
                print(json.dumps(error_result, ensure_ascii=False, indent=2))
                sys.exit(1)

        # Parse phase output
        result = ParserFactory.parse(
            args.from_phase,
            args.to_phase,
            upstream_output
        )

        # Enhance with knowledge base settings
        result = enhance_with_knowledge_base(
            result,
            args.from_phase,
            args.to_phase,
            args.knowledge_base
        )

        # Build final output
        output = {
            "data": result,
            "from_phase": args.from_phase,
            "to_phase": args.to_phase,
            "status": "success"
        }

        # Write output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"Output written to {args.output}")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))

    except ValueError as e:
        error_result = {
            "error": str(e),
            "status": "failed"
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        error_result = {
            "error": f"Unexpected error: {e}",
            "status": "failed"
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
