# CFG Parser Core

A complete, reusable Context-Free Grammar (CFG) parser implementation in Python.

## What is This?

A parser engine that can be reused for:

- **JSON/YAML/TOML/CSV parsing** - Parse any structured data format
- **LLM Constrained Decoding** - Force valid output from language models
- **DSL (Domain Specific Languages)** - Build your own mini-languages
- **Expression Evaluation** - Math, boolean, template expressions
- **Linting & Validation** - Syntax checking and error reporting
- **Autocomplete** - Know what tokens are valid next

## Requirements

- **Python 3.7+** (uses only standard library)

## Quick Start

```python
from core import Grammar, Tokenizer, Parser

# 1. Define your grammar
grammar = Grammar("greeting")
grammar.terminal("HELLO", "WORLD")
grammar.add_rule("greeting",
    ["HELLO"],
    ["HELLO", "WORLD"]
)

# 2. Define your tokenizer
tokenizer = Tokenizer()
tokenizer.add("HELLO", r"hello")
tokenizer.add("WORLD", r"world")
tokenizer.add("WS", r"\s+", skip=True)

# 3. Create parser and use it
parser = Parser(grammar, tokenizer)

# Validate input
print(parser.parse("hello world"))  # True

# Get valid next tokens (THE KEY FUNCTION)
state = parser.initial_state()
print(parser.get_valid_next(state))  # {'HELLO'}
```

## Project Structure

```
cfg-parser-core/
├── core/                       # The reusable parser core
│   ├── grammar.py              # Grammar definition
│   ├── tokenizer.py            # Tokenization
│   ├── parser.py               # Parse engine (includes get_valid_next!)
│   ├── sets.py                 # FIRST/FOLLOW set computation
│   ├── ast.py                  # AST nodes
│   ├── visitor.py              # AST traversal & evaluation
│   ├── errors.py               # Error handling
│   └── visualize.py            # Debug tools
│
├── grammars/                   # Pre-built grammars
│   ├── json_grammar.py         # JSON parser
│   ├── math_grammar.py         # Math expression evaluator
│   ├── csv_grammar.py          # CSV parser
│   ├── toml_grammar.py         # TOML config parser
│   └── yaml_grammar.py         # YAML (flow style) parser
│
├── examples/                   # Usage examples
│   ├── 01_basic_parsing.py
│   ├── 02_json_parsing.py
│   ├── 03_math_expressions.py
│   ├── 04_llm_constrained_decoding.py
│   └── 05_build_custom_dsl.py
│
├── tests/                      # Unit tests (28 tests)
│   └── test_parser.py
│
├── cli_test.py                 # Interactive CLI for testing
│
├── COMPLETE_GUIDE.md           # Full project guide
├── UNDERSTANDING_THE_CORE.md   # Core concepts explanation
├── USE_CASES_GUIDE.md          # Use case examples
```

## The Key Function: `get_valid_next()`

This single function powers everything:

```python
valid_tokens = parser.get_valid_next(state)
```

| Use Case | How get_valid_next() Helps |
|----------|---------------------------|
| LLM Constrained Decoding | Mask invalid tokens |
| Autocomplete | Suggest valid completions |
| Validation | Know what was expected |
| Error Messages | "Expected X or Y, got Z" |

## Built-in Grammars

### 1. JSON Parser

```python
from grammars.json_grammar import parse_json, validate_json

# Parse to Python dict
result = parse_json('{"name": "John", "age": 30}')
print(result["name"])  # John

# Validate
validate_json('{"valid": true}')   # True
validate_json('{"invalid": }')     # False
```

### 2. Math Expression Evaluator

```python
from grammars.math_grammar import evaluate

evaluate("2 + 3 * 4")           # 14
evaluate("(2 + 3) * 4")         # 20
evaluate("sqrt(16) + 2^3")      # 12.0
evaluate("sin(0) + cos(0)")     # 1.0
```

### 3. CSV Parser

```python
from grammars.csv_grammar import parse_csv, csv_to_dicts

# Parse as list of lists
rows = parse_csv('name,age\nJohn,30\nJane,25')
# [['name', 'age'], ['John', '30'], ['Jane', '25']]

# Parse with headers (returns list of dicts)
data = csv_to_dicts('name,age\nJohn,30\nJane,25')
# [{'name': 'John', 'age': '30'}, {'name': 'Jane', 'age': '25'}]
```

