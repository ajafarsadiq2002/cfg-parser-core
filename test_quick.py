"""
Quick Test Script for CFG Parser Core
Run: python test_quick.py
"""

import sys
sys.path.insert(0, '.')

def test_json():
    """Test JSON parsing."""
    from grammars.json_grammar import parse_json, validate_json

    print("[JSON] Testing...")

    # Parse
    result = parse_json('{"name": "John", "scores": [1, 2, 3]}')
    assert result == {"name": "John", "scores": [1, 2, 3]}, "JSON parse failed"

    # Validate
    assert validate_json('{"valid": true}') == True
    assert validate_json('{"invalid": }') == False

    print("[JSON] PASSED")

def test_math():
    """Test math expressions."""
    from grammars.math_grammar import evaluate

    print("[MATH] Testing...")

    assert evaluate("2 + 3") == 5.0
    assert evaluate("2 + 3 * 4") == 14.0
    assert evaluate("(2 + 3) * 4") == 20.0
    assert evaluate("2 ^ 3") == 8.0
    assert evaluate("sqrt(16)") == 4.0
    assert evaluate("x + y", {"x": 10, "y": 5}) == 15.0

    print("[MATH] PASSED")

def test_get_valid_next():
    """Test the key get_valid_next() function."""
    from grammars.json_grammar import create_json_parser

    print("[get_valid_next] Testing...")

    parser = create_json_parser()
    state = parser.initial_state()

    # At start, should accept value starters
    valid = parser.get_valid_next(state)
    assert '{' in valid
    assert '[' in valid
    assert 'STRING' in valid
    assert 'NUMBER' in valid

    # After '{', should accept STRING or '}'
    token = parser.tokenizer.tokenize('{')[0]
    state = parser.step(state, token)
    valid = parser.get_valid_next(state)
    assert 'STRING' in valid
    assert '}' in valid
    assert '[' not in valid  # Can't start array inside object key position

    print("[get_valid_next] PASSED")

def test_custom_grammar():
    """Test creating custom grammar."""
    from core import Grammar, Tokenizer, Parser

    print("[CUSTOM] Testing...")

    # Simple command grammar: ACTION TARGET
    g = Grammar("command")
    g.terminal("ACTION", "TARGET")
    g.add_rule("command", ["ACTION", "TARGET"])

    t = Tokenizer()
    t.add("ACTION", r"(get|set|delete)")
    t.add("TARGET", r"[a-z]+")
    t.add("WS", r"\s+", skip=True)

    p = Parser(g, t)

    assert p.parse("get user") == True
    assert p.parse("set config") == True
    assert p.parse("delete item") == True
    assert p.parse("invalid") == False

    print("[CUSTOM] PASSED")

def main():
    print("=" * 50)
    print("CFG PARSER CORE - QUICK TEST")
    print("=" * 50)
    print()

    tests = [
        test_json,
        test_math,
        test_get_valid_next,
        test_custom_grammar,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAILED] {test.__name__}: {e}")
            failed += 1

    print()
    print("=" * 50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
