"""
Grammar System - Define context-free grammars.

This is Component 2 of the CFG Parser Core.

Features:
- Define production rules
- Mark terminals vs non-terminals
- Support alternation (|)
- Support optional (?), zero-or-more (*), one-or-more (+)
- Validate grammar consistency
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Union, Tuple
from enum import Enum


class SymbolType(Enum):
    """Type of grammar symbol."""
    TERMINAL = "terminal"
    NONTERMINAL = "nonterminal"
    EPSILON = "epsilon"  # Empty production


@dataclass
class Rule:
    """
    A single production rule.

    Represents: name -> symbols

    Attributes:
        name: The non-terminal being defined
        symbols: List of symbols in the production
        label: Optional label for this alternative (for AST)
    """
    name: str
    symbols: List[str]
    label: Optional[str] = None

    def __repr__(self):
        symbols_str = " ".join(self.symbols) if self.symbols else "ε"
        label_str = f" #{self.label}" if self.label else ""
        return f"{self.name} -> {symbols_str}{label_str}"

    def __len__(self):
        return len(self.symbols)

    def is_epsilon(self) -> bool:
        """Check if this is an epsilon (empty) production."""
        return len(self.symbols) == 0


@dataclass
class Symbol:
    """
    Represents a grammar symbol with optional modifiers.

    Modifiers:
        ? - Optional (zero or one)
        * - Zero or more
        + - One or more
    """
    name: str
    optional: bool = False      # ?
    zero_or_more: bool = False  # *
    one_or_more: bool = False   # +

    @classmethod
    def parse(cls, text: str) -> 'Symbol':
        """Parse a symbol string like 'expr?' or 'stmt*'.

        Note: Single-character symbols like '+', '*', '?' are treated
        as literal terminals, not modifiers.
        """
        # Only interpret as modifier if there's a name before the modifier
        # Single char symbols like '+', '*', '?' should be literal terminals
        if len(text) > 1:
            if text.endswith('?'):
                return cls(text[:-1], optional=True)
            elif text.endswith('*'):
                return cls(text[:-1], zero_or_more=True)
            elif text.endswith('+'):
                return cls(text[:-1], one_or_more=True)
        return cls(text)

    def __repr__(self):
        mod = ''
        if self.optional:
            mod = '?'
        elif self.zero_or_more:
            mod = '*'
        elif self.one_or_more:
            mod = '+'
        return f"{self.name}{mod}"


class Grammar:
    """
    Context-Free Grammar definition.

    A grammar consists of:
    - A start symbol
    - Terminal symbols (tokens)
    - Non-terminal symbols (rules)
    - Production rules

    Usage:
        g = Grammar("expr")
        g.terminal("NUMBER", "+", "-", "*", "/")
        g.add_rule("expr", ["term"], ["expr", "+", "term"])
        g.add_rule("term", ["NUMBER"], ["(", "expr", ")"])
    """

    def __init__(self, start_symbol: str):
        """
        Create a new grammar.

        Args:
            start_symbol: The start symbol (entry point) for parsing
        """
        self.start: str = start_symbol
        self.rules: Dict[str, List[Rule]] = {}
        self.terminals: Set[str] = set()
        self._nonterminals: Set[str] = set()

        # Add special symbols
        self.terminals.add("EOF")
        self.terminals.add("EPSILON")

    def terminal(self, *names: str) -> 'Grammar':
        """
        Mark symbols as terminals.

        Args:
            *names: Terminal symbol names

        Returns:
            self (for chaining)
        """
        for name in names:
            self.terminals.add(name)
        return self

    def add_rule(self, name: str, *productions: List[str],
                 labels: Optional[List[str]] = None) -> 'Grammar':
        """
        Add production rules for a non-terminal.

        Args:
            name: The non-terminal being defined
            *productions: One or more productions (alternatives)
            labels: Optional labels for each alternative

        Returns:
            self (for chaining)

        Example:
            g.add_rule("value",
                ["object"],       # value -> object
                ["array"],        # value -> array
                ["STRING"]        # value -> STRING
            )
        """
        if name not in self.rules:
            self.rules[name] = []
            self._nonterminals.add(name)

        labels = labels or [None] * len(productions)

        for i, prod in enumerate(productions):
            # Handle empty production
            if prod is None or (isinstance(prod, list) and len(prod) == 0):
                prod = []

            # Normalize to list
            if isinstance(prod, str):
                prod = [prod]

            label = labels[i] if i < len(labels) else None
            self.rules[name].append(Rule(name, list(prod), label))

            # Track non-terminals referenced
            for symbol in prod:
                base = Symbol.parse(symbol).name
                if base not in self.terminals:
                    self._nonterminals.add(base)

        return self

    def rule(self, name: str, production: List[str],
             label: Optional[str] = None) -> 'Grammar':
        """
        Add a single production rule.

        Alternative to add_rule for adding one production at a time.
        """
        return self.add_rule(name, production, labels=[label] if label else None)

    def is_terminal(self, symbol: str) -> bool:
        """Check if a symbol is a terminal."""
        base = Symbol.parse(symbol).name
        return base in self.terminals

    def is_nonterminal(self, symbol: str) -> bool:
        """Check if a symbol is a non-terminal."""
        base = Symbol.parse(symbol).name
        return base in self.rules

    def get_rules(self, name: str) -> List[Rule]:
        """Get all production rules for a non-terminal."""
        return self.rules.get(name, [])

    def get_all_symbols(self) -> Set[str]:
        """Get all symbols (terminals + non-terminals)."""
        return self.terminals | set(self.rules.keys())

    def validate(self) -> List[str]:
        """
        Validate the grammar for consistency.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check start symbol is defined
        if self.start not in self.rules:
            errors.append(f"Start symbol '{self.start}' has no production rules")

        # Check all referenced non-terminals are defined
        for name, rules in self.rules.items():
            for rule in rules:
                for symbol in rule.symbols:
                    base = Symbol.parse(symbol).name
                    if not self.is_terminal(base) and base not in self.rules:
                        errors.append(
                            f"Symbol '{base}' in rule '{name}' is not defined"
                        )

        # Check for left recursion (warning, not error)
        for name in self.rules:
            for rule in self.rules[name]:
                if rule.symbols and rule.symbols[0] == name:
                    errors.append(
                        f"Warning: Left recursion in rule '{name}'"
                    )

        return errors

    def expand_modifiers(self) -> 'Grammar':
        """
        Expand ?, *, + modifiers into explicit rules.

        This creates new rules to handle optional/repeated symbols.

        Returns:
            A new grammar with modifiers expanded
        """
        new_grammar = Grammar(self.start)
        new_grammar.terminals = self.terminals.copy()

        for name, rules in self.rules.items():
            for rule in rules:
                new_symbols = []
                for sym_str in rule.symbols:
                    sym = Symbol.parse(sym_str)

                    if sym.optional:
                        # Create: sym? -> sym | ε
                        opt_name = f"{sym.name}_opt"
                        if opt_name not in new_grammar.rules:
                            new_grammar.add_rule(opt_name, [sym.name], [])
                        new_symbols.append(opt_name)

                    elif sym.zero_or_more:
                        # Create: sym* -> sym sym* | ε
                        rep_name = f"{sym.name}_star"
                        if rep_name not in new_grammar.rules:
                            new_grammar.add_rule(rep_name,
                                [sym.name, rep_name],
                                []
                            )
                        new_symbols.append(rep_name)

                    elif sym.one_or_more:
                        # Create: sym+ -> sym sym*
                        rep_name = f"{sym.name}_plus"
                        star_name = f"{sym.name}_star"
                        if rep_name not in new_grammar.rules:
                            if star_name not in new_grammar.rules:
                                new_grammar.add_rule(star_name,
                                    [sym.name, star_name],
                                    []
                                )
                            new_grammar.add_rule(rep_name, [sym.name, star_name])
                        new_symbols.append(rep_name)

                    else:
                        new_symbols.append(sym.name)

                new_grammar.rule(name, new_symbols, rule.label)

        return new_grammar

    def __repr__(self):
        lines = [f"Grammar(start={self.start!r})"]
        lines.append(f"  Terminals: {sorted(self.terminals)}")
        lines.append("  Rules:")
        for name, rules in self.rules.items():
            for rule in rules:
                lines.append(f"    {rule}")
        return "\n".join(lines)

    def to_bnf(self) -> str:
        """Convert grammar to BNF notation string."""
        lines = []
        for name, rules in self.rules.items():
            productions = []
            for rule in rules:
                if rule.symbols:
                    productions.append(" ".join(rule.symbols))
                else:
                    productions.append("ε")
            lines.append(f"<{name}> ::= {' | '.join(productions)}")
        return "\n".join(lines)