### 4. TOML Config Parser

```python
from grammars.toml_grammar import parse_toml

config = parse_toml('''
name = "my-app"
port = 8080
debug = true
tags = ["web", "api"]
''')
print(config['port'])  # 8080
```

### 5. YAML Parser (Flow Style)

```python
from grammars.yaml_grammar import parse_yaml

# Flow/inline style YAML
data = parse_yaml('{name: John, age: 30, active: yes}')
print(data)  # {'name': 'John', 'age': 30, 'active': True}

# Arrays
parse_yaml('[1, 2, 3, true, null]')  # [1, 2, 3, True, None]
```

## Interactive CLI

Test all parsers interactively:

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

### Example: JSON Validator
```
JSON> {"name": "John", "age": 30}
  Valid! Parsed: {'name': 'John', 'age': 30}

JSON> {"invalid": }
  Invalid!
```

### Example: Math Calculator
```
Math> 2 + 3 * 4
  = 14

Math> sqrt(16) + 2^3
  = 12.0
```

### Example: get_valid_next() Demo
```
Token> {
  Valid next: {'STRING', 'RBRACE'}

Token> "name"
  Valid next: {'COLON'}

Token> :
  Valid next: {'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL', 'LBRACE', 'LBRACKET'}
```

## LLM Constrained Decoding

```python
from grammars.json_grammar import create_json_parser

parser = create_json_parser()

# During LLM generation:
state = parser.initial_state()

# Get valid tokens at each step
valid = parser.get_valid_next(state)  # {'{', '[', 'STRING', 'NUMBER', ...}

# In your LLM loop:
# logits[invalid_tokens] = -infinity  # Mask invalid tokens
# next_token = sample(logits)
# state = parser.step(state, next_token)
```

## Build Your Own Grammar

```python
from core import Grammar, Tokenizer, Parser

# Define grammar for: variable = value;
g = Grammar("assignment")
g.terminal("ID", "EQUALS", "NUMBER", "SEMICOLON")
g.add_rule("statement", ["ID", "EQUALS", "NUMBER", "SEMICOLON"])

t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("SEMICOLON", r";")
t.add("EQUALS", r"=")
t.add("NUMBER", r"\d+")
t.add("ID", r"[a-zA-Z_]\w*")

parser = Parser(g, t)
parser.parse("x = 42;")  # True
```

## Core Components

| Component | Purpose |
|-----------|---------|
| **Grammar** | Define production rules |
| **Tokenizer** | Convert text to tokens |
| **Parser** | Parse tokens, get valid next |
| **AST** | Tree structure of parsed input |
| **Visitor** | Traverse and evaluate AST |
| **Visualizer** | Debug and display tools |

## Running Tests

```bash
# Run all tests
python -m pytest tests/test_parser.py -v

# Or without pytest
python tests/test_parser.py
```

All 28 tests passing.

## Documentation

| File | Description |
|------|-------------|
| [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) | Full project guide with all details |
| [UNDERSTANDING_THE_CORE.md](UNDERSTANDING_THE_CORE.md) | How the parser works |
| [USE_CASES_GUIDE.md](USE_CASES_GUIDE.md) | Real-world use case examples |

## How It Works

1. **Grammar** defines the language rules
2. **FIRST sets** compute what tokens can start each symbol
3. **FOLLOW sets** compute what tokens can follow each symbol
4. **Parser** uses these sets to validate and guide generation
5. **get_valid_next()** returns valid tokens at any parse state

## Use Cases Summary

| Use Case | Grammar to Use |
|----------|----------------|
| Config files | TOML, YAML |
| Data exchange | JSON, CSV |
| Math/calculations | Math |
| LLM structured output | JSON (with get_valid_next) |
| Custom DSL | Build your own |
| Validation | Any grammar |
| Autocomplete | Any grammar (use get_valid_next) |

## License

MIT License - Use freely for your projects!

---

Built as Weekend Project #2 - A reusable foundation for all parsing needs.
