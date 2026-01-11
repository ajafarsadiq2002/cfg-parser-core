"""
Tokenizer - Converts input text into a stream of tokens.

This is Component 1 of the CFG Parser Core.

Features:
- Regex-based pattern matching
- Line and column tracking for error messages
- Skip patterns (whitespace, comments)
- Lookahead support
- Streaming tokenization
"""

from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Callable
import re


@dataclass
class Token:
    """
    Represents a single token from the input.

    Attributes:
        type: The token type (e.g., "STRING", "NUMBER", "{")
        value: The actual text matched
        line: Line number (1-based)
        column: Column number (1-based)
        pos: Absolute position in input
    """
    type: str
    value: str
    line: int = 1
    column: int = 1
    pos: int = 0

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, line={self.line}, col={self.column})"

    def __eq__(self, other):
        if isinstance(other, Token):
            return self.type == other.type and self.value == other.value
        if isinstance(other, str):
            return self.type == other
        return False


@dataclass
class TokenPattern:
    """
    Defines a pattern for matching tokens.

    Attributes:
        name: Token type name
        pattern: Regex pattern string
        regex: Compiled regex
        skip: If True, matched tokens are discarded (for whitespace/comments)
        transform: Optional function to transform matched value
    """
    name: str
    pattern: str
    regex: re.Pattern
    skip: bool = False
    transform: Optional[Callable[[str], str]] = None


class Tokenizer:
    r"""
    Configurable tokenizer that converts text into tokens.

    The tokenizer tries patterns in the order they were added,
    so more specific patterns should be added before general ones.

    Usage:
        tokenizer = Tokenizer()
        tokenizer.add("NUMBER", r"\d+")
        tokenizer.add("+", r"\+")
        tokenizer.add("WHITESPACE", r"\s+", skip=True)

        tokens = tokenizer.tokenize("1 + 2")
        # [Token('NUMBER', '1'), Token('+', '+'), Token('NUMBER', '2'), Token('EOF', '')]
    """

    def __init__(self):
        self.patterns: List[TokenPattern] = []
        self._tokens: List[Token] = []
        self._pos: int = 0

    def add(self, name: str, pattern: str, skip: bool = False,
            transform: Optional[Callable[[str], str]] = None) -> 'Tokenizer':
        """
        Add a token pattern.

        Args:
            name: Token type name (e.g., "NUMBER", "STRING")
            pattern: Regex pattern to match
            skip: If True, don't include in output (for whitespace)
            transform: Optional function to transform matched text

        Returns:
            self (for method chaining)
        """
        compiled = re.compile(pattern)
        self.patterns.append(TokenPattern(name, pattern, compiled, skip, transform))
        return self

    def add_keyword(self, keyword: str) -> 'Tokenizer':
        """Add a keyword token (exact match, word boundary)."""
        pattern = rf"\b{re.escape(keyword)}\b"
        return self.add(keyword.upper(), pattern)

    def add_keywords(self, *keywords: str) -> 'Tokenizer':
        """Add multiple keywords."""
        for kw in keywords:
            self.add_keyword(kw)
        return self

    def tokenize(self, text: str) -> List[Token]:
        """
        Convert input text to a list of tokens.

        Args:
            text: Input string to tokenize

        Returns:
            List of Token objects, ending with EOF token

        Raises:
            LexerError: If an unexpected character is encountered
        """
        from .errors import LexerError

        tokens = []
        pos = 0
        line = 1
        column = 1
        line_start = 0

        while pos < len(text):
            match = None

            for pattern in self.patterns:
                match = pattern.regex.match(text, pos)
                if match:
                    value = match.group()

                    # Apply transform if provided
                    if pattern.transform:
                        value = pattern.transform(value)

                    if not pattern.skip:
                        tokens.append(Token(
                            type=pattern.name,
                            value=value,
                            line=line,
                            column=pos - line_start + 1,
                            pos=pos
                        ))

                    # Update position tracking
                    matched_text = match.group()
                    newlines = matched_text.count('\n')
                    if newlines:
                        line += newlines
                        line_start = pos + matched_text.rfind('\n') + 1

                    pos = match.end()
                    break

            if not match:
                context = text[max(0, pos-10):pos+10]
                raise LexerError(
                    f"Unexpected character",
                    char=text[pos],
                    line=line,
                    column=pos - line_start + 1,
                    context=context
                )

        # Add EOF token
        tokens.append(Token("EOF", "", line, pos - line_start + 1, pos))

        self._tokens = tokens
        self._pos = 0

        return tokens

    def tokenize_iter(self, text: str) -> Iterator[Token]:
        """
        Tokenize lazily, yielding tokens one at a time.
        Useful for large inputs or streaming.
        """
        for token in self.tokenize(text):
            yield token

    # Stream interface for parser integration
    def reset(self):
        """Reset the token stream position."""
        self._pos = 0

    def peek(self, offset: int = 0) -> Optional[Token]:
        """Look ahead in the token stream without consuming."""
        idx = self._pos + offset
        if 0 <= idx < len(self._tokens):
            return self._tokens[idx]
        return None

    def current(self) -> Optional[Token]:
        """Get current token without consuming."""
        return self.peek(0)

    def advance(self) -> Optional[Token]:
        """Consume and return current token."""
        token = self.current()
        if token:
            self._pos += 1
        return token

    def expect(self, token_type: str) -> Token:
        """
        Consume token of expected type or raise error.

        Args:
            token_type: Expected token type

        Returns:
            The consumed token

        Raises:
            ParseError: If current token doesn't match
        """
        from .errors import ParseError

        token = self.current()
        if token is None:
            raise ParseError(
                "Unexpected end of input",
                expected={token_type},
                found="EOF"
            )
        if token.type != token_type:
            raise ParseError(
                f"Expected {token_type}",
                expected={token_type},
                found=token.type,
                line=token.line,
                column=token.column
            )
        return self.advance()

    def match(self, *token_types: str) -> Optional[Token]:
        """
        If current token matches any type, consume and return it.
        Otherwise return None.
        """
        token = self.current()
        if token and token.type in token_types:
            return self.advance()
        return None

    def is_at_end(self) -> bool:
        """Check if at end of token stream."""
        token = self.current()
        return token is None or token.type == "EOF"

    def remaining(self) -> List[Token]:
        """Get all remaining tokens."""
        return self._tokens[self._pos:]

    def __repr__(self):
        return f"Tokenizer(patterns={len(self.patterns)})"
