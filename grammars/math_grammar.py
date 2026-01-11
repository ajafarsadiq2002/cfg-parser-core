"""
Math Expression Grammar - Parse and evaluate mathematical expressions.

This demonstrates the CFG Parser Core for expression parsing.

Features:
- Arithmetic operations (+, -, *, /, %)
- Parentheses for grouping
- Operator precedence
- Unary minus
- Variable support
- Function calls (sin, cos, sqrt, etc.)
"""

import sys
import os
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.grammar import Grammar
from core.tokenizer import Tokenizer
from core.parser import Parser
from core.ast import Node
from core.visitor import Evaluator, SymbolTable
from typing import Any, Dict, Callable, Optional


def create_math_grammar() -> Grammar:
    """
    Create the math expression grammar.

    Grammar handles operator precedence:
        expr     -> term (('+' | '-') term)*
        term     -> factor (('*' | '/' | '%') factor)*
        factor   -> unary ('^' unary)*
        unary    -> '-' unary | primary
        primary  -> NUMBER | IDENT | IDENT '(' args ')' | '(' expr ')'
        args     -> expr (',' expr)*

    Note: This is converted to a non-left-recursive form for LL parsing.
    """
    g = Grammar("expr")

    # Define terminals
    g.terminal(
        "NUMBER", "IDENT",
        "+", "-", "*", "/", "%", "^",
        "(", ")", ","
    )

    # Expression (lowest precedence: + -)
    g.add_rule("expr",
        ["term", "expr_rest"]
    )

    g.add_rule("expr_rest",
        ["+", "term", "expr_rest"],
        ["-", "term", "expr_rest"],
        []  # epsilon
    )

    # Term (higher precedence: * / %)
    g.add_rule("term",
        ["factor", "term_rest"]
    )

    g.add_rule("term_rest",
        ["*", "factor", "term_rest"],
        ["/", "factor", "term_rest"],
        ["%", "factor", "term_rest"],
        []  # epsilon
    )

    # Factor (exponentiation ^)
    g.add_rule("factor",
        ["unary", "factor_rest"]
    )

    g.add_rule("factor_rest",
        ["^", "unary", "factor_rest"],
        []  # epsilon
    )

    # Unary (unary minus)
    g.add_rule("unary",
        ["-", "unary"],
        ["primary"]
    )

    # Primary (highest precedence)
    g.add_rule("primary",
        ["NUMBER"],
        ["IDENT", "primary_rest"],
        ["(", "expr", ")"]
    )

    # After IDENT: either function call or just variable
    g.add_rule("primary_rest",
        ["(", "args", ")"],
        []  # epsilon - just a variable
    )

    # Function arguments
    g.add_rule("args",
        ["expr", "args_rest"],
        []  # epsilon for no-arg functions
    )

    g.add_rule("args_rest",
        [",", "expr", "args_rest"],
        []  # epsilon
    )

    return g


def create_math_tokenizer() -> Tokenizer:
    """
    Create the math expression tokenizer.

    Handles:
    - Numbers (integer and floating point)
    - Identifiers (variable and function names)
    - Operators (+, -, *, /, %, ^)
    - Parentheses and commas
    - Whitespace (skipped)
    """
    t = Tokenizer()

    # Skip whitespace
    t.add("WHITESPACE", r"[ \t\n\r]+", skip=True)

    # Operators (order matters for multi-char operators)
    t.add("+", r"\+")
    t.add("-", r"-")
    t.add("*", r"\*")
    t.add("/", r"/")
    t.add("%", r"%")
    t.add("^", r"\^")
    t.add("(", r"\(")
    t.add(")", r"\)")
    t.add(",", r",")

    # Number (integer or floating point)
    t.add("NUMBER", r"\d+\.?\d*")

    # Identifier (variable or function name)
    t.add("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")

    return t


