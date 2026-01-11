# Understanding CFG Parser Core

A simple guide to understand how this parser works.

---

## The Big Picture

Think of this parser like a **language teacher** that checks if sentences follow grammar rules.

```
Input Text  -->  [Tokenizer]  -->  Tokens  -->  [Parser]  -->  Valid/Invalid + AST
   "2+3"         breaks it           [2,+,3]      checks rules      Valid! Tree: (+ 2 3)
                 into pieces
```

---

## The 8 Components (In Order of Use)

### 1. Tokenizer (`tokenizer.py`)
**Job:** Break text into meaningful pieces called "tokens"

```
Input:  "2 + 3 * 4"
Output: [NUMBER:2] [+] [NUMBER:3] [*] [NUMBER:4] [EOF]
```

**Real-life analogy:** Like breaking a sentence into words
- "The cat sat" --> ["The", "cat", "sat"]

**Key code:**
```python
tokenizer = Tokenizer()
tokenizer.add("NUMBER", r"\d+")      # Match digits
tokenizer.add("+", r"\+")            # Match plus sign
tokenizer.add("WS", r"\s+", skip=True)  # Skip whitespace

tokens = tokenizer.tokenize("2 + 3")
# Result: [Token(NUMBER, "2"), Token(+, "+"), Token(NUMBER, "3"), Token(EOF, "")]
```

---

### 2. Grammar (`grammar.py`)
**Job:** Define the RULES of your language

```
Grammar for simple math:
  expr   ->  NUMBER
  expr   ->  expr + expr
  expr   ->  ( expr )
```

**Real-life analogy:** Like English grammar rules
- "Subject + Verb + Object" is valid
- "Verb + Verb + Verb" is NOT valid

**Key code:**
```python
g = Grammar("expr")              # Start symbol
g.terminal("NUMBER", "+", "-")   # These are "words" (tokens)
g.add_rule("expr",               # Rules for "expr"
    ["NUMBER"],                  # expr can be just a NUMBER
    ["expr", "+", "expr"]        # OR expr + expr
)
```

**Two types of symbols:**
- **Terminals:** The actual tokens (NUMBER, +, -, etc.) - the "words"
- **Non-terminals:** Rules that expand into other things (expr, term) - the "categories"

---

### 3. FIRST/FOLLOW Sets (`sets.py`)
**Job:** Answer "What tokens can come next?"

This is the BRAIN of the parser. It pre-computes:

**FIRST(X):** What tokens can START something derived from X?
```
FIRST(expr) = { NUMBER, ( }    -- An expr can start with NUMBER or (
FIRST(NUMBER) = { NUMBER }     -- A NUMBER starts with... NUMBER
```

**FOLLOW(X):** What tokens can come AFTER X?
```
FOLLOW(expr) = { +, -, ), EOF }  -- After an expr, we might see +, -, ), or end
```

**Real-life analogy:**
- FIRST("noun phrase") = {"the", "a", "my", ...}  -- words that can start a noun phrase
- FOLLOW("noun phrase") = {"is", "was", "runs", ...}  -- words that can follow a noun phrase

---

### 4. Parser (`parser.py`)
**Job:** Check if tokens follow the grammar rules

The parser uses a **stack** to track what it's expecting:

```
Parsing "2 + 3":

Stack: [expr, EOF]           Input: [2, +, 3, EOF]
  --> expr starts with NUMBER? Yes! Expand expr -> NUMBER + expr

Stack: [NUMBER, +, expr, EOF]  Input: [2, +, 3, EOF]
  --> Match NUMBER with 2? Yes!

Stack: [+, expr, EOF]        Input: [+, 3, EOF]
  --> Match + with +? Yes!

Stack: [expr, EOF]           Input: [3, EOF]
  --> Expand expr -> NUMBER

Stack: [NUMBER, EOF]         Input: [3, EOF]
  --> Match NUMBER with 3? Yes!

Stack: [EOF]                 Input: [EOF]
  --> Match! VALID!
```

**Key code:**
```python
parser = Parser(grammar, tokenizer)

# Simple validation
is_valid = parser.parse("2 + 3")  # True

# Get AST (tree structure)
ast = parser.parse_to_ast("2 + 3")
```

---

### 5. THE KEY FUNCTION: `get_valid_next()`

This is the MOST IMPORTANT function in the whole codebase!

**Job:** Given current parsing state, what tokens are valid next?

```python
state = parser.initial_state()
valid = parser.get_valid_next(state)
# Returns: {'NUMBER', '('}  -- At start, we can have NUMBER or (

# Feed a token
token = Token("NUMBER", "2")
state = parser.step(state, token)
valid = parser.get_valid_next(state)
# Returns: {'+', '-', '*', '/', 'EOF'}  -- After a number
```

**Why is this the key function?**

1. **LLM Constrained Decoding:** Force AI to only generate valid tokens
2. **Autocomplete:** Show user what they can type next
3. **Validation:** Know what was expected when there's an error
4. **Syntax Highlighting:** Know if current input is valid so far

---

### 6. AST (`ast.py`)
**Job:** Build a TREE representation of the parsed input

