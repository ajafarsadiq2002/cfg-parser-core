"""
Example 1: Basic Parsing

Demonstrates the fundamental parsing operations:
- Creating a grammar
- Creating a tokenizer
- Parsing input
- Getting valid next tokens
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import Grammar, Tokenizer, Parser


def main():
    print("=" * 60)
    print("Example 1: Basic Parsing")
    print("=" * 60)

    # Step 1: Create a simple grammar
    # This grammar recognizes: "hello" or "hello world"
    # Note: We use LL(1) form to avoid conflicts
    print("\n1. Creating Grammar")
    print("-" * 40)

    grammar = Grammar("greeting")
    grammar.terminal("HELLO", "WORLD")
    # LL(1) form: factor out common prefix
    grammar.add_rule("greeting",
        ["HELLO", "greeting_rest"]
    )
    grammar.add_rule("greeting_rest",
        ["WORLD"],  # hello world
        []          # just hello (epsilon)
    )

    print("Grammar created:")
    print(f"  Start: {grammar.start}")
    print(f"  Terminals: {grammar.terminals}")
    print(f"  Rules: greeting -> HELLO greeting_rest")
    print(f"         greeting_rest -> WORLD | epsilon")

    # Step 2: Create a tokenizer
    print("\n2. Creating Tokenizer")
    print("-" * 40)

    tokenizer = Tokenizer()
    tokenizer.add("WHITESPACE", r"\s+", skip=True)
    tokenizer.add("HELLO", r"hello")
    tokenizer.add("WORLD", r"world")

    # Test tokenization
    text = "hello world"
    tokens = tokenizer.tokenize(text)
    print(f"Input: '{text}'")
    print(f"Tokens: {[(t.type, t.value) for t in tokens]}")

    # Step 3: Create parser and parse
    print("\n3. Parsing")
    print("-" * 40)

    parser = Parser(grammar, tokenizer)

    test_inputs = ["hello", "hello world", "world", "hello hello"]
    for text in test_inputs:
        is_valid = parser.parse(text)
        print(f"'{text}' -> {'Valid' if is_valid else 'Invalid'}")

    # Step 4: Get valid next tokens (THE KEY FUNCTION)
    print("\n4. Get Valid Next Tokens")
    print("-" * 40)

    state = parser.initial_state()
    print(f"Initial state: {state}")
    print(f"Valid next tokens: {parser.get_valid_next(state)}")

    # Feed first token
    tokens = tokenizer.tokenize("hello")
    state = parser.step(state, tokens[0])
    print(f"\nAfter 'hello': {state}")
    print(f"Valid next tokens: {parser.get_valid_next(state)}")


if __name__ == "__main__":
    main()
