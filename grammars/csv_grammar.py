"""
CSV Grammar - Parse CSV (Comma-Separated Values) data.

Features:
- Parse CSV files/strings
- Handle quoted fields (with escaped quotes)
- Handle empty fields
- Convert to list of lists or list of dicts
- Validate CSV structure
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.grammar import Grammar
from core.tokenizer import Tokenizer
from core.parser import Parser
from core.ast import Node
from core.visitor import Visitor
from typing import List, Dict, Any, Optional


def create_csv_grammar() -> Grammar:
    """
    Create the CSV grammar.

    CSV Grammar (LL(1) compatible):
        csv         -> row csv_rest
        csv_rest    -> NEWLINE row csv_rest | NEWLINE | ε
        row         -> field row_rest
        row_rest    -> COMMA field row_rest | ε
        field       -> QUOTED | UNQUOTED | ε
    """
    g = Grammar("csv")

    # Define terminals
    g.terminal("QUOTED", "UNQUOTED", "COMMA", "NEWLINE")

    # csv -> row csv_rest
    g.add_rule("csv", ["row", "csv_rest"])

    # csv_rest -> NEWLINE row csv_rest | NEWLINE | ε
    g.add_rule("csv_rest",
        ["NEWLINE", "row", "csv_rest"],
        ["NEWLINE"],
        []  # epsilon - end of file
    )

    # row -> field row_rest
    g.add_rule("row", ["field", "row_rest"])

    # row_rest -> COMMA field row_rest | ε
    g.add_rule("row_rest",
        ["COMMA", "field", "row_rest"],
        []  # epsilon - end of row
    )

    # field -> QUOTED | UNQUOTED | ε (empty field)
    g.add_rule("field",
        ["QUOTED"],
        ["UNQUOTED"],
        []  # epsilon - empty field
    )

    return g


def create_csv_tokenizer(delimiter: str = ",") -> Tokenizer:
    """
    Create the CSV tokenizer.

    Args:
        delimiter: Field delimiter (default: comma)

    Handles:
    - Quoted fields (double quotes, with escaped quotes as "")
    - Unquoted fields
    - Commas (or custom delimiter)
    - Newlines (CRLF or LF)
    """
    t = Tokenizer()

    # Newlines (CRLF or LF) - must come before other patterns
    t.add("NEWLINE", r"\r?\n")

    # Delimiter (comma by default)
    if delimiter == ",":
        t.add("COMMA", r",")
    else:
        t.add("COMMA", rf"{delimiter}")

    # Quoted field: "..." with "" for escaped quotes
    t.add("QUOTED", r'"(?:[^"]|"")*"')

    # Unquoted field: anything except comma, quote, newline
    t.add("UNQUOTED", rf'[^{delimiter}"\r\n]+')

    return t


class CSVEvaluator(Visitor):
    """
    Evaluates CSV AST to Python data structures.

    Usage:
        ast = parser.parse_to_ast('a,b,c\\n1,2,3')
        rows = CSVEvaluator().visit(ast)
        # rows = [['a', 'b', 'c'], ['1', '2', '3']]
    """

    def visit_csv(self, node: Node) -> List[List[str]]:
        """Convert CSV to list of rows."""
        rows = []

        for child in node.children:
            if child.type == "row":
                row = self.visit(child)
                if row is not None:
                    rows.append(row)
            elif child.type == "csv_rest":
                rest_rows = self._collect_csv_rest(child)
                rows.extend(rest_rows)

        return rows

    def _collect_csv_rest(self, node: Node) -> List[List[str]]:
        """Collect rows from csv_rest node."""
        rows = []

        for child in node.children:
            if child.type == "row":
                row = self.visit(child)
                if row is not None:
                    rows.append(row)
            elif child.type == "csv_rest":
                rows.extend(self._collect_csv_rest(child))

        return rows

    def visit_row(self, node: Node) -> List[str]:
        """Convert row to list of field values."""
        fields = []

        for child in node.children:
            if child.type == "field":
                value = self.visit(child)
                fields.append(value)
            elif child.type == "row_rest":
                rest_fields = self._collect_row_rest(child)
                fields.extend(rest_fields)

        return fields

    def _collect_row_rest(self, node: Node) -> List[str]:
        """Collect fields from row_rest node."""
        fields = []

        for child in node.children:
            if child.type == "field":
                value = self.visit(child)
                fields.append(value)
            elif child.type == "row_rest":
                fields.extend(self._collect_row_rest(child))

        return fields

    def visit_field(self, node: Node) -> str:
        """Get field value."""
        if not node.children:
            return ""  # Empty field

        child = node.children[0]
        if child.type == "QUOTED":
            return self._parse_quoted(child.value)
        elif child.type == "UNQUOTED":
            return child.value.strip()

        return ""

    def _parse_quoted(self, s: str) -> str:
        """Parse quoted field, handling escaped quotes."""
        # Remove surrounding quotes
        s = s[1:-1]
        # Replace escaped quotes ("") with single quote
        s = s.replace('""', '"')
        return s

    def visit_QUOTED(self, node: Node) -> str:
        return self._parse_quoted(node.value)

    def visit_UNQUOTED(self, node: Node) -> str:
        return node.value.strip()


# ==================== Convenience Functions ====================

def create_csv_parser(delimiter: str = ",") -> Parser:
    """Create a ready-to-use CSV parser."""
    return Parser(create_csv_grammar(), create_csv_tokenizer(delimiter))


def parse_csv(text: str, has_header: bool = False,
              delimiter: str = ",") -> List[Any]:
    """
    Parse CSV string to Python data structure.

    Args:
        text: CSV string
        has_header: If True, first row is treated as headers,
                    returns list of dicts. Otherwise returns list of lists.
        delimiter: Field delimiter (default: comma)

    Returns:
        List of lists (no header) or list of dicts (with header)
    """
    parser = create_csv_parser(delimiter)
    ast = parser.parse_to_ast(text)
    rows = CSVEvaluator().visit(ast)

    if not rows:
        return []

    if has_header:
        headers = rows[0]
        data = []
        for row in rows[1:]:
            # Pad row if needed
            while len(row) < len(headers):
                row.append("")
            data.append(dict(zip(headers, row)))
        return data

    return rows


def validate_csv(text: str, delimiter: str = ",") -> bool:
    """
    Check if text is valid CSV.

    Args:
        text: CSV string
        delimiter: Field delimiter

    Returns:
        True if valid CSV
    """
    parser = create_csv_parser(delimiter)
    return parser.parse(text)


def csv_to_dicts(text: str, delimiter: str = ",") -> List[Dict[str, str]]:
    """
    Parse CSV with first row as headers.

    Args:
        text: CSV string (first row = headers)
        delimiter: Field delimiter

    Returns:
        List of dicts
    """
    return parse_csv(text, has_header=True, delimiter=delimiter)


# ==================== Demo ====================

if __name__ == "__main__":
    print("=" * 60)
    print("CSV Parser Demo")
    print("=" * 60)

    # Simple CSV
    csv_text = '''name,age,city
John,30,New York
Jane,25,Los Angeles
Bob,35,"San Francisco"'''

    print("\nInput CSV:")
    print(csv_text)

    # Validate
    print(f"\nValid CSV: {validate_csv(csv_text)}")

    # Parse as list of lists
    rows = parse_csv(csv_text)
    print(f"\nAs list of lists:")
    for row in rows:
        print(f"  {row}")

    # Parse with headers
    data = csv_to_dicts(csv_text)
    print(f"\nAs list of dicts:")
    for item in data:
        print(f"  {item}")

    # Test quoted fields with commas
    csv_with_quotes = '''product,description,price
"Widget","A small, useful item",9.99
"Gadget","He said ""Hello""",19.99'''

    print("\n" + "=" * 60)
    print("CSV with quoted fields:")
    print(csv_with_quotes)

    data = csv_to_dicts(csv_with_quotes)
    print("\nParsed:")
    for item in data:
        print(f"  {item}")

    # Test get_valid_next
    print("\n" + "=" * 60)
    print("get_valid_next() Demo")
    print("=" * 60)

    parser = create_csv_parser()
    state = parser.initial_state()
    print(f"\nInitial - valid next: {parser.get_valid_next(state)}")

    tokens = parser.tokenizer.tokenize("name,")
    for tok in tokens[:-1]:
        state = parser.step(state, tok)
        print(f"After '{tok.value}': valid next = {parser.get_valid_next(state)}")
