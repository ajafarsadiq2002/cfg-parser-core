# CFG Parser Core - Use Cases Guide

Practical examples showing how to use this parser in real-world scenarios.

---

## Table of Contents

1. [LLM Constrained Decoding](#1-llm-constrained-decoding) - Force AI to generate valid output
2. [JSON Parsing & Validation](#2-json-parsing--validation) - Parse and validate JSON
3. [Math Expression Evaluator](#3-math-expression-evaluator) - Calculator with variables
4. [Building a DSL](#4-building-a-dsl) - Create your own mini-language
5. [Autocomplete System](#5-autocomplete-system) - Suggest valid completions
6. [Form Validation](#6-form-validation) - Validate complex input patterns
7. [SQL Query Builder](#7-sql-query-builder) - Safe query construction
8. [Config File Parser](#8-config-file-parser) - Custom config format

---

## 1. LLM Constrained Decoding

**The Problem:** LLMs can generate invalid JSON, broken code, or malformed output.

**The Solution:** Use `get_valid_next()` to mask invalid tokens during generation.

### How It Works

```
Normal LLM:        "Generate JSON" --> {"name": "John,  age: 25}  (BROKEN!)

Constrained LLM:   "Generate JSON" --> {"name": "John", "age": 25}  (VALID!)
                                        ^
                                        At each step, we only allow valid tokens
```

### Complete Example

```python
from core import Grammar, Tokenizer, Parser
from grammars.json_grammar import create_json_parser

# Create JSON parser
parser = create_json_parser()

# Simulate LLM vocabulary (in reality, this comes from the model)
vocab = {
    0: "{", 1: "}", 2: "[", 3: "]", 4: ":", 5: ",",
    6: '"name"', 7: '"age"', 8: '"city"',
    9: '"John"', 10: '"25"', 11: "true", 12: "false", 13: "null"
}

def get_valid_token_ids(parser, state, vocab):
    """Get which token IDs are valid given current state."""
    valid_terminals = parser.get_valid_next(state)
    valid_ids = []

    for token_id, token_str in vocab.items():
        # Map vocab tokens to grammar terminals
        if token_str in ["{", "}", "[", "]", ":", ","]:
            if token_str in valid_terminals:
                valid_ids.append(token_id)
        elif token_str.startswith('"'):
            if "STRING" in valid_terminals:
                valid_ids.append(token_id)
        elif token_str in ["true", "false"]:
            if "BOOLEAN" in valid_terminals:
                valid_ids.append(token_id)
        elif token_str == "null":
            if "NULL" in valid_terminals:
                valid_ids.append(token_id)

    return valid_ids

def constrained_generate(parser, vocab, max_tokens=20):
    """Generate valid JSON token by token."""
    state = parser.initial_state()
    generated = []

    for _ in range(max_tokens):
        # Get valid tokens
        valid_ids = get_valid_token_ids(parser, state, vocab)

        if not valid_ids:
            break

        # In real LLM: mask invalid tokens, sample from valid ones
        # Here we just pick the first valid token for demo
        chosen_id = valid_ids[0]
        chosen_token = vocab[chosen_id]

        generated.append(chosen_token)

        # Update parser state
        token = parser.tokenizer.tokenize(chosen_token)[0]
        state = parser.step(state, token)

        # Check if complete
        if state.is_complete():
            break

    return " ".join(generated)

# Generate valid JSON!
result = constrained_generate(parser, vocab)
print(result)  # Always valid JSON structure
```

### Integration with Real LLMs

```python
import torch

def apply_grammar_mask(logits, parser, state, vocab, tokenizer):
    """Apply grammar constraints to LLM logits."""
    valid_terminals = parser.get_valid_next(state)

    # Create mask (True = allowed, False = blocked)
    mask = torch.zeros(len(vocab), dtype=torch.bool)

    for token_id, token_str in vocab.items():
        terminal = map_to_terminal(token_str)  # Your mapping function
        if terminal in valid_terminals:
            mask[token_id] = True

    # Apply mask: set invalid tokens to -infinity
    logits[~mask] = float('-inf')

    return logits

# In your generation loop:
# logits = model(input_ids)
# logits = apply_grammar_mask(logits, parser, state, vocab, tokenizer)
# next_token = torch.argmax(logits)
```

---

## 2. JSON Parsing & Validation

### Validate JSON

```python
from grammars.json_grammar import validate_json, parse_json

# Validation
print(validate_json('{"name": "John", "age": 25}'))  # True
print(validate_json('{"broken": }'))                  # False
print(validate_json('[1, 2, 3]'))                     # True
print(validate_json('{"nested": {"a": [1,2]}}'))     # True

# Parse to Python object
data = parse_json('{"users": [{"name": "Alice"}, {"name": "Bob"}]}')
print(data)  # {'users': [{'name': 'Alice'}, {'name': 'Bob'}]}
```

### Custom JSON Validator with Error Messages

```python
from grammars.json_grammar import create_json_parser
from core.errors import ParseError

def validate_with_errors(json_string):
    """Validate JSON and return helpful error messages."""
    parser = create_json_parser()

    try:
        tokens = parser.tokenizer.tokenize(json_string)
        state = parser.initial_state()

        for token in tokens:
            if token.type == "EOF":
                break

            valid = parser.get_valid_next(state)

            if token.type not in valid:
                return {
                    "valid": False,
                    "error": f"Unexpected '{token.value}' at line {token.line}, col {token.column}",
                    "expected": list(valid),
                    "found": token.type
                }

            state = parser.step(state, token)

        return {"valid": True}

    except Exception as e:
        return {"valid": False, "error": str(e)}

# Test
result = validate_with_errors('{"name": }')
print(result)
# {'valid': False, 'error': "Unexpected '}' at line 1, col 10",
#  'expected': ['STRING', 'NUMBER', '{', '[', 'true', 'false', 'null'],
#  'found': '}'}
```

---

## 3. Math Expression Evaluator

### Basic Calculator

```python
from grammars.math_grammar import evaluate

# Basic operations
print(evaluate("2 + 3"))           # 5.0
print(evaluate("10 - 4 * 2"))      # 2.0  (respects precedence)
print(evaluate("(10 - 4) * 2"))    # 12.0

# Powers and roots
print(evaluate("2 ^ 10"))          # 1024.0
print(evaluate("sqrt(144)"))       # 12.0

# Functions
print(evaluate("sin(0)"))          # 0.0
print(evaluate("cos(0)"))          # 1.0
print(evaluate("abs(-5)"))         # 5.0
print(evaluate("max(3, 7, 2)"))    # 7.0
```

### Calculator with Variables

```python
from grammars.math_grammar import evaluate

# Define variables
variables = {
    "x": 10,
    "y": 5,
    "pi": 3.14159,
    "tax_rate": 0.08
}

# Use variables in expressions
print(evaluate("x + y", variables))              # 15.0
print(evaluate("x * y + 2", variables))          # 52.0
print(evaluate("2 * pi * 5", variables))         # 31.4159
print(evaluate("price * (1 + tax_rate)", {"price": 100, **variables}))  # 108.0
```

### Build Your Own Calculator

```python
from core import Grammar, Tokenizer, Parser
from core.visitor import Visitor
from core.ast import Node

# Step 1: Define grammar
g = Grammar("expr")
g.terminal("NUMBER", "+", "-", "*", "/", "(", ")")

# expr -> term (('+' | '-') term)*
# term -> factor (('*' | '/') factor)*
# factor -> NUMBER | '(' expr ')'

# LL(1) compatible form:
g.add_rule("expr", ["term", "expr_rest"])
g.add_rule("expr_rest", ["+", "term", "expr_rest"], ["-", "term", "expr_rest"], [])
g.add_rule("term", ["factor", "term_rest"])
g.add_rule("term_rest", ["*", "factor", "term_rest"], ["/", "factor", "term_rest"], [])
g.add_rule("factor", ["NUMBER"], ["(", "expr", ")"])

# Step 2: Create tokenizer
t = Tokenizer()
t.add("NUMBER", r"\d+\.?\d*")
t.add("+", r"\+")
t.add("-", r"-")
t.add("*", r"\*")
t.add("/", r"/")
t.add("(", r"\(")
t.add(")", r"\)")
t.add("WS", r"\s+", skip=True)

# Step 3: Create evaluator
class Evaluator(Visitor):
    def visit_NUMBER(self, node):
        return float(node.value)

    def visit_expr(self, node):
        result = self.visit(node.children[0])  # term
        return self._process_rest(result, node.children[1], ['+', '-'])

    def visit_term(self, node):
        result = self.visit(node.children[0])  # factor
        return self._process_rest(result, node.children[1], ['*', '/'])

    def visit_factor(self, node):
        if node.children[0].type == "NUMBER":
            return self.visit(node.children[0])
        else:  # ( expr )
            return self.visit(node.children[1])

    def _process_rest(self, left, rest_node, ops):
        if not rest_node.children:
            return left
        op = rest_node.children[0].value
        right = self.visit(rest_node.children[1])

        if op == '+': result = left + right
        elif op == '-': result = left - right
        elif op == '*': result = left * right
        elif op == '/': result = left / right

        # Continue with more operations
        if len(rest_node.children) > 2:
            return self._process_rest(result, rest_node.children[2], ops)
        return result

# Step 4: Use it!
parser = Parser(g, t)
evaluator = Evaluator()

def calculate(expression):
    ast = parser.parse_to_ast(expression)
    return evaluator.visit(ast)

print(calculate("2 + 3 * 4"))      # 14.0
print(calculate("(2 + 3) * 4"))    # 20.0
print(calculate("100 / 4 / 5"))    # 5.0
```

---

## 4. Building a DSL

### Example: Task Definition Language

Create a simple language for defining tasks:

```
task "Deploy App" {
    depends_on "Build"
    depends_on "Test"
    run "docker push myapp"
    timeout 300
}
```

```python
from core import Grammar, Tokenizer, Parser
from core.visitor import Visitor

# Step 1: Define the grammar
g = Grammar("program")
g.terminal("TASK", "DEPENDS_ON", "RUN", "TIMEOUT",
           "STRING", "NUMBER", "{", "}")

g.add_rule("program", ["task_list"])
g.add_rule("task_list", ["task", "task_list"], [])
g.add_rule("task", ["TASK", "STRING", "{", "statements", "}"])
g.add_rule("statements", ["statement", "statements"], [])
g.add_rule("statement",
    ["DEPENDS_ON", "STRING"],
    ["RUN", "STRING"],
    ["TIMEOUT", "NUMBER"]
)

# Step 2: Create tokenizer
t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("TASK", r"task")
t.add("DEPENDS_ON", r"depends_on")
t.add("RUN", r"run")
t.add("TIMEOUT", r"timeout")
t.add("STRING", r'"[^"]*"')
t.add("NUMBER", r"\d+")
t.add("{", r"\{")
t.add("}", r"\}")

# Step 3: Create interpreter
class TaskInterpreter(Visitor):
    def __init__(self):
        self.tasks = {}

    def visit_program(self, node):
        self.visit(node.children[0])  # task_list
        return self.tasks

    def visit_task_list(self, node):
        for child in node.children:
            self.visit(child)

    def visit_task(self, node):
        name = node.children[1].value.strip('"')
        self.tasks[name] = {
            "depends_on": [],
            "commands": [],
            "timeout": None
        }
        self._current_task = name
        self.visit(node.children[3])  # statements

    def visit_statements(self, node):
        for child in node.children:
            self.visit(child)

    def visit_statement(self, node):
        stmt_type = node.children[0].type
        value = node.children[1].value

        if stmt_type == "DEPENDS_ON":
            self.tasks[self._current_task]["depends_on"].append(value.strip('"'))
        elif stmt_type == "RUN":
            self.tasks[self._current_task]["commands"].append(value.strip('"'))
        elif stmt_type == "TIMEOUT":
            self.tasks[self._current_task]["timeout"] = int(value)

# Step 4: Use it!
parser = Parser(g, t)
interpreter = TaskInterpreter()

dsl_code = '''
task "Build" {
    run "npm install"
    run "npm run build"
    timeout 600
}

task "Deploy" {
    depends_on "Build"
    run "docker push myapp"
    timeout 300
}
'''

ast = parser.parse_to_ast(dsl_code)
tasks = interpreter.visit(ast)

print(tasks)
# {
#   'Build': {'depends_on': [], 'commands': ['npm install', 'npm run build'], 'timeout': 600},
#   'Deploy': {'depends_on': ['Build'], 'commands': ['docker push myapp'], 'timeout': 300}
# }
```

### Example: Query Language

```python
# A simple query language: "SELECT name, age FROM users WHERE age > 25"

g = Grammar("query")
g.terminal("SELECT", "FROM", "WHERE", "AND", "OR",
           "IDENT", "NUMBER", "STRING", ",", ">", "<", "=", ">=", "<=")

g.add_rule("query", ["SELECT", "columns", "FROM", "IDENT", "where_clause"])
g.add_rule("columns", ["IDENT", "more_columns"])
g.add_rule("more_columns", [",", "IDENT", "more_columns"], [])
g.add_rule("where_clause", ["WHERE", "condition"], [])
g.add_rule("condition", ["IDENT", "operator", "value"])
g.add_rule("operator", [">"], ["<"], ["="], [">="], ["<="])
g.add_rule("value", ["NUMBER"], ["STRING"])

t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("SELECT", r"SELECT|select")
t.add("FROM", r"FROM|from")
t.add("WHERE", r"WHERE|where")
t.add(">=", r">=")
t.add("<=", r"<=")
t.add(">", r">")
t.add("<", r"<")
t.add("=", r"=")
t.add(",", r",")
t.add("NUMBER", r"\d+")
t.add("STRING", r"'[^']*'")
t.add("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")

parser = Parser(g, t)

# Validate queries
print(parser.parse("SELECT name, age FROM users"))  # True
print(parser.parse("SELECT name FROM users WHERE age > 25"))  # True
print(parser.parse("SELECT FROM users"))  # False (missing columns)
```

---

## 5. Autocomplete System

### Terminal Autocomplete

```python
from core import Grammar, Tokenizer, Parser

# Grammar for shell commands
g = Grammar("command")
g.terminal("CMD", "FLAG", "PATH", "PIPE", "AND", "OR")

g.add_rule("command", ["CMD", "args", "pipe_chain"])
g.add_rule("args", ["arg", "args"], [])
g.add_rule("arg", ["FLAG"], ["PATH"])
g.add_rule("pipe_chain", ["PIPE", "command"], ["AND", "command"], ["OR", "command"], [])

t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("PIPE", r"\|")
t.add("AND", r"&&")
t.add("OR", r"\|\|")
t.add("FLAG", r"-[a-zA-Z]+")
t.add("CMD", r"(ls|cat|grep|echo|cd|mkdir|rm)")
t.add("PATH", r"[a-zA-Z0-9_./-]+")

parser = Parser(g, t)

def get_completions(partial_input):
    """Get valid completions for partial input."""
    try:
        # Tokenize what we have so far
        tokens = t.tokenize(partial_input)
        tokens = [tok for tok in tokens if tok.type != "EOF"]

        # Walk through tokens to get current state
        state = parser.initial_state()
        for token in tokens:
            try:
                state = parser.step(state, token)
            except:
                return []

        # Get valid next tokens
        valid = parser.get_valid_next(state)

        # Map to user-friendly suggestions
        suggestions = []
        if "CMD" in valid:
            suggestions.extend(["ls", "cat", "grep", "echo", "cd", "mkdir", "rm"])
        if "FLAG" in valid:
            suggestions.extend(["-l", "-a", "-r", "-v", "-h"])
        if "PATH" in valid:
            suggestions.append("<path>")
        if "PIPE" in valid:
            suggestions.append("|")
        if "AND" in valid:
            suggestions.append("&&")
        if "EOF" in valid:
            suggestions.append("<enter>")

        return suggestions
    except:
        return []

# Test autocomplete
print(get_completions(""))           # ['ls', 'cat', 'grep', ...] - commands
print(get_completions("ls"))         # ['-l', '-a', ..., '<path>', '|', '&&', '<enter>']
print(get_completions("ls -la"))     # ['-l', ..., '<path>', '|', '&&', '<enter>']
print(get_completions("ls |"))       # ['ls', 'cat', 'grep', ...] - commands after pipe
```

### Code Editor Autocomplete

```python
def get_code_completions(code, cursor_position):
    """Get completions for code at cursor position."""
    # Get text up to cursor
    text_before_cursor = code[:cursor_position]

    # Parse to get state
    state = parser.initial_state()
    try:
        tokens = tokenizer.tokenize(text_before_cursor)
        for token in tokens:
            if token.type != "EOF":
                state = parser.step(state, token)
    except:
        pass

    # Get valid completions
    valid = parser.get_valid_next(state)

    # Return completions with documentation
    completions = []
    for terminal in valid:
        completions.append({
            "label": terminal,
            "kind": "keyword" if terminal.isupper() else "symbol",
            "documentation": get_doc_for_terminal(terminal)
        })

    return completions
```

---

## 6. Form Validation

### Email Pattern Validation

```python
from core import Grammar, Tokenizer, Parser

# Grammar for email: local@domain.tld
g = Grammar("email")
g.terminal("LOCAL_PART", "AT", "DOMAIN", "DOT", "TLD")

g.add_rule("email", ["LOCAL_PART", "AT", "domain_part"])
g.add_rule("domain_part", ["DOMAIN", "DOT", "tld_part"])
g.add_rule("tld_part", ["TLD"], ["DOMAIN", "DOT", "tld_part"])

t = Tokenizer()
t.add("AT", r"@")
t.add("DOT", r"\.")
t.add("TLD", r"(com|org|net|edu|io|co)")
t.add("LOCAL_PART", r"[a-zA-Z0-9._%+-]+")
t.add("DOMAIN", r"[a-zA-Z0-9-]+")

parser = Parser(g, t)

def validate_email(email):
    return parser.parse(email)

print(validate_email("user@example.com"))      # True
print(validate_email("test.user@mail.co"))     # True
print(validate_email("invalid"))               # False
print(validate_email("no@dots"))               # False
```

### Phone Number Validation

```python
# Grammar for US phone: (123) 456-7890 or 123-456-7890
g = Grammar("phone")
g.terminal("DIGIT", "LPAREN", "RPAREN", "DASH", "SPACE")

g.add_rule("phone",
    ["LPAREN", "area", "RPAREN", "SPACE", "exchange", "DASH", "subscriber"],
    ["area", "DASH", "exchange", "DASH", "subscriber"]
)
g.add_rule("area", ["DIGIT", "DIGIT", "DIGIT"])
g.add_rule("exchange", ["DIGIT", "DIGIT", "DIGIT"])
g.add_rule("subscriber", ["DIGIT", "DIGIT", "DIGIT", "DIGIT"])

t = Tokenizer()
t.add("LPAREN", r"\(")
t.add("RPAREN", r"\)")
t.add("DASH", r"-")
t.add("SPACE", r" ")
t.add("DIGIT", r"\d")

parser = Parser(g, t)

print(parser.parse("(123) 456-7890"))  # True
print(parser.parse("123-456-7890"))    # True
print(parser.parse("1234567890"))      # False
```

### Complex Form Field

```python
# Validate a version string: v1.2.3, v1.2.3-beta, v1.2.3-rc.1

g = Grammar("version")
g.terminal("V", "NUMBER", "DOT", "DASH", "PRERELEASE")

g.add_rule("version", ["V", "NUMBER", "DOT", "NUMBER", "DOT", "NUMBER", "prerelease"])
g.add_rule("prerelease", ["DASH", "PRERELEASE", "prerelease_num"], [])
g.add_rule("prerelease_num", ["DOT", "NUMBER"], [])

t = Tokenizer()
t.add("V", r"v")
t.add("DOT", r"\.")
t.add("DASH", r"-")
t.add("PRERELEASE", r"(alpha|beta|rc)")
t.add("NUMBER", r"\d+")

parser = Parser(g, t)

versions = ["v1.0.0", "v2.1.3", "v1.0.0-beta", "v2.0.0-rc.1", "1.0.0", "v1.0"]
for v in versions:
    print(f"{v}: {parser.parse(v)}")
# v1.0.0: True
# v2.1.3: True
# v1.0.0-beta: True
# v2.0.0-rc.1: True
# 1.0.0: False (missing v)
# v1.0: False (missing patch)
```

---

## 7. SQL Query Builder

### Safe Query Construction

```python
from core import Grammar, Tokenizer, Parser

# Grammar ensures only valid SQL structure
g = Grammar("query")
g.terminal("SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "INTO", "SET", "WHERE",
           "VALUES", "AND", "OR", "IDENT", "VALUE", "COMMA", "EQ", "LPAREN", "RPAREN", "STAR")

g.add_rule("query", ["select_stmt"], ["insert_stmt"], ["update_stmt"], ["delete_stmt"])

# SELECT columns FROM table WHERE condition
g.add_rule("select_stmt", ["SELECT", "select_cols", "FROM", "IDENT", "where_clause"])
g.add_rule("select_cols", ["STAR"], ["col_list"])
g.add_rule("col_list", ["IDENT", "more_cols"])
g.add_rule("more_cols", ["COMMA", "IDENT", "more_cols"], [])

# INSERT INTO table (cols) VALUES (vals)
g.add_rule("insert_stmt", ["INSERT", "INTO", "IDENT", "LPAREN", "col_list", "RPAREN",
                           "VALUES", "LPAREN", "val_list", "RPAREN"])
g.add_rule("val_list", ["VALUE", "more_vals"])
g.add_rule("more_vals", ["COMMA", "VALUE", "more_vals"], [])

# WHERE clause
g.add_rule("where_clause", ["WHERE", "condition"], [])
g.add_rule("condition", ["IDENT", "EQ", "VALUE", "more_conditions"])
g.add_rule("more_conditions", ["AND", "condition"], ["OR", "condition"], [])

# UPDATE table SET col=val WHERE condition
g.add_rule("update_stmt", ["UPDATE", "IDENT", "SET", "assignments", "where_clause"])
g.add_rule("assignments", ["IDENT", "EQ", "VALUE", "more_assignments"])
g.add_rule("more_assignments", ["COMMA", "IDENT", "EQ", "VALUE", "more_assignments"], [])

# DELETE FROM table WHERE condition
g.add_rule("delete_stmt", ["DELETE", "FROM", "IDENT", "where_clause"])

t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("SELECT", r"SELECT")
t.add("INSERT", r"INSERT")
t.add("UPDATE", r"UPDATE")
t.add("DELETE", r"DELETE")
t.add("FROM", r"FROM")
t.add("INTO", r"INTO")
t.add("SET", r"SET")
t.add("WHERE", r"WHERE")
t.add("VALUES", r"VALUES")
t.add("AND", r"AND")
t.add("OR", r"OR")
t.add("STAR", r"\*")
t.add("COMMA", r",")
t.add("EQ", r"=")
t.add("LPAREN", r"\(")
t.add("RPAREN", r"\)")
t.add("VALUE", r"'[^']*'|\d+")
t.add("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")

parser = Parser(g, t)

# Validate SQL queries
queries = [
    "SELECT * FROM users",
    "SELECT name, age FROM users WHERE id = 1",
    "INSERT INTO users (name, age) VALUES ('John', 25)",
    "UPDATE users SET name = 'Jane' WHERE id = 1",
    "DELETE FROM users WHERE id = 1",
    "SELECT * FROM; DROP TABLE users;--",  # SQL injection attempt!
]

for q in queries:
    valid = parser.parse(q)
    print(f"{'VALID' if valid else 'INVALID'}: {q}")

# VALID: SELECT * FROM users
# VALID: SELECT name, age FROM users WHERE id = 1
# VALID: INSERT INTO users (name, age) VALUES ('John', 25)
# VALID: UPDATE users SET name = 'Jane' WHERE id = 1
# VALID: DELETE FROM users WHERE id = 1
# INVALID: SELECT * FROM; DROP TABLE users;--   <-- Injection blocked!
```

---

## 8. Config File Parser

### Custom Config Format

Parse config files like:

```
server {
    host = "localhost"
    port = 8080
    ssl = true
}

database {
    url = "postgres://localhost/mydb"
    pool_size = 10
}
```

```python
from core import Grammar, Tokenizer, Parser
from core.visitor import Visitor

# Grammar
g = Grammar("config")
g.terminal("IDENT", "STRING", "NUMBER", "BOOLEAN",
           "LBRACE", "RBRACE", "EQ")

g.add_rule("config", ["sections"])
g.add_rule("sections", ["section", "sections"], [])
g.add_rule("section", ["IDENT", "LBRACE", "properties", "RBRACE"])
g.add_rule("properties", ["property", "properties"], [])
g.add_rule("property", ["IDENT", "EQ", "value"])
g.add_rule("value", ["STRING"], ["NUMBER"], ["BOOLEAN"])

# Tokenizer
t = Tokenizer()
t.add("WS", r"\s+", skip=True)
t.add("COMMENT", r"#[^\n]*", skip=True)
t.add("BOOLEAN", r"(true|false)")
t.add("NUMBER", r"\d+")
t.add("STRING", r'"[^"]*"')
t.add("LBRACE", r"\{")
t.add("RBRACE", r"\}")
t.add("EQ", r"=")
t.add("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")

# Config interpreter
class ConfigInterpreter(Visitor):
    def visit_config(self, node):
        return self.visit(node.children[0])

    def visit_sections(self, node):
        result = {}
        for child in node.children:
            section = self.visit(child)
            result.update(section)
        return result

    def visit_section(self, node):
        name = node.children[0].value
        props = self.visit(node.children[2])
        return {name: props}

    def visit_properties(self, node):
        result = {}
        for child in node.children:
            key, value = self.visit(child)
            result[key] = value
        return result

    def visit_property(self, node):
        key = node.children[0].value
        value = self.visit(node.children[2])
        return (key, value)

    def visit_value(self, node):
        child = node.children[0]
        if child.type == "STRING":
            return child.value.strip('"')
        elif child.type == "NUMBER":
            return int(child.value)
        elif child.type == "BOOLEAN":
            return child.value == "true"

# Use it
parser = Parser(g, t)
interpreter = ConfigInterpreter()

config_text = '''
# Server configuration
server {
    host = "localhost"
    port = 8080
    ssl = true
}

database {
    url = "postgres://localhost/mydb"
    pool_size = 10
}
'''

ast = parser.parse_to_ast(config_text)
config = interpreter.visit(ast)

print(config)
# {
#     'server': {'host': 'localhost', 'port': 8080, 'ssl': True},
#     'database': {'url': 'postgres://localhost/mydb', 'pool_size': 10}
# }

# Access config values
print(config['server']['port'])  # 8080
print(config['database']['url'])  # postgres://localhost/mydb
```

---

## Summary

| Use Case | Key Function | What It Does |
|----------|--------------|--------------|
| **LLM Constraining** | `get_valid_next()` | Mask invalid tokens during generation |
| **JSON Validation** | `parse()` | Check if JSON is valid |
| **Math Evaluation** | `parse_to_ast()` + Visitor | Parse and compute expressions |
| **Building DSLs** | Grammar + Interpreter | Create custom languages |
| **Autocomplete** | `get_valid_next()` | Suggest valid completions |
| **Form Validation** | `parse()` | Validate complex input patterns |
| **Query Building** | `parse()` | Ensure valid SQL structure |
| **Config Parsing** | `parse_to_ast()` + Visitor | Parse custom config formats |

The power is in combining:
1. **Grammar** - Define what's valid
2. **Parser** - Check validity
3. **get_valid_next()** - Know what's valid next
4. **AST + Visitor** - Process the parsed structure
