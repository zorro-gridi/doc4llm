"""
Params Parser API for Doc-RAG Pipeline

Reusable API for parsing data interface parameters between phases
in the doc-rag retrieval workflow.

Usage:
    from params_parser_api import ParamsParserAPI, PhaseTransitionRequest

    api = ParamsParserAPI()
    response = api.parse(
        from_phase="0a",
        to_phase="1",
        upstream_output={"query_analysis": {...}, "optimized_queries": [...]}
    )
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, field_validator

from .parser_factory import ParserFactory


# =============================================================================
# Pydantic Data Models
# =============================================================================

class PhaseTransitionRequest(BaseModel):
    """
    Phase transition request model.

    Attributes:
        from_phase: Source phase identifier (0a, 0b, 0a+0b, 1, 1.5, 2)
        to_phase: Target phase identifier (1, 1.5, 2, 3, 4)
        upstream_output: Output from the upstream phase
        do_validate: Whether to validate schema (default: True)
    """
    from_phase: str = Field(..., description="Source phase identifier")
    to_phase: str = Field(..., description="Target phase identifier")
    upstream_output: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ...,
        description="Output from upstream phase (dict for single phase, list for 0a+0b merge)"
    )
    do_validate: bool = Field(default=True, description="Whether to validate schema")

    @field_validator("from_phase")
    @classmethod
    def validate_from_phase(cls, v: str) -> str:
        allowed = ["0a", "0b", "0a+0b", "1", "1.5", "2"]
        if v not in allowed:
            raise ValueError(f"from_phase must be one of {allowed}, got '{v}'")
        return v

    @field_validator("to_phase")
    @classmethod
    def validate_to_phase(cls, v: str) -> str:
        allowed = ["1", "1.5", "2", "3", "4"]
        if v not in allowed:
            raise ValueError(f"to_phase must be one of {allowed}, got '{v}'")
        return v


class MultiPhaseRequest(BaseModel):
    """
    Merge mode request model for 0a+0b -> 1 transition.

    Attributes:
        phases: List of phase outputs with phase identifier
        to_phase: Target phase identifier (should be "1" for merge)
    """
    phases: List[Dict[str, Any]] = Field(
        ...,
        description="List of phase outputs: [{\"phase\": \"0a\", \"output\": {...}}, ...]"
    )
    to_phase: str = Field(default="1", description="Target phase identifier")

    @field_validator("to_phase")
    @classmethod
    def validate_to_phase(cls, v: str) -> str:
        if v != "1":
            raise ValueError(f"to_phase for multi-phase must be '1', got '{v}'")
        return v


class PhaseTransitionResponse(BaseModel):
    """
    Phase transition response model.

    Attributes:
        config: Parsed configuration for the target phase
        from_phase: Source phase identifier
        to_phase: Target phase identifier
        status: Response status ("success" or "failed")
        errors: List of error messages (None if status is "success")
    """
    config: Optional[Dict[str, Any]] = Field(default=None, description="Parsed configuration")
    from_phase: str = Field(..., description="Source phase identifier")
    to_phase: str = Field(..., description="Target phase identifier")
    status: str = Field(default="success", description="Response status")
    errors: Optional[List[str]] = Field(default=None, description="Error messages")

    class Config:
        json_encoders = {
            # Handle non-serializable types
        }


# =============================================================================
# ParamsParserAPI Class
# =============================================================================

@dataclass
class ParamsParserAPI:
    """
    Parameter Parser API for Doc-RAG Pipeline.

    Provides a reusable API for parsing data interface parameters
    between phases in the doc-rag retrieval workflow.

    Attributes:
        validate: Whether to validate schema by default (default: True)
        debug: Enable debug mode (default: False)
        output_format: Output format - "cli" or "api" (default: "api")

    Example:
        >>> api = ParamsParserAPI()
        >>> response = api.parse("0a", "1", {"query_analysis": {...}, "optimized_queries": [...]})
        >>> print(response.config)
    """
    validate: bool = True
    debug: bool = False
    output_format: str = "api"

    def parse(
        self,
        from_phase: str,
        to_phase: str,
        upstream_output: Union[Dict[str, Any], List[Dict[str, Any]]],
        validate: Optional[bool] = None,
        output_format: Optional[str] = None
    ) -> PhaseTransitionResponse:
        """
        Execute single phase transition.

        Args:
            from_phase: Source phase identifier (0a, 0b, 1, 1.5, 2)
            to_phase: Target phase identifier (1, 1.5, 2, 3, 4)
            upstream_output: Output from the upstream phase
            validate: Override for validation flag (uses instance default if None)
            output_format: Output format - "cli" or "api" (uses instance default if None)

        Returns:
            PhaseTransitionResponse with config and status

        Example:
            >>> api = ParamsParserAPI()
            >>> response = api.parse("0a", "1", optimizer_output)
            >>> if response.status == "success":
            ...     print(response.config)
        """
        # Use instance settings if not overridden
        do_validate = validate if validate is not None else self.validate
        fmt = output_format if output_format is not None else self.output_format

        # Build request for validation
        try:
            request = PhaseTransitionRequest(
                from_phase=from_phase,
                to_phase=to_phase,
                upstream_output=upstream_output,
                do_validate=do_validate
            )
        except ValidationError as e:
            return PhaseTransitionResponse(
                config=None,
                from_phase=from_phase,
                to_phase=to_phase,
                status="failed",
                errors=[str(e)]
            )

        # Special validation for 0a+0b merge mode
        if request.from_phase == "0a+0b":
            if not isinstance(request.upstream_output, list):
                return PhaseTransitionResponse(
                    config=None,
                    from_phase=from_phase,
                    to_phase=to_phase,
                    status="failed",
                    errors=["For 0a+0b merge mode, upstream_output must be a list"]
                )

            required_phases = set()
            for item in request.upstream_output:
                if not isinstance(item, dict):
                    return PhaseTransitionResponse(
                        config=None,
                        from_phase=from_phase,
                        to_phase=to_phase,
                        status="failed",
                        errors=["Each item in the list must be a dict with 'phase' and 'output' keys"]
                    )

                phase = item.get("phase")
                if phase not in ["0a", "0b"]:
                    return PhaseTransitionResponse(
                        config=None,
                        from_phase=from_phase,
                        to_phase=to_phase,
                        status="failed",
                        errors=[f"Invalid phase '{phase}' in list. Expected '0a' or '0b'"]
                    )
                required_phases.add(phase)

            if "0a" not in required_phases or "0b" not in required_phases:
                return PhaseTransitionResponse(
                    config=None,
                    from_phase=from_phase,
                    to_phase=to_phase,
                    status="failed",
                    errors=["0a+0b merge mode requires both '0a' and '0b' outputs in the list"]
                )

        # Validate transition exists
        if not ParserFactory.is_valid_transition(request.from_phase, request.to_phase):
            valid_transitions = ", ".join(f"{a}->{b}" for a, b in ParserFactory.VALID_TRANSITIONS)
            return PhaseTransitionResponse(
                config=None,
                from_phase=from_phase,
                to_phase=to_phase,
                status="failed",
                errors=[f"Invalid phase transition: {from_phase} -> {to_phase}. Valid: {valid_transitions}"]
            )

        # Schema validation if enabled
        if do_validate:
            is_valid, errors = ParserFactory.validate_output(
                request.from_phase,
                request.to_phase,
                request.upstream_output,
                output_format=fmt
            )
            if not is_valid:
                return PhaseTransitionResponse(
                    config=None,
                    from_phase=from_phase,
                    to_phase=to_phase,
                    status="failed",
                    errors=errors
                )

        try:
            result = ParserFactory.parse(
                request.from_phase,
                request.to_phase,
                request.upstream_output,
                output_format=fmt
            )

            return PhaseTransitionResponse(
                config=result,
                from_phase=from_phase,
                to_phase=to_phase,
                status="success",
                errors=None
            )

        except ValueError as e:
            return PhaseTransitionResponse(
                config=None,
                from_phase=from_phase,
                to_phase=to_phase,
                status="failed",
                errors=[str(e)]
            )
        except Exception as e:
            if self.debug:
                raise
            return PhaseTransitionResponse(
                config=None,
                from_phase=from_phase,
                to_phase=to_phase,
                status="failed",
                errors=[f"Unexpected error: {e}"]
            )

    def parse_multi_phase(
        self,
        to_phase: str,
        phases: List[Dict[str, Any]],
        output_format: Optional[str] = None
    ) -> PhaseTransitionResponse:
        """
        Execute merge mode transition (0a+0b -> 1).

        Convenience method that wraps the 0a+0b merge logic.

        Args:
            to_phase: Target phase identifier (should be "1")
            phases: List of phase outputs with phase identifier
                Example: [
                    {"phase": "0a", "output": {...}},
                    {"phase": "0b", "output": {...}}
                ]
            output_format: Output format - "cli" or "api" (uses instance default if None)

        Returns:
            PhaseTransitionResponse with merged config

        Example:
            >>> api = ParamsParserAPI()
            >>> response = api.parse_multi_phase("1", [
            ...     {"phase": "0a", "output": optimizer_output},
            ...     {"phase": "0b", "output": router_output}
            ... ])
            >>> print(response.config)
        """
        # Build request for validation
        try:
            request = MultiPhaseRequest(phases=phases, to_phase=to_phase)
        except ValidationError as e:
            return PhaseTransitionResponse(
                config=None,
                from_phase="0a+0b",
                to_phase=to_phase,
                status="failed",
                errors=[str(e)]
            )

        # Call parse with 0a+0b transition
        return self.parse(
            from_phase="0a+0b",
            to_phase=to_phase,
            upstream_output=phases,
            output_format=output_format
        )

    def validate_transition(
        self,
        from_phase: str,
        to_phase: str
    ) -> tuple[bool, List[str]]:
        """
        Validate if a phase transition is valid.

        Args:
            from_phase: Source phase identifier
            to_phase: Target phase identifier

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            >>> api = ParamsParserAPI()
            >>> is_valid, errors = api.validate_transition("0a", "1")
            >>> print(f"Valid: {is_valid}")
        """
        errors = []

        # Validate phase values
        valid_from = ["0a", "0b", "0a+0b", "1", "1.5", "2"]
        valid_to = ["1", "1.5", "2", "3", "4"]

        if from_phase not in valid_from:
            errors.append(f"from_phase must be one of {valid_from}, got '{from_phase}'")

        if to_phase not in valid_to:
            errors.append(f"to_phase must be one of {valid_to}, got '{to_phase}'")

        if errors:
            return False, errors

        # Check if transition exists
        if not ParserFactory.is_valid_transition(from_phase, to_phase):
            valid_transitions = ", ".join(f"{a}->{b}" for a, b in ParserFactory.VALID_TRANSITIONS)
            errors.append(f"No parser available for transition {from_phase} -> {to_phase}")
            errors.append(f"Valid transitions: {valid_transitions}")
            return False, errors

        return True, []

    def get_available_transitions(
        self,
        from_phase: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get list of available phase transitions.

        Args:
            from_phase: Optional source phase to filter by

        Returns:
            List of transition dicts with "from" and "to" keys

        Example:
            >>> api = ParamsParserAPI()
            >>> transitions = api.get_available_transitions()
            >>> print(transitions)
            [{"from": "0a", "to": "1"}, {"from": "0b", "to": "1"}, ...]

            >>> # Filter by source phase
            >>> transitions = api.get_available_transitions("0a")
            >>> print(transitions)
            [{"from": "0a", "to": "1"}]
        """
        transitions = ParserFactory.get_available_transitions(from_phase)
        return [{"from": t[0], "to": t[1]} for t in transitions]


# =============================================================================
# Convenience Functions
# =============================================================================

def parse_phase(
    from_phase: str,
    to_phase: str,
    upstream_output: Dict[str, Any],
    validate: bool = True,
    output_format: str = "api"
) -> PhaseTransitionResponse:
    """
    Convenience function to parse phase output.

    Args:
        from_phase: Source phase identifier
        to_phase: Target phase identifier
        upstream_output: Output from the upstream phase
        validate: Whether to validate schema (default: True)
        output_format: Output format - "cli" or "api" (default: "api")

    Returns:
        PhaseTransitionResponse with config and status

    Example:
        >>> response = parse_phase("0a", "1", optimizer_output)
        >>> print(response.config)
    """
    api = ParamsParserAPI(
        validate=validate,
        output_format=output_format
    )
    return api.parse(from_phase, to_phase, upstream_output)
