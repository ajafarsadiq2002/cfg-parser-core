"""
Example 4: LLM Constrained Decoding

This is THE KEY USE CASE for the CFG Parser Core.

Demonstrates:
- How to constrain LLM output to valid JSON
- Token masking
- Simulated LLM generation
- Real-world integration pattern
"""

import sys
import os
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import Grammar, Tokenizer, Parser
from core.parser import ConstrainedDecoder, StreamingParser
from grammars.json_grammar import create_json_grammar, create_json_tokenizer


def main():
    print("=" * 60)
    print("Example 4: LLM Constrained Decoding")
    print("=" * 60)

    # Setup
    grammar = create_json_grammar()
    tokenizer = create_json_tokenizer()
    parser = Parser(grammar, tokenizer)

    # =========================================================
    # Part 1: Understanding get_valid_next()
    # =========================================================
    print("\n1. Understanding get_valid_next()")
    print("-" * 40)
    print("This function tells us what tokens are valid at each step.")

    state = parser.initial_state()

    print(f"\nAt start of JSON:")
    print(f"  Valid tokens: {parser.get_valid_next(state)}")
    print("  (Can start with object, array, string, number, or literals)")

    # Simulate parsing: {
    tokens = tokenizer.tokenize('{"name": "John"}')

    print(f"\nSimulating step-by-step parsing:")
    generated = ""
    for i, token in enumerate(tokens[:-1]):  # Skip EOF
        generated += token.value
        valid_before = parser.get_valid_next(state)
        state = parser.step(state, token)
        valid_after = parser.get_valid_next(state)

        print(f"\n  Step {i+1}: Token = '{token.type}' ('{token.value}')")
        print(f"    Before: {valid_before}")
        print(f"    After:  {valid_after}")

    # =========================================================
    # Part 2: Simulated LLM with Constrained Decoding
    # =========================================================
    print("\n" + "=" * 60)
    print("2. Simulated LLM Generation with Constraints")
    print("-" * 40)

    # Simulate an LLM vocabulary
    llm_vocab = {
        0: '{',
        1: '}',
        2: '[',
        3: ']',
        4: ':',
        5: ',',
        6: '"name"',
        7: '"age"',
        8: '"city"',
        9: '"John"',
        10: '"Alice"',
        11: '25',
        12: '30',
        13: 'true',
        14: 'false',
        15: 'null',
    }

    # Map LLM tokens to grammar terminals
    def get_terminal_type(token_str):
        """Map LLM token string to grammar terminal."""
        if token_str in '{}[]:,':
            return token_str
        if token_str.startswith('"'):
            return 'STRING'
        if token_str.replace('.', '').replace('-', '').isdigit():
            return 'NUMBER'
        if token_str == 'true':
            return 'TRUE'
        if token_str == 'false':
            return 'FALSE'
        if token_str == 'null':
            return 'NULL'
        return None

    def constrained_generate(parser, vocab, max_tokens=20):
        """
        Simulate LLM generation with grammar constraints.

        This is the pattern you'd use with a real LLM.
        """
        state = parser.initial_state()
        generated_tokens = []
        generated_text = ""

        print("\nGenerating JSON with constraints:")
        print(f"{'Step':<6} {'Token':<12} {'Valid Options':<40}")
        print("-" * 60)

        for step in range(max_tokens):
            # Get valid grammar terminals
            valid_terminals = parser.get_valid_next(state)

            # Find LLM tokens that match valid terminals
            valid_token_ids = []
            for token_id, token_str in vocab.items():
                terminal = get_terminal_type(token_str)
                if terminal in valid_terminals:
                    valid_token_ids.append(token_id)

            if not valid_token_ids:
                # Check if we're done (EOF is valid)
                if 'EOF' in valid_terminals:
                    print(f"{step:<6} {'[DONE]':<12}")
                    break
                else:
                    print(f"{step:<6} {'[ERROR]':<12} No valid tokens!")
                    break

            # In a real LLM, you would:
            # 1. Get logits from the model
            # 2. Set logits[invalid_tokens] = -infinity
            # 3. Sample from the masked distribution

            # Here we just randomly pick a valid token
            chosen_id = random.choice(valid_token_ids)
            chosen_str = vocab[chosen_id]

            # Show what happened
            valid_strs = [vocab[i] for i in valid_token_ids[:5]]
            if len(valid_token_ids) > 5:
                valid_strs.append("...")

            print(f"{step:<6} {chosen_str:<12} {str(valid_strs):<40}")

            # Update state
            terminal = get_terminal_type(chosen_str)
            token = type('Token', (), {
                'type': terminal,
                'value': chosen_str,
                'line': 1,
                'column': 1
            })()

            try:
                state = parser.step(state, token)
            except Exception as e:
                print(f"  Error: {e}")
                break

            generated_tokens.append(chosen_str)
            generated_text += chosen_str

            # Simple completion check
            if chosen_str == '}' and state.is_complete():
                break
            if chosen_str == ']' and state.is_complete():
                break

        return generated_text

    # Run simulation multiple times
    print("\nGenerating 3 random valid JSON objects:\n")
    for i in range(3):
        print(f"\n--- Generation {i+1} ---")
        random.seed(42 + i)
        result = constrained_generate(parser, llm_vocab)
        print(f"\nResult: {result}")

    # =========================================================
    # Part 3: Integration Pattern for Real LLMs
    # =========================================================
    print("\n" + "=" * 60)
    print("3. Integration Pattern for Real LLMs")
    print("-" * 40)

    integration_code = '''
# Real-world integration with Hugging Face / vLLM:

from transformers import AutoModelForCausalLM, AutoTokenizer
from cfg_parser import Parser, create_json_grammar

class ConstrainedGenerator:
    def __init__(self, model_name, grammar):
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.parser = Parser(grammar)

        # Build vocab mapping
        self.token_to_terminal = self._build_mapping()

    def generate(self, prompt, max_tokens=100):
        state = self.parser.initial_state()
        input_ids = self.tokenizer.encode(prompt)

        for _ in range(max_tokens):
            # Get model logits
            outputs = self.model(input_ids)
            logits = outputs.logits[0, -1, :]

            # Get valid tokens from grammar
            valid_terminals = self.parser.get_valid_next(state)

            # Mask invalid tokens
            for token_id in range(len(logits)):
                terminal = self.token_to_terminal.get(token_id)
                if terminal not in valid_terminals:
                    logits[token_id] = float('-inf')

            # Sample from masked distribution
            next_token = torch.multinomial(F.softmax(logits), 1)

            # Update state
            state = self.parser.step(state, next_token)
            input_ids = torch.cat([input_ids, next_token])

            if self.parser.is_complete(state):
                break

        return self.tokenizer.decode(input_ids)
'''
    print(integration_code)

    # =========================================================
    # Part 4: Streaming Parser
    # =========================================================
    print("\n" + "=" * 60)
    print("4. Streaming Parser (Incremental Input)")
    print("-" * 40)

    streaming = StreamingParser(grammar, tokenizer)

    chunks = ['{"na', 'me": "Jo', 'hn", "age":', ' 25}']

    print("Feeding chunks incrementally:")
    for chunk in chunks:
        consumed = streaming.feed(chunk)
        print(f"\n  Fed: '{chunk}'")
        print(f"  Consumed tokens: {[t.type for t in consumed]}")
        print(f"  Valid next: {streaming.get_valid_next()}")
        print(f"  Complete: {streaming.is_complete()}")


if __name__ == "__main__":
    main()
