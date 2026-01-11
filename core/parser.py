"""
Parser Engine - The heart of the CFG Parser Core.

This is Component 3 of the CFG Parser Core.

Features:
- Recursive descent parsing
- LL(1) table-driven parsing
- Incremental/streaming parsing
- Parse state management
- get_valid_next() for constrained decoding
- AST construction
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict, Tuple, Callable, Any
from copy import deepcopy

from .grammar import Grammar, Rule, Symbol
from .tokenizer import Tokenizer, Token
from .sets import GrammarSets
from .ast import Node, ASTBuilder
from .errors import ParseError, LexerError


@dataclass
class ParseState:
    """
    Represents the current state of parsing.

    This is immutable - operations return new states.
    Enables backtracking and parallel exploration.

    Attributes:
        stack: Grammar symbols still to be matched
        pos: Current position in token stream
        ast_stack: Nodes being built
    """
    stack: Tuple[str, ...]
    pos: int = 0
    ast_stack: Tuple[Node, ...] = field(default_factory=tuple)

    def with_stack(self, new_stack: List[str]) -> 'ParseState':
        """Create new state with different stack."""
        return ParseState(tuple(new_stack), self.pos, self.ast_stack)

    def advance(self, steps: int = 1) -> 'ParseState':
        """Create new state with advanced position."""
        return ParseState(self.stack, self.pos + steps, self.ast_stack)

    def push_symbols(self, symbols: List[str]) -> 'ParseState':
        """Push symbols onto the stack."""
        return ParseState(
            tuple(symbols) + self.stack,
            self.pos,
            self.ast_stack
        )

    def pop_symbol(self) -> Tuple[str, 'ParseState']:
        """Pop top symbol, return it and new state."""
        if not self.stack:
            raise RuntimeError("Cannot pop from empty stack")
        return self.stack[0], ParseState(
            self.stack[1:],
            self.pos,
            self.ast_stack
        )

    def is_complete(self) -> bool:
        """Check if parsing is complete (stack empty)."""
        return len(self.stack) == 0

    def top(self) -> Optional[str]:
        """Get top of stack without popping."""
        return self.stack[0] if self.stack else None

    def __repr__(self):
        stack_str = " ".join(self.stack[:5])
        if len(self.stack) > 5:
            stack_str += "..."
        return f"ParseState(pos={self.pos}, stack=[{stack_str}])"


class Parser:
    r"""
    Main parser class - parses tokens using a grammar.

    Supports multiple parsing modes:
    1. Validation: parse() returns bool
    2. AST Construction: parse_to_ast() returns Node
    3. Incremental: step() for token-by-token parsing
    4. Constrained: get_valid_next() for LLM decoding

    Usage:
        # Setup
        grammar = Grammar("expr")
        grammar.terminal("NUMBER", "+")
        grammar.add_rule("expr", ["NUMBER"], ["expr", "+", "NUMBER"])

        tokenizer = Tokenizer()
        tokenizer.add("NUMBER", r"\d+")
        tokenizer.add("+", r"\+")

        parser = Parser(grammar, tokenizer)

        # Validate
        is_valid = parser.parse("1 + 2")

        # Get AST
        ast = parser.parse_to_ast("1 + 2")

        # Constrained decoding
        state = parser.initial_state()
        valid = parser.get_valid_next(state)
    """

    def __init__(self, grammar: Grammar, tokenizer: Optional[Tokenizer] = None):
        """
        Initialize the parser.

        Args:
            grammar: The grammar to parse with
            tokenizer: Optional tokenizer (can also pass tokens directly)
        """
        self.grammar = grammar
        self.tokenizer = tokenizer
        self.sets = GrammarSets(grammar)

        # Try to build LL(1) parse table
        self._parse_table: Optional[Dict[Tuple[str, str], Rule]] = None
        try:
            self._parse_table = self.sets.build_parse_table()
        except Exception:
            pass  # Grammar not LL(1), use recursive descent

    # ==================== Main API ====================

    def parse(self, input_or_tokens) -> bool:
        """
        Parse input and return True if valid.

        Args:
            input_or_tokens: String (tokenized) or list of tokens

        Returns:
            True if input matches grammar
        """
        try:
            tokens = self._ensure_tokens(input_or_tokens)
            state = self.initial_state()
            state = self._parse_recursive(tokens, state)
            return state.is_complete() and state.pos >= len(tokens) - 1
        except (ParseError, LexerError):
            return False

    def parse_to_ast(self, input_or_tokens) -> Node:
        """
        Parse input and return AST.

        Args:
            input_or_tokens: String (tokenized) or list of tokens

        Returns:
            Root node of AST

        Raises:
            ParseError: If input doesn't match grammar
        """
        tokens = self._ensure_tokens(input_or_tokens)
        builder = ASTBuilder()

        state = self.initial_state()
        self._parse_with_ast(tokens, state, builder)

        ast = builder.get_ast()
        if ast is None:
            raise ParseError("Failed to build AST", found="empty result")
        return ast

    def get_valid_next(self, state: ParseState) -> Set[str]:
        """
        THE KEY FUNCTION - Get valid next tokens.

        Given current parse state, return all terminals that
        would be valid as the next token.

        This is the function that powers:
        - LLM constrained decoding
        - Autocomplete
        - Error messages
        - Validation

        Args:
            state: Current parse state

        Returns:
            Set of valid terminal symbols
        """
        return self.sets.get_valid_next(list(state.stack))

    def initial_state(self) -> ParseState:
        """Get the initial parse state."""
        return ParseState(stack=(self.grammar.start, "EOF"))

    def step(self, state: ParseState, token: Token) -> ParseState:
        """
        Advance parse state by one token.

        For incremental/streaming parsing.

        Args:
            state: Current state
            token: Next token

        Returns:
            New state after consuming token

        Raises:
            ParseError: If token is not valid
        """
        if state.is_complete():
            raise ParseError("Parsing already complete", found=token.type)

        valid = self.get_valid_next(state)
        if token.type not in valid:
            raise ParseError(
                f"Unexpected token",
                expected=valid,
                found=token.type,
                line=token.line,
                column=token.column
            )

        return self._consume_token(state, token)

    # ==================== Parsing Implementations ====================

    def _parse_recursive(self, tokens: List[Token], state: ParseState) -> ParseState:
        """
        Recursive descent parsing.

        Handles non-LL(1) grammars with backtracking.
        """
        while not state.is_complete():
            if state.pos >= len(tokens):
                raise ParseError("Unexpected end of input",
                               expected=self.get_valid_next(state))

            top = state.top()
            token = tokens[state.pos]

            # Terminal: must match
            if self.grammar.is_terminal(top):
                if token.type == top:
                    _, state = state.pop_symbol()
                    state = state.advance()
                else:
                    raise ParseError(
                        f"Expected {top}",
                        expected={top},
                        found=token.type,
                        line=token.line,
                        column=token.column
                    )

            # Non-terminal: expand using a rule
            else:
                rule = self._select_rule(top, token)
                if rule is None:
                    raise ParseError(
                        f"No rule for {top} with lookahead {token.type}",
                        expected=self.sets.first(top),
                        found=token.type,
                        line=token.line,
                        column=token.column
                    )

                _, state = state.pop_symbol()
                if rule.symbols:
                    state = state.push_symbols(list(rule.symbols))

        return state

    def _parse_with_ast(self, tokens: List[Token], state: ParseState,
                        builder: ASTBuilder) -> ParseState:
        """
        Parse and build AST simultaneously.
        """
        # Track node starts with their expected end stack depth
        # Each entry is (node_type, stack_depth_when_done)
        node_stack: List[Tuple[str, int]] = []

        while not state.is_complete():
            if state.pos >= len(tokens):
                break

            top = state.top()
            token = tokens[state.pos]

            # Terminal: add to AST (skip EOF - it's not part of syntax tree)
            if self.grammar.is_terminal(top):
                if token.type == top:
                    if top != "EOF":
                        builder.add_terminal(token.type, token.value,
                                            token.line, token.column)
                    _, state = state.pop_symbol()
                    state = state.advance()
                else:
                    raise ParseError(
                        f"Expected {top}",
                        expected={top},
                        found=token.type,
                        line=token.line,
                        column=token.column
                    )

            # Non-terminal: start new node
            else:
                rule = self._select_rule(top, token)
                if rule is None:
                    raise ParseError(
                        f"No rule for {top}",
                        expected=self.sets.first(top),
                        found=token.type,
                        line=token.line,
                        column=token.column
                    )

                # Record the stack depth where this node will be complete
                # After popping current symbol and pushing rule symbols,
                # the node is complete when we return to current depth - 1
                end_depth = len(state.stack) - 1

                builder.start_node(top, rule.label, token.line, token.column)
                node_stack.append((top, end_depth))

                _, state = state.pop_symbol()
                if rule.symbols:
                    state = state.push_symbols(list(rule.symbols))
                else:
                    # Empty production - end node immediately
                    builder.end_node()
                    node_stack.pop()

            # End nodes that are now complete (stack returned to their end depth)
            while node_stack and len(state.stack) <= node_stack[-1][1]:
                builder.end_node()
                node_stack.pop()

        # Close remaining nodes
        while node_stack:
            builder.end_node()
            node_stack.pop()

        return state

    def _get_rule_symbols(self, nonterminal: str) -> Set[str]:
        """Get all symbols that can appear in rules for a non-terminal."""
        symbols = set()
        for rule in self.grammar.get_rules(nonterminal):
            symbols.update(rule.symbols)
        return symbols

    def _select_rule(self, nonterminal: str, token: Token) -> Optional[Rule]:
        """
        Select which production rule to use.

        Uses parse table if available, otherwise tries each rule.
        """
        # Try LL(1) table first
        if self._parse_table:
            key = (nonterminal, token.type)
            if key in self._parse_table:
                return self._parse_table[key]

        # Fall back to trying each rule
        for rule in self.grammar.get_rules(nonterminal):
            first_of_rule = self.sets.first_of_sequence(rule.symbols)

            if token.type in first_of_rule:
                return rule

            # Handle nullable rules
            if GrammarSets.EPSILON in first_of_rule:
                follow = self.sets.follow(nonterminal)
                if token.type in follow:
                    return rule

        return None

    def _consume_token(self, state: ParseState, token: Token) -> ParseState:
        """Consume a token and update state."""
        while not state.is_complete():
            top = state.top()

            if self.grammar.is_terminal(top):
                if token.type == top:
                    _, state = state.pop_symbol()
                    return state
                break

            # Expand non-terminal
            rule = self._select_rule(top, token)
            if rule is None:
                break

            _, state = state.pop_symbol()
            if rule.symbols:
                state = state.push_symbols(list(rule.symbols))

        return state

    # ==================== Utilities ====================

    def _ensure_tokens(self, input_or_tokens) -> List[Token]:
        """Convert input to tokens if needed."""
        if isinstance(input_or_tokens, str):
            if self.tokenizer is None:
                raise ValueError("No tokenizer provided")
            return self.tokenizer.tokenize(input_or_tokens)
        return list(input_or_tokens)

    def validate(self, text: str) -> List[str]:
        """
        Validate input and return list of errors.

        Args:
            text: Input to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        try:
            tokens = self._ensure_tokens(text)
            state = self.initial_state()
            self._parse_recursive(tokens, state)
        except ParseError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Error: {e}")
        return errors


