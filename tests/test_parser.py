"""
Tests for CFG Parser Core

Run with: python -m pytest tests/test_parser.py -v
Or simply: python tests/test_parser.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from core import Grammar, Tokenizer, Parser, Node
from core.sets import GrammarSets
from core.errors import ParseError, LexerError
from grammars.json_grammar import create_json_grammar, create_json_tokenizer, parse_json
from grammars.math_grammar import create_math_grammar, create_math_tokenizer, evaluate


class TestTokenizer(unittest.TestCase):
    """Test the tokenizer component."""

    def test_basic_tokenization(self):
        t = Tokenizer()
        t.add("NUMBER", r"\d+")
        t.add("PLUS", r"\+")
        t.add("WS", r"\s+", skip=True)

        tokens = t.tokenize("1 + 2")

        self.assertEqual(len(tokens), 4)  # 3 tokens + EOF
        self.assertEqual(tokens[0].type, "NUMBER")
        self.assertEqual(tokens[0].value, "1")
        self.assertEqual(tokens[1].type, "PLUS")
        self.assertEqual(tokens[2].type, "NUMBER")
        self.assertEqual(tokens[2].value, "2")
        self.assertEqual(tokens[3].type, "EOF")

    def test_skip_whitespace(self):
        t = Tokenizer()
        t.add("WORD", r"\w+")
        t.add("WS", r"\s+", skip=True)

        tokens = t.tokenize("hello   world")

        self.assertEqual(len(tokens), 3)  # 2 words + EOF
        self.assertEqual(tokens[0].value, "hello")
        self.assertEqual(tokens[1].value, "world")

    def test_line_tracking(self):
        t = Tokenizer()
        t.add("WORD", r"\w+")
        t.add("NL", r"\n", skip=True)
        t.add("WS", r"[ \t]+", skip=True)

        tokens = t.tokenize("line1\nline2\nline3")

        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[1].line, 2)
        self.assertEqual(tokens[2].line, 3)

    def test_lexer_error(self):
        t = Tokenizer()
        t.add("NUMBER", r"\d+")

        with self.assertRaises(LexerError):
            t.tokenize("123abc")


class TestGrammar(unittest.TestCase):
    """Test the grammar component."""

    def test_basic_grammar(self):
        g = Grammar("expr")
        g.terminal("NUMBER", "+")
        g.add_rule("expr", ["NUMBER"], ["expr", "+", "NUMBER"])

        self.assertEqual(g.start, "expr")
        self.assertIn("NUMBER", g.terminals)
        self.assertIn("+", g.terminals)
        self.assertTrue(g.is_terminal("NUMBER"))
        self.assertTrue(g.is_nonterminal("expr"))

    def test_multiple_productions(self):
        g = Grammar("value")
        g.terminal("NUMBER", "STRING")
        g.add_rule("value",
            ["NUMBER"],
            ["STRING"]
        )

        rules = g.get_rules("value")
        self.assertEqual(len(rules), 2)

    def test_grammar_validation(self):
        g = Grammar("start")
        g.terminal("A")
        g.add_rule("start", ["undefined_symbol"])

        errors = g.validate()
        self.assertTrue(len(errors) > 0)


class TestGrammarSets(unittest.TestCase):
    """Test FIRST and FOLLOW set computation."""

    def test_first_set_terminal(self):
        g = Grammar("expr")
        g.terminal("NUMBER")
        g.add_rule("expr", ["NUMBER"])

        sets = GrammarSets(g)
        first = sets.first("expr")

        self.assertIn("NUMBER", first)

    def test_first_set_multiple(self):
        g = Grammar("value")
        g.terminal("NUMBER", "STRING", "BOOL")
        g.add_rule("value",
            ["NUMBER"],
            ["STRING"],
            ["BOOL"]
        )

        sets = GrammarSets(g)
        first = sets.first("value")

        self.assertIn("NUMBER", first)
        self.assertIn("STRING", first)
        self.assertIn("BOOL", first)

    def test_nullable(self):
        g = Grammar("opt")
        g.terminal("A")
        g.add_rule("opt", ["A"], [])  # opt -> A | ε

        sets = GrammarSets(g)

        self.assertTrue(sets.nullable("opt"))

    def test_follow_set(self):
        g = Grammar("expr")
        g.terminal("NUMBER", "+")
        g.add_rule("expr", ["NUMBER", "rest"])
        g.add_rule("rest", ["+", "NUMBER"], [])

        sets = GrammarSets(g)
        follow = sets.follow("rest")

        self.assertIn("EOF", follow)


class TestParser(unittest.TestCase):
    """Test the parser component."""

    def test_simple_parse(self):
        g = Grammar("greeting")
        g.terminal("HELLO")
        g.add_rule("greeting", ["HELLO"])

        t = Tokenizer()
        t.add("HELLO", r"hello")
        t.add("WS", r"\s+", skip=True)

        p = Parser(g, t)

        self.assertTrue(p.parse("hello"))

    def test_parse_sequence(self):
        g = Grammar("greeting")
        g.terminal("HELLO", "WORLD")
        g.add_rule("greeting", ["HELLO", "WORLD"])

        t = Tokenizer()
        t.add("HELLO", r"hello")
        t.add("WORLD", r"world")
        t.add("WS", r"\s+", skip=True)

        p = Parser(g, t)

        self.assertTrue(p.parse("hello world"))
        self.assertFalse(p.parse("hello"))
        self.assertFalse(p.parse("world"))

    def test_parse_alternatives(self):
        g = Grammar("value")
        g.terminal("NUMBER", "STRING")
        g.add_rule("value", ["NUMBER"], ["STRING"])

        t = Tokenizer()
        t.add("NUMBER", r"\d+")
        t.add("STRING", r'"[^"]*"')
        t.add("WS", r"\s+", skip=True)

        p = Parser(g, t)

        self.assertTrue(p.parse("42"))
        self.assertTrue(p.parse('"hello"'))
        self.assertFalse(p.parse("hello"))

    def test_get_valid_next(self):
        g = Grammar("expr")
        g.terminal("NUMBER", "+")
        g.add_rule("expr", ["NUMBER"], ["NUMBER", "+", "NUMBER"])

        t = Tokenizer()
        t.add("NUMBER", r"\d+")
        t.add("+", r"\+")
        t.add("WS", r"\s+", skip=True)

        p = Parser(g, t)

        state = p.initial_state()
        valid = p.get_valid_next(state)

        self.assertIn("NUMBER", valid)


class TestJSONParser(unittest.TestCase):
    """Test the JSON grammar implementation."""

    def test_parse_primitives(self):
        self.assertEqual(parse_json("42"), 42)
        self.assertEqual(parse_json('"hello"'), "hello")
        self.assertEqual(parse_json("true"), True)
        self.assertEqual(parse_json("false"), False)
        self.assertEqual(parse_json("null"), None)

    def test_parse_array(self):
        result = parse_json("[1, 2, 3]")
        self.assertEqual(result, [1, 2, 3])

    def test_parse_object(self):
        result = parse_json('{"name": "John", "age": 30}')
        self.assertEqual(result["name"], "John")
        self.assertEqual(result["age"], 30)

    def test_parse_nested(self):
        result = parse_json('{"user": {"name": "Alice"}, "scores": [1, 2]}')
        self.assertEqual(result["user"]["name"], "Alice")
        self.assertEqual(result["scores"], [1, 2])

    def test_constrained_decoding(self):
        parser = Parser(create_json_grammar(), create_json_tokenizer())

        state = parser.initial_state()
        valid = parser.get_valid_next(state)

        # At start of JSON, valid tokens are value starters
        self.assertIn("{", valid)
        self.assertIn("[", valid)
        self.assertIn("STRING", valid)
        self.assertIn("NUMBER", valid)


class TestMathParser(unittest.TestCase):
    """Test the math expression grammar."""

    def test_basic_arithmetic(self):
        self.assertEqual(evaluate("2 + 3"), 5)
        self.assertEqual(evaluate("10 - 4"), 6)
        self.assertEqual(evaluate("3 * 4"), 12)
        self.assertEqual(evaluate("15 / 3"), 5)

    def test_operator_precedence(self):
        self.assertEqual(evaluate("2 + 3 * 4"), 14)
        self.assertEqual(evaluate("(2 + 3) * 4"), 20)

    def test_unary_minus(self):
        self.assertEqual(evaluate("-5"), -5)
        self.assertEqual(evaluate("-5 + 10"), 5)

    def test_exponentiation(self):
        self.assertEqual(evaluate("2 ^ 3"), 8)
        self.assertEqual(evaluate("2 ^ 3 ^ 2"), 512)  # Right-associative

    def test_functions(self):
        self.assertAlmostEqual(evaluate("sqrt(16)"), 4)
        self.assertEqual(evaluate("abs(-5)"), 5)
        self.assertAlmostEqual(evaluate("sin(0)"), 0)

    def test_variables(self):
        result = evaluate("x + y", {"x": 10, "y": 5})
        self.assertEqual(result, 15)


class TestAST(unittest.TestCase):
    """Test AST construction and traversal."""

    def test_ast_construction(self):
        g = Grammar("expr")
        g.terminal("NUMBER")
        g.add_rule("expr", ["NUMBER"])

        t = Tokenizer()
        t.add("NUMBER", r"\d+")

        p = Parser(g, t)
        ast = p.parse_to_ast("42")

        self.assertIsInstance(ast, Node)

    def test_ast_to_dict(self):
        node = Node("test", value="hello")
        d = node.to_dict()

        self.assertEqual(d["type"], "test")
        self.assertEqual(d["value"], "hello")


# Run tests
if __name__ == "__main__":
    unittest.main(verbosity=2)
