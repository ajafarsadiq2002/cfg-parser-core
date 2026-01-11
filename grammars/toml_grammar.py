"""
TOML Grammar - Parse TOML (Tom's Obvious Minimal Language) data.

Features:
- Key-value pairs
- Basic strings and literal strings
- Integers, floats, booleans
- Arrays (inline)
- Tables [table] and inline tables {key = value}
- Datetime support
- Comments

Note: This implements TOML v1.0.0 subset suitable for LL(1) parsing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.grammar import Grammar
from core.tokenizer import Tokenizer
from core.parser import Parser
from core.ast import Node
from core.visitor import Visitor
from typing import Dict, List, Any, Union
from datetime import datetime, date, time


def create_toml_grammar() -> Grammar:
    """
    Create the TOML grammar.

    TOML Grammar (LL(1) compatible):
        toml        -> items
        items       -> item items | ε
        item        -> table | keyval | NEWLINE | COMMENT
        table       -> LBRACKET key RBRACKET
        keyval      -> key EQUALS value
        key         -> BARE_KEY | BASIC_STRING | LITERAL_STRING
        value       -> BASIC_STRING | LITERAL_STRING | INTEGER | FLOAT
                     | BOOLEAN | DATETIME | array | inline_table
        array       -> LBRACKET array_body RBRACKET
        array_body  -> elements | ε
        elements    -> value elements_rest
        elements_rest -> COMMA value elements_rest | COMMA | ε
        inline_table -> LBRACE inline_body RBRACE
        inline_body -> inline_pairs | ε
        inline_pairs -> keyval inline_pairs_rest
        inline_pairs_rest -> COMMA keyval inline_pairs_rest | ε
    """
    g = Grammar("toml")

    # Define terminals
    g.terminal(
        "LBRACKET", "RBRACKET", "LBRACE", "RBRACE",
        "EQUALS", "COMMA", "DOT", "NEWLINE", "COMMENT",
        "BARE_KEY", "BASIC_STRING", "LITERAL_STRING",
        "INTEGER", "FLOAT", "BOOLEAN", "DATETIME"
    )

    # toml -> items
    g.add_rule("toml", ["items"])

    # items -> item items | ε
    g.add_rule("items",
        ["item", "items"],
        []  # epsilon
    )

    # item -> table | keyval | NEWLINE | COMMENT
    # Need to distinguish: LBRACKET starts table, key starts keyval
    g.add_rule("item",
        ["table"],
        ["keyval"],
        ["NEWLINE"],
        ["COMMENT"]
    )

    # table -> LBRACKET key RBRACKET
    g.add_rule("table",
        ["LBRACKET", "key", "RBRACKET"]
    )

    # keyval -> key EQUALS value
    g.add_rule("keyval",
        ["key", "EQUALS", "value"]
    )

    # key -> BARE_KEY | BASIC_STRING | LITERAL_STRING
    g.add_rule("key",
        ["BARE_KEY"],
        ["BASIC_STRING"],
        ["LITERAL_STRING"]
    )

    # value -> string | number | boolean | datetime | array | inline_table
    g.add_rule("value",
        ["BASIC_STRING"],
        ["LITERAL_STRING"],
        ["INTEGER"],
        ["FLOAT"],
        ["BOOLEAN"],
        ["DATETIME"],
        ["array"],
        ["inline_table"]
    )

    # array -> LBRACKET array_body RBRACKET
    g.add_rule("array",
        ["LBRACKET", "array_body", "RBRACKET"]
    )

    # array_body -> elements | ε
    g.add_rule("array_body",
        ["elements"],
        []  # epsilon - empty array
    )

    # elements -> value elements_rest
    g.add_rule("elements",
        ["value", "elements_rest"]
    )

    # elements_rest -> COMMA value elements_rest | COMMA | ε
    g.add_rule("elements_rest",
        ["COMMA", "value", "elements_rest"],
        ["COMMA"],  # trailing comma
        []  # epsilon
    )

    # inline_table -> LBRACE inline_body RBRACE
    g.add_rule("inline_table",
        ["LBRACE", "inline_body", "RBRACE"]
    )

    # inline_body -> inline_pairs | ε
    g.add_rule("inline_body",
        ["inline_pairs"],
        []  # epsilon - empty table
    )

    # inline_pairs -> keyval inline_pairs_rest
    g.add_rule("inline_pairs",
        ["keyval", "inline_pairs_rest"]
    )

    # inline_pairs_rest -> COMMA keyval inline_pairs_rest | ε
    g.add_rule("inline_pairs_rest",
        ["COMMA", "keyval", "inline_pairs_rest"],
        []  # epsilon
    )

    return g


def create_toml_tokenizer() -> Tokenizer:
    """
    Create the TOML tokenizer.

    Handles:
    - Whitespace (skipped, except newlines)
    - Comments (# ...)
    - Structural characters
    - Strings (basic "..." and literal '...')
    - Numbers (integers and floats)
    - Booleans
    - Datetimes
    - Bare keys
    """
    t = Tokenizer()

    # Skip spaces and tabs (NOT newlines - they're significant)
    t.add("WS", r"[ \t]+", skip=True)

    # Comments
    t.add("COMMENT", r"#[^\n]*")

    # Newlines
    t.add("NEWLINE", r"\n|\r\n")

    # Structural characters
    t.add("LBRACKET", r"\[")
    t.add("RBRACKET", r"\]")
    t.add("LBRACE", r"\{")
    t.add("RBRACE", r"\}")
    t.add("EQUALS", r"=")
    t.add("COMMA", r",")
    t.add("DOT", r"\.")

    # Booleans (before bare keys)
    t.add("BOOLEAN", r"true|false")

    # Datetime (ISO 8601 format) - before integers
    t.add("DATETIME", r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?")

    # Float (before integer to match first)
    t.add("FLOAT", r"[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?|[+-]?\d+[eE][+-]?\d+|[+-]?(?:inf|nan)")

    # Integer (decimal, hex, octal, binary)
    t.add("INTEGER", r"[+-]?(?:0x[0-9a-fA-F_]+|0o[0-7_]+|0b[01_]+|\d[0-9_]*)")

    # Basic string (double-quoted, with escapes)
    t.add("BASIC_STRING", r'"(?:[^"\\]|\\.)*"')

    # Literal string (single-quoted, no escapes)
    t.add("LITERAL_STRING", r"'[^']*'")

    # Bare key (alphanumeric, dash, underscore)
    t.add("BARE_KEY", r"[A-Za-z0-9_-]+")

    return t


class TOMLEvaluator(Visitor):
    """
    Evaluates TOML AST to Python dict.

    Usage:
        ast = parser.parse_to_ast('key = "value"')
        result = TOMLEvaluator().visit(ast)
        # result = {"key": "value"}
    """

    def __init__(self):
        self._result: Dict[str, Any] = {}
        self._current_table: Dict[str, Any] = None

    def visit_toml(self, node: Node) -> Dict[str, Any]:
        """Convert TOML to dict."""
        self._result = {}
        self._current_table = self._result

        for child in node.children:
            if child.type == "items":
                self._visit_items(child)

        return self._result

    def _visit_items(self, node: Node):
        """Process items."""
        for child in node.children:
            if child.type == "item":
                self._visit_item(child)
            elif child.type == "items":
                self._visit_items(child)

    def _visit_item(self, node: Node):
        """Process single item."""
        for child in node.children:
            if child.type == "table":
                self._visit_table(child)
            elif child.type == "keyval":
                key, value = self._parse_keyval(child)
                self._current_table[key] = value

    def _visit_table(self, node: Node):
        """Process table header [name]."""
        key = None
        for child in node.children:
            if child.type == "key":
                key = self._parse_key(child)

        if key:
            # Create nested table if needed
            if key not in self._result:
                self._result[key] = {}
            self._current_table = self._result[key]

    def _parse_keyval(self, node: Node) -> tuple:
        """Parse key = value."""
        key = None
        value = None

        for child in node.children:
            if child.type == "key":
                key = self._parse_key(child)
            elif child.type == "value":
                value = self._parse_value(child)

        return key, value

    def _parse_key(self, node: Node) -> str:
        """Parse key."""
        for child in node.children:
            if child.type == "BARE_KEY":
                return child.value
            elif child.type == "BASIC_STRING":
                return self._parse_basic_string(child.value)
            elif child.type == "LITERAL_STRING":
                return child.value[1:-1]  # Remove quotes
        return ""

    def _parse_value(self, node: Node) -> Any:
        """Parse value."""
        for child in node.children:
            if child.type == "BASIC_STRING":
                return self._parse_basic_string(child.value)
            elif child.type == "LITERAL_STRING":
                return child.value[1:-1]
            elif child.type == "INTEGER":
                return self._parse_integer(child.value)
            elif child.type == "FLOAT":
                return self._parse_float(child.value)
            elif child.type == "BOOLEAN":
                return child.value == "true"
            elif child.type == "DATETIME":
                return self._parse_datetime(child.value)
            elif child.type == "array":
                return self._parse_array(child)
            elif child.type == "inline_table":
                return self._parse_inline_table(child)
        return None

    def _parse_basic_string(self, s: str) -> str:
        """Parse basic string with escapes."""
        s = s[1:-1]  # Remove quotes

        # Handle escape sequences
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                c = s[i + 1]
                if c == 'n': result.append('\n')
                elif c == 't': result.append('\t')
                elif c == 'r': result.append('\r')
                elif c == '\\': result.append('\\')
                elif c == '"': result.append('"')
                elif c == 'b': result.append('\b')
                elif c == 'f': result.append('\f')
                else: result.append(c)
                i += 2
            else:
                result.append(s[i])
                i += 1

        return ''.join(result)

    def _parse_integer(self, s: str) -> int:
        """Parse integer (handles underscores and bases)."""
        s = s.replace('_', '')
        if s.startswith('0x') or s.startswith('+0x') or s.startswith('-0x'):
            return int(s, 16)
        elif s.startswith('0o') or s.startswith('+0o') or s.startswith('-0o'):
            return int(s, 8)
        elif s.startswith('0b') or s.startswith('+0b') or s.startswith('-0b'):
            return int(s, 2)
        return int(s)

    def _parse_float(self, s: str) -> float:
        """Parse float (handles inf, nan)."""
        s = s.replace('_', '')
        if s in ('inf', '+inf'):
            return float('inf')
        elif s == '-inf':
            return float('-inf')
        elif s in ('nan', '+nan', '-nan'):
            return float('nan')
        return float(s)

    def _parse_datetime(self, s: str) -> Union[datetime, date]:
        """Parse datetime."""
        try:
            if 'T' in s:
                # Full datetime
                if s.endswith('Z'):
                    s = s[:-1] + '+00:00'
                return datetime.fromisoformat(s)
            else:
                # Date only
                return date.fromisoformat(s)
        except ValueError:
            return s  # Return as string if parsing fails

    def _parse_array(self, node: Node) -> List[Any]:
        """Parse array."""
        result = []
        for child in node.children:
            if child.type == "array_body":
                self._collect_array_body(child, result)
        return result

    def _collect_array_body(self, node: Node, result: List[Any]):
        """Collect array elements."""
        for child in node.children:
            if child.type == "elements":
                self._collect_elements(child, result)

    def _collect_elements(self, node: Node, result: List[Any]):
        """Collect elements."""
        for child in node.children:
            if child.type == "value":
                result.append(self._parse_value(child))
            elif child.type == "elements_rest":
                self._collect_elements(child, result)

    def _parse_inline_table(self, node: Node) -> Dict[str, Any]:
        """Parse inline table."""
        result = {}
        for child in node.children:
            if child.type == "inline_body":
                self._collect_inline_body(child, result)
        return result

    def _collect_inline_body(self, node: Node, result: Dict[str, Any]):
        """Collect inline table pairs."""
        for child in node.children:
            if child.type == "inline_pairs":
                self._collect_inline_pairs(child, result)

    def _collect_inline_pairs(self, node: Node, result: Dict[str, Any]):
        """Collect key-value pairs."""
        for child in node.children:
            if child.type == "keyval":
                key, value = self._parse_keyval(child)
                result[key] = value
            elif child.type == "inline_pairs_rest":
                self._collect_inline_pairs(child, result)


# ==================== Convenience Functions ====================

def create_toml_parser() -> Parser:
    """Create a ready-to-use TOML parser."""
    return Parser(create_toml_grammar(), create_toml_tokenizer())


def parse_toml(text: str) -> Dict[str, Any]:
    """
    Parse TOML string to Python dict.

    Args:
        text: TOML string

    Returns:
        Python dict
    """
    parser = create_toml_parser()
    ast = parser.parse_to_ast(text)
    return TOMLEvaluator().visit(ast)


def validate_toml(text: str) -> bool:
    """
    Check if text is valid TOML.

    Args:
        text: TOML string

    Returns:
        True if valid TOML
    """
    parser = create_toml_parser()
    return parser.parse(text)


# ==================== Demo ====================

if __name__ == "__main__":
    print("=" * 60)
    print("TOML Parser Demo")
    print("=" * 60)

    toml_text = '''# This is a TOML document
title = "TOML Example"

[owner]
name = "Tom Preston-Werner"
enabled = true

[database]
server = "192.168.1.1"
ports = [8001, 8001, 8002]
connection_max = 5000
enabled = true

[servers]
alpha = {ip = "10.0.0.1", dc = "east"}
beta = {ip = "10.0.0.2", dc = "west"}
'''

    print("\nInput TOML:")
    print(toml_text)

    # Validate
    print(f"\nValid TOML: {validate_toml(toml_text)}")

    # Parse
    result = parse_toml(toml_text)
    print("\nParsed result:")
    import json
    print(json.dumps(result, indent=2, default=str))

    # Simple example
    print("\n" + "=" * 60)
    simple_toml = '''name = "test"
count = 42
pi = 3.14159
active = true
tags = ["a", "b", "c"]
'''
    print("Simple TOML:")
    print(simple_toml)
    result = parse_toml(simple_toml)
    print(f"Parsed: {result}")

    # get_valid_next demo
    print("\n" + "=" * 60)
    print("get_valid_next() Demo")
    print("=" * 60)

    parser = create_toml_parser()
    state = parser.initial_state()
    print(f"\nInitial - valid next: {parser.get_valid_next(state)}")
