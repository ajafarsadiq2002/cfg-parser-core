"""
JSON Grammar - Parse and evaluate JSON data.

This demonstrates the CFG Parser Core for a real-world format.

Features:
- Full JSON parsing (objects, arrays, strings, numbers, booleans, null)
- AST construction
- Evaluation to Python objects
- LLM constrained decoding support
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.grammar import Grammar
from core.tokenizer import Tokenizer
from core.parser import Parser
from core.ast import Node
from core.visitor import Evaluator
from typing import Any, Dict, List, Union


def create_json_grammar() -> Grammar:
    """
    Create the JSON grammar.

    JSON Grammar (LL(1) compatible):
        value       -> object | array | STRING | NUMBER | TRUE | FALSE | NULL
        object      -> '{' object_body '}'
        object_body -> members | ε
        members     -> pair members_rest
        members_rest-> ',' pair members_rest | ε
        pair        -> STRING ':' value
        array       -> '[' array_body ']'
        array_body  -> elements | ε
        elements    -> value elements_rest
        elements_rest -> ',' value elements_rest | ε
    """
    g = Grammar("value")

    # Define terminals
    g.terminal(
        "{", "}", "[", "]", ":", ",",
        "STRING", "NUMBER", "TRUE", "FALSE", "NULL"
    )

    # Production rules
    g.add_rule("value",
        ["object"],
        ["array"],
        ["STRING"],
        ["NUMBER"],
        ["TRUE"],
        ["FALSE"],
        ["NULL"]
    )

    # Object: { object_body }
    g.add_rule("object",
        ["{", "object_body", "}"]
    )

    # object_body: members | ε (empty)
    g.add_rule("object_body",
        ["members"],
        []  # epsilon - empty object
    )

    # members: pair members_rest
    g.add_rule("members",
        ["pair", "members_rest"]
    )

    # members_rest: , pair members_rest | ε
    g.add_rule("members_rest",
        [",", "pair", "members_rest"],
        []  # epsilon
    )

    # pair: STRING : value
    g.add_rule("pair",
        ["STRING", ":", "value"]
    )

    # Array: [ array_body ]
    g.add_rule("array",
        ["[", "array_body", "]"]
    )

    # array_body: elements | ε (empty)
    g.add_rule("array_body",
        ["elements"],
        []  # epsilon - empty array
    )

    # elements: value elements_rest
    g.add_rule("elements",
        ["value", "elements_rest"]
    )

    # elements_rest: , value elements_rest | ε
    g.add_rule("elements_rest",
        [",", "value", "elements_rest"],
        []  # epsilon
    )

    return g


def create_json_tokenizer() -> Tokenizer:
    """
    Create the JSON tokenizer.

    Handles:
    - Whitespace (skipped)
    - Strings (double-quoted)
    - Numbers (integer and floating point)
    - Booleans (true/false)
    - Null
    - Structural characters ({, }, [, ], :, ,)
    """
    t = Tokenizer()

    # Skip whitespace
    t.add("WHITESPACE", r"[ \t\n\r]+", skip=True)

    # Structural characters (order matters - add before identifiers)
    t.add("{", r"\{")
    t.add("}", r"\}")
    t.add("[", r"\[")
    t.add("]", r"\]")
    t.add(":", r":")
    t.add(",", r",")

    # Keywords (before STRING to match first)
    t.add("TRUE", r"true")
    t.add("FALSE", r"false")
    t.add("NULL", r"null")

    # String (handles escape sequences)
    t.add("STRING", r'"(?:[^"\\]|\\.)*"')

    # Number (integer or floating point, with optional sign and exponent)
    t.add("NUMBER", r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")

    return t


class JSONEvaluator(Evaluator):
    """
    Evaluates JSON AST to Python objects.

    Usage:
        ast = parser.parse_to_ast('{"name": "John", "age": 30}')
        result = JSONEvaluator().visit(ast)
        # result = {"name": "John", "age": 30}
    """

    def visit_value(self, node: Node) -> Any:
        """Value is a wrapper - return child's value."""
        if node.children:
            return self.visit(node.children[0])
        return None

    def visit_object(self, node: Node) -> Dict[str, Any]:
        """Convert object node to Python dict."""
        result = {}

        for child in node.children:
            if child.type == "object_body":
                self._collect_object_body(child, result)
            elif child.type == "members":
                self._collect_members(child, result)
            elif child.type == "pair":
                key, value = self._parse_pair(child)
                result[key] = value

        return result

    def _collect_object_body(self, node: Node, result: Dict[str, Any]):
        """Collect from object_body node."""
        for child in node.children:
            if child.type == "members":
                self._collect_members(child, result)

    def _collect_members(self, node: Node, result: Dict[str, Any]):
        """Recursively collect all pairs from members node."""
        for child in node.children:
            if child.type == "pair":
                key, value = self._parse_pair(child)
                result[key] = value
            elif child.type == "members_rest":
                self._collect_members_rest(child, result)

    def _collect_members_rest(self, node: Node, result: Dict[str, Any]):
        """Collect from members_rest node."""
        for child in node.children:
            if child.type == "pair":
                key, value = self._parse_pair(child)
                result[key] = value
            elif child.type == "members_rest":
                self._collect_members_rest(child, result)

    def _parse_pair(self, node: Node) -> tuple:
        """Parse a key-value pair."""
        key = None
        value = None

        for child in node.children:
            if child.type == "STRING" and key is None:
                key = self._parse_string(child.value)
            elif child.type in ("value", "object", "array", "STRING", "NUMBER",
                               "TRUE", "FALSE", "NULL"):
                value = self.visit(child)

        return key, value

    def visit_array(self, node: Node) -> List[Any]:
        """Convert array node to Python list."""
        result = []

        for child in node.children:
            if child.type == "array_body":
                self._collect_array_body(child, result)
            elif child.type == "elements":
                self._collect_elements(child, result)
            elif child.type == "value":
                result.append(self.visit(child))

        return result

    def _collect_array_body(self, node: Node, result: List[Any]):
        """Collect from array_body node."""
        for child in node.children:
            if child.type == "elements":
                self._collect_elements(child, result)

    def _collect_elements(self, node: Node, result: List[Any]):
        """Recursively collect all values from elements node."""
        for child in node.children:
            if child.type == "value":
                result.append(self.visit(child))
            elif child.type == "elements_rest":
                self._collect_elements_rest(child, result)

    def _collect_elements_rest(self, node: Node, result: List[Any]):
        """Collect from elements_rest node."""
        for child in node.children:
            if child.type == "value":
                result.append(self.visit(child))
            elif child.type == "elements_rest":
                self._collect_elements_rest(child, result)

    def visit_STRING(self, node: Node) -> str:
        """Parse string value (remove quotes, handle escapes)."""
        return self._parse_string(node.value)

    def _parse_string(self, s: str) -> str:
        """Parse JSON string, handling escapes."""
        # Remove surrounding quotes
        s = s[1:-1]

        # Handle escape sequences
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                next_char = s[i + 1]
                if next_char == 'n':
                    result.append('\n')
                elif next_char == 't':
                    result.append('\t')
                elif next_char == 'r':
                    result.append('\r')
                elif next_char == '\\':
                    result.append('\\')
                elif next_char == '"':
                    result.append('"')
                elif next_char == '/':
                    result.append('/')
                elif next_char == 'b':
                    result.append('\b')
                elif next_char == 'f':
                    result.append('\f')
                elif next_char == 'u' and i + 5 < len(s):
                    # Unicode escape
                    hex_str = s[i+2:i+6]
                    try:
                        result.append(chr(int(hex_str, 16)))
                        i += 4
                    except ValueError:
                        result.append(next_char)
                else:
                    result.append(next_char)
                i += 2
            else:
                result.append(s[i])
                i += 1

        return ''.join(result)

    def visit_NUMBER(self, node: Node) -> Union[int, float]:
        """Parse number value."""
        s = node.value
        if '.' in s or 'e' in s or 'E' in s:
            return float(s)
        return int(s)

    def visit_TRUE(self, node: Node) -> bool:
        """Parse true."""
        return True

    def visit_FALSE(self, node: Node) -> bool:
        """Parse false."""
        return False

    def visit_NULL(self, node: Node) -> None:
        """Parse null."""
        return None