class MathEvaluator(Evaluator):
    """
    Evaluates math expression AST to numeric result.

    Supports:
    - Basic arithmetic (+, -, *, /, %)
    - Exponentiation (^)
    - Variables
    - Built-in functions (sin, cos, sqrt, etc.)

    Usage:
        ast = parser.parse_to_ast("2 + 3 * 4")
        result = MathEvaluator().visit(ast)  # 14

        # With variables
        evaluator = MathEvaluator({"x": 10})
        result = evaluator.visit(ast_with_x)  # Uses x = 10
    """

    def __init__(self, variables: Optional[Dict[str, float]] = None):
        super().__init__()
        self.variables = variables or {}

        # Built-in functions
        self.functions: Dict[str, Callable] = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "abs": abs,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "floor": math.floor,
            "ceil": math.ceil,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
        }

        # Built-in constants
        self.variables["pi"] = math.pi
        self.variables["e"] = math.e

    def visit_expr(self, node: Node) -> float:
        """Evaluate expression: term expr_rest."""
        result = self.visit(node.children[0])  # term

        if len(node.children) > 1:
            result = self._apply_expr_rest(result, node.children[1])

        return result

    def _apply_expr_rest(self, left: float, node: Node) -> float:
        """Apply expr_rest: ('+' | '-') term expr_rest."""
        if not node.children:
            return left

        i = 0
        result = left

        while i < len(node.children):
            child = node.children[i]

            if child.type == "+":
                i += 1
                right = self.visit(node.children[i])
                result = result + right
            elif child.type == "-":
                i += 1
                right = self.visit(node.children[i])
                result = result - right
            elif child.type == "term":
                right = self.visit(child)
                result = result + right  # Implicit addition
            elif child.type == "expr_rest":
                result = self._apply_expr_rest(result, child)

            i += 1

        return result

    def visit_term(self, node: Node) -> float:
        """Evaluate term: factor term_rest."""
        result = self.visit(node.children[0])  # factor

        if len(node.children) > 1:
            result = self._apply_term_rest(result, node.children[1])

        return result

    def _apply_term_rest(self, left: float, node: Node) -> float:
        """Apply term_rest: ('*' | '/' | '%') factor term_rest."""
        if not node.children:
            return left

        i = 0
        result = left

        while i < len(node.children):
            child = node.children[i]

            if child.type == "*":
                i += 1
                right = self.visit(node.children[i])
                result = result * right
            elif child.type == "/":
                i += 1
                right = self.visit(node.children[i])
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                result = result / right
            elif child.type == "%":
                i += 1
                right = self.visit(node.children[i])
                result = result % right
            elif child.type == "factor":
                right = self.visit(child)
                result = result * right  # Implicit multiplication
            elif child.type == "term_rest":
                result = self._apply_term_rest(result, child)

            i += 1

        return result

    def visit_factor(self, node: Node) -> float:
        """Evaluate factor: unary factor_rest."""
        result = self.visit(node.children[0])  # unary

        if len(node.children) > 1:
            result = self._apply_factor_rest(result, node.children[1])

        return result

    def _apply_factor_rest(self, left: float, node: Node) -> float:
        """Apply factor_rest: '^' unary factor_rest (right-associative)."""
        if not node.children:
            return left

        # Collect all operands for right-associative evaluation
        operands = [left]
        current = node

        while current.children:
            i = 0
            while i < len(current.children):
                child = current.children[i]
                if child.type == "^":
                    i += 1
                    operands.append(self.visit(current.children[i]))
                elif child.type == "unary":
                    operands.append(self.visit(child))
                elif child.type == "factor_rest":
                    current = child
                    break
                i += 1
            else:
                break

        # Evaluate right-to-left
        result = operands[-1]
        for i in range(len(operands) - 2, -1, -1):
            result = operands[i] ** result

        return result

    def visit_unary(self, node: Node) -> float:
        """Evaluate unary: '-' unary | primary."""
        if len(node.children) == 2 and node.children[0].type == "-":
            return -self.visit(node.children[1])
        return self.visit(node.children[0])

    def visit_primary(self, node: Node) -> float:
        """Evaluate primary: NUMBER | IDENT | function call | (expr)."""
        first_child = node.children[0]

        if first_child.type == "NUMBER":
            return float(first_child.value)

        if first_child.type == "IDENT":
            name = first_child.value

            # Check for function call
            if len(node.children) > 1:
                primary_rest = node.children[1]
                if primary_rest.children and primary_rest.children[0].type == "(":
                    # Function call
                    args = self._collect_args(primary_rest)
                    return self._call_function(name, args)

            # Variable lookup
            if name in self.variables:
                return self.variables[name]
            raise NameError(f"Undefined variable: {name}")

        if first_child.type == "(":
            # Parenthesized expression
            return self.visit(node.children[1])  # expr

        return self.visit(first_child)

    def _collect_args(self, primary_rest: Node) -> list:
        """Collect function arguments."""
        args = []

        for child in primary_rest.children:
            if child.type == "args":
                self._collect_from_args(child, args)
            elif child.type == "expr":
                args.append(self.visit(child))

        return args

    def _collect_from_args(self, node: Node, args: list):
        """Recursively collect from args node."""
        for child in node.children:
            if child.type == "expr":
                args.append(self.visit(child))
            elif child.type == "args_rest":
                self._collect_from_args(child, args)

    def _call_function(self, name: str, args: list) -> float:
        """Call a built-in function."""
        if name not in self.functions:
            raise NameError(f"Undefined function: {name}")

        func = self.functions[name]
        return func(*args)

    def visit_NUMBER(self, node: Node) -> float:
        """Parse number."""
        return float(node.value)

    def visit_IDENT(self, node: Node) -> float:
        """Look up variable."""
        name = node.value
        if name in self.variables:
            return self.variables[name]
        raise NameError(f"Undefined variable: {name}")


