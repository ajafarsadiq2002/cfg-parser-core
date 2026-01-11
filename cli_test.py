"""Interactive CLI for testing the parser."""
import sys
sys.path.insert(0, '.')

from grammars.json_grammar import create_json_parser, parse_json
from grammars.math_grammar import evaluate
from grammars.csv_grammar import create_csv_parser, parse_csv, csv_to_dicts
from grammars.toml_grammar import create_toml_parser, parse_toml
from grammars.yaml_grammar import create_yaml_parser, parse_yaml


def test_json_interactive():
    parser = create_json_parser()
    print("JSON Validator (type 'quit' to exit)")
    print("-" * 40)

    while True:
        try:
            text = input("JSON> ").strip()
            if text == 'quit':
                break
            if not text:
                continue

            if parser.parse(text):
                result = parse_json(text)
                print(f"  Valid! Parsed: {result}")
            else:
                print("  Invalid!")
        except Exception as e:
            print(f"  Error: {e}")


def test_math_interactive():
    print("Math Calculator (type 'quit' to exit)")
    print("Supports: +, -, *, /, ^, sqrt(), sin(), cos(), etc.")
    print("-" * 40)

    while True:
        try:
            text = input("Math> ").strip()
            if text == 'quit':
                break
            if not text:
                continue

            result = evaluate(text)
            print(f"  = {result}")
        except Exception as e:
            print(f"  Error: {e}")


def test_csv_interactive():
    print("CSV Parser (type 'quit' to exit)")
    print("Enter CSV rows (use \\n for newlines or enter multiline)")
    print("-" * 40)

    while True:
        try:
            text = input("CSV> ").strip()
            if text == 'quit':
                break
            if not text:
                continue

            # Replace literal \n with newlines
            text = text.replace('\\n', '\n')

            rows = parse_csv(text)
            print(f"  Parsed {len(rows)} rows:")
            for i, row in enumerate(rows):
                print(f"    [{i}]: {row}")

        except Exception as e:
            print(f"  Error: {e}")


def test_toml_interactive():
    print("TOML Parser (type 'quit' to exit, 'example' for sample)")
    print("-" * 40)

    while True:
        try:
            text = input("TOML> ").strip()
            if text == 'quit':
                break
            if not text:
                continue

            if text == 'example':
                text = 'name = "test"\ncount = 42\nactive = true'
                print(f"  Example: {text}")

            # Replace literal \n with newlines
            text = text.replace('\\n', '\n')

            result = parse_toml(text)
            print(f"  Parsed: {result}")

        except Exception as e:
            print(f"  Error: {e}")


def test_yaml_interactive():
    print("YAML Parser - Flow/Inline Style (type 'quit' to exit)")
    print("Format: {key: value, key2: value2} or [1, 2, 3]")
    print("-" * 40)

    while True:
        try:
            text = input("YAML> ").strip()
            if text == 'quit':
                break
            if not text:
                continue

            result = parse_yaml(text)
            print(f"  Parsed: {result}")

        except Exception as e:
            print(f"  Error: {e}")


def test_valid_next_interactive():
    print("get_valid_next() Demo - Choose grammar:")
    print("  1. JSON")
    print("  2. CSV")
    print("  3. TOML")
    print("  4. YAML")

    grammar_choice = input("Grammar (1-4): ").strip()

    if grammar_choice == "1":
        parser = create_json_parser()
        name = "JSON"
    elif grammar_choice == "2":
        parser = create_csv_parser()
        name = "CSV"
    elif grammar_choice == "3":
        parser = create_toml_parser()
        name = "TOML"
    elif grammar_choice == "4":
        parser = create_yaml_parser()
        name = "YAML"
    else:
        print("Invalid choice, using JSON")
        parser = create_json_parser()
        name = "JSON"

    state = parser.initial_state()

    print(f"\n{name} get_valid_next() Demo")
    print("-" * 40)
    print("Commands: 'reset', 'quit', 'stack'")
    print("-" * 40)
    print(f"Stack: {list(state.stack)}")
    print(f"Valid next: {parser.get_valid_next(state)}")

    while True:
        try:
            text = input("\nToken> ").strip()
            if text == 'quit':
                break
            if text == 'reset':
                state = parser.initial_state()
                print("Reset!")
                print(f"Stack: {list(state.stack)}")
                print(f"Valid next: {parser.get_valid_next(state)}")
                continue
            if text == 'stack':
                print(f"Stack: {list(state.stack)}")
                print(f"Valid next: {parser.get_valid_next(state)}")
                continue
            if not text:
                continue

            # Tokenize and step
            tokens = parser.tokenizer.tokenize(text)
            for token in tokens:
                if token.type == "EOF":
                    continue

                print(f"  Trying to feed: {token.type} = {token.value!r}")
                print(f"  Current stack: {list(state.stack)[:5]}...")
                print(f"  Valid tokens: {parser.get_valid_next(state)}")

                state = parser.step(state, token)
                print(f"  Success! New stack: {list(state.stack)[:5]}...")

            print(f"\nValid next: {parser.get_valid_next(state)}")

            if state.is_complete():
                print("[Parse complete!]")

        except Exception as e:
            print(f"  Error: {e}")
            print(f"  Stack was: {list(state.stack)[:5]}...")


if __name__ == "__main__":
    print("=" * 50)
    print("CFG Parser Core - Interactive CLI")
    print("=" * 50)
    print()
    print("1. JSON Validator")
    print("2. Math Calculator")
    print("3. CSV Parser")
    print("4. TOML Parser")
    print("5. YAML Parser")
    print("6. get_valid_next() Demo")
    print()

    choice = input("Choose (1-6): ").strip()
    print()

    if choice == "1":
        test_json_interactive()
    elif choice == "2":
        test_math_interactive()
    elif choice == "3":
        test_csv_interactive()
    elif choice == "4":
        test_toml_interactive()
    elif choice == "5":
        test_yaml_interactive()
    elif choice == "6":
        test_valid_next_interactive()
    else:
        print("Invalid choice")