# ==================== Convenience Functions ====================

def create_json_parser() -> Parser:
    """Create a ready-to-use JSON parser."""
    return Parser(create_json_grammar(), create_json_tokenizer())


def parse_json(text: str) -> Any:
    """
    Parse JSON string to Python object.

    Args:
        text: JSON string

    Returns:
        Python object (dict, list, str, number, bool, or None)
    """
    parser = create_json_parser()
    ast = parser.parse_to_ast(text)
    return JSONEvaluator().visit(ast)


def validate_json(text: str) -> bool:
    """
    Check if text is valid JSON.

    Args:
        text: JSON string

    Returns:
        True if valid JSON
    """
    parser = create_json_parser()
    return parser.parse(text)


# ==================== Demo ====================

if __name__ == "__main__":
    # Demo usage
    json_text = '''
    {
        "name": "John Doe",
        "age": 30,
        "active": true,
        "email": null,
        "scores": [95, 87, 92],
        "address": {
            "city": "New York",
            "zip": "10001"
        }
    }
    '''

    print("=" * 60)
    print("JSON Parser Demo")
    print("=" * 60)

    # Validate
    print(f"\nValid JSON: {validate_json(json_text)}")

    # Parse to Python
    result = parse_json(json_text)
    print(f"\nParsed result:")
    print(f"  Name: {result['name']}")
    print(f"  Age: {result['age']}")
    print(f"  Active: {result['active']}")
    print(f"  Scores: {result['scores']}")
    print(f"  City: {result['address']['city']}")

    # Show constrained decoding
    print("\n" + "=" * 60)
    print("Constrained Decoding Demo")
    print("=" * 60)

    parser = create_json_parser()
    state = parser.initial_state()

    print("\nInitial state - valid tokens:", parser.get_valid_next(state))

    # Simulate feeding tokens
    tokens = parser.tokenizer.tokenize('{"name": ')

    for token in tokens[:-1]:  # Exclude EOF
        state = parser.step(state, token)
        valid = parser.get_valid_next(state)
        print(f"After '{token.value}': valid = {valid}")