# ==================== Convenience Functions ====================

def create_math_parser() -> Parser:
    """Create a ready-to-use math expression parser."""
    return Parser(create_math_grammar(), create_math_tokenizer())


def evaluate(expression: str, variables: Optional[Dict[str, float]] = None) -> float:
    """
    Evaluate a math expression.

    Args:
        expression: Math expression string
        variables: Optional variable values

    Returns:
        Numeric result
    """
    parser = create_math_parser()
    ast = parser.parse_to_ast(expression)
    return MathEvaluator(variables).visit(ast)


def validate_expression(expression: str) -> bool:
    """
    Check if expression is valid.

    Args:
        expression: Math expression string

    Returns:
        True if valid syntax
    """
    parser = create_math_parser()
    return parser.parse(expression)


# ==================== Demo ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Math Expression Parser Demo")
    print("=" * 60)

    expressions = [
        "2 + 3",
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "2 ^ 3 ^ 2",       # Right-associative: 2^(3^2) = 2^9 = 512
        "-5 + 3",
        "sqrt(16) + 2",
        "sin(pi / 2)",
        "max(1, 2, 3)",
    ]

    print("\nBasic expressions:")
    for expr in expressions:
        try:
            result = evaluate(expr)
            print(f"  {expr} = {result}")
        except Exception as e:
            print(f"  {expr} -> Error: {e}")

    print("\nWith variables:")
    variables = {"x": 10, "y": 5}
    var_expressions = [
        "x + y",
        "x * y",
        "x ^ 2 + y ^ 2",
        "sqrt(x ^ 2 + y ^ 2)",
    ]

    for expr in var_expressions:
        result = evaluate(expr, variables)
        print(f"  {expr} = {result}  (x={variables['x']}, y={variables['y']})")

    # Show constrained decoding
    print("\n" + "=" * 60)
    print("Constrained Decoding Demo")
    print("=" * 60)

    parser = create_math_parser()
    state = parser.initial_state()

    print("\nInitial state - valid tokens:", parser.get_valid_next(state))

    # Simulate feeding tokens
    tokens = parser.tokenizer.tokenize("2 + ")

    for token in tokens[:-1]:  # Exclude EOF
        state = parser.step(state, token)
        valid = parser.get_valid_next(state)
        print(f"After '{token.value}': valid = {valid}")