# ==================== Streaming Parser ====================

class StreamingParser:
    """
    Parser for streaming/incremental input.

    Maintains state across multiple input chunks.

    Usage:
        sp = StreamingParser(grammar, tokenizer)

        sp.feed('{"name":')
        print(sp.get_valid_next())  # What can come next?

        sp.feed('"John"}')
        print(sp.is_complete())  # True
    """

    def __init__(self, grammar: Grammar, tokenizer: Tokenizer):
        self.parser = Parser(grammar, tokenizer)
        self.tokenizer = tokenizer
        self._state = self.parser.initial_state()
        self._buffer = ""
        self._tokens: List[Token] = []

    def feed(self, text: str) -> List[Token]:
        """
        Feed more input text.

        Args:
            text: Additional input

        Returns:
            New tokens consumed
        """
        self._buffer += text

        # Try to tokenize
        try:
            new_tokens = self.tokenizer.tokenize(self._buffer)
            # Remove EOF for now (more input may come)
            if new_tokens and new_tokens[-1].type == "EOF":
                new_tokens = new_tokens[:-1]
        except Exception:
            return []

        # Process new tokens
        consumed = []
        for token in new_tokens[len(self._tokens):]:
            try:
                self._state = self.parser.step(self._state, token)
                consumed.append(token)
                self._tokens.append(token)
            except ParseError:
                break

        return consumed

    def get_valid_next(self) -> Set[str]:
        """Get valid next tokens."""
        return self.parser.get_valid_next(self._state)

    def is_complete(self) -> bool:
        """Check if parsing is complete."""
        return self._state.is_complete()

    def get_state(self) -> ParseState:
        """Get current parse state."""
        return self._state

    def reset(self):
        """Reset parser state."""
        self._state = self.parser.initial_state()
        self._buffer = ""
        self._tokens = []