```
Input: "2 + 3 * 4"

AST (Abstract Syntax Tree):
        +
       / \
      2   *
         / \
        3   4
```

**Why trees?**
- Easy to evaluate: visit nodes recursively
- Easy to transform: modify the tree
- Easy to analyze: find patterns

**Key code:**
```python
ast = parser.parse_to_ast("2 + 3")
print(ast.type)      # "expr"
print(ast.children)  # [Node(NUMBER, "2"), Node(+), Node(NUMBER, "3")]
```

---

### 7. Visitor (`visitor.py`)
**Job:** Walk the AST and DO something at each node

**Pattern:** Instead of putting logic IN the tree, we VISIT the tree

```python
class Calculator(Visitor):
    def visit_NUMBER(self, node):
        return float(node.value)

    def visit_expr(self, node):
        if len(node.children) == 1:
            return self.visit(node.children[0])
        left = self.visit(node.children[0])
        op = node.children[1].value
        right = self.visit(node.children[2])
        if op == '+': return left + right
        if op == '*': return left * right

calc = Calculator()
result = calc.visit(ast)  # Evaluates the expression!
```

---

### 8. Visualizer (`visualize.py`)
**Job:** Debug and display grammars, ASTs, parse traces

```python
viz = Visualizer()
viz.print_grammar(grammar)    # Show all rules
viz.print_ast(ast)            # Show tree structure
viz.print_sets(grammar)       # Show FIRST/FOLLOW sets
viz.print_parse_trace(parser, "2+3")  # Step-by-step parsing
```

---

## How It All Connects

```
                                    UNDERSTANDING FLOW

     You Define                         Core Computes                    You Use
    ┌─────────────┐                   ┌──────────────┐               ┌─────────────┐
    │   Grammar   │ ──────────────>   │ FIRST/FOLLOW │ ──────────>  │ get_valid_  │
    │   (rules)   │                   │    Sets      │              │   next()    │
    └─────────────┘                   └──────────────┘               └─────────────┘
           │                                 │                              │
           v                                 v                              v
    ┌─────────────┐                   ┌──────────────┐               ┌─────────────┐
    │  Tokenizer  │ ──────────────>   │    Parser    │ ──────────>  │  AST/Valid  │
    │  (patterns) │                   │   (engine)   │              │   Result    │
    └─────────────┘                   └──────────────┘               └─────────────┘
```

---

## Built-in Grammars

The project includes 5 ready-to-use grammars:

### 1. JSON Grammar (`grammars/json_grammar.py`)
```python
from grammars.json_grammar import parse_json, validate_json

parse_json('{"name": "John", "age": 30}')
# {'name': 'John', 'age': 30}

validate_json('{"valid": true}')   # True
validate_json('{"invalid": }')     # False
```

### 2. Math Grammar (`grammars/math_grammar.py`)
```python
from grammars.math_grammar import evaluate

evaluate("2 + 3 * 4")           # 14 (respects precedence)
evaluate("sqrt(16) + 2^3")      # 12.0
evaluate("sin(0) + cos(0)")     # 1.0
```

### 3. CSV Grammar (`grammars/csv_grammar.py`)
```python
from grammars.csv_grammar import parse_csv, csv_to_dicts

# List of lists
parse_csv('a,b,c\n1,2,3')
# [['a', 'b', 'c'], ['1', '2', '3']]

# List of dicts (first row as headers)
csv_to_dicts('name,age\nJohn,30')
# [{'name': 'John', 'age': '30'}]
```

### 4. TOML Grammar (`grammars/toml_grammar.py`)
```python
from grammars.toml_grammar import parse_toml

parse_toml('name = "test"\ncount = 42')
# {'name': 'test', 'count': 42}
```

### 5. YAML Grammar (`grammars/yaml_grammar.py`)
```python
from grammars.yaml_grammar import parse_yaml

# Flow/inline style only
parse_yaml('{name: John, age: 30}')
# {'name': 'John', 'age': 30}

parse_yaml('[1, 2, true, null]')
# [1, 2, True, None]
```

---

## Interactive CLI

Test all parsers without writing code:

```bash
python cli_test.py
```

```
==================================================
CFG Parser Core - Interactive CLI
==================================================

1. JSON Validator
2. Math Calculator
3. CSV Parser
4. TOML Parser
5. YAML Parser
6. get_valid_next() Demo

Choose (1-6):
```

### Option 6: get_valid_next() Demo

This is the most educational option - see exactly what tokens are valid at each step:

```
JSON get_valid_next() Demo
----------------------------------------
Stack: ['json']
Valid next: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}

Token> {
  Trying to feed: LBRACE = '{'
  Success! New stack: ['object_body', 'RBRACE']...

Valid next: {'STRING', 'RBRACE'}

Token> "name"
  Success! New stack: ['COLON', 'value', 'pairs_rest', 'RBRACE']...

Valid next: {'COLON'}
```

---

## File Structure

