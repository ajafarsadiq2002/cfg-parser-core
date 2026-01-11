"""
Example 2: JSON Parsing

Demonstrates parsing JSON:
- Parsing JSON strings
- Building AST
- Evaluating to Python objects
- Error handling
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grammars.json_grammar import (
    create_json_parser,
    parse_json,
    validate_json,
    JSONEvaluator
)
from core.visualize import Visualizer


def main():
    print("=" * 60)
    print("Example 2: JSON Parsing")
    print("=" * 60)

    # Simple JSON examples
    print("\n1. Basic JSON Parsing")
    print("-" * 40)

    examples = [
        '42',
        '"hello"',
        'true',
        'null',
        '[1, 2, 3]',
        '{"name": "John"}',
    ]

    for json_str in examples:
        result = parse_json(json_str)
        print(f"{json_str:<25} -> {result!r}")

    # Complex JSON
    print("\n2. Complex JSON")
    print("-" * 40)

    complex_json = '''
    {
        "user": {
            "name": "Alice",
            "age": 30,
            "active": true
        },
        "scores": [95, 87, 92],
        "metadata": null
    }
    '''

    result = parse_json(complex_json)
    print(f"Parsed object:")
    print(f"  User name: {result['user']['name']}")
    print(f"  User age: {result['user']['age']}")
    print(f"  Scores: {result['scores']}")
    print(f"  Total score: {sum(result['scores'])}")

    # AST Visualization
    print("\n3. AST Visualization")
    print("-" * 40)

    parser = create_json_parser()
    ast = parser.parse_to_ast('{"a": 1, "b": [2, 3]}')

    viz = Visualizer()
    viz.print_ast(ast)

    # Validation
    print("\n4. Validation")
    print("-" * 40)

    test_cases = [
        ('{"valid": true}', True),
        ('{"missing": }', False),
        ('[1, 2, ]', False),  # Trailing comma
        ('{"key": "value",}', False),  # Trailing comma
    ]

    for json_str, expected in test_cases:
        is_valid = validate_json(json_str)
        status = "PASS" if is_valid == expected else "FAIL"
        print(f"[{status}] '{json_str[:30]}...' -> {is_valid}")

    # Constrained decoding simulation
    print("\n5. Constrained Decoding (LLM Use Case)")
    print("-" * 40)

    parser = create_json_parser()
    state = parser.initial_state()

    print("Simulating LLM token-by-token generation:")
    print(f"Start -> Valid: {parser.get_valid_next(state)}")

    # Simulate generating: {"name": "John"}
    tokens_to_generate = ['{"', 'name', '":', '"John', '"}']
    partial = ""

    tokens = parser.tokenizer.tokenize('{"name": "John"}')
    for token in tokens[:-1]:  # Skip EOF
        partial += token.value
        state = parser.step(state, token)
        valid_next = parser.get_valid_next(state)
        print(f"After '{partial}' -> Valid next: {valid_next}")


if __name__ == "__main__":
    main()
