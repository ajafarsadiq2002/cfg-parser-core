"""
Error Handling - Clear, helpful error messages for parsing.

This is Component 6 of the CFG Parser Core.

Features:
- Pinpoint exact error location (line, column)
- Show what was expected vs what was found
- Display context around the error
- Suggest possible fixes
"""

from dataclasses import dataclass, field
from typing import Set, Optional, List


class CFGParserError(Exception):
    """Base exception for all parser errors."""
    pass


@dataclass
class LexerError(CFGParserError):
    """
    Error during tokenization.

    Raised when the tokenizer encounters an unexpected character
    that doesn't match any defined pattern.
    """
    message: str
    char: str = ""
    line: int = 1
    column: int = 1
    context: str = ""

    def __str__(self):
        error_msg = [
            f"LexerError at line {self.line}, column {self.column}:",
            f"  {self.message}: {self.char!r}",
        ]
        if self.context:
            error_msg.append(f"  Context: ...{self.context}...")
        return "\n".join(error_msg)


@dataclass
class ParseError(CFGParserError):
    """
    Error during parsing.

    Raised when the parser encounters a token that doesn't match
    the expected grammar.
    """
    message: str
    expected: Set[str] = field(default_factory=set)
    found: str = ""
    line: int = 1
    column: int = 1
    context: str = ""
    source: str = ""

    def __str__(self):
        lines = [f"ParseError at line {self.line}, column {self.column}:"]
        lines.append(f"  {self.message}")

        if self.expected:
            expected_str = ", ".join(sorted(self.expected))
            lines.append(f"  Expected: {expected_str}")

        if self.found:
            lines.append(f"  Found: {self.found}")

        if self.source and self.line > 0:
            lines.append("")
            lines.append(self._format_source_context())

        return "\n".join(lines)

    def _format_source_context(self) -> str:
        """Format the source code context with error indicator."""
        source_lines = self.source.split('\n')

        if self.line <= len(source_lines):
            error_line = source_lines[self.line - 1]
            pointer = " " * (self.column - 1) + "^"

            return f"  {error_line}\n  {pointer}"
        return ""

    def with_source(self, source: str) -> 'ParseError':
        """Return a copy with source context added."""
        return ParseError(
            message=self.message,
            expected=self.expected,
            found=self.found,
            line=self.line,
            column=self.column,
            context=self.context,
            source=source
        )


@dataclass
class GrammarError(CFGParserError):
    """
    Error in grammar definition.

    Raised when the grammar is invalid or inconsistent.
    """
    message: str
    rule_name: str = ""
    details: str = ""

    def __str__(self):
        lines = [f"GrammarError: {self.message}"]
        if self.rule_name:
            lines.append(f"  In rule: {self.rule_name}")
        if self.details:
            lines.append(f"  Details: {self.details}")
        return "\n".join(lines)


class ErrorCollector:
    """
    Collects multiple errors during parsing.

    Useful for reporting all errors in a file instead of stopping at the first.
    """

    def __init__(self, max_errors: int = 10):
        self.errors: List[CFGParserError] = []
        self.max_errors = max_errors

    def add(self, error: CFGParserError):
        """Add an error to the collection."""
        self.errors.append(error)
        if len(self.errors) >= self.max_errors:
            raise TooManyErrorsError(f"Too many errors (>{self.max_errors})")

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def clear(self):
        """Clear all collected errors."""
        self.errors = []

    def format_all(self) -> str:
        """Format all errors as a string."""
        return "\n\n".join(str(e) for e in self.errors)

    def __len__(self):
        return len(self.errors)

    def __iter__(self):
        return iter(self.errors)


class TooManyErrorsError(CFGParserError):
    """Raised when error limit is exceeded."""
    pass


def format_error_context(source: str, line: int, column: int,
                         context_lines: int = 2) -> str:
    """
    Format error context showing surrounding lines.

    Args:
        source: Full source text
        line: Error line (1-based)
        column: Error column (1-based)
        context_lines: Number of lines to show before/after

    Returns:
        Formatted string with line numbers and error pointer
    """
    lines = source.split('\n')
    result = []

    start = max(0, line - 1 - context_lines)
    end = min(len(lines), line + context_lines)

    # Calculate width for line numbers
    width = len(str(end))

    for i in range(start, end):
        line_num = i + 1
        prefix = ">" if line_num == line else " "
        result.append(f"{prefix} {line_num:>{width}} | {lines[i]}")

        # Add error pointer
        if line_num == line:
            pointer = " " * (width + 4 + column - 1) + "^"
            result.append(pointer)

    return "\n".join(result)