```
cfg-parser-core/
├── core/                       # The engine
│   ├── __init__.py             # Exports: Grammar, Tokenizer, Parser
│   ├── tokenizer.py            # Component 1: Text -> Tokens
│   ├── grammar.py              # Component 2: Define rules
│   ├── parser.py               # Component 3: Parse tokens (THE HEART)
│   ├── ast.py                  # Component 4: Tree structure
│   ├── visitor.py              # Component 5: Walk trees
│   ├── errors.py               # Component 6: Error types
│   ├── sets.py                 # Component 7: FIRST/FOLLOW (THE BRAIN)
│   └── visualize.py            # Component 8: Debug tools
│
├── grammars/                   # Ready-to-use grammars
│   ├── json_grammar.py         # Parse JSON
│   ├── math_grammar.py         # Parse & evaluate math
│   ├── csv_grammar.py          # Parse CSV files
│   ├── toml_grammar.py         # Parse TOML config
│   └── yaml_grammar.py         # Parse YAML (flow style)
│
├── examples/                   # Learn by example
│   ├── 01_basic_parsing.py
│   ├── 02_json_parsing.py
│   ├── 03_math_expressions.py
│   ├── 04_llm_constrained_decoding.py
│   └── 05_build_custom_dsl.py
│
├── tests/                      # Unit tests
│   └── test_parser.py          # 28 tests
│
├── cli_test.py                 # Interactive CLI tool
│
├── COMPLETE_GUIDE.md           # Full detailed guide
├── UNDERSTANDING_THE_CORE.md   # This file
├── USE_CASES_GUIDE.md          # Use case examples
└── FUTURE_ENHANCEMENTS.md      # Optional enhancements
```

---

## Quick Examples

### Example 1: Validate JSON
```python
from grammars.json_grammar import validate_json

validate_json('{"name": "John"}')  # True
validate_json('{"broken": }')       # False
```

### Example 2: Evaluate Math
```python
from grammars.math_grammar import evaluate

evaluate("2 + 3 * 4")           # 14.0
evaluate("sqrt(16) + 2^3")      # 12.0
```

### Example 3: Parse CSV
```python
from grammars.csv_grammar import csv_to_dicts

data = csv_to_dicts('name,age\nJohn,30\nJane,25')
print(data[0]['name'])  # John
```

### Example 4: Parse Config (TOML)
```python
from grammars.toml_grammar import parse_toml

config = parse_toml('host = "localhost"\nport = 8080')
print(config['port'])  # 8080
```

### Example 5: Build Custom Language
```python
from core import Grammar, Tokenizer, Parser

# Define grammar for commands: "get user", "set config", etc.
g = Grammar("command")
g.terminal("ACTION", "TARGET")
g.add_rule("command", ["ACTION", "TARGET"])

t = Tokenizer()
t.add("ACTION", r"(get|set|delete)")
t.add("TARGET", r"[a-z]+")
t.add("WS", r"\s+", skip=True)

p = Parser(g, t)
p.parse("get user")    # True
p.parse("hello")       # False
```

### Example 6: LLM Constrained Decoding
```python
from grammars.json_grammar import create_json_parser

parser = create_json_parser()

# Only let AI generate valid JSON
state = parser.initial_state()
valid_tokens = parser.get_valid_next(state)
# {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}

# In LLM loop: mask invalid tokens
# for token_id in range(vocab_size):
#     if token_id_to_string[token_id] not in valid_tokens:
#         logits[token_id] = -infinity
```

---

## The Core Insight

The whole library is built around ONE key insight:

> **Given a grammar, we can PRE-COMPUTE what tokens are valid at any point in parsing.**

This is done through FIRST and FOLLOW sets:
- FIRST tells us what can START a derivation
- FOLLOW tells us what can COME AFTER

Combined with the parse stack, `get_valid_next()` can always tell you:
**"These are the only valid tokens right now"**

This single function enables:
- Validation
- Error messages
- Autocomplete
- LLM constraining
- And more!

---

## Glossary

| Term | Meaning |
|------|---------|
| **Token** | A piece of input (like a word) |
| **Terminal** | A token type (NUMBER, STRING, +) |
| **Non-terminal** | A grammar rule (expr, statement) |
| **Production** | A rule like `expr -> NUMBER + NUMBER` |
| **AST** | Tree representation of parsed input |
| **FIRST set** | Tokens that can start a derivation |
| **FOLLOW set** | Tokens that can come after something |
| **LL(1)** | Parser that reads Left-to-right, uses Leftmost derivation, with 1 token lookahead |
| **Epsilon** | Empty/nothing (a rule can produce nothing) |
| **EOF** | End Of File/Input marker |

---

## Summary

1. **Tokenizer** breaks text into tokens
2. **Grammar** defines what's valid
3. **Sets** pre-compute what can come where
4. **Parser** checks if input follows rules
5. **get_valid_next()** is the key function - tells you valid next tokens
6. **AST** gives you a tree to work with
7. **Visitor** lets you process the tree
8. **Visualizer** helps you debug

**5 Built-in Grammars:** JSON, Math, CSV, TOML, YAML

**Interactive CLI:** `python cli_test.py`

The power is in `get_valid_next()` - it's what makes this useful for LLMs, autocomplete, and validation!
