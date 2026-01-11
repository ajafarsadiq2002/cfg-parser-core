"""
AST (Abstract Syntax Tree) - Tree representation of parsed input.

This is Component 4 of the CFG Parser Core.

Features:
- Node structure for representing parsed data
- Build trees during parsing
- Serialize to dict/JSON
- Pretty print for debugging
"""

from dataclasses import dataclass, field
from typing import List, Any, Optional, Dict, Union
import json


@dataclass
class Node:
    """
    Represents a node in the Abstract Syntax Tree.

    A Node can be either:
    - A terminal (leaf node with a value)
    - A non-terminal (internal node with children)

    Attributes:
        type: The grammar symbol this node represents
        value: The actual value (for terminals)
        children: Child nodes (for non-terminals)
        line: Source line number
        column: Source column number
        label: Optional label from grammar rule
    """
    type: str
    value: Any = None
    children: List['Node'] = field(default_factory=list)
    line: int = 0
    column: int = 0
    label: Optional[str] = None

    def is_terminal(self) -> bool:
        """Check if this is a terminal (leaf) node."""
        return len(self.children) == 0

    def is_nonterminal(self) -> bool:
        """Check if this is a non-terminal (internal) node."""
        return len(self.children) > 0

    def add_child(self, node: 'Node'):
        """Add a child node."""
        self.children.append(node)

    def get_child(self, index: int) -> Optional['Node']:
        """Get child at index, or None if out of bounds."""
        if 0 <= index < len(self.children):
            return self.children[index]
        return None

    def find_child(self, node_type: str) -> Optional['Node']:
        """Find first child with given type."""
        for child in self.children:
            if child.type == node_type:
                return child
        return None

    def find_all(self, node_type: str) -> List['Node']:
        """Find all children with given type."""
        return [c for c in self.children if c.type == node_type]

    def to_dict(self) -> Dict:
        """
        Convert to dictionary representation.

        Useful for serialization and debugging.
        """
        result = {"type": self.type}

        if self.value is not None:
            result["value"] = self.value

        if self.children:
            result["children"] = [c.to_dict() for c in self.children]

        if self.label:
            result["label"] = self.label

        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def pretty_print(self, indent: int = 0, prefix: str = "") -> str:
        """
        Create a pretty-printed tree representation.

        Example output:
            object
            ├── pair
            │   ├── STRING ("name")
            │   └── STRING ("John")
            └── pair
                ├── STRING ("age")
                └── NUMBER (25)
        """
        lines = []

        # Current node
        node_str = self.type
        if self.value is not None:
            node_str += f" ({self.value!r})"
        if self.label:
            node_str += f" #{self.label}"

        lines.append(prefix + node_str)

        # Children
        for i, child in enumerate(self.children):
            is_last = (i == len(self.children) - 1)

            if is_last:
                child_prefix = prefix + "└── "
                next_prefix = prefix + "    "
            else:
                child_prefix = prefix + "├── "
                next_prefix = prefix + "│   "

            lines.append(child.pretty_print(indent + 1, child_prefix)[len(child_prefix):])
            if not child.is_terminal():
                for grandchild in child.children:
                    gc_is_last = grandchild == child.children[-1]
                    if gc_is_last:
                        gc_prefix = next_prefix + "└── "
                        gc_next = next_prefix + "    "
                    else:
                        gc_prefix = next_prefix + "├── "
                        gc_next = next_prefix + "│   "
                    # Recursively print grandchildren
                    lines.extend(self._print_subtree(grandchild, gc_prefix, gc_next))

        return "\n".join(lines)

    def _print_subtree(self, node: 'Node', prefix: str, next_prefix: str) -> List[str]:
        """Helper to print a subtree."""
        lines = []
        node_str = node.type
        if node.value is not None:
            node_str += f" ({node.value!r})"
        lines.append(prefix + node_str)

        for i, child in enumerate(node.children):
            is_last = (i == len(node.children) - 1)
            if is_last:
                child_prefix = next_prefix + "└── "
                child_next = next_prefix + "    "
            else:
                child_prefix = next_prefix + "├── "
                child_next = next_prefix + "│   "
            lines.extend(self._print_subtree(child, child_prefix, child_next))

        return lines

    def walk(self):
        """
        Iterate over all nodes in pre-order.

        Yields:
            Each node in the tree
        """
        yield self
        for child in self.children:
            yield from child.walk()

    def walk_leaves(self):
        """
        Iterate over all leaf (terminal) nodes.

        Yields:
            Each terminal node
        """
        if self.is_terminal():
            yield self
        else:
            for child in self.children:
                yield from child.walk_leaves()

    def flatten(self) -> str:
        """
        Flatten tree back to string (all leaf values concatenated).
        """
        if self.is_terminal():
            return str(self.value) if self.value is not None else ""
        return "".join(child.flatten() for child in self.children)

    def __repr__(self):
        if self.value is not None:
            return f"Node({self.type!r}, {self.value!r})"
        return f"Node({self.type!r}, children={len(self.children)})"

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return (self.type == other.type and
                self.value == other.value and
                self.children == other.children)


class ASTBuilder:
    """
    Builds AST during parsing.

    Used by the parser to construct the tree as tokens are consumed.

    Usage:
        builder = ASTBuilder()
        builder.start_node("object")
        builder.add_terminal("STRING", "name")
        builder.add_terminal("STRING", "John")
        builder.end_node()
        ast = builder.get_ast()
    """

    def __init__(self):
        self._stack: List[Node] = []
        self._root: Optional[Node] = None

    def start_node(self, node_type: str, label: Optional[str] = None,
                   line: int = 0, column: int = 0):
        """
        Start building a new non-terminal node.

        Args:
            node_type: The grammar symbol
            label: Optional label from grammar rule
            line: Source line
            column: Source column
        """
        node = Node(type=node_type, label=label, line=line, column=column)
        self._stack.append(node)

    def end_node(self) -> Node:
        """
        Finish the current node and attach to parent.

        Returns:
            The completed node
        """
        if not self._stack:
            raise RuntimeError("No node to end")

        node = self._stack.pop()

        if self._stack:
            self._stack[-1].add_child(node)
        else:
            self._root = node

        return node

    def add_terminal(self, token_type: str, value: Any,
                     line: int = 0, column: int = 0):
        """
        Add a terminal (leaf) node.

        Args:
            token_type: The token type
            value: The token value
            line: Source line
            column: Source column
        """
        node = Node(type=token_type, value=value, line=line, column=column)

        if self._stack:
            self._stack[-1].add_child(node)
        else:
            self._root = node

    def add_token(self, token: 'Token'):
        """Add a terminal node from a Token object."""
        from .tokenizer import Token
        self.add_terminal(token.type, token.value, token.line, token.column)

    def current_node(self) -> Optional[Node]:
        """Get the current node being built."""
        return self._stack[-1] if self._stack else None

    def get_ast(self) -> Optional[Node]:
        """Get the completed AST."""
        return self._root

    def reset(self):
        """Reset the builder."""
        self._stack = []
        self._root = None


# Convenience functions

def terminal(token_type: str, value: Any) -> Node:
    """Create a terminal node."""
    return Node(type=token_type, value=value)


def nonterminal(node_type: str, *children: Node) -> Node:
    """Create a non-terminal node with children."""
    return Node(type=node_type, children=list(children))
