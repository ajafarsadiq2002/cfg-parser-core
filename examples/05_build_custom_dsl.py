"""
Example 5: Build Your Own Domain Specific Language (DSL)

Demonstrates how to create custom mini-languages:
- Query DSL (like SQL lite)
- Config file format
- Command language

This shows the true power of the reusable parser core.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import Grammar, Tokenizer, Parser
from core.ast import Node
from core.visitor import Evaluator
from typing import Any, Dict, List


# =========================================================
# Example DSL 1: Simple Query Language
# =========================================================

def create_query_grammar() -> Grammar:
    """
    Query language grammar:
        query  -> SELECT fields FROM table where_clause?
        fields -> IDENT (',' IDENT)*
        where_clause -> WHERE condition
        condition -> IDENT op value
        op -> '=' | '!=' | '>' | '<'
        value -> STRING | NUMBER

    Example: SELECT name, age FROM users WHERE age > 18
    """
    g = Grammar("query")

    g.terminal(
        "SELECT", "FROM", "WHERE",
        "IDENT", "STRING", "NUMBER",
        ",", "=", "!=", ">", "<", ">=", "<="
    )

    g.add_rule("query",
        ["SELECT", "fields", "FROM", "IDENT", "where_clause"],
        ["SELECT", "fields", "FROM", "IDENT"]
    )

    g.add_rule("fields",
        ["IDENT", "more_fields"],
        ["IDENT"]
    )

    g.add_rule("more_fields",
        [",", "IDENT", "more_fields"],
        []
    )

    g.add_rule("where_clause",
        ["WHERE", "condition"]
    )

    g.add_rule("condition",
        ["IDENT", "op", "value"]
    )

    g.add_rule("op",
        ["="], ["!="], [">"], ["<"], [">="], ["<="]
    )

    g.add_rule("value",
        ["STRING"],
        ["NUMBER"]
    )

    return g


def create_query_tokenizer() -> Tokenizer:
    t = Tokenizer()
    t.add("WHITESPACE", r"\s+", skip=True)

    # Keywords (before IDENT)
    t.add("SELECT", r"SELECT|select")
    t.add("FROM", r"FROM|from")
    t.add("WHERE", r"WHERE|where")

    # Operators
    t.add("!=", r"!=")
    t.add(">=", r">=")
    t.add("<=", r"<=")
    t.add("=", r"=")
    t.add(">", r">")
    t.add("<", r"<")
    t.add(",", r",")

    # Literals
    t.add("STRING", r"'[^']*'|\"[^\"]*\"")
    t.add("NUMBER", r"\d+")
    t.add("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")

    return t


class QueryEvaluator(Evaluator):
    """Converts query AST to a query object."""

    def visit_query(self, node: Node) -> Dict:
        result = {
            "type": "SELECT",
            "fields": [],
            "table": None,
            "where": None
        }

        for child in node.children:
            if child.type == "fields":
                result["fields"] = self._collect_fields(child)
            elif child.type == "IDENT":
                result["table"] = child.value
            elif child.type == "where_clause":
                result["where"] = self.visit(child)

        return result

    def _collect_fields(self, node: Node) -> List[str]:
        fields = []
        for child in node.children:
            if child.type == "IDENT":
                fields.append(child.value)
            elif child.type == "more_fields":
                fields.extend(self._collect_fields(child))
        return fields

    def visit_where_clause(self, node: Node) -> Dict:
        for child in node.children:
            if child.type == "condition":
                return self.visit(child)
        return {}

    def visit_condition(self, node: Node) -> Dict:
        field = None
        op = None
        value = None

        for child in node.children:
            if child.type == "IDENT":
                field = child.value
            elif child.type == "op":
                op = self._get_op(child)
            elif child.type == "value":
                value = self.visit(child)

        return {"field": field, "op": op, "value": value}

    def _get_op(self, node: Node) -> str:
        for child in node.children:
            return child.type
        return "="

    def visit_value(self, node: Node) -> Any:
        for child in node.children:
            if child.type == "STRING":
                return child.value.strip("'\"")
            if child.type == "NUMBER":
                return int(child.value)
        return None


# =========================================================
# Example DSL 2: Simple Config Language
# =========================================================

def create_config_grammar() -> Grammar:
    """
    Config language grammar:
        config -> statement*
        statement -> IDENT '=' value ';'
        value -> STRING | NUMBER | BOOL | list
        list -> '[' items ']'
        items -> value (',' value)*

    Example:
        name = "myapp";
        port = 8080;
        debug = true;
        hosts = ["localhost", "127.0.0.1"];
    """
    g = Grammar("config")

    g.terminal("IDENT", "STRING", "NUMBER", "BOOL", "=", ";", "[", "]", ",")

    g.add_rule("config",
        ["statements"]
    )

    g.add_rule("statements",
        ["statement", "statements"],
        []
    )

    g.add_rule("statement",
        ["IDENT", "=", "value", ";"]
    )

    g.add_rule("value",
        ["STRING"],
        ["NUMBER"],
        ["BOOL"],
        ["list"]
    )

    g.add_rule("list",
        ["[", "items", "]"],
        ["[", "]"]
    )

    g.add_rule("items",
        ["value", "more_items"]
    )

    g.add_rule("more_items",
        [",", "value", "more_items"],
        []
    )

    return g


def create_config_tokenizer() -> Tokenizer:
    t = Tokenizer()
    t.add("WHITESPACE", r"\s+", skip=True)
    t.add("COMMENT", r"#[^\n]*", skip=True)

    t.add("BOOL", r"true|false")
    t.add("STRING", r'"[^"]*"')
    t.add("NUMBER", r"\d+\.?\d*")
    t.add("=", r"=")
    t.add(";", r";")
    t.add("[", r"\[")
    t.add("]", r"\]")
    t.add(",", r",")
    t.add("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")

    return t


# =========================================================
# Demo
# =========================================================

def main():
    print("=" * 60)
    print("Example 5: Build Your Own DSL")
    print("=" * 60)

    # Query Language Demo
    print("\n1. Query Language DSL")
    print("-" * 40)

    query_grammar = create_query_grammar()
    query_tokenizer = create_query_tokenizer()
    query_parser = Parser(query_grammar, query_tokenizer)

    queries = [
        "SELECT name FROM users",
        "SELECT name, age FROM users",
        "SELECT name, age, email FROM users WHERE age > 18",
        "SELECT * FROM products WHERE price < 100",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        is_valid = query_parser.parse(query)
        print(f"  Valid: {is_valid}")

        if is_valid and "WHERE" not in query or True:
            try:
                ast = query_parser.parse_to_ast(query)
                result = QueryEvaluator().visit(ast)
                print(f"  Parsed: {result}")
            except Exception as e:
                print(f"  Parse error: {e}")

    # Show constrained decoding for queries
    print("\n" + "-" * 40)
    print("Query Language - Valid Next Tokens:")

    state = query_parser.initial_state()
    print(f"Start: {query_parser.get_valid_next(state)}")

    tokens = query_tokenizer.tokenize("SELECT name FROM")
    for token in tokens[:-1]:
        state = query_parser.step(state, token)
        print(f"After '{token.value}': {query_parser.get_valid_next(state)}")

    # Config Language Demo
    print("\n" + "=" * 60)
    print("2. Config Language DSL")
    print("-" * 40)

    config_grammar = create_config_grammar()
    config_tokenizer = create_config_tokenizer()
    config_parser = Parser(config_grammar, config_tokenizer)

    config_text = '''
        name = "myapp";
        port = 8080;
        debug = true;
    '''

    print(f"Config text:{config_text}")
    is_valid = config_parser.parse(config_text)
    print(f"Valid: {is_valid}")

    # Show the power: you can build any DSL!
    print("\n" + "=" * 60)
    print("3. The Power of Reusable Parser Core")
    print("-" * 40)
    print("""
With the CFG Parser Core, you can create:

1. Query Languages
   - SQL-like queries
   - GraphQL subset
   - Search filters

2. Config Formats
   - Application config
   - Build files
   - Deployment specs

3. Command Languages
   - CLI command parsers
   - Bot commands
   - Macro languages

4. Expression Languages
   - Math expressions
   - Boolean logic
   - Template expressions

5. Data Formats
   - JSON/YAML subsets
   - Custom serialization
   - Protocol messages

All using the same core:
   grammar = Grammar("start")
   grammar.add_rule(...)
   parser = Parser(grammar, tokenizer)
   parser.get_valid_next(state)  # The magic function!
""")


if __name__ == "__main__":
    main()
