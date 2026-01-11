"""
Example 3: Math Expression Parsing and Evaluation

Demonstrates:
- Expression parsing with operator precedence
- Evaluation with variables
- Function calls
- Building a calculator
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grammars.math_grammar import (
    create_math_parser,
    evaluate,
    validate_expression,
    MathEvaluator
)
from core.visualize import Visualizer


def main():
    print("=" * 60)
    print("Example 3: Math Expression Parser")
    print("=" * 60)

    # Basic arithmetic
    print("\n1. Basic Arithmetic")
    print("-" * 40)

    expressions = [
        ("2 + 3", 5),
        ("10 - 4", 6),
        ("3 * 4", 12),
        ("15 / 3", 5),
        ("17 % 5", 2),
    ]

    for expr, expected in expressions:
        result = evaluate(expr)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] {expr} = {result}")

    # Operator precedence
    print("\n2. Operator Precedence")
    print("-" * 40)

    precedence_tests = [
        ("2 + 3 * 4", 14),        # Multiplication first
        ("(2 + 3) * 4", 20),      # Parentheses override
        ("2 ^ 3 ^ 2", 512),       # Right-associative: 2^(3^2) = 2^9
        ("10 - 3 - 2", 5),        # Left-associative
        ("-5 + 10", 5),           # Unary minus
        ("2 * -3", -6),           # Unary in expression
    ]

    for expr, expected in precedence_tests:
        result = evaluate(expr)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] {expr} = {result}")

    # Variables
    print("\n3. Variables")
    print("-" * 40)

    variables = {"x": 10, "y": 5, "radius": 3}

    var_expressions = [
        "x + y",
        "x * y",
        "x ^ 2",
        "pi * radius ^ 2",  # Circle area
    ]

    for expr in var_expressions:
        result = evaluate(expr, variables)
        print(f"{expr} = {result:.4f}")

    # Built-in functions
    print("\n4. Built-in Functions")
    print("-" * 40)

    function_tests = [
        "sqrt(16)",
        "abs(-5)",
        "sin(0)",
        "cos(0)",
        "sin(pi / 2)",
        "max(1, 5, 3)",
        "min(10, 2, 8)",
        "log(e)",
        "pow(2, 10)",
    ]

    for expr in function_tests:
        result = evaluate(expr)
        print(f"{expr} = {result:.4f}")

    # Complex expressions
    print("\n5. Complex Expressions")
    print("-" * 40)

    complex_exprs = [
        "sqrt(3^2 + 4^2)",                    # Pythagorean: 5
        "(-5 + sqrt(25 + 4 * 3)) / (2 * 1)",  # Quadratic formula
        "sin(pi/4) ^ 2 + cos(pi/4) ^ 2",      # Should be 1
    ]

    for expr in complex_exprs:
        result = evaluate(expr)
        print(f"{expr}")
        print(f"  = {result:.6f}")

    # Interactive calculator demo
    print("\n6. Calculator Demo")
    print("-" * 40)
    print("(Simulating interactive input)")

    calc_session = [
        "10 + 20",
        "30 * 2",
        "sqrt(3600)",
    ]

    for expr in calc_session:
        result = evaluate(expr)
        print(f"> {expr}")
        print(f"  {result}")


if __name__ == "__main__":
    main()
