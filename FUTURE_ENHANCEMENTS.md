# Future Enhancements Guide

This document explains all optional enhancements that could be added to CFG Parser Core. Each enhancement includes what it means, why it's valuable, and implementation considerations.

---

## Table of Contents

1. [Advanced Features](#advanced-features)
   - [Error Recovery](#1-error-recovery)
   - [LR/GLR Parser](#2-lrglr-parser)
   - [Grammar Conflict Detection](#3-grammar-conflict-detection)
   - [PyPI Package Publishing](#4-pypi-package-publishing)
   - [Async Streaming Parser](#5-async-streaming-parser)
   - [VSCode Extension Integration](#6-vscode-extension-integration)

2. [LLM-Specific Features](#llm-specific-features)
   - [HuggingFace Integration Example](#7-huggingface-integration-example)
   - [Token-to-Terminal Mapping Helper](#8-token-to-terminal-mapping-helper)
   - [Batch Constraint Checking](#9-batch-constraint-checking)

3. [Enhancement Summary Table](#enhancement-summary-table)

---

## Advanced Features

### 1. Error Recovery

| Effort | Value |
|--------|-------|
| Hard   | High  |

#### What It Means

**Error Recovery** means the parser can keep going after finding an error, instead of stopping immediately at the first problem.

#### Current Behavior (No Error Recovery)

```
Input: {"name": "John", age: 30, "city": "NYC"}
                        ↑
                        Missing quotes around "age"

Parser: ❌ Error at position 16: Expected STRING, got UNQUOTED
        *STOPS HERE* - You only see 1 error
```

#### With Error Recovery

```
Input: {"name": "John", age: 30, "city": "NYC", valid: true}
                        ↑                       ↑
                        Error 1                 Error 2

Parser: ❌ Error 1: Expected STRING at position 16
        ⏩ *SKIPS TO NEXT COMMA, CONTINUES*
        ❌ Error 2: Expected STRING at position 44
        ⏩ *SKIPS TO NEXT COMMA, CONTINUES*

        Found 2 errors total!
```

#### Why It's Valuable

| Without Recovery | With Recovery |
|------------------|---------------|
| Fix 1 error, re-run, find next error | See ALL errors at once |
| Frustrating for users | Better developer experience |
| Multiple iterations needed | Fix everything in one pass |

#### Why It's Hard

The parser must decide:
- **How far to skip?** (to next comma? next line? next `}`)
- **How to resync the stack?** (parser state is corrupted after error)
- **Avoid cascading false errors** (one error can cause 100 fake errors)

#### Real-World Example

IDEs like VSCode use error recovery to show **all** red squiggles at once, not just the first one.

#### Implementation Approach

```python
class ErrorRecoveryParser(Parser):
    def parse_with_recovery(self, text: str) -> tuple[bool, list[Error]]:
        errors = []
        state = self.initial_state()

        for token in self.tokenizer.tokenize(text):
            try:
                state = self.step(state, token)
            except ParseError as e:
                errors.append(e)
                state = self._recover(state, token)  # Skip to sync point

        return len(errors) == 0, errors

    def _recover(self, state, token):
        # Strategy 1: Skip tokens until we find a "sync" token
        sync_tokens = {"COMMA", "RBRACE", "RBRACKET", "NEWLINE"}
        # ... skip until sync point found
```

---

### 2. LR/GLR Parser

| Effort | Value  |
|--------|--------|
| Hard   | Medium |

#### What It Means

**LR (Left-to-Right, Rightmost derivation)** and **GLR (Generalized LR)** are more powerful parsing algorithms that can handle grammars that LL(1) cannot.

#### Current Limitation (LL(1))

```
# This grammar is NOT LL(1) - ambiguous lookahead
expr -> expr + expr    # Left recursion - LL(1) can't handle this!
expr -> NUMBER
```

LL(1) requires:
- No left recursion
- Single token lookahead must determine the rule
- FIRST sets can't overlap

#### With LR/GLR Parser

```
# LR can handle left recursion naturally
expr -> expr + term    # ✅ Works in LR
expr -> term
term -> NUMBER

# GLR can even handle ambiguous grammars
stmt -> if expr then stmt
stmt -> if expr then stmt else stmt  # ✅ GLR handles ambiguity
```

#### Comparison

| Feature | LL(1) (Current) | LR(1) | GLR |
|---------|-----------------|-------|-----|
| Left recursion | ❌ No | ✅ Yes | ✅ Yes |
| Lookahead | 1 token | 1 token | Unlimited |
| Ambiguous grammars | ❌ No | ❌ No | ✅ Yes |
| Parse table size | Small | Large | Large |
| Implementation | Simple | Complex | Very Complex |
| Speed | Fast | Fast | Slower |

#### Why It's Medium Value

Most practical grammars (JSON, TOML, YAML, Math) work fine with LL(1). LR/GLR is mainly needed for:
- Programming language parsers (C, C++, Java)
- Natural language processing
- Highly ambiguous grammars

#### Implementation Approach

```python
class LRParser:
    def __init__(self, grammar):
        self.action_table = {}   # (state, terminal) -> action
        self.goto_table = {}     # (state, nonterminal) -> state
        self._build_tables(grammar)

    def parse(self, tokens):
        stack = [0]  # State stack

        for token in tokens:
            action = self.action_table[(stack[-1], token.type)]

            if action.type == "shift":
                stack.append(action.state)
            elif action.type == "reduce":
                # Pop RHS symbols, push LHS
                for _ in range(len(action.rule.rhs)):
                    stack.pop()
                stack.append(self.goto_table[(stack[-1], action.rule.lhs)])
            elif action.type == "accept":
                return True
```

---

### 3. Grammar Conflict Detection

| Effort | Value  |
|--------|--------|
| Medium | Medium |

#### What It Means

**Grammar Conflict Detection** automatically identifies problems in your grammar that will cause parsing issues, BEFORE you try to use it.

#### Types of Conflicts

**1. FIRST/FIRST Conflict**
```python
# Problem: Both alternatives start with the same token
value -> NUMBER      # FIRST = {NUMBER}
value -> NUMBER ID   # FIRST = {NUMBER}  ← Conflict!

# Parser sees NUMBER, can't decide which rule to use
```

**2. FIRST/FOLLOW Conflict**
```python
# Problem: Optional rule overlaps with what comes after
optional -> COMMA items   # FIRST = {COMMA}
optional -> ε             # FOLLOW = {COMMA, RBRACE}
                          # COMMA is in both! ← Conflict!
```

**3. Left Recursion**
```python
# Problem: Rule references itself as first symbol
expr -> expr PLUS term   # ← Infinite loop in LL(1)!
```

#### Current Behavior

```python
g = Grammar("broken")
g.add_rule("value", ["NUMBER"], ["NUMBER", "ID"])  # Conflict!

parser = Parser(g, tokenizer)
parser.parse("123")  # ??? Undefined behavior, silent bugs
```

#### With Conflict Detection

```python
g = Grammar("broken")
g.add_rule("value", ["NUMBER"], ["NUMBER", "ID"])

conflicts = g.detect_conflicts()
# Returns:
# [
#   GrammarConflict(
#     type="FIRST/FIRST",
#     rule="value",
#     token="NUMBER",
#     alternatives=[["NUMBER"], ["NUMBER", "ID"]],
#     suggestion="Add more lookahead or refactor grammar"
#   )
# ]

g.validate()  # Raises GrammarError with detailed explanation
```

#### Why It's Valuable

| Without Detection | With Detection |
|-------------------|----------------|
| Silent bugs, wrong parses | Clear error messages |
| Hours debugging | Instant feedback |
| "Why doesn't this work?" | "Rule X conflicts with Y" |

#### Implementation Approach

```python
def detect_conflicts(grammar):
    conflicts = []

    for nonterminal, rules in grammar.rules.items():
        first_sets = [grammar.first(rule) for rule in rules]

        # Check FIRST/FIRST conflicts
        for i, first_i in enumerate(first_sets):
            for j, first_j in enumerate(first_sets[i+1:], i+1):
                overlap = first_i & first_j
                if overlap:
                    conflicts.append(FirstFirstConflict(
                        nonterminal, rules[i], rules[j], overlap
                    ))

        # Check FIRST/FOLLOW conflicts for epsilon rules
        follow = grammar.follow(nonterminal)
        for i, rule in enumerate(rules):
            if rule == []:  # epsilon
                overlap = first_sets[i] & follow
                if overlap:
                    conflicts.append(FirstFollowConflict(...))

    return conflicts
```

---

### 4. PyPI Package Publishing

| Effort | Value |
|--------|-------|
| Easy   | High  |

#### What It Means

**PyPI Publishing** means anyone can install your parser with a simple pip command:

```bash
pip install cfg-parser-core
```

Instead of:
```bash
git clone https://github.com/you/cfg-parser-core
cd cfg-parser-core
# manually add to PYTHONPATH...
```

#### What's Needed

**1. Project Structure**
```
cfg-parser-core/
├── pyproject.toml      # ← Package metadata (NEW)
├── setup.py            # ← Optional, for compatibility
├── README.md
├── LICENSE
├── src/
│   └── cfg_parser_core/
│       ├── __init__.py
│       ├── core/
│       │   ├── grammar.py
│       │   ├── parser.py
│       │   └── ...
│       └── grammars/
│           ├── json_grammar.py
│           └── ...
└── tests/
```

**2. pyproject.toml**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "cfg-parser-core"
version = "1.0.0"
description = "Reusable CFG parser with get_valid_next() for LLM constrained decoding"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "you@example.com"}]
keywords = ["parser", "cfg", "grammar", "llm", "constrained-decoding"]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
]
requires-python = ">=3.8"

[project.urls]
Homepage = "https://github.com/you/cfg-parser-core"
```

**3. Publishing Commands**
```bash
# Build the package
pip install build
python -m build

# Upload to PyPI
pip install twine
twine upload dist/*
```

#### After Publishing

```python
# Anyone can now do:
pip install cfg-parser-core

# And use it:
from cfg_parser_core import create_json_parser, parse_json

parser = create_json_parser()
valid_next = parser.get_valid_next(state)
```

#### Why It's High Value

| Without PyPI | With PyPI |
|--------------|-----------|
| Manual installation | `pip install cfg-parser-core` |
| Copy-paste code | Proper dependency management |
| No version control | Semantic versioning |
| Hard to share | Easy to share and cite |

---

### 5. Async Streaming Parser

| Effort | Value  |
|--------|--------|
| Medium | Medium |

#### What It Means

**Async Streaming Parser** processes input as it arrives, without waiting for the complete input. Useful for:
- Parsing LLM output token-by-token as it's generated
- Real-time validation while user types
- Processing large files without loading entirely into memory

#### Current Behavior (Batch)

```python
# Must wait for ENTIRE response before parsing
full_response = await llm.generate(prompt)  # Wait 5 seconds...
result = parse_json(full_response)          # Then parse
```

#### With Async Streaming

```python
async def parse_stream(token_stream):
    parser = create_json_parser()
    state = parser.initial_state()

    async for token in token_stream:
        # Process each token as it arrives
        state = parser.step(state, token)

        # Can yield partial results or validation status
        yield {
            "valid_so_far": True,
            "complete": state.is_complete(),
            "valid_next": parser.get_valid_next(state)
        }

# Use with LLM streaming
async for status in parse_stream(llm.stream(prompt)):
    update_ui(status)  # Real-time feedback!
```

#### Visual Comparison

```
Batch Parsing:
LLM: {"name": "John", "age": 30}
     ════════════════════════════► Parse all at once
                                   └─→ Result

Streaming Parsing:
LLM: {  "name"  :  "John"  ,  "age"  :  30  }
     ↓    ↓     ↓    ↓     ↓    ↓    ↓   ↓   ↓
     ✓    ✓     ✓    ✓     ✓    ✓    ✓   ✓   ✓  (validate each token)
     └─→ Real-time feedback at each step
```

#### Why It's Medium Value

Most use cases work fine with batch parsing. Streaming is mainly valuable for:
- Very long outputs (parsing as you go)
- Real-time UI feedback
- Memory-constrained environments

#### Implementation Approach

```python
class AsyncStreamingParser:
    def __init__(self, grammar, tokenizer):
        self.grammar = grammar
        self.tokenizer = tokenizer

    async def parse_stream(self, char_stream) -> AsyncIterator[ParseEvent]:
        state = self.initial_state()
        buffer = ""

        async for char in char_stream:
            buffer += char

            # Try to extract complete tokens
            tokens = self.tokenizer.tokenize_partial(buffer)

            for token in tokens:
                state = self.step(state, token)
                yield ParseEvent(
                    token=token,
                    valid=True,
                    complete=state.is_complete(),
                    valid_next=self.get_valid_next(state)
                )

            # Keep untokenized remainder in buffer
            buffer = self.tokenizer.remainder
```

---

### 6. VSCode Extension Integration

| Effort | Value |
|--------|-------|
| Hard   | High  |

#### What It Means

**VSCode Extension** brings your parser into the IDE, providing:
- Real-time syntax highlighting
- Error squiggles as you type
- Autocomplete suggestions from `get_valid_next()`
- Hover information

#### What It Looks Like

```
┌─────────────────────────────────────────────────────────────┐
│ config.json                                              ×  │
├─────────────────────────────────────────────────────────────┤
│  1 │ {                                                      │
│  2 │   "name": "John",                                      │
│  3 │   "age": 30,                                           │
│  4 │   "city": NYC        ← Red squiggle: Expected STRING   │
│  5 │   ▊                                                    │
│    │   ┌──────────────────┐                                 │
│    │   │ "address"        │  ← Autocomplete from            │
│    │   │ "email"          │    get_valid_next()!            │
│    │   │ "phone"          │                                 │
│    │   │ }                │                                 │
│    │   └──────────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

#### Architecture

```
┌─────────────┐      ┌─────────────────┐      ┌──────────────┐
│   VSCode    │ ←──→ │ Language Server │ ←──→ │ CFG Parser   │
│  Extension  │ LSP  │    (Python)     │      │    Core      │
└─────────────┘      └─────────────────┘      └──────────────┘
     │                       │                       │
     │ User types            │ Validate              │ get_valid_next()
     │ in editor             │ & suggest             │ parse()
```

#### Components Needed

**1. Language Server (Python)**
```python
from pygls.server import LanguageServer
from cfg_parser_core import create_json_parser

server = LanguageServer("cfg-parser-ls", "v1")

@server.feature("textDocument/completion")
def completions(params):
    # Get cursor position
    doc = server.workspace.get_document(params.text_document.uri)
    text_before_cursor = doc.source[:params.position]

    # Use parser to get valid next tokens
    parser = create_json_parser()
    state = parse_partial(text_before_cursor)
    valid_next = parser.get_valid_next(state)

    # Convert to VSCode completion items
    return [CompletionItem(label=t) for t in valid_next]

@server.feature("textDocument/diagnostic")
def diagnostics(params):
    doc = server.workspace.get_document(params.text_document.uri)

    try:
        parser.parse(doc.source)
        return []  # No errors
    except ParseError as e:
        return [Diagnostic(
            range=error_range(e),
            message=str(e),
            severity=DiagnosticSeverity.Error
        )]
```

**2. VSCode Extension (TypeScript)**
```typescript
// extension.ts
import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';

export function activate(context: vscode.ExtensionContext) {
    const client = new LanguageClient(
        'cfgParser',
        'CFG Parser Language Server',
        { command: 'python', args: ['-m', 'cfg_parser_ls'] },
        { documentSelector: [{ scheme: 'file', language: 'json' }] }
    );

    client.start();
}
```

#### Why It's Hard

- Requires learning Language Server Protocol (LSP)
- Two codebases: Python server + TypeScript extension
- Real-time performance requirements
- Complex state synchronization

#### Why It's High Value

- Visual, interactive experience
- Immediate feedback
- Great for demonstrating the parser's capabilities
- Professional-grade tooling

---

## LLM-Specific Features

### 7. HuggingFace Integration Example

| Effort | Value |
|--------|-------|
| Medium | High  |

#### What It Means

**HuggingFace Integration** shows how to use `get_valid_next()` with real LLMs to force them to output valid JSON/YAML/etc.

#### The Problem

```python
# Ask LLM to generate JSON
prompt = "Generate a user profile as JSON:"

# LLM might output INVALID JSON:
output = '{"name": "John", age: 30}'  # ❌ Missing quotes around "age"
```

#### The Solution: Constrained Decoding

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from cfg_parser_core import create_json_parser

model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")
parser = create_json_parser()

def generate_valid_json(prompt):
    state = parser.initial_state()
    output_ids = []

    while not state.is_complete():
        # 1. Get valid next tokens from grammar
        valid_terminals = parser.get_valid_next(state)

        # 2. Convert grammar terminals to LLM token IDs
        valid_token_ids = terminals_to_token_ids(valid_terminals, tokenizer)

        # 3. Get model predictions
        inputs = tokenizer(prompt, return_tensors="pt")
        logits = model(**inputs).logits[:, -1, :]

        # 4. MASK invalid tokens (set probability to -infinity)
        mask = torch.ones_like(logits) * float('-inf')
        mask[:, valid_token_ids] = 0
        masked_logits = logits + mask  # ← Key step!

        # 5. Sample from valid tokens only
        next_token_id = torch.argmax(masked_logits, dim=-1)
        output_ids.append(next_token_id)

        # 6. Update parser state
        next_token_str = tokenizer.decode(next_token_id)
        grammar_token = string_to_grammar_token(next_token_str)
        state = parser.step(state, grammar_token)

    return tokenizer.decode(output_ids)  # ✅ GUARANTEED valid JSON
```

#### Visual Explanation

```
LLM generating: {"name": "John", |
                                 ↑ cursor here

Without constraint:           With constraint:
┌─────────────────────┐       ┌─────────────────────┐
│ "age"    → 15%      │       │ "age"    → 60%      │ ✅ valid
│ age      → 20%      │ ❌    │ age      → 0%       │ ← MASKED
│ 123      → 10%      │ ❌    │ 123      → 0%       │ ← MASKED
│ "city"   → 12%      │       │ "city"   → 40%      │ ✅ valid
│ [random] → 43%      │ ❌    │ [random] → 0%       │ ← MASKED
└─────────────────────┘       └─────────────────────┘

Result: LLM can ONLY pick valid JSON tokens!
```

#### Why It's Medium Effort

| Challenge | Description |
|-----------|-------------|
| Token mapping | LLM tokens ≠ grammar terminals |
| Sub-word tokens | `"name"` might be `["\"", "name", "\""]` in LLM |
| Tokenizer differences | GPT-2, LLaMA, Mistral tokenize differently |
| Performance | Must compute valid tokens at each generation step |

#### Why It's High Value

This is **THE killer use case** for CFG Parser Core! It enables:
- 100% valid JSON from any LLM
- Structured data extraction
- Function calling / tool use
- API response generation
- Form filling
- Code generation with valid syntax

---

### 8. Token-to-Terminal Mapping Helper

| Effort | Value |
|--------|-------|
| Medium | High  |

#### What It Means

**Token-to-Terminal Mapping** bridges the gap between LLM tokens (subwords) and grammar terminals (logical units like STRING, NUMBER).

#### The Problem

```
Grammar terminal:  STRING = "hello"     (one logical unit)
                   ↓
LLM tokens:        ['"', 'hello', '"']  (three subword tokens)
```

The parser thinks in terms of `STRING`, but the LLM generates `"`, `hello`, `"` separately.

#### Visual Example

```
Grammar says valid next: {STRING, NUMBER, BOOLEAN}

LLM vocabulary:
  Token 0: "the"
  Token 1: "{"        → maps to LBRACE
  Token 2: "hello"    → could be part of STRING or UNQUOTED
  Token 3: '"'        → starts STRING
  Token 4: "123"      → maps to NUMBER
  Token 5: "true"     → maps to BOOLEAN
  Token 6: ": "       → maps to COLON
  ...

Need mapping:
  STRING  → {token 3, token 7, token 12, ...}  (all tokens that can start/continue strings)
  NUMBER  → {token 4, token 15, token 23, ...}
  BOOLEAN → {token 5, token 6}
```

#### The Solution

```python
class TokenTerminalMapper:
    def __init__(self, grammar_tokenizer, llm_tokenizer):
        self.grammar_tokenizer = grammar_tokenizer
        self.llm_tokenizer = llm_tokenizer
        self._build_mapping()

    def _build_mapping(self):
        """Pre-compute which LLM tokens can produce each grammar terminal."""
        self.terminal_to_llm_tokens = {}

        for terminal in self.grammar_tokenizer.terminals:
            matching_llm_tokens = []

            for token_id in range(self.llm_tokenizer.vocab_size):
                token_str = self.llm_tokenizer.decode([token_id])

                # Check if this LLM token matches the terminal's pattern
                if self._matches_terminal(token_str, terminal):
                    matching_llm_tokens.append(token_id)

            self.terminal_to_llm_tokens[terminal] = matching_llm_tokens

    def get_valid_llm_tokens(self, valid_terminals: set) -> list:
        """Convert grammar terminals to LLM token IDs."""
        valid_ids = []
        for terminal in valid_terminals:
            valid_ids.extend(self.terminal_to_llm_tokens[terminal])
        return valid_ids
```

#### Handling Partial Tokens

```python
class PartialTokenMapper:
    """Handle cases where grammar terminal spans multiple LLM tokens."""

    def __init__(self, grammar_tokenizer, llm_tokenizer):
        self.partial_state = ""  # Accumulates partial terminal

    def get_valid_llm_tokens(self, valid_terminals: set, partial: str = "") -> list:
        """
        If partial="\"hel", and valid_terminals={STRING}:
        Return LLM tokens that can continue this partial string.
        """
        valid_ids = []

        for token_id in range(self.llm_tokenizer.vocab_size):
            token_str = self.llm_tokenizer.decode([token_id])
            candidate = partial + token_str

            # Check if candidate could be a valid STRING (or prefix of one)
            if self._could_be_terminal(candidate, valid_terminals):
                valid_ids.append(token_id)

        return valid_ids
```

#### Why It's High Value

Without this mapping, HuggingFace integration is incomplete. This is the **critical bridge** between grammar-level thinking and token-level generation.

---

### 9. Batch Constraint Checking

| Effort | Value  |
|--------|--------|
| Medium | Medium |

#### What It Means

**Batch Constraint Checking** validates multiple token sequences in parallel, useful for:
- Beam search (checking N candidates at once)
- Batch inference (multiple prompts)
- Speculative decoding (verify multiple continuations)

#### Current Behavior (One at a Time)

```python
candidates = [
    '{"name": "John"}',
    '{"name": "Jane"}',
    '{"name": 123}',      # Invalid
    '{"name": "Bob"}',
]

# Check each one sequentially
results = []
for candidate in candidates:
    results.append(parser.parse(candidate))  # 4 separate calls
```

#### With Batch Checking

```python
candidates = [
    '{"name": "John"}',
    '{"name": "Jane"}',
    '{"name": 123}',      # Invalid
    '{"name": "Bob"}',
]

# Check all at once - much faster!
results = parser.parse_batch(candidates)
# Returns: [True, True, False, True]
```

#### Why It's Faster

```
Sequential:
  Candidate 1 → Parse → Result
  Candidate 2 → Parse → Result
  Candidate 3 → Parse → Result
  Candidate 4 → Parse → Result
  Total: 4 × parse_time

Batch (with shared prefix optimization):
  All share: {"name": "
  Only differ at: John"} vs Jane"} vs 123} vs Bob"}

  Parse shared prefix ONCE, then branch
  Total: 1 × shared_parse + 4 × diff_parse (much smaller)
```

#### Implementation Approach

```python
class BatchParser:
    def parse_batch(self, texts: list[str]) -> list[bool]:
        # Find common prefix
        prefix = common_prefix(texts)

        # Parse prefix once
        state = self._parse_prefix(prefix)

        # Fork state for each suffix
        results = []
        for text in texts:
            suffix = text[len(prefix):]
            forked_state = state.copy()
            results.append(self._parse_suffix(forked_state, suffix))

        return results

    def get_valid_next_batch(self, states: list[ParseState]) -> list[set]:
        """Get valid next tokens for multiple states at once."""
        # Can optimize by grouping states with same stack top
        results = []
        for state in states:
            results.append(self.get_valid_next(state))
        return results
```

#### Use Case: Beam Search

```python
def constrained_beam_search(prompt, beam_width=5):
    beams = [(parser.initial_state(), "", 0.0)]  # (state, text, score)

    while not all_complete(beams):
        all_candidates = []

        for state, text, score in beams:
            valid_tokens = parser.get_valid_next(state)

            for token in valid_tokens:
                new_state = parser.step(state, token)
                new_text = text + token
                new_score = score + model.log_prob(token)
                all_candidates.append((new_state, new_text, new_score))

        # Keep top-k beams
        beams = sorted(all_candidates, key=lambda x: x[2])[-beam_width:]

    return beams[0][1]  # Best complete sequence
```

#### Why It's Medium Value

Beam search and batch inference are advanced use cases. Most users will be fine with single-sequence generation.

---

## Enhancement Summary Table

| # | Enhancement | Effort | Value | Category |
|---|-------------|--------|-------|----------|
| 1 | Error Recovery | Hard | High | Advanced |
| 2 | LR/GLR Parser | Hard | Medium | Advanced |
| 3 | Grammar Conflict Detection | Medium | Medium | Advanced |
| 4 | PyPI Package Publishing | Easy | High | Advanced |
| 5 | Async Streaming Parser | Medium | Medium | Advanced |
| 6 | VSCode Extension | Hard | High | Advanced |
| 7 | HuggingFace Integration | Medium | High | LLM |
| 8 | Token-to-Terminal Mapping | Medium | High | LLM |
| 9 | Batch Constraint Checking | Medium | Medium | LLM |

## Recommended Priority

**If you want to continue the project:**

1. **PyPI Package** (Easy, High Value) - Makes sharing easy
2. **HuggingFace Integration** (Medium, High Value) - The killer demo
3. **Token-to-Terminal Mapping** (Medium, High Value) - Required for #2
4. **Grammar Conflict Detection** (Medium, Medium Value) - Better DX

**Can skip for now:**
- LR/GLR Parser - LL(1) handles most practical grammars
- VSCode Extension - Cool but lots of work
- Error Recovery - Nice to have but complex