# Convenience functions for building grammars

def grammar(start: str) -> Grammar:
    """Create a new grammar with the given start symbol."""
    return Grammar(start)


def load_bnf(bnf_string: str) -> Grammar:
    """
    Parse a BNF grammar string into a Grammar object.

    Format:
        <name> ::= production1 | production2
        <other> ::= term1 term2

    Terminals are UPPERCASE, non-terminals are <bracketed> or lowercase.
    """
    import re

    lines = [l.strip() for l in bnf_string.strip().split('\n') if l.strip()]

    g = None

    for line in lines:
        # Skip comments
        if line.startswith('#') or line.startswith('//'):
            continue

        # Parse rule
        match = re.match(r'<(\w+)>\s*::=\s*(.+)', line)
        if match:
            name = match.group(1)
            productions_str = match.group(2)

            if g is None:
                g = Grammar(name)

            # Split alternatives
            alternatives = [p.strip() for p in productions_str.split('|')]

            for alt in alternatives:
                if alt == 'ε' or alt == 'epsilon' or alt == '':
                    g.rule(name, [])
                else:
                    # Parse symbols
                    symbols = []
                    for sym in alt.split():
                        # Remove < > brackets if present
                        sym = re.sub(r'^<(\w+)>$', r'\1', sym)
                        symbols.append(sym)

                        # Auto-detect terminals (UPPERCASE)
                        if sym.isupper() and sym not in ['EPSILON']:
                            g.terminal(sym)

                    g.rule(name, symbols)

    if g is None:
        from .errors import GrammarError
        raise GrammarError("No valid rules found in BNF string")

    return g