# ==================== Constrained Decoder ====================

class ConstrainedDecoder:
    """
    Helper for LLM constrained decoding.

    Maps between LLM vocabulary and grammar terminals.

    Usage:
        decoder = ConstrainedDecoder(parser, llm_vocab)

        # During generation
        mask = decoder.get_token_mask(state)
        logits[~mask] = float('-inf')
    """

    def __init__(self, parser: Parser, vocab: Dict[int, str],
                 terminal_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize constrained decoder.

        Args:
            parser: The parser to use
            vocab: LLM vocabulary {token_id: token_string}
            terminal_mapping: Map LLM tokens to grammar terminals
        """
        self.parser = parser
        self.vocab = vocab
        self.terminal_mapping = terminal_mapping or {}

        # Build reverse mapping
        self._token_to_terminal = self._build_mapping()

    def _build_mapping(self) -> Dict[int, str]:
        """Map LLM token IDs to grammar terminals."""
        mapping = {}

        for token_id, token_str in self.vocab.items():
            token_str = token_str.strip()

            # Check explicit mapping first
            if token_str in self.terminal_mapping:
                mapping[token_id] = self.terminal_mapping[token_str]
                continue

            # Try to match grammar terminals
            for terminal in self.parser.grammar.terminals:
                if token_str == terminal or token_str == terminal.lower():
                    mapping[token_id] = terminal
                    break

        return mapping

    def get_token_mask(self, state: ParseState) -> List[bool]:
        """
        Get mask of valid tokens.

        Args:
            state: Current parse state

        Returns:
            Boolean list - True if token is valid
        """
        valid_terminals = self.parser.get_valid_next(state)

        mask = [False] * len(self.vocab)
        for token_id, terminal in self._token_to_terminal.items():
            if terminal in valid_terminals:
                mask[token_id] = True

        return mask

    def get_valid_token_ids(self, state: ParseState) -> Set[int]:
        """Get set of valid token IDs."""
        valid_terminals = self.parser.get_valid_next(state)
        return {
            tid for tid, term in self._token_to_terminal.items()
            if term in valid_terminals
        }

    def step(self, state: ParseState, token_id: int) -> ParseState:
        """
        Advance state with an LLM token.

        Args:
            state: Current state
            token_id: LLM token ID

        Returns:
            New state
        """
        terminal = self._token_to_terminal.get(token_id)
        if terminal is None:
            raise ValueError(f"Token ID {token_id} not mapped to grammar")

        token = Token(type=terminal, value=self.vocab[token_id])
        return self.parser.step(state, token)
