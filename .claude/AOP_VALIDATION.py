#!/usr/bin/env python3
"""
AOP (Agent Output Protocol) Validation Tool

Validates that agent outputs conform to the AOP specification.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AOPMarker:
    """Represents an AOP marker."""
    type: str
    attributes: Dict[str, str]
    start_pos: int
    end_pos: Optional[int] = None


class AOPValidator:
    """Validates AOP markers in agent outputs."""

    # AOP marker patterns
    MARKER_PATTERN = r'=== AOP-(\w+)(?:\s*\|(.+))? ==='
    END_MARKER_PATTERN = r'=== END-AOP-(\w+) ==='

    # Valid marker types
    VALID_TYPES = {'FINAL', 'INTERMEDIATE', 'STREAM', 'ERROR', 'CONTEXT'}

    # Required attributes by marker type
    REQUIRED_ATTRIBUTES = {
        'FINAL': {'agent'},
        'ERROR': {'agent'},
        'INTERMEDIATE': set(),
        'STREAM': set(),
        'CONTEXT': set(),
    }

    def validate(self, output: str) -> Tuple[bool, List[str]]:
        """
        Validate AOP output.

        Returns:
            (is_valid, list of error messages)
        """
        errors = []

        # Find all markers
        start_markers = list(re.finditer(self.MARKER_PATTERN, output))
        end_markers = list(re.finditer(self.END_MARKER_PATTERN, output))

        # Check if any markers found
        if not start_markers:
            errors.append("No AOP start marker found")
            return False, errors

        # Validate each marker block
        for i, start_match in enumerate(start_markers):
            marker_type = start_match.group(1)
            attributes_str = start_match.group(2) or ''

            # Validate marker type
            if marker_type not in self.VALID_TYPES:
                errors.append(f"Invalid AOP type: {marker_type}")

            # Parse and validate attributes
            attrs = self._parse_attributes(attributes_str)
            required = self.REQUIRED_ATTRIBUTES.get(marker_type, set())
            missing = required - attrs.keys()
            if missing:
                errors.append(f"Missing required attributes for {marker_type}: {missing}")

            # Find corresponding end marker
            if i < len(end_markers):
                end_match = end_markers[i]
                end_type = end_match.group(1)
                if end_type != marker_type:
                    errors.append(f"Marker mismatch: start={marker_type}, end={end_type}")

                # Check ordering
                if end_match.start() < start_match.end():
                    errors.append(f"End marker before start marker for type {marker_type}")
            else:
                errors.append(f"No END-AOP-{marker_type} marker found")

        return len(errors) == 0, errors

    def _parse_attributes(self, attributes_str: str) -> Dict[str, str]:
        """Parse key=value attributes from marker."""
        attrs = {}
        if not attributes_str:
            return attrs

        # Split by | and parse key=value pairs
        for pair in attributes_str.split('|'):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                attrs[key.strip()] = value.strip()
        return attrs

    def detect_marker(self, output: str) -> Optional[AOPMarker]:
        """
        Detect the first AOP marker in output.

        Returns AOPMarker object or None if no marker found.
        """
        match = re.search(self.MARKER_PATTERN, output)
        if not match:
            return None

        marker_type = match.group(1)
        attributes_str = match.group(2) or ''

        return AOPMarker(
            type=marker_type,
            attributes=self._parse_attributes(attributes_str),
            start_pos=match.start()
        )

    def extract_content(self, output: str, marker_type: str) -> Optional[str]:
        """
        Extract content between AOP markers of specified type.

        Returns content string or None if markers not found.
        """
        pattern = rf'=== AOP-{marker_type}.*? ===\n(.*?)\n=== END-AOP-{marker_type} ==='
        match = re.search(pattern, output, re.DOTALL)

        if match:
            return match.group(1).strip()
        return None


def validate_file(file_path: str) -> Tuple[bool, List[str]]:
    """Validate AOP markers in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        validator = AOPValidator()
        return validator.validate(content)
    except Exception as e:
        return False, [f"Error reading file: {e}"]


def validate_agent_output(output: str) -> Dict:
    """
    Validate agent output and return detailed report.

    Returns dict with validation results.
    """
    validator = AOPValidator()
    is_valid, errors = validator.validate(output)
    marker = validator.detect_marker(output)

    return {
        'valid': is_valid,
        'errors': errors,
        'marker_type': marker.type if marker else None,
        'attributes': marker.attributes if marker else {},
    }


# CLI usage
if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python AOP_VALIDATION.py <output_string_or_file>")
        sys.exit(1)

    input_arg = sys.argv[1]

    # Check if it's a file path
    try:
        with open(input_arg, 'r') as f:
            output = f.read()
    except FileNotFoundError:
        output = input_arg

    result = validate_agent_output(output)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result['valid'] else 1)
