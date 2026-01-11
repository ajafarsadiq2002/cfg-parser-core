"""
Debug & Visualization Tools - See what's happening inside the parser.

This is Component 8 of the CFG Parser Core.

Features:
- Print grammar in various formats
- Visualize AST
- Show parse trace
- Display FIRST/FOLLOW sets
- Export to DOT format for Graphviz
"""

from typing import List, Optional, Set, Dict, Any
from .grammar import Grammar, Rule
from .tokenizer import Token
from .ast import Node
from .sets import GrammarSets
from .parser import ParseState


class Visualizer:
    """
    Debug and visualization utilities.

    Usage:
        viz = Visualizer()
        viz.print_grammar(grammar)
        viz.print_ast(ast)
        viz.print_parse_trace(parser, "1 + 2")
    """

    def __init__(self, use_unicode: bool = None):
        """
        Initialize visualizer.

        Args:
            use_unicode: Use Unicode box-drawing characters (auto-detect if None)
        """
        # Auto-detect Unicode support
        if use_unicode is None:
            import sys
            try:
                # Try to encode a Unicode character
                "├".encode(sys.stdout.encoding or 'utf-8')
                use_unicode = True
            except (UnicodeEncodeError, LookupError):
                use_unicode = False

        self.use_unicode = use_unicode

        if use_unicode:
            self.BRANCH = "├── "
            self.LAST_BRANCH = "└── "
            self.VERTICAL = "│   "
            self.SPACE = "    "
            self.ARROW = "→"
            self.EPSILON = "ε"
        else:
            self.BRANCH = "|-- "
            self.LAST_BRANCH = "`-- "
            self.VERTICAL = "|   "
            self.SPACE = "    "
            self.ARROW = "->"
            self.EPSILON = "(epsilon)"

    # ==================== Grammar Visualization ====================

    def print_grammar(self, grammar: Grammar):
        """Print grammar rules in readable format."""
        print(f"Grammar (start: {grammar.start})")
        print(f"Terminals: {sorted(grammar.terminals - {'EOF', 'EPSILON'})}")
        print("\nProduction Rules:")
        for name, rules in grammar.rules.items():
            for rule in rules:
                symbols = " ".join(rule.symbols) if rule.symbols else self.EPSILON
                label = f"  #{rule.label}" if rule.label else ""
                print(f"  {name} {self.ARROW} {symbols}{label}")
        print()

    def grammar_to_bnf(self, grammar: Grammar) -> str:
        """Convert grammar to BNF notation."""
        lines = []
        for name, rules in grammar.rules.items():
            productions = []
            for rule in rules:
                if rule.symbols:
                    productions.append(" ".join(rule.symbols))
                else:
                    productions.append(self.EPSILON)
            lines.append(f"<{name}> ::= {' | '.join(productions)}")
        return "\n".join(lines)

    def grammar_to_ebnf(self, grammar: Grammar) -> str:
        """Convert grammar to EBNF notation."""
        lines = []
        for name, rules in grammar.rules.items():
            productions = []
            for rule in rules:
                if rule.symbols:
                    productions.append(" ".join(rule.symbols))
                else:
                    productions.append("")
            lines.append(f"{name} = {' | '.join(productions)} ;")
        return "\n".join(lines)

    # ==================== Token Visualization ====================

    def print_tokens(self, tokens: List[Token]):
        """Print token list in table format."""
        print("Tokens:")
        print("-" * 60)
        print(f"{'Type':<15} {'Value':<20} {'Line':<6} {'Col':<6}")
        print("-" * 60)
        for token in tokens:
            value_str = repr(token.value)[:18]
            print(f"{token.type:<15} {value_str:<20} {token.line:<6} {token.column:<6}")
        print("-" * 60)
        print()

    # ==================== AST Visualization ====================

    def print_ast(self, node: Node, indent: int = 0, prefix: str = ""):
        """
        Print AST as tree structure.

        Args:
            node: Root node
            indent: Current indentation level
            prefix: Prefix string for current line
        """
        # Node display
        if node.value is not None:
            node_str = f"{node.type} = {node.value!r}"
        else:
            node_str = node.type

        if node.label:
            node_str += f" #{node.label}"

        print(prefix + node_str)

        # Children
        for i, child in enumerate(node.children):
            is_last = (i == len(node.children) - 1)

            if is_last:
                child_prefix = prefix.replace(self.BRANCH, self.VERTICAL).replace(
                    self.LAST_BRANCH, self.SPACE)
                child_prefix += self.LAST_BRANCH
            else:
                child_prefix = prefix.replace(self.BRANCH, self.VERTICAL).replace(
                    self.LAST_BRANCH, self.SPACE)
                child_prefix += self.BRANCH

            self.print_ast(child, indent + 1, child_prefix)

    def ast_to_dot(self, node: Node, name: str = "ast") -> str:
        """
        Convert AST to DOT format for Graphviz.

        Args:
            node: Root node
            name: Graph name

        Returns:
            DOT format string
        """
        lines = [f"digraph {name} {{"]
        lines.append("  node [shape=box];")

        node_id = [0]

        def add_node(n: Node, parent_id: Optional[int] = None):
            current_id = node_id[0]
            node_id[0] += 1

            # Node label
            if n.value is not None:
                label = f"{n.type}\\n{n.value!r}"
            else:
                label = n.type

            lines.append(f'  n{current_id} [label="{label}"];')

            # Edge from parent
            if parent_id is not None:
                lines.append(f"  n{parent_id} -> n{current_id};")

            # Children
            for child in n.children:
                add_node(child, current_id)

        add_node(node)
        lines.append("}")

        return "\n".join(lines)

    def ast_to_json(self, node: Node, indent: int = 2) -> str:
        """Convert AST to JSON string."""
        return node.to_json(indent)

    # ==================== FIRST/FOLLOW Visualization ====================

    def print_sets(self, grammar: Grammar):
        """Print FIRST and FOLLOW sets."""
        sets = GrammarSets(grammar)

        print("FIRST sets:")
        print("-" * 40)
        for name in grammar.rules:
            first = sorted(sets.first(name))
            print(f"  FIRST({name}) = {{ {', '.join(first)} }}")

        print("\nFOLLOW sets:")
        print("-" * 40)
        for name in grammar.rules:
            follow = sorted(sets.follow(name))
            print(f"  FOLLOW({name}) = {{ {', '.join(follow)} }}")

        print("\nNullable:")
        print("-" * 40)
        for name in grammar.rules:
            nullable = sets.nullable(name)
            print(f"  {name}: {nullable}")
        print()

    def print_parse_table(self, grammar: Grammar):
        """Print LL(1) parse table."""
        sets = GrammarSets(grammar)

        try:
            table = sets.build_parse_table()
        except Exception as e:
            print(f"Cannot build parse table: {e}")
            return

        # Get all terminals (columns)
        terminals = sorted(grammar.terminals - {"EPSILON"})
        nonterminals = list(grammar.rules.keys())

        # Header
        col_width = 20
        header = f"{'':15}"
        for t in terminals:
            header += f"{t:>{col_width}}"
        print(header)
        print("-" * len(header))

        # Rows
        for nt in nonterminals:
            row = f"{nt:15}"
            for t in terminals:
                key = (nt, t)
                if key in table:
                    rule = table[key]
                    symbols = " ".join(rule.symbols) if rule.symbols else self.EPSILON
                    cell = symbols[:col_width-1]
                else:
                    cell = "-"
                row += f"{cell:>{col_width}}"
            print(row)
        print()

    # ==================== Parse Trace ====================

    def print_parse_trace(self, parser: 'Parser', text: str):
        """
        Print step-by-step parse trace.

        Shows stack, input, and action at each step.
        """
        from .parser import Parser

        tokens = parser._ensure_tokens(text)
        state = parser.initial_state()

        print("Parse Trace:")
        print("-" * 70)
        print(f"{'Stack':<30} {'Input':<20} {'Action':<20}")
        print("-" * 70)

        step = 0
        max_steps = 100

        while not state.is_complete() and step < max_steps:
            step += 1

            # Format stack
            stack_str = " ".join(state.stack[:5])
            if len(state.stack) > 5:
                stack_str += "..."

            # Format input
            if state.pos < len(tokens):
                input_str = tokens[state.pos].type
                remaining = [t.type for t in tokens[state.pos:state.pos+3]]
                if len(remaining) > 1:
                    input_str = " ".join(remaining)
            else:
                input_str = "EOF"

            # Determine action
            top = state.top()
            action = ""

            if parser.grammar.is_terminal(top):
                if state.pos < len(tokens) and tokens[state.pos].type == top:
                    action = f"Match {top}"
                else:
                    action = f"Error: expected {top}"
            else:
                action = f"Expand {top}"

            print(f"{stack_str:<30} {input_str:<20} {action:<20}")

            # Advance
            try:
                if state.pos < len(tokens):
                    state = parser.step(state, tokens[state.pos])
                else:
                    break
            except Exception:
                print("  [Parse error]")
                break

        if state.is_complete():
            print("-" * 70)
            print("Parse successful!")
        print()

    # ==================== State Visualization ====================

    def print_state(self, state: ParseState):
        """Print current parse state."""
        print(f"ParseState:")
        print(f"  Position: {state.pos}")
        print(f"  Stack: {' '.join(state.stack)}")
        print(f"  Complete: {state.is_complete()}")
        print()

    def print_valid_next(self, parser: 'Parser', state: ParseState):
        """Print valid next tokens."""
        valid = parser.get_valid_next(state)
        print(f"Valid next tokens: {sorted(valid)}")
        print()


# ==================== Convenience Functions ====================

def print_grammar(grammar: Grammar):
    """Print grammar rules."""
    Visualizer().print_grammar(grammar)


def print_tokens(tokens: List[Token]):
    """Print token list."""
    Visualizer().print_tokens(tokens)


def print_ast(node: Node):
    """Print AST tree."""
    Visualizer().print_ast(node)


def print_sets(grammar: Grammar):
    """Print FIRST/FOLLOW sets."""
    Visualizer().print_sets(grammar)
