"""
Visitor Pattern - Walk and transform ASTs.

This is Component 5 of the CFG Parser Core.

Features:
- Traverse AST nodes
- Transform AST (returns new nodes)
- Evaluate AST (returns values)
- Pre/post-order traversal hooks
"""

from typing import Any, Dict, Optional, Callable, List, TypeVar, Generic
from .ast import Node

T = TypeVar('T')


class Visitor(Generic[T]):
    """
    Base visitor class for traversing AST nodes.

    Subclass and implement visit_<NodeType> methods.

    Usage:
        class PrintVisitor(Visitor):
            def visit_NUMBER(self, node):
                print(f"Number: {node.value}")

            def visit_object(self, node):
                print("Object:")
                for child in node.children:
                    self.visit(child)

        visitor = PrintVisitor()
        visitor.visit(ast)
    """

    def visit(self, node: Node) -> T:
        """
        Visit a node by dispatching to the appropriate method.

        Looks for visit_<node.type> method, falls back to generic_visit.

        Args:
            node: The AST node to visit

        Returns:
            Result of the visit method
        """
        method_name = f"visit_{node.type}"
        method = getattr(self, method_name, None)

        if method is None:
            return self.generic_visit(node)

        return method(node)

    def generic_visit(self, node: Node) -> T:
        """
        Default visit method when no specific handler exists.

        Override in subclasses for custom default behavior.

        Args:
            node: The AST node

        Returns:
            None by default
        """
        # Visit all children by default
        for child in node.children:
            self.visit(child)
        return None  # type: ignore

    def visit_children(self, node: Node) -> List[T]:
        """
        Visit all children and collect results.

        Args:
            node: Parent node

        Returns:
            List of results from visiting each child
        """
        return [self.visit(child) for child in node.children]


class Transformer(Visitor[Node]):
    """
    Visitor that transforms AST nodes.

    Returns new nodes (doesn't modify in place).
    Useful for AST rewriting, optimization, etc.

    Usage:
        class SimplifyMath(Transformer):
            def visit_add(self, node):
                left = self.visit(node.children[0])
                right = self.visit(node.children[1])

                # Simplify 0 + x -> x
                if left.type == "NUMBER" and left.value == 0:
                    return right
                if right.type == "NUMBER" and right.value == 0:
                    return left

                return Node("add", children=[left, right])

        simplified_ast = SimplifyMath().visit(ast)
    """

    def generic_visit(self, node: Node) -> Node:
        """
        Default: return node with transformed children.
        """
        if not node.children:
            return node

        new_children = [self.visit(child) for child in node.children]
        return Node(
            type=node.type,
            value=node.value,
            children=new_children,
            line=node.line,
            column=node.column,
            label=node.label
        )


class Evaluator(Visitor[Any]):
    """
    Visitor that evaluates AST to produce values.

    Useful for interpreters, calculators, etc.

    Usage:
        class MathEvaluator(Evaluator):
            def visit_NUMBER(self, node):
                return float(node.value)

            def visit_add(self, node):
                left = self.visit(node.children[0])
                right = self.visit(node.children[1])
                return left + right

            def visit_multiply(self, node):
                left = self.visit(node.children[0])
                right = self.visit(node.children[1])
                return left * right

        result = MathEvaluator().visit(ast)  # Returns number
    """

    def __init__(self):
        self.context: Dict[str, Any] = {}

    def generic_visit(self, node: Node) -> Any:
        """
        Default: return value for terminals, visit children for non-terminals.
        """
        if node.is_terminal():
            return node.value

        results = [self.visit(child) for child in node.children]

        # If single child, return its value
        if len(results) == 1:
            return results[0]

        return results


class WalkVisitor(Visitor[None]):
    """
    Simple visitor that walks the entire tree.

    Provides hooks for pre/post-order traversal.

    Usage:
        class Counter(WalkVisitor):
            def __init__(self):
                self.count = 0

            def enter(self, node):
                self.count += 1

            def leave(self, node):
                pass  # Called after children are visited

        counter = Counter()
        counter.visit(ast)
        print(counter.count)
    """

    def visit(self, node: Node) -> None:
        """Visit with pre/post hooks."""
        self.enter(node)

        for child in node.children:
            self.visit(child)

        self.leave(node)

    def enter(self, node: Node) -> None:
        """Called before visiting children. Override in subclass."""
        pass

    def leave(self, node: Node) -> None:
        """Called after visiting children. Override in subclass."""
        pass

    def generic_visit(self, node: Node) -> None:
        """Not used - visit() handles all nodes."""
        pass


class SymbolTable:
    """
    Symbol table for variable tracking during evaluation.

    Supports nested scopes.
    """

    def __init__(self):
        self._scopes: List[Dict[str, Any]] = [{}]

    def push_scope(self):
        """Enter a new scope."""
        self._scopes.append({})

    def pop_scope(self) -> Dict[str, Any]:
        """Exit current scope."""
        if len(self._scopes) <= 1:
            raise RuntimeError("Cannot pop global scope")
        return self._scopes.pop()

    def define(self, name: str, value: Any):
        """Define a variable in current scope."""
        self._scopes[-1][name] = value

    def get(self, name: str) -> Any:
        """Get variable value, searching from inner to outer scope."""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Undefined variable: {name}")

    def set(self, name: str, value: Any):
        """Set variable value in the scope where it's defined."""
        for scope in reversed(self._scopes):
            if name in scope:
                scope[name] = value
                return
        raise NameError(f"Undefined variable: {name}")

    def has(self, name: str) -> bool:
        """Check if variable is defined."""
        for scope in reversed(self._scopes):
            if name in scope:
                return True
        return False


# ==================== Utility Functions ====================

def walk(node: Node, callback: Callable[[Node], None]):
    """
    Walk tree and call callback for each node.

    Args:
        node: Root node
        callback: Function to call for each node
    """
    callback(node)
    for child in node.children:
        walk(child, callback)


def walk_with_parent(node: Node, callback: Callable[[Node, Optional[Node]], None],
                     parent: Optional[Node] = None):
    """
    Walk tree with parent reference.

    Args:
        node: Current node
        callback: Function(node, parent) to call
        parent: Parent node
    """
    callback(node, parent)
    for child in node.children:
        walk_with_parent(child, callback, node)


def find_nodes(node: Node, node_type: str) -> List[Node]:
    """
    Find all nodes of a specific type.

    Args:
        node: Root node
        node_type: Type to search for

    Returns:
        List of matching nodes
    """
    results = []

    def collector(n: Node):
        if n.type == node_type:
            results.append(n)

    walk(node, collector)
    return results


def map_tree(node: Node, transform: Callable[[Node], Node]) -> Node:
    """
    Transform each node in the tree.

    Args:
        node: Root node
        transform: Function to transform each node

    Returns:
        New transformed tree
    """
    new_node = transform(node)

    if new_node.children:
        new_node = Node(
            type=new_node.type,
            value=new_node.value,
            children=[map_tree(child, transform) for child in new_node.children],
            line=new_node.line,
            column=new_node.column,
            label=new_node.label
        )

    return new_node


def fold_tree(node: Node, combine: Callable[[Node, List[Any]], Any]) -> Any:
    """
    Fold tree to single value (bottom-up).

    Args:
        node: Root node
        combine: Function(node, child_results) -> result

    Returns:
        Folded value
    """
    child_results = [fold_tree(child, combine) for child in node.children]
    return combine(node, child_results)
