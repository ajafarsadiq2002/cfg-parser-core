"""
FIRST/FOLLOW Sets - Compute predictive parsing sets.

This is Component 7 of the CFG Parser Core.

These sets are the KEY to everything:
- FIRST(X) = All terminals that can begin strings derived from X
- FOLLOW(X) = All terminals that can appear after X in some derivation

Features:
- Compute FIRST sets for all symbols
- Compute FOLLOW sets for all non-terminals
- Compute FIRST of symbol sequences
- Check if symbol is nullable
- Build LL(1) parse table
"""

from typing import Set, Dict, List, Optional, Tuple
from .grammar import Grammar, Rule, Symbol


class GrammarSets:
    """
    Computes and caches FIRST and FOLLOW sets for a grammar.

    The FIRST set tells us what terminals can start a derivation.
    The FOLLOW set tells us what terminals can come after a non-terminal.

    These are essential for:
    - Predictive parsing (LL parsers)
    - get_valid_next() - knowing what tokens are valid next
    - Error recovery - knowing what was expected
    - LLM constrained decoding

    Usage:
        grammar = Grammar("expr")
        # ... define grammar ...
        sets = GrammarSets(grammar)

        first_of_expr = sets.first("expr")
        follow_of_term = sets.follow("term")
        valid_next = sets.first_of_sequence(["expr", "+", "term"])
    """

    # Special symbols
    EPSILON = "EPSILON"  # Empty string
    EOF = "EOF"          # End of input

    def __init__(self, grammar: Grammar):
        """
        Initialize and compute all sets for the grammar.

        Args:
            grammar: The grammar to analyze
        """
        self.grammar = grammar

        # Caches
        self._first: Dict[str, Set[str]] = {}
        self._follow: Dict[str, Set[str]] = {}
        self._nullable: Dict[str, bool] = {}

        # Compute all sets
        self._compute_nullable()
        self._compute_first()
        self._compute_follow()

    def nullable(self, symbol: str) -> bool:
        """
        Check if a symbol can derive the empty string.

        Args:
            symbol: Terminal or non-terminal

        Returns:
            True if symbol can derive ε
        """
        base = Symbol.parse(symbol).name
        return self._nullable.get(base, False)

    def first(self, symbol: str) -> Set[str]:
        """
        Get the FIRST set of a symbol.

        FIRST(X) = Set of terminals that can begin strings derived from X

        Args:
            symbol: Terminal or non-terminal

        Returns:
            Set of terminal symbols
        """
        parsed = Symbol.parse(symbol)
        base = parsed.name

        # Handle modifiers
        if parsed.optional or parsed.zero_or_more:
            result = self._first.get(base, set()).copy()
            result.add(self.EPSILON)
            return result

        return self._first.get(base, set()).copy()

    def follow(self, symbol: str) -> Set[str]:
        """
        Get the FOLLOW set of a non-terminal.

        FOLLOW(X) = Set of terminals that can appear immediately after X

        Args:
            symbol: Non-terminal symbol

        Returns:
            Set of terminal symbols
        """
        base = Symbol.parse(symbol).name
        return self._follow.get(base, set()).copy()

    def first_of_sequence(self, symbols: List[str]) -> Set[str]:
        """
        Compute FIRST set of a sequence of symbols.

        This is crucial for determining what can come next given
        a sequence of symbols still to be matched.

        Args:
            symbols: List of grammar symbols

        Returns:
            Set of terminals that can start this sequence
        """
        if not symbols:
            return {self.EPSILON}

        result: Set[str] = set()

        for sym in symbols:
            first_of_sym = self.first(sym)

            # Add everything except EPSILON
            result |= (first_of_sym - {self.EPSILON})

            # If this symbol can't be empty, stop here
            if self.EPSILON not in first_of_sym:
                break
        else:
            # All symbols are nullable
            result.add(self.EPSILON)

        return result

    def get_valid_next(self, stack: List[str]) -> Set[str]:
        """
        THE KEY FUNCTION - What terminals can come next?

        Given the current parse stack, compute all valid next tokens.

        Used for:
        - Predictive parsing
        - LLM token constraining
        - Autocomplete suggestions
        - Error messages ("expected X or Y")

        Args:
            stack: Current parse stack (top of stack is first)

        Returns:
            Set of valid terminal symbols
        """
        if not stack:
            return {self.EOF}

        top = stack[0]
        rest = stack[1:]

        # Terminal: only that terminal is valid
        if self.grammar.is_terminal(top):
            base = Symbol.parse(top).name
            return {base}

        # Non-terminal: return FIRST set
        result = self.first(top)

        # If top is nullable, also include FIRST of rest
        if self.EPSILON in result:
            result = result - {self.EPSILON}
            result |= self.first_of_sequence(rest)

        return result

    def _compute_nullable(self):
        """Compute which symbols can derive epsilon."""
        # Terminals are not nullable (except EPSILON itself)
        for t in self.grammar.terminals:
            self._nullable[t] = (t == self.EPSILON)

        # Initialize non-terminals as not nullable
        for name in self.grammar.rules:
            self._nullable[name] = False

        # Iterate until no changes
        changed = True
        while changed:
            changed = False
            for name, rules in self.grammar.rules.items():
                if self._nullable[name]:
                    continue

                for rule in rules:
                    # Empty production = nullable
                    if rule.is_epsilon():
                        self._nullable[name] = True
                        changed = True
                        break

                    # All symbols nullable = rule is nullable
                    if all(self._nullable.get(Symbol.parse(s).name, False)
                           for s in rule.symbols):
                        self._nullable[name] = True
                        changed = True
                        break

    def _compute_first(self):
        """Compute FIRST sets for all symbols."""
        # FIRST of terminal is itself
        for t in self.grammar.terminals:
            self._first[t] = {t}

        # Initialize FIRST of non-terminals
        for name in self.grammar.rules:
            self._first[name] = set()

        # Iterate until no changes
        changed = True
        while changed:
            changed = False
            for name, rules in self.grammar.rules.items():
                for rule in rules:
                    # Empty production adds EPSILON
                    if rule.is_epsilon():
                        if self.EPSILON not in self._first[name]:
                            self._first[name].add(self.EPSILON)
                            changed = True
                        continue

                    # Process each symbol in the production
                    for sym_str in rule.symbols:
                        sym = Symbol.parse(sym_str)
                        base = sym.name

                        # Get FIRST of this symbol
                        if base in self._first:
                            sym_first = self._first[base]
                        elif base in self.grammar.terminals:
                            sym_first = {base}
                        else:
                            sym_first = set()

                        # Add to FIRST set (except EPSILON)
                        before = len(self._first[name])
                        self._first[name] |= (sym_first - {self.EPSILON})

                        if len(self._first[name]) > before:
                            changed = True

                        # Handle optional/star modifiers
                        if sym.optional or sym.zero_or_more:
                            continue  # Keep going to next symbol

                        # If not nullable, stop here
                        if self.EPSILON not in sym_first:
                            break
                    else:
                        # All symbols nullable - add EPSILON
                        if self.EPSILON not in self._first[name]:
                            self._first[name].add(self.EPSILON)
                            changed = True

    def _compute_follow(self):
        """Compute FOLLOW sets for all non-terminals."""
        # Initialize FOLLOW sets
        for name in self.grammar.rules:
            self._follow[name] = set()

        # Start symbol has EOF in its FOLLOW set
        self._follow[self.grammar.start].add(self.EOF)

        # Iterate until no changes
        changed = True
        while changed:
            changed = False

            for name, rules in self.grammar.rules.items():
                for rule in rules:
                    # For each position in the rule
                    for i, sym_str in enumerate(rule.symbols):
                        sym = Symbol.parse(sym_str)
                        base = sym.name

                        # Only compute FOLLOW for non-terminals
                        if base not in self.grammar.rules:
                            continue

                        # Get what follows this symbol
                        rest = rule.symbols[i + 1:]

                        # Add FIRST(rest) to FOLLOW(sym)
                        first_of_rest = self.first_of_sequence(rest)
                        before = len(self._follow[base])
                        self._follow[base] |= (first_of_rest - {self.EPSILON})

                        if len(self._follow[base]) > before:
                            changed = True

                        # If rest is empty or nullable, add FOLLOW(rule.name)
                        if not rest or self.EPSILON in first_of_rest:
                            before = len(self._follow[base])
                            self._follow[base] |= self._follow[name]

                            if len(self._follow[base]) > before:
                                changed = True

    def build_parse_table(self) -> Dict[Tuple[str, str], Rule]:
        """
        Build an LL(1) parse table.

        The table maps (non-terminal, terminal) -> production rule.

        Returns:
            Dictionary mapping (non-terminal, lookahead) to Rule

        Raises:
            GrammarError: If grammar is not LL(1)
        """
        from .errors import GrammarError

        table: Dict[Tuple[str, str], Rule] = {}
        conflicts: List[str] = []

        for name, rules in self.grammar.rules.items():
            for rule in rules:
                # Get FIRST of this production
                first_of_prod = self.first_of_sequence(rule.symbols)

                # For each terminal in FIRST
                for terminal in first_of_prod:
                    if terminal == self.EPSILON:
                        continue

                    key = (name, terminal)
                    if key in table:
                        conflicts.append(
                            f"Conflict at ({name}, {terminal}): "
                            f"{table[key]} vs {rule}"
                        )
                    else:
                        table[key] = rule

                # If production is nullable, add FOLLOW entries
                if self.EPSILON in first_of_prod:
                    for terminal in self._follow[name]:
                        key = (name, terminal)
                        if key in table:
                            conflicts.append(
                                f"Conflict at ({name}, {terminal}): "
                                f"{table[key]} vs {rule}"
                            )
                        else:
                            table[key] = rule

        if conflicts:
            raise GrammarError(
                "Grammar is not LL(1)",
                details="\n".join(conflicts)
            )

        return table

    def __repr__(self):
        lines = ["GrammarSets:"]
        lines.append("  FIRST sets:")
        for name in self.grammar.rules:
            lines.append(f"    {name}: {sorted(self._first.get(name, set()))}")
        lines.append("  FOLLOW sets:")
        for name in self.grammar.rules:
            lines.append(f"    {name}: {sorted(self._follow.get(name, set()))}")
        return "\n".join(lines)
