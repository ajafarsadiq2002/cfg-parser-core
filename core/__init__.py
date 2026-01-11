r"""
CFG Parser Core - A Reusable Context-Free Grammar Parser

This module provides a complete, reusable parser core that can be used for:
- JSON/YAML/TOML parsing
- LLM constrained decoding
- Domain Specific Languages (DSL)
- Expression evaluation
- Linting and validation
- Autocomplete systems
- And more...

Usage:
    from core import Grammar, Tokenizer, Parser

    # Define grammar
    g = Grammar("expr")
    g.terminal("NUMBER", "+", "-")
    g.add_rule("expr", ["term"], ["expr", "+", "term"])

    # Define tokenizer
    t = Tokenizer()
    t.add("NUMBER", r"\d+")
    t.add("+", r"\+")

    # Parse
    parser = Parser(g, t)
    result = parser.parse("1 + 2")
"""

from .tokenizer import Token, Tokenizer
from .grammar import Grammar, Rule
from .sets import GrammarSets
from .errors import ParseError, LexerError, GrammarError
from .ast import Node, ASTBuilder
from .parser import Parser, ParseState
from .visitor import Visitor, Transformer, Evaluator
from .visualize import Visualizer

__version__ = "1.0.0"
__all__ = [
    "Token", "Tokenizer",
    "Grammar", "Rule",
    "GrammarSets",
    "ParseError", "LexerError", "GrammarError",
    "Node", "ASTBuilder",
    "Parser", "ParseState",
    "Visitor", "Transformer", "Evaluator",
    "Visualizer"
]
