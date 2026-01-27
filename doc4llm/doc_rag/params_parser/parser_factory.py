"""
Parser Factory for Doc-RAG Pipeline

Factory class that returns the appropriate parser for phase transitions.
"""

from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from .phase_parser import PhaseParser

from .phase_parser import (
    Phase0aToPhase1Parser,
    Phase0bToPhase1Parser,
    MultiPhaseToPhase1Parser,
    Phase1ToPhase1_5Parser,
    Phase1ToPhase2Parser,
    Phase1_5ToPhase2Parser,
)


class ParserFactory:
    """
    Factory class for creating phase parsers.

    Provides parsers for all valid phase transitions in the doc-rag pipeline.
    """

    # Registry of available parsers by phase transition
    PARSERS: Dict[tuple, Type["PhaseParser"]] = {
        ("0a", "1"): Phase0aToPhase1Parser,
        ("0b", "1"): Phase0bToPhase1Parser,
        ("0a+0b", "1"): MultiPhaseToPhase1Parser,
        ("1", "1.5"): Phase1ToPhase1_5Parser,
        ("1", "2"): Phase1ToPhase2Parser,
        ("1.5", "2"): Phase1_5ToPhase2Parser,
    }

    VALID_PHASES = ["0a", "0b", "0a+0b", "1", "1.5", "2"]

    # Valid transitions
    VALID_TRANSITIONS = list(PARSERS.keys())

    @classmethod
    def get_parser(cls, from_phase: str, to_phase: str) -> "PhaseParser":
        """
        Get a parser for the specified phase transition.

        Args:
            from_phase: Source phase identifier
            to_phase: Target phase identifier

        Returns:
            PhaseParser instance for the transition

        Raises:
            ValueError: If no parser exists for the transition
        """
        key = (from_phase, to_phase)
        if key not in cls.PARSERS:
            valid = ", ".join(f"{a}->{b}" for a, b in cls.VALID_TRANSITIONS)
            raise ValueError(
                f"No parser available for phase {from_phase} -> {to_phase}.\n"
                f"Valid transitions: {valid}"
            )
        return cls.PARSERS[key]()

    @classmethod
    def parse(
        cls,
        from_phase: str,
        to_phase: str,
        upstream_output: dict,
        target_skill: str = None,
        output_format: str = "cli"
    ) -> dict:
        """
        Parse upstream output for the target phase.

        Args:
            from_phase: Source phase identifier
            to_phase: Target phase identifier
            upstream_output: Output from the upstream phase
            target_skill: Target skill name (optional)
            output_format: Output format - "cli" or "api" (default: "cli")

        Returns:
            Input dict for the downstream phase

        Raises:
            ValueError: If no parser exists for the transition
        """
        parser = cls.get_parser(from_phase, to_phase)
        skill_name = f"phase_{to_phase}" if target_skill is None else target_skill
        return parser.parse(upstream_output, skill_name, output_format=output_format)

    @classmethod
    def is_valid_transition(cls, from_phase: str, to_phase: str) -> bool:
        """
        Check if a phase transition is valid.

        Args:
            from_phase: Source phase identifier
            to_phase: Target phase identifier

        Returns:
            True if transition is valid, False otherwise
        """
        return (from_phase, to_phase) in cls.PARSERS

    @classmethod
    def get_available_transitions(cls, from_phase: str = None) -> list:
        """
        Get available transitions, optionally filtered by source phase.

        Args:
            from_phase: Optional source phase to filter by

        Returns:
            List of available transitions
        """
        if from_phase is None:
            return list(cls.PARSERS.keys())
        return [t for t in cls.PARSERS.keys() if t[0] == from_phase]

    @classmethod
    def validate_output(
        cls,
        from_phase: str,
        to_phase: str,
        upstream_output: dict,
        output_format: str = "cli"
    ) -> tuple[bool, list]:
        """
        Validate upstream output against expected schema.

        Args:
            from_phase: Source phase identifier
            to_phase: Target phase identifier
            upstream_output: Output from the upstream phase
            output_format: Output format - "cli" or "api" (default: "cli")

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            parser = cls.get_parser(from_phase, to_phase)
            # Try parsing to validate
            parser.parse(upstream_output, f"phase_{to_phase}", output_format=output_format)
            return True, []
        except Exception as e:
            return False, [str(e)]


# Convenience function for CLI
def parse_phase(
    from_phase: str,
    to_phase: str,
    upstream_output: dict,
    output_format: str = "cli"
) -> dict:
    """
    Convenience function to parse phase output.

    Args:
        from_phase: Source phase identifier
        to_phase: Target phase identifier
        upstream_output: Output from the upstream phase
        output_format: Output format - "cli" or "api" (default: "cli")

    Returns:
        Input dict for the downstream phase
    """
    return ParserFactory.parse(from_phase, to_phase, upstream_output, output_format=output_format)
