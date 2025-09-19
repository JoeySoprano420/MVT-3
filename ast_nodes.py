# ast_nodes.py
# Abstract Syntax Tree for MIPA VEIL Trizzle (MVT 3)

from typing import List, Optional, Union

# === Base Node ===
class ASTNode:
    def accept(self, visitor):
        """Accept a visitor for traversal/codegen."""
        method_name = 'visit_' + self.__class__.__name__
        visit = getattr(visitor, method_name, visitor.generic_visit)
        return visit(self)

# === Program Root ===
class Program(ASTNode):
    def __init__(self, body: List[ASTNode]):
        self.body = body  # list of statements/tasks

# === Trizzle Mode ===
class Main(ASTNode):
    def __init__(self, body: List[ASTNode]):
        self.body = body

class Prog(ASTNode):
    def __init__(self, name: str, body: List[ASTNode]):
        self.name = name
        self.body = body

# === Veil Mode ===
class Task(ASTNode):
    def __init__(self, intention, tool, logic):
        self.intention = intention  # Intention node
        self.tool = tool            # Tool node
        self.logic = logic          # Logic node

class Intention(ASTNode):
    def __init__(self, name: str, params: List['Param']):
        self.name = name
        self.params = params

class Tool(ASTNode):
    def __init__(self, name: str):
        self.name = name

class Logic(ASTNode):
    def __init__(self, body: List[ASTNode]):
        self.body = body

# === Parameters / Types ===
class Param(ASTNode):
    def __init__(self, type_name: str, name: str):
        self.type_name = type_name
        self.name = name

# === Statements ===
class Declaration(ASTNode):
    def __init__(self, name: str, expr: 'Expr'):
        self.name = name
        self.expr = expr

class Assignment(ASTNode):
    def __init__(self, name: str, expr: 'Expr'):
        self.name = name
        self.expr = expr

class Print(ASTNode):
    def __init__(self, expr: 'Expr'):
        self.expr = expr

class Return(ASTNode):
    def __init__(self, expr: 'Expr'):
        self.expr = expr

class If(ASTNode):
    def __init__(self, condition: 'Expr', then_body: List[ASTNode], else_body: Optional[List[ASTNode]] = None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

class Loop(ASTNode):
    def __init__(self, var: str, start: 'Expr', end: 'Expr', body: List[ASTNode]):
        self.var = var
        self.start = start
        self.end = end
        self.body = body

class TryCatch(ASTNode):
    def __init__(self, try_body: List[ASTNode], catch_body: List[ASTNode]):
        self.try_body = try_body
        self.catch_body = catch_body

class Async(ASTNode):
    def __init__(self, body: List[ASTNode]):
        self.body = body

class Await(ASTNode):
    def __init__(self, name: str):
        self.name = name

# === Expressions ===
class Expr(ASTNode):
    pass

class BinaryOp(Expr):
    def __init__(self, left: Expr, op: str, right: Expr):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(Expr):
    def __init__(self, op: str, operand: Expr):
        self.op = op
        self.operand = operand

class Literal(Expr):
    def __init__(self, value: Union[int, float, str, bool]):
        self.value = value

class Identifier(Expr):
    def __init__(self, name: str):
        self.name = name

# ast_nodes.py (extend Async)

class Async(ASTNode):
    def __init__(self, body: List[ASTNode], name: Optional[str] = None):
        self.body = body
        self.name = name  # new: task identifier

# ast_nodes.py (already has Return node — no change needed)
# Just ensure Async nodes can carry body statements that include Return.
class Async(ASTNode):
    def __init__(self, body: List[ASTNode], name: Optional[str] = None):
        self.body = body
        self.name = name

# ast_nodes.py additions

class Declaration(ASTNode):
    def __init__(self, name, expr: 'Expr'):
        # name can be str or list of str for tuple destructuring
        self.name = name
        self.expr = expr

class Assignment(ASTNode):
    def __init__(self, name, expr: 'Expr'):
        # same: str or list of str
        self.name = name
        self.expr = expr

# ast_nodes.py addition

class DestructureSlot(ASTNode):
    def __init__(self, name: str, default: Optional['Expr'] = None):
        self.name = name
        self.default = default

