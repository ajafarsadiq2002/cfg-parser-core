"""
YAML Grammar - Parse YAML (YAML Ain't Markup Language) data.

This implements a JSON-compatible subset of YAML that can be parsed with LL(1).

Features:
- Key-value pairs (flow style: key: value)
- Strings (quoted and unquoted)
- Numbers, booleans, null
- Inline arrays [1, 2, 3]
- Inline objects {a: 1, b: 2}
- Comments (# ...)

Note: This does NOT support indentation-based block style.
Full YAML requires a context-sensitive parser which is beyond LL(1).
This subset covers most common YAML use cases in config files.
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


def create_yaml_grammar() -> Grammar:
    """
    Create the YAML grammar (JSON-compatible subset).

    YAML Grammar (LL(1) compatible):
        yaml        -> value
        value       -> object | array | scalar
        object      -> LBRACE object_body RBRACE
        object_body -> pairs | ε
        pairs       -> pair pairs_rest
        pairs_rest  -> COMMA pair pairs_rest | ε
        pair        -> key COLON value
        key         -> STRING | UNQUOTED
        array       -> LBRACKET array_body RBRACKET
        array_body  -> elements | ε
        elements    -> value elements_rest
        elements_rest -> COMMA value elements_rest | ε
        scalar      -> STRING | NUMBER | BOOLEAN | NULL | UNQUOTED
    """
    g = Grammar("yaml")

    # Define terminals
    g.terminal(
        "LBRACE", "RBRACE", "LBRACKET", "RBRACKET",
        "COLON", "COMMA",
        "STRING", "NUMBER", "BOOLEAN", "NULL", "UNQUOTED"
    )

    # yaml -> value
    g.add_rule("yaml", ["value"])

    # value -> object | array | scalar
    g.add_rule("value",
        ["object"],
        ["array"],
        ["scalar"]
    )

    # object -> LBRACE object_body RBRACE
    g.add_rule("object",
        ["LBRACE", "object_body", "RBRACE"]
    )

    # object_body -> pairs | ε
    g.add_rule("object_body",
        ["pairs"],
        []  # epsilon - empty object
    )

    # pairs -> pair pairs_rest
    g.add_rule("pairs",
        ["pair", "pairs_rest"]
    )

    # pairs_rest -> COMMA pair pairs_rest | ε
    g.add_rule("pairs_rest",
        ["COMMA", "pair", "pairs_rest"],
        []  # epsilon
    )

    # pair -> key COLON value
    g.add_rule("pair",
        ["key", "COLON", "value"]
    )

    # key -> STRING | UNQUOTED
    g.add_rule("key",
        ["STRING"],
        ["UNQUOTED"]
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

    # elements_rest -> COMMA value elements_rest | ε
    g.add_rule("elements_rest",
        ["COMMA", "value", "elements_rest"],
        []  # epsilon
    )

    # scalar -> STRING | NUMBER | BOOLEAN | NULL | UNQUOTED
    g.add_rule("scalar",
        ["STRING"],
        ["NUMBER"],
        ["BOOLEAN"],
        ["NULL"],
        ["UNQUOTED"]
    )

    return g


def create_yaml_tokenizer() -> Tokenizer:
    """
    Create the YAML tokenizer.

    Handles:
    - Whitespace (skipped)
    - Comments (# ...)
    - Structural characters
    - Strings (single or double quoted)
    - Numbers
    - Booleans (true/false, yes/no, on/off)
    - Null (null, ~)
    - Unquoted strings
    """
    t = Tokenizer()

    # Skip whitespace and newlines (flow style doesn't care)
    t.add("WS", r"[ \t\n\r]+", skip=True)

    # Comments
    t.add("COMMENT", r"#[^\n]*", skip=True)

    # Structural characters
    t.add("LBRACE", r"\{")
    t.add("RBRACE", r"\}")
    t.add("LBRACKET", r"\[")
    t.add("RBRACKET", r"\]")
    t.add("COLON", r":")
    t.add("COMMA", r",")

    # Null (before boolean and unquoted)
    t.add("NULL", r"null|Null|NULL|~")

    # Boolean (various YAML formats)
    t.add("BOOLEAN", r"true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF")

    # Number (integer and float)
    t.add("NUMBER", r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")

    # Double-quoted string
    t.add("STRING", r'"(?:[^"\\]|\\.)*"')

    # Single-quoted string (no escapes in YAML single quotes)
    t.add("STRING", r"'(?:[^']|'')*'")

    # Unquoted string (alphanumeric, safe chars - stops at special chars)
    t.add("UNQUOTED", r"[a-zA-Z_][a-zA-Z0-9_.-]*")

    return t


def create_yaml_flow_tokenizer() -> Tokenizer:
    """
    Create YAML tokenizer for simple key: value format.

    This is an alternative tokenizer for parsing simple YAML like:
        name: John
        age: 30
    """
    t = Tokenizer()

    # Newlines are significant in this mode
    t.add("NEWLINE", r"\n|\r\n")

    # Skip spaces and tabs
    t.add("WS", r"[ \t]+", skip=True)

    # Comments
    t.add("COMMENT", r"#[^\n]*", skip=True)

    # Colon (with optional space after for key: value)
    t.add("COLON", r":[ \t]*")

    # Null
    t.add("NULL", r"null|Null|NULL|~")

    # Boolean
    t.add("BOOLEAN", r"true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO")

    # Number
    t.add("NUMBER", r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")

    # Quoted strings
    t.add("STRING", r'"(?:[^"\\]|\\.)*"')
    t.add("STRING", r"'(?:[^']|'')*'")

    # Unquoted value (rest of line)
    t.add("UNQUOTED", r"[^\n\r#:,\[\]\{\}]+")

    return t


class YAMLEvaluator(Visitor):
    """
    Evaluates YAML AST to Python data structures.

    Usage:
        ast = parser.parse_to_ast('{name: John, age: 30}')
        result = YAMLEvaluator().visit(ast)
        # result = {"name": "John", "age": 30}
    """

    def visit_yaml(self, node: Node) -> Any:
        """Root node."""
        if node.children:
            return self.visit(node.children[0])
        return None

    def visit_value(self, node: Node) -> Any:
        """Parse value."""
        if node.children:
            return self.visit(node.children[0])
        return None

    def visit_object(self, node: Node) -> Dict[str, Any]:
        """Parse object."""
        result = {}
        for child in node.children:
            if child.type == "object_body":
                self._collect_object_body(child, result)
        return result

    def _collect_object_body(self, node: Node, result: Dict[str, Any]):
        """Collect from object_body."""
        for child in node.children:
            if child.type == "pairs":
                self._collect_pairs(child, result)

    def _collect_pairs(self, node: Node, result: Dict[str, Any]):
        """Collect key-value pairs."""
        for child in node.children:
            if child.type == "pair":
                key, value = self._parse_pair(child)
                result[key] = value
            elif child.type == "pairs_rest":
                self._collect_pairs(child, result)

    def _parse_pair(self, node: Node) -> tuple:
        """Parse key: value pair."""
        key = None
        value = None

        for child in node.children:
            if child.type == "key":
                key = self._parse_key(child)
            elif child.type == "value":
                value = self.visit(child)

        return key, value

    def _parse_key(self, node: Node) -> str:
        """Parse key."""
        for child in node.children:
            if child.type == "STRING":
                return self._parse_string(child.value)
            elif child.type == "UNQUOTED":
                return child.value
        return ""

    def visit_array(self, node: Node) -> List[Any]:
        """Parse array."""
        result = []
        for child in node.children:
            if child.type == "array_body":
                self._collect_array_body(child, result)
        return result

    def _collect_array_body(self, node: Node, result: List[Any]):
        """Collect from array_body."""
        for child in node.children:
            if child.type == "elements":
                self._collect_elements(child, result)

    def _collect_elements(self, node: Node, result: List[Any]):
        """Collect array elements."""
        for child in node.children:
            if child.type == "value":
                result.append(self.visit(child))
            elif child.type == "elements_rest":
                self._collect_elements(child, result)

    def visit_scalar(self, node: Node) -> Any:
        """Parse scalar value."""
        if not node.children:
            return None

        child = node.children[0]

        if child.type == "STRING":
            return self._parse_string(child.value)
        elif child.type == "NUMBER":
            return self._parse_number(child.value)
        elif child.type == "BOOLEAN":
            return self._parse_boolean(child.value)
        elif child.type == "NULL":
            return None
        elif child.type == "UNQUOTED":
            return child.value

        return None

    def _parse_string(self, s: str) -> str:
        """Parse string value."""
        if s.startswith('"') and s.endswith('"'):
            # Double-quoted: handle escapes
            s = s[1:-1]
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
                    else: result.append(c)
                    i += 2
                else:
                    result.append(s[i])
                    i += 1
            return ''.join(result)
        elif s.startswith("'") and s.endswith("'"):
            # Single-quoted: only '' -> '
            s = s[1:-1]
            return s.replace("''", "'")
        return s

    def _parse_number(self, s: str) -> Union[int, float]:
        """Parse number."""
        if '.' in s or 'e' in s.lower():
            return float(s)
        return int(s)

    def _parse_boolean(self, s: str) -> bool:
        """Parse boolean."""
        return s.lower() in ('true', 'yes', 'on')

    # Terminal visitors
    def visit_STRING(self, node: Node) -> str:
        return self._parse_string(node.value)

    def visit_NUMBER(self, node: Node) -> Union[int, float]:
        return self._parse_number(node.value)

    def visit_BOOLEAN(self, node: Node) -> bool:
        return self._parse_boolean(node.value)

    def visit_NULL(self, node: Node) -> None:
        return None

    def visit_UNQUOTED(self, node: Node) -> str:
        return node.value


# ==================== Convenience Functions ====================

def create_yaml_parser() -> Parser:
    """Create a ready-to-use YAML parser (flow/inline style)."""
    return Parser(create_yaml_grammar(), create_yaml_tokenizer())


def parse_yaml(text: str) -> Any:
    """
    Parse YAML string to Python data structure.

    Note: This parses JSON-compatible YAML (flow/inline style).
    Does NOT support indentation-based block style.

    Args:
        text: YAML string (flow style)

    Returns:
        Python object (dict, list, or scalar)
    """
    parser = create_yaml_parser()
    ast = parser.parse_to_ast(text)
    return YAMLEvaluator().visit(ast)


def validate_yaml(text: str) -> bool:
    """
    Check if text is valid YAML (flow style).

    Args:
        text: YAML string

    Returns:
        True if valid
    """
    parser = create_yaml_parser()
    return parser.parse(text)


def yaml_to_dict(text: str) -> Dict[str, Any]:
    """
    Parse YAML object to Python dict.

    Args:
        text: YAML object string like '{name: John, age: 30}'

    Returns:
        Python dict
    """
    result = parse_yaml(text)
    if isinstance(result, dict):
        return result
    raise ValueError("Input is not a YAML object")


# ==================== Demo ====================

if __name__ == "__main__":
    print("=" * 60)
    print("YAML Parser Demo (Flow/Inline Style)")
    print("=" * 60)

    # Simple object
    yaml1 = '{name: John, age: 30, active: true}'
    print(f"\nInput: {yaml1}")
    print(f"Valid: {validate_yaml(yaml1)}")
    print(f"Parsed: {parse_yaml(yaml1)}")

    # Nested object
    yaml2 = '{user: {name: "Jane Doe", email: "jane@example.com"}, count: 42}'
    print(f"\nInput: {yaml2}")
    print(f"Parsed: {parse_yaml(yaml2)}")

    # Array
    yaml3 = '[1, 2, 3, "four", true, null]'
    print(f"\nInput: {yaml3}")
    print(f"Parsed: {parse_yaml(yaml3)}")

    # Mixed
    yaml4 = '{users: [{name: Alice, age: 25}, {name: Bob, age: 30}], total: 2}'
    print(f"\nInput: {yaml4}")
    result = parse_yaml(yaml4)
    print(f"Parsed: {result}")
    print(f"First user: {result['users'][0]}")

    # Various booleans
    yaml5 = '{a: true, b: false, c: yes, d: no, e: on, f: off}'
    print(f"\nBoolean variations: {yaml5}")
    print(f"Parsed: {parse_yaml(yaml5)}")

    # Null variations
    yaml6 = '{a: null, b: ~, c: Null}'
    print(f"\nNull variations: {yaml6}")
    print(f"Parsed: {parse_yaml(yaml6)}")

    # get_valid_next demo
    print("\n" + "=" * 60)
    print("get_valid_next() Demo")
    print("=" * 60)

    parser = create_yaml_parser()
    state = parser.initial_state()
    print(f"\nInitial - valid next: {parser.get_valid_next(state)}")

    tokens = parser.tokenizer.tokenize("{name:")
    for tok in tokens[:-1]:
        state = parser.step(state, tok)
        print(f"After '{tok.value}': valid next = {parser.get_valid_next(state)}")
