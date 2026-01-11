# CFG Parser Core - Complete Guide

A simple, detailed guide to understanding the CFG Parser Core project from scratch.

---

## Table of Contents

1. [What is This Project?](#1-what-is-this-project)
2. [Key Definitions](#2-key-definitions)
3. [The Core Components](#3-the-core-components)
4. [How It All Works Together](#4-how-it-all-works-together)
5. [The Magic Function: get_valid_next()](#5-the-magic-function-get_valid_next)
6. [Built-in Grammars](#6-built-in-grammars)
7. [Code Examples](#7-code-examples)
8. [Using the CLI](#8-using-the-cli)
9. [Real-World Use Cases](#9-real-world-use-cases)
10. [Project Structure](#10-project-structure)

---

## 1. What is This Project?

### Simple Explanation

CFG Parser Core is a **parser builder**. It helps you:
- Define rules for a language (like JSON, math expressions, config files)
- Check if text follows those rules
- Know what can come next at any point

### The One-Sentence Summary

> **"Given some text and grammar rules, tell me what tokens are valid to type next."**

### Why Does This Matter?

Imagine you're typing JSON:

```
{"name": "John", |
                 ↑ cursor here
```

What can you type next?
- `"age"` - Yes, valid (another key)
- `}` - Yes, valid (close the object)
- `123` - No! A number can't come here
- `hello` - No! Unquoted text is invalid

**This parser can tell you exactly what's valid at any position.** That's the core value.

---

## 2. Key Definitions

### Grammar

**Definition:** A set of rules that define what's valid in a language.

**Example - English Grammar:**
```
sentence → subject verb object
subject  → "I" | "You" | "He"
verb     → "eat" | "see" | "like"
object   → "apples" | "cats" | "pizza"
```

Valid sentences: "I eat apples", "You like pizza"
Invalid: "eat I apples" (wrong order)

**Example - JSON Grammar:**
```
json    → object | array
object  → { pairs }
pairs   → key : value , pairs | empty
key     → STRING
value   → STRING | NUMBER | true | false | null | object | array
array   → [ elements ]
```

---

### Terminal

**Definition:** The actual characters/tokens that appear in the text. The "leaves" of the grammar tree.

**Examples:**
| Terminal | What It Matches |
|----------|-----------------|
| `STRING` | `"hello"`, `"world"`, `"123"` |
| `NUMBER` | `42`, `3.14`, `-17` |
| `LBRACE` | `{` |
| `RBRACE` | `}` |
| `COMMA` | `,` |
| `COLON` | `:` |
| `TRUE` | `true` |
| `FALSE` | `false` |

---

### Non-Terminal

**Definition:** Abstract categories that expand into other rules. The "branches" of the grammar tree.

**Examples:**
| Non-Terminal | What It Represents |
|--------------|-------------------|
| `value` | Any JSON value (string, number, object, etc.) |
| `object` | A JSON object like `{"a": 1}` |
| `array` | A JSON array like `[1, 2, 3]` |
| `pairs` | Key-value pairs inside an object |

**Visual:**
```
value (non-terminal)
  ├── STRING (terminal)      → "hello"
  ├── NUMBER (terminal)      → 42
  ├── TRUE (terminal)        → true
  ├── FALSE (terminal)       → false
  ├── NULL (terminal)        → null
  ├── object (non-terminal)  → {"a": 1}
  └── array (non-terminal)   → [1, 2]
```

---

### Token

**Definition:** A single unit of text identified by the tokenizer.

**Example:**
```
Input:  {"name": "John", "age": 30}

Tokens:
  1. LBRACE     →  {
  2. STRING     →  "name"
  3. COLON      →  :
  4. STRING     →  "John"
  5. COMMA      →  ,
  6. STRING     →  "age"
  7. COLON      →  :
  8. NUMBER     →  30
  9. RBRACE     →  }
```

---

### Tokenizer (Lexer)

**Definition:** Breaks raw text into tokens using patterns (regular expressions).

**How It Works:**
```
Input: "age": 30

Step 1: See "age" → matches STRING pattern → Token(STRING, "age")
Step 2: See :     → matches COLON pattern  → Token(COLON, ":")
Step 3: See 30    → matches NUMBER pattern → Token(NUMBER, "30")

Output: [Token(STRING), Token(COLON), Token(NUMBER)]
```

---

### Parser

**Definition:** Checks if a sequence of tokens follows the grammar rules.

**How It Works:**
```
Grammar: value → STRING | NUMBER | object
Input tokens: [STRING("hello")]

Parser:
  1. I need to match "value"
  2. "value" can be STRING, NUMBER, or object
  3. I see STRING
  4. STRING matches first option
  5. ✓ Valid!
```

---

### AST (Abstract Syntax Tree)

**Definition:** A tree structure representing the parsed text.

**Example:**
```
Input: {"name": "John"}

AST:
        object
           │
       object_body
           │
         pairs
           │
         pair
        /    \
      key    value
       │       │
    STRING  STRING
    "name"  "John"
```

---

### FIRST Set

**Definition:** The set of terminals that can appear FIRST when expanding a rule.

**Example:**
```
Grammar:
  value → object | array | STRING | NUMBER
  object → LBRACE pairs RBRACE
  array → LBRACKET elements RBRACKET

FIRST(value) = {LBRACE, LBRACKET, STRING, NUMBER}

Why?
  - value can start with object → object starts with LBRACE
  - value can start with array → array starts with LBRACKET
  - value can start with STRING
  - value can start with NUMBER
```

---

### FOLLOW Set

**Definition:** The set of terminals that can appear AFTER a non-terminal.

**Example:**
```
Grammar:
  pair → key COLON value
  pairs → pair pairs_rest
  pairs_rest → COMMA pair pairs_rest | ε

FOLLOW(value) = {COMMA, RBRACE}

Why?
  - After value in a pair, we might see COMMA (another pair)
  - After value in a pair, we might see RBRACE (end of object)
```

---

### LL(1) Parser

**Definition:** A parser that reads Left-to-right, uses Leftmost derivation, with 1 token lookahead.

**What This Means:**
- Reads input from left to right (like reading English)
- Builds the parse tree from the top down
- Only looks at 1 token ahead to decide what to do

**Example:**
```
Input: {"name": "John"}
       ↑
       Looking at this token: LBRACE

Parser thinks:
  "I see LBRACE. What rules start with LBRACE?"
  "object starts with LBRACE!"
  "I'll try to match object."
```

---

## 3. The Core Components

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CFG Parser Core                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐              │
│   │  Grammar  │    │ Tokenizer │    │  Parser   │              │
│   │           │    │           │    │           │              │
│   │ • Rules   │    │ • Patterns│    │ • Parse   │              │
│   │ • FIRST   │    │ • Tokens  │    │ • Step    │              │
│   │ • FOLLOW  │    │           │    │ • Valid   │              │
│   └───────────┘    └───────────┘    └───────────┘              │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │ get_valid   │  ← THE KEY FUNCTION           │
│                   │ _next()     │                               │
│                   └─────────────┘                               │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐              │
│   │    AST    │    │  Visitor  │    │ Visualizer│              │
│   │  Builder  │    │  Pattern  │    │           │              │
│   └───────────┘    └───────────┘    └───────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.1 Grammar (core/grammar.py)

**Purpose:** Define the rules of your language.

**Key Methods:**
```python
g = Grammar("json")

# Define what terminals exist
g.terminal("STRING", "NUMBER", "LBRACE", "RBRACE", "COLON", "COMMA")

# Define rules
g.add_rule("json", ["value"])                    # json → value
g.add_rule("value", ["STRING"], ["NUMBER"], ["object"])  # value → STRING | NUMBER | object
g.add_rule("object", ["LBRACE", "pairs", "RBRACE"])      # object → { pairs }

# Get computed sets
g.first("value")   # → {"STRING", "NUMBER", "LBRACE"}
g.follow("value")  # → {"COMMA", "RBRACE", "EOF"}
```

**Example - Complete JSON Grammar:**
```python
def create_json_grammar():
    g = Grammar("json")

    # Terminals (actual tokens)
    g.terminal(
        "LBRACE", "RBRACE",      # { }
        "LBRACKET", "RBRACKET",  # [ ]
        "COLON", "COMMA",        # : ,
        "STRING", "NUMBER",      # "hello", 123
        "TRUE", "FALSE", "NULL"  # true, false, null
    )

    # Rules (grammar structure)
    g.add_rule("json", ["value"])

    g.add_rule("value",
        ["object"],
        ["array"],
        ["STRING"],
        ["NUMBER"],
        ["TRUE"],
        ["FALSE"],
        ["NULL"]
    )

    g.add_rule("object", ["LBRACE", "object_body", "RBRACE"])
    g.add_rule("object_body", ["pairs"], [])  # pairs or empty

    g.add_rule("pairs", ["pair", "pairs_rest"])
    g.add_rule("pairs_rest", ["COMMA", "pair", "pairs_rest"], [])

    g.add_rule("pair", ["STRING", "COLON", "value"])

    g.add_rule("array", ["LBRACKET", "array_body", "RBRACKET"])
    g.add_rule("array_body", ["elements"], [])

    g.add_rule("elements", ["value", "elements_rest"])
    g.add_rule("elements_rest", ["COMMA", "value", "elements_rest"], [])

    return g
```

---

### 3.2 Tokenizer (core/tokenizer.py)

**Purpose:** Convert raw text into tokens using regex patterns.

**Key Methods:**
```python
t = Tokenizer()

# Add patterns (order matters - first match wins)
t.add("WHITESPACE", r"\s+", skip=True)  # Skip whitespace
t.add("LBRACE", r"\{")
t.add("RBRACE", r"\}")
t.add("STRING", r'"[^"]*"')
t.add("NUMBER", r"-?\d+(\.\d+)?")

# Tokenize text
tokens = t.tokenize('{"age": 30}')
# → [Token(LBRACE, "{"), Token(STRING, "age"), Token(COLON, ":"), ...]
```

**Example - Complete JSON Tokenizer:**
```python
def create_json_tokenizer():
    t = Tokenizer()

    # Skip whitespace
    t.add("WS", r"[ \t\n\r]+", skip=True)

    # Structural tokens
    t.add("LBRACE", r"\{")
    t.add("RBRACE", r"\}")
    t.add("LBRACKET", r"\[")
    t.add("RBRACKET", r"\]")
    t.add("COLON", r":")
    t.add("COMMA", r",")

    # Literals (order matters!)
    t.add("TRUE", r"true")
    t.add("FALSE", r"false")
    t.add("NULL", r"null")

    # String: "..." with escape handling
    t.add("STRING", r'"(?:[^"\\]|\\.)*"')

    # Number: integers and decimals
    t.add("NUMBER", r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")

    return t
```

---

### 3.3 Parser (core/parser.py)

**Purpose:** Use grammar + tokenizer to parse text and track state.

**Key Methods:**
```python
parser = Parser(grammar, tokenizer)

# Parse complete text
is_valid = parser.parse('{"name": "John"}')  # → True or False

# Parse to AST
ast = parser.parse_to_ast('{"name": "John"}')

# Step-by-step parsing
state = parser.initial_state()
state = parser.step(state, token)

# THE KEY FUNCTION
valid_tokens = parser.get_valid_next(state)  # → {"STRING", "RBRACE"}
```

**Example - Using the Parser:**
```python
from grammars.json_grammar import create_json_parser

parser = create_json_parser()

# Validate JSON
print(parser.parse('{"valid": true}'))   # True
print(parser.parse('{"invalid": }'))     # False

# Get valid next tokens
state = parser.initial_state()
print(parser.get_valid_next(state))
# → {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}

# Step through tokens
tokens = parser.tokenizer.tokenize('{"name":')
for token in tokens:
    if token.type != "EOF":
        state = parser.step(state, token)
        print(f"After {token.value}: valid = {parser.get_valid_next(state)}")
```

---

### 3.4 AST (core/ast.py)

**Purpose:** Represent parsed text as a tree structure.

**Structure:**
```python
class Node:
    type: str           # "object", "array", "STRING", etc.
    value: str          # For terminals: the actual text
    children: [Node]    # For non-terminals: child nodes
```

**Example:**
```python
# Parsing {"a": 1} creates:
Node(type="json", children=[
    Node(type="value", children=[
        Node(type="object", children=[
            Node(type="LBRACE", value="{"),
            Node(type="object_body", children=[
                Node(type="pairs", children=[
                    Node(type="pair", children=[
                        Node(type="STRING", value='"a"'),
                        Node(type="COLON", value=':'),
                        Node(type="value", children=[
                            Node(type="NUMBER", value='1')
                        ])
                    ])
                ])
            ]),
            Node(type="RBRACE", value="}")
        ])
    ])
])
```

---

### 3.5 Visitor (core/visitor.py)

**Purpose:** Walk the AST and extract/transform data.

**How It Works:**
```python
class MyVisitor(Visitor):
    def visit_object(self, node):
        # Called for every "object" node
        result = {}
        for child in node.children:
            if child.type == "pairs":
                # Process pairs...
        return result

    def visit_STRING(self, node):
        # Called for every STRING terminal
        return node.value[1:-1]  # Remove quotes
```

**Example - JSON Evaluator:**
```python
class JSONEvaluator(Visitor):
    def visit_json(self, node):
        return self.visit(node.children[0])

    def visit_value(self, node):
        return self.visit(node.children[0])

    def visit_object(self, node):
        result = {}
        # ... collect key-value pairs
        return result

    def visit_array(self, node):
        result = []
        # ... collect elements
        return result

    def visit_STRING(self, node):
        return node.value[1:-1]  # "hello" → hello

    def visit_NUMBER(self, node):
        return float(node.value) if '.' in node.value else int(node.value)

    def visit_TRUE(self, node):
        return True

    def visit_FALSE(self, node):
        return False

    def visit_NULL(self, node):
        return None

# Usage
ast = parser.parse_to_ast('{"name": "John", "age": 30}')
result = JSONEvaluator().visit(ast)
# → {"name": "John", "age": 30}  (Python dict)
```

---

### 3.6 Visualizer (core/visualizer.py)

**Purpose:** Display AST, parse tables, and grammar in readable format.

**Example Output:**
```
AST for: {"a": 1}
══════════════════

json
└── value
    └── object
        ├── LBRACE: {
        ├── object_body
        │   └── pairs
        │       └── pair
        │           ├── STRING: "a"
        │           ├── COLON: :
        │           └── value
        │               └── NUMBER: 1
        └── RBRACE: }
```

---

## 4. How It All Works Together

### The Complete Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         INPUT TEXT                               │
│                    '{"name": "John"}'                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         TOKENIZER                                │
│                                                                  │
│  Input: '{"name": "John"}'                                       │
│                                                                  │
│  Output: [                                                       │
│    Token(LBRACE, "{"),                                           │
│    Token(STRING, "name"),                                        │
│    Token(COLON, ":"),                                            │
│    Token(STRING, "John"),                                        │
│    Token(RBRACE, "}")                                            │
│  ]                                                               │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                          PARSER                                  │
│                                                                  │
│  Uses GRAMMAR rules + FIRST/FOLLOW sets                          │
│                                                                  │
│  For each token:                                                 │
│    1. Look at current stack top                                  │
│    2. If terminal: match token, pop stack                        │
│    3. If non-terminal: use FIRST set to pick rule, expand        │
│                                                                  │
│  Stack trace:                                                    │
│    [json]           → see LBRACE → expand json → value           │
│    [value]          → see LBRACE → expand value → object         │
│    [object]         → see LBRACE → expand object                 │
│    [LBRACE, ...]    → match LBRACE ✓                             │
│    [STRING, ...]    → match STRING "name" ✓                      │
│    ...              → continue until stack empty                 │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                           AST                                    │
│                                                                  │
│                          json                                    │
│                           │                                      │
│                         value                                    │
│                           │                                      │
│                        object                                    │
│                       /   |   \                                  │
│                   LBRACE pairs RBRACE                            │
│                      {    │      }                               │
│                         pair                                     │
│                       /   |   \                                  │
│                  STRING COLON value                              │
│                  "name"   :     │                                │
│                              STRING                              │
│                              "John"                              │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         VISITOR                                  │
│                                                                  │
│  Walks AST, transforms to Python objects:                        │
│                                                                  │
│  visit(json) → visit(value) → visit(object) →                    │
│    → collect pairs → visit(pair) →                               │
│      → key = "name", value = "John"                              │
│    → return {"name": "John"}                                     │
│                                                                  │
│  Final Result: {"name": "John"}  (Python dict)                   │
└──────────────────────────────────────────────────────────────────┘
```

---

### Step-by-Step Parsing Example

Let's trace parsing `{"a": 1}` in detail:

```
Input: {"a": 1}
Tokens: [LBRACE, STRING("a"), COLON, NUMBER(1), RBRACE]

═══════════════════════════════════════════════════════════════════

Step 1: Initial State
────────────────────
Stack: [json]
Token: LBRACE

Action: json is non-terminal
        FIRST(json) includes LBRACE (via value → object)
        Expand: json → value
Stack: [value]

═══════════════════════════════════════════════════════════════════

Step 2: Expand value
────────────────────
Stack: [value]
Token: LBRACE

Action: value is non-terminal
        LBRACE is in FIRST(object)
        Expand: value → object
Stack: [object]

═══════════════════════════════════════════════════════════════════

Step 3: Expand object
─────────────────────
Stack: [object]
Token: LBRACE

Action: object is non-terminal
        Expand: object → LBRACE object_body RBRACE
Stack: [LBRACE, object_body, RBRACE]

═══════════════════════════════════════════════════════════════════

Step 4: Match LBRACE
────────────────────
Stack: [LBRACE, object_body, RBRACE]
Token: LBRACE

Action: LBRACE is terminal, matches token!
        Pop LBRACE, consume token
Stack: [object_body, RBRACE]
Next Token: STRING("a")

═══════════════════════════════════════════════════════════════════

Step 5: Expand object_body
──────────────────────────
Stack: [object_body, RBRACE]
Token: STRING

Action: object_body is non-terminal
        STRING is in FIRST(pairs)
        Expand: object_body → pairs
Stack: [pairs, RBRACE]

═══════════════════════════════════════════════════════════════════

Step 6: Expand pairs
────────────────────
Stack: [pairs, RBRACE]
Token: STRING

Action: Expand: pairs → pair pairs_rest
Stack: [pair, pairs_rest, RBRACE]

═══════════════════════════════════════════════════════════════════

Step 7: Expand pair
───────────────────
Stack: [pair, pairs_rest, RBRACE]
Token: STRING

Action: Expand: pair → STRING COLON value
Stack: [STRING, COLON, value, pairs_rest, RBRACE]

═══════════════════════════════════════════════════════════════════

Step 8: Match STRING
────────────────────
Stack: [STRING, COLON, value, pairs_rest, RBRACE]
Token: STRING("a")

Action: STRING matches! Pop and consume.
Stack: [COLON, value, pairs_rest, RBRACE]
Next Token: COLON

═══════════════════════════════════════════════════════════════════

Step 9: Match COLON
───────────────────
Stack: [COLON, value, pairs_rest, RBRACE]
Token: COLON

Action: COLON matches! Pop and consume.
Stack: [value, pairs_rest, RBRACE]
Next Token: NUMBER(1)

═══════════════════════════════════════════════════════════════════

Step 10: Expand value (for NUMBER)
──────────────────────────────────
Stack: [value, pairs_rest, RBRACE]
Token: NUMBER

Action: NUMBER is in FIRST(value)
        Expand: value → NUMBER
Stack: [NUMBER, pairs_rest, RBRACE]

═══════════════════════════════════════════════════════════════════

Step 11: Match NUMBER
─────────────────────
Stack: [NUMBER, pairs_rest, RBRACE]
Token: NUMBER(1)

Action: NUMBER matches! Pop and consume.
Stack: [pairs_rest, RBRACE]
Next Token: RBRACE

═══════════════════════════════════════════════════════════════════

Step 12: Expand pairs_rest (epsilon)
────────────────────────────────────
Stack: [pairs_rest, RBRACE]
Token: RBRACE

Action: pairs_rest is non-terminal
        RBRACE is in FOLLOW(pairs_rest), not FIRST
        Expand: pairs_rest → ε (empty)
Stack: [RBRACE]

═══════════════════════════════════════════════════════════════════

Step 13: Match RBRACE
─────────────────────
Stack: [RBRACE]
Token: RBRACE

Action: RBRACE matches! Pop and consume.
Stack: []
Next Token: EOF

═══════════════════════════════════════════════════════════════════

Step 14: Complete!
──────────────────
Stack: []
Token: EOF

Stack is empty and we've consumed all tokens.
✓ PARSE SUCCESSFUL!
```

---

## 5. The Magic Function: get_valid_next()

### What It Does

`get_valid_next()` tells you what tokens are valid at the current parse state.

```python
state = parser.initial_state()
valid = parser.get_valid_next(state)
# → {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}
#    Any valid JSON can start with these tokens
```

### How It Works

```
get_valid_next(state):
    1. Look at the stack top
    2. If terminal → that terminal is valid
    3. If non-terminal → return FIRST(non-terminal)
    4. If epsilon is possible → also include FOLLOW set
```

### Visual Example

```
Stack: [value, pairs_rest, RBRACE]
       ↑ top

value is non-terminal
FIRST(value) = {STRING, NUMBER, TRUE, FALSE, NULL, LBRACE, LBRACKET}

get_valid_next() returns:
{STRING, NUMBER, TRUE, FALSE, NULL, LBRACE, LBRACKET}
```

### Interactive Example

```
Parsing: {"name": |
                  ↑ cursor here

Stack state: [value, pairs_rest, RBRACE]

get_valid_next() returns:
┌─────────────────────────────────────────────┐
│ Valid tokens at this position:              │
├─────────────────────────────────────────────┤
│ STRING    → "John", "hello", etc.           │
│ NUMBER    → 42, 3.14, -17                   │
│ TRUE      → true                            │
│ FALSE     → false                           │
│ NULL      → null                            │
│ LBRACE    → {  (nested object)              │
│ LBRACKET  → [  (array)                      │
└─────────────────────────────────────────────┘

NOT valid:
❌ COLON    → : (already had colon)
❌ COMMA    → , (need value first)
❌ RBRACE   → } (need value first)
```

### Why This Is Powerful

This single function enables:
- **Autocomplete** - Show valid options to users
- **Validation** - Check input character by character
- **LLM Constrained Decoding** - Force AI to generate valid syntax
- **Syntax Highlighting** - Know what's expected
- **Error Messages** - "Expected STRING, got NUMBER"

---

## 6. Built-in Grammars

### 6.1 JSON Grammar

**File:** `grammars/json_grammar.py`

**Parses:**
```json
{
  "name": "John",
  "age": 30,
  "active": true,
  "address": {
    "city": "NYC"
  },
  "tags": ["a", "b", "c"]
}
```

**Usage:**
```python
from grammars.json_grammar import parse_json, validate_json, create_json_parser

# Parse to Python dict
data = parse_json('{"name": "John", "age": 30}')
print(data)  # {'name': 'John', 'age': 30}

# Validate
print(validate_json('{"valid": true}'))   # True
print(validate_json('{"invalid": }'))     # False

# Use parser directly
parser = create_json_parser()
state = parser.initial_state()
print(parser.get_valid_next(state))  # Valid starting tokens
```

---

### 6.2 Math Grammar

**File:** `grammars/math_grammar.py`

**Parses:**
```
2 + 3 * 4
(1 + 2) * 3
sqrt(16) + sin(0)
2 ^ 10
-5 + 3
```

**Usage:**
```python
from grammars.math_grammar import evaluate

print(evaluate("2 + 3 * 4"))       # 14 (respects precedence)
print(evaluate("(2 + 3) * 4"))     # 20
print(evaluate("sqrt(16)"))        # 4.0
print(evaluate("2 ^ 10"))          # 1024
print(evaluate("sin(0) + cos(0)")) # 1.0
```

**Supported Operations:**
| Operation | Example | Result |
|-----------|---------|--------|
| Addition | `2 + 3` | `5` |
| Subtraction | `5 - 2` | `3` |
| Multiplication | `3 * 4` | `12` |
| Division | `10 / 2` | `5` |
| Power | `2 ^ 3` | `8` |
| Square root | `sqrt(16)` | `4` |
| Sine | `sin(0)` | `0` |
| Cosine | `cos(0)` | `1` |
| Tangent | `tan(0)` | `0` |
| Absolute | `abs(-5)` | `5` |

---

### 6.3 CSV Grammar

**File:** `grammars/csv_grammar.py`

**Parses:**
```csv
name,age,city
John,30,New York
Jane,25,"Los Angeles"
"Bob ""Builder""",35,Chicago
```

**Usage:**
```python
from grammars.csv_grammar import parse_csv, csv_to_dicts

csv_text = '''name,age,city
John,30,New York
Jane,25,Los Angeles'''

# Parse as list of lists
rows = parse_csv(csv_text)
print(rows)
# [['name', 'age', 'city'], ['John', '30', 'New York'], ['Jane', '25', 'Los Angeles']]

# Parse with headers (returns list of dicts)
data = csv_to_dicts(csv_text)
print(data)
# [{'name': 'John', 'age': '30', 'city': 'New York'},
#  {'name': 'Jane', 'age': '25', 'city': 'Los Angeles'}]
```

**Features:**
- Quoted fields with commas: `"New York, NY"`
- Escaped quotes: `"He said ""Hello"""`
- Empty fields: `a,,c`
- Custom delimiters: `parse_csv(text, delimiter=";")`

---

### 6.4 TOML Grammar

**File:** `grammars/toml_grammar.py`

**Parses:**
```toml
# This is a comment
title = "My Config"

[database]
host = "localhost"
port = 5432
enabled = true

[servers]
alpha = {ip = "10.0.0.1", dc = "east"}
```

**Usage:**
```python
from grammars.toml_grammar import parse_toml, validate_toml

toml_text = '''
name = "test"
count = 42
pi = 3.14159
active = true
tags = ["a", "b", "c"]
'''

data = parse_toml(toml_text)
print(data)
# {'name': 'test', 'count': 42, 'pi': 3.14159, 'active': True, 'tags': ['a', 'b', 'c']}
```

**Supported Types:**
| Type | Example |
|------|---------|
| String | `name = "John"` or `name = 'John'` |
| Integer | `count = 42`, `hex = 0xFF` |
| Float | `pi = 3.14`, `inf = inf` |
| Boolean | `active = true` |
| Array | `tags = [1, 2, 3]` |
| Inline Table | `point = {x = 1, y = 2}` |
| Date | `date = 2024-01-15` |

---

### 6.5 YAML Grammar (Flow Style)

**File:** `grammars/yaml_grammar.py`

**Parses:**
```yaml
{name: John, age: 30, active: true}
[1, 2, 3, "four", true, null]
{users: [{name: Alice}, {name: Bob}]}
```

**Note:** This parses **flow/inline style** YAML only (JSON-like). It does NOT parse indentation-based block style.

**Usage:**
```python
from grammars.yaml_grammar import parse_yaml, validate_yaml

# Simple object
data = parse_yaml('{name: John, age: 30}')
print(data)  # {'name': 'John', 'age': 30}

# Array
data = parse_yaml('[1, 2, 3, true, null]')
print(data)  # [1, 2, 3, True, None]

# Nested
data = parse_yaml('{user: {name: John, scores: [95, 87, 92]}}')
print(data)  # {'user': {'name': 'John', 'scores': [95, 87, 92]}}
```

**YAML Boolean Variations:**
| YAML | Python |
|------|--------|
| `true`, `True`, `TRUE` | `True` |
| `false`, `False`, `FALSE` | `False` |
| `yes`, `Yes`, `YES` | `True` |
| `no`, `No`, `NO` | `False` |
| `on`, `On`, `ON` | `True` |
| `off`, `Off`, `OFF` | `False` |

**YAML Null Variations:**
| YAML | Python |
|------|--------|
| `null`, `Null`, `NULL` | `None` |
| `~` | `None` |

---

## 7. Code Examples

### Example 1: Basic JSON Validation

```python
from grammars.json_grammar import create_json_parser

parser = create_json_parser()

# Validate JSON strings
test_cases = [
    '{"name": "John"}',           # Valid
    '[1, 2, 3]',                   # Valid
    '{"a": {"b": {"c": 1}}}',     # Valid - nested
    'true',                        # Valid - bare value
    '{"invalid": }',               # Invalid - missing value
    '{name: "John"}',              # Invalid - unquoted key
]

for json_str in test_cases:
    is_valid = parser.parse(json_str)
    status = "✓ Valid" if is_valid else "✗ Invalid"
    print(f"{status}: {json_str}")
```

**Output:**
```
✓ Valid: {"name": "John"}
✓ Valid: [1, 2, 3]
✓ Valid: {"a": {"b": {"c": 1}}}
✓ Valid: true
✗ Invalid: {"invalid": }
✗ Invalid: {name: "John"}
```

---

### Example 2: Step-by-Step Parsing with get_valid_next()

```python
from grammars.json_grammar import create_json_parser

parser = create_json_parser()

# Start parsing
state = parser.initial_state()
print(f"Initial valid tokens: {parser.get_valid_next(state)}")

# Tokenize input
input_text = '{"name":'
tokens = parser.tokenizer.tokenize(input_text)

# Step through each token
for token in tokens:
    if token.type == "EOF":
        continue

    print(f"\n--- Processing: {token.type} = {token.value!r} ---")
    print(f"Valid BEFORE: {parser.get_valid_next(state)}")

    state = parser.step(state, token)

    print(f"Valid AFTER:  {parser.get_valid_next(state)}")

print(f"\n--- Current position: waiting for value ---")
print(f"Can type: {parser.get_valid_next(state)}")
```

**Output:**
```
Initial valid tokens: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}

--- Processing: LBRACE = '{' ---
Valid BEFORE: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}
Valid AFTER:  {'STRING', 'RBRACE'}

--- Processing: STRING = '"name"' ---
Valid BEFORE: {'STRING', 'RBRACE'}
Valid AFTER:  {'COLON'}

--- Processing: COLON = ':' ---
Valid BEFORE: {'COLON'}
Valid AFTER:  {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}

--- Current position: waiting for value ---
Can type: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}
```

---

### Example 3: Math Expression Evaluator

```python
from grammars.math_grammar import evaluate

expressions = [
    "2 + 3",
    "2 + 3 * 4",
    "(2 + 3) * 4",
    "2 ^ 3 ^ 2",
    "sqrt(16) + sqrt(9)",
    "sin(0) + cos(0)",
    "abs(-10) + abs(10)",
    "10 / 3",
]

print("Math Expression Evaluator")
print("=" * 40)

for expr in expressions:
    result = evaluate(expr)
    print(f"{expr:25} = {result}")
```

**Output:**
```
Math Expression Evaluator
========================================
2 + 3                     = 5
2 + 3 * 4                 = 14
(2 + 3) * 4               = 20
2 ^ 3 ^ 2                 = 512
sqrt(16) + sqrt(9)        = 7.0
sin(0) + cos(0)           = 1.0
abs(-10) + abs(10)        = 20
10 / 3                    = 3.3333333333333335
```

---

### Example 4: CSV to JSON Converter

```python
from grammars.csv_grammar import csv_to_dicts
import json

csv_data = '''name,age,city,active
John Smith,30,New York,true
Jane Doe,25,Los Angeles,false
Bob Builder,35,"San Francisco, CA",true'''

# Parse CSV with headers
records = csv_to_dicts(csv_data)

# Convert to JSON
json_output = json.dumps(records, indent=2)
print(json_output)
```

**Output:**
```json
[
  {
    "name": "John Smith",
    "age": "30",
    "city": "New York",
    "active": "true"
  },
  {
    "name": "Jane Doe",
    "age": "25",
    "city": "Los Angeles",
    "active": "false"
  },
  {
    "name": "Bob Builder",
    "age": "35",
    "city": "San Francisco, CA",
    "active": "true"
  }
]
```

---

### Example 5: Building a Custom Grammar

```python
from core.grammar import Grammar
from core.tokenizer import Tokenizer
from core.parser import Parser

# Create a simple "assignment" language
# Syntax: variable = value;

# Step 1: Define Grammar
g = Grammar("assignment")
g.terminal("ID", "EQUALS", "NUMBER", "STRING", "SEMICOLON")

g.add_rule("program", ["statements"])
g.add_rule("statements", ["statement", "statements"], [])  # One or more statements
g.add_rule("statement", ["ID", "EQUALS", "value", "SEMICOLON"])
g.add_rule("value", ["NUMBER"], ["STRING"])

# Step 2: Define Tokenizer
t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("SEMICOLON", r";")
t.add("EQUALS", r"=")
t.add("NUMBER", r"\d+")
t.add("STRING", r'"[^"]*"')
t.add("ID", r"[a-zA-Z_][a-zA-Z0-9_]*")

# Step 3: Create Parser
parser = Parser(g, t)

# Step 4: Test it
test_input = 'x = 42; name = "John";'

if parser.parse(test_input):
    print("✓ Valid assignment program!")

    # Show what's valid at the start
    state = parser.initial_state()
    print(f"Program must start with: {parser.get_valid_next(state)}")
else:
    print("✗ Invalid!")
```

**Output:**
```
✓ Valid assignment program!
Program must start with: {'ID'}
```

---

### Example 6: Autocomplete Suggestion System

```python
from grammars.json_grammar import create_json_parser

def get_suggestions(partial_input: str) -> list:
    """Get autocomplete suggestions for partial JSON input."""
    parser = create_json_parser()

    try:
        # Parse what we have so far
        state = parser.initial_state()
        tokens = parser.tokenizer.tokenize(partial_input)

        for token in tokens:
            if token.type == "EOF":
                break
            state = parser.step(state, token)

        # Get valid next tokens
        valid = parser.get_valid_next(state)

        # Convert to human-readable suggestions
        suggestions = []
        for token_type in valid:
            if token_type == "STRING":
                suggestions.append('"..."')
            elif token_type == "NUMBER":
                suggestions.append("123")
            elif token_type == "TRUE":
                suggestions.append("true")
            elif token_type == "FALSE":
                suggestions.append("false")
            elif token_type == "NULL":
                suggestions.append("null")
            elif token_type == "LBRACE":
                suggestions.append("{")
            elif token_type == "RBRACE":
                suggestions.append("}")
            elif token_type == "LBRACKET":
                suggestions.append("[")
            elif token_type == "RBRACKET":
                suggestions.append("]")
            elif token_type == "COLON":
                suggestions.append(":")
            elif token_type == "COMMA":
                suggestions.append(",")

        return suggestions

    except Exception as e:
        return [f"Error: {e}"]


# Test autocomplete
test_cases = [
    '',                    # Empty - start of JSON
    '{',                   # After opening brace
    '{"name"',             # After key
    '{"name":',            # After colon
    '{"name": "John"',     # After value
    '{"name": "John",',    # After comma
]

print("JSON Autocomplete Demo")
print("=" * 50)

for partial in test_cases:
    suggestions = get_suggestions(partial)
    display = partial if partial else "(empty)"
    print(f'"{display}" → {suggestions}')
```

**Output:**
```
JSON Autocomplete Demo
==================================================
"(empty)" → ['"..."', '123', 'true', 'false', 'null', '{', '[']
"{" → ['"..."', '}']
"{"name"" → [':']
"{"name":" → ['"..."', '123', 'true', 'false', 'null', '{', '[']
"{"name": "John"" → [',', '}']
"{"name": "John"," → ['"..."']
```

---

## 8. Using the CLI

### Running the Interactive CLI

```bash
cd cfg-parser-core
python cli_test.py
```

### Main Menu

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

---

### Option 1: JSON Validator

```
JSON Validator (type 'quit' to exit)
----------------------------------------
JSON> {"name": "John"}
  Valid! Parsed: {'name': 'John'}

JSON> {"invalid": }
  Invalid!

JSON> [1, 2, 3, true, null]
  Valid! Parsed: [1, 2, 3, True, None]

JSON> quit
```

---

### Option 2: Math Calculator

```
Math Calculator (type 'quit' to exit)
Supports: +, -, *, /, ^, sqrt(), sin(), cos(), etc.
----------------------------------------
Math> 2 + 3 * 4
  = 14

Math> sqrt(16) + sqrt(9)
  = 7.0

Math> (1 + 2) * (3 + 4)
  = 21

Math> quit
```

---

### Option 3: CSV Parser

```
CSV Parser (type 'quit' to exit)
Enter CSV rows (use \n for newlines or enter multiline)
----------------------------------------
CSV> name,age,city\nJohn,30,NYC
  Parsed 2 rows:
    [0]: ['name', 'age', 'city']
    [1]: ['John', '30', 'NYC']

CSV> quit
```

---

### Option 4: TOML Parser

```
TOML Parser (type 'quit' to exit, 'example' for sample)
----------------------------------------
TOML> example
  Example: name = "test"\ncount = 42\nactive = true
  Parsed: {'name': 'test', 'count': 42, 'active': True}

TOML> port = 8080\nhost = "localhost"
  Parsed: {'port': 8080, 'host': 'localhost'}

TOML> quit
```

---

### Option 5: YAML Parser

```
YAML Parser - Flow/Inline Style (type 'quit' to exit)
Format: {key: value, key2: value2} or [1, 2, 3]
----------------------------------------
YAML> {name: John, age: 30}
  Parsed: {'name': 'John', 'age': 30}

YAML> [1, 2, true, null]
  Parsed: [1, 2, True, None]

YAML> quit
```

---

### Option 6: get_valid_next() Demo

```
get_valid_next() Demo - Choose grammar:
  1. JSON
  2. CSV
  3. TOML
  4. YAML
Grammar (1-4): 1

JSON get_valid_next() Demo
----------------------------------------
Commands: 'reset', 'quit', 'stack'
----------------------------------------
Stack: ['json']
Valid next: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}

Token> {
  Trying to feed: LBRACE = '{'
  Current stack: ['json']...
  Valid tokens: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}
  Success! New stack: ['object_body', 'RBRACE']...

Valid next: {'STRING', 'RBRACE'}

Token> "name"
  Trying to feed: STRING = '"name"'
  Success! New stack: ['COLON', 'value', 'pairs_rest', 'RBRACE']...

Valid next: {'COLON'}

Token> :
  Trying to feed: COLON = ':'
  Success! New stack: ['value', 'pairs_rest', 'RBRACE']...

Valid next: {'LBRACE', 'LBRACKET', 'STRING', 'NUMBER', 'TRUE', 'FALSE', 'NULL'}
```

---

## 9. Real-World Use Cases

### Use Case 1: LLM Constrained Decoding

**Problem:** LLMs can generate invalid JSON
**Solution:** Use `get_valid_next()` to mask invalid tokens

```python
# Concept (pseudocode)
def generate_valid_json(llm, prompt):
    parser = create_json_parser()
    state = parser.initial_state()
    output = ""

    while not state.is_complete():
        # Get valid tokens from grammar
        valid = parser.get_valid_next(state)

        # Ask LLM for next token, but mask invalid ones
        next_token = llm.generate(
            prompt + output,
            allowed_tokens=valid  # Only allow valid tokens!
        )

        output += next_token
        state = parser.step(state, next_token)

    return output  # Guaranteed valid JSON!
```

---

### Use Case 2: Syntax-Aware Autocomplete

**Problem:** IDE needs to suggest valid completions
**Solution:** Use `get_valid_next()` to know what's valid

```python
def autocomplete(code_so_far):
    parser = create_json_parser()
    state = parse_partial(code_so_far)
    valid = parser.get_valid_next(state)

    suggestions = []
    if "STRING" in valid:
        suggestions.append('""')
    if "NUMBER" in valid:
        suggestions.append("0")
    if "LBRACE" in valid:
        suggestions.append("{}")
    # ... etc

    return suggestions
```

---

### Use Case 3: Real-Time Validation

**Problem:** Validate user input as they type
**Solution:** Parse incrementally, report errors immediately

```python
def validate_realtime(partial_input):
    parser = create_json_parser()
    state = parser.initial_state()

    for char in partial_input:
        try:
            tokens = parser.tokenizer.tokenize(char)
            for token in tokens:
                state = parser.step(state, token)
        except ParseError as e:
            return {"valid": False, "error": str(e)}

    return {
        "valid": True,
        "complete": state.is_complete(),
        "expecting": parser.get_valid_next(state)
    }
```

---

### Use Case 4: Config File Parser

**Problem:** Parse application configuration
**Solution:** Use TOML/YAML grammar

```python
from grammars.toml_grammar import parse_toml

config_text = '''
[server]
host = "localhost"
port = 8080

[database]
url = "postgres://localhost/mydb"
pool_size = 10
'''

config = parse_toml(config_text)
print(config['server']['host'])  # localhost
print(config['database']['pool_size'])  # 10
```

---

### Use Case 5: Data Format Converter

**Problem:** Convert between formats
**Solution:** Parse with one grammar, output with another

```python
from grammars.csv_grammar import csv_to_dicts
from grammars.json_grammar import parse_json
import json

# CSV to JSON
csv_data = "name,age\nJohn,30\nJane,25"
records = csv_to_dicts(csv_data)
json_output = json.dumps(records)

# JSON to YAML-like
json_data = '{"name": "John", "age": 30}'
data = parse_json(json_data)
yaml_output = "{" + ", ".join(f"{k}: {v}" for k, v in data.items()) + "}"
```

---

## 10. Project Structure

```
cfg-parser-core/
│
├── core/                       # Core parsing engine
│   ├── __init__.py
│   ├── grammar.py              # Grammar definition, FIRST/FOLLOW
│   ├── tokenizer.py            # Regex-based tokenization
│   ├── parser.py               # LL(1) parser, get_valid_next()
│   ├── ast.py                  # AST node structure
│   ├── visitor.py              # Visitor pattern base class
│   └── visualizer.py           # Pretty-print AST and tables
│
├── grammars/                   # Pre-built grammars
│   ├── __init__.py
│   ├── json_grammar.py         # JSON parser
│   ├── math_grammar.py         # Math expression evaluator
│   ├── csv_grammar.py          # CSV parser
│   ├── toml_grammar.py         # TOML config parser
│   └── yaml_grammar.py         # YAML flow-style parser
│
├── examples/                   # Usage examples
│   ├── 01_basic_parsing.py
│   ├── 02_json_parsing.py
│   ├── 03_math_expressions.py
│   ├── 04_llm_constrained_decoding.py
│   └── 05_build_custom_dsl.py
│
├── tests/                      # Unit tests
│   └── test_parser.py          # 28 comprehensive tests
│
├── cli_test.py                 # Interactive CLI tool
│
├── COMPLETE_GUIDE.md           # This file
├── FUTURE_ENHANCEMENTS.md      # Optional enhancements
├── UNDERSTANDING_THE_CORE.md   # Core concepts explanation
├── USE_CASES_GUIDE.md          # Use case examples
│
└── README.md                   # Project overview
```

---

## Quick Reference

### Import Shortcuts

```python
# JSON
from grammars.json_grammar import parse_json, validate_json, create_json_parser

# Math
from grammars.math_grammar import evaluate

# CSV
from grammars.csv_grammar import parse_csv, csv_to_dicts

# TOML
from grammars.toml_grammar import parse_toml, validate_toml

# YAML
from grammars.yaml_grammar import parse_yaml, validate_yaml
```

### Common Operations

```python
# Create parser
parser = create_json_parser()

# Validate text
is_valid = parser.parse('{"a": 1}')

# Parse to Python object
data = parse_json('{"a": 1}')

# Get valid next tokens
state = parser.initial_state()
valid = parser.get_valid_next(state)

# Step-by-step parsing
state = parser.step(state, token)

# Check if complete
if state.is_complete():
    print("Done!")
```

---

## Summary

CFG Parser Core is a **reusable parsing toolkit** that:

1. **Defines grammars** - Rules for what's valid
2. **Tokenizes input** - Breaks text into tokens
3. **Parses tokens** - Checks if they follow rules
4. **Builds ASTs** - Creates tree structures
5. **Tells you what's next** - The key `get_valid_next()` function

The core insight: **`get_valid_next()` is the magic function** that enables autocomplete, validation, constrained decoding, and more.

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   Grammar + Parser + get_valid_next()           │
│                    ↓                            │
│   "What tokens are valid at this position?"     │
│                    ↓                            │
│   Autocomplete, Validation, LLM Constraints     │
│                                                 │
└─────────────────────────────────────────────────┘
```

That's the entire project in a nutshell!
