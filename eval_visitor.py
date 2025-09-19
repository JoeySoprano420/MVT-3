# eval_visitor.py
from ast_nodes import *

class EvalVisitor(ASTVisitor):
    def __init__(self):
        # Variable environment (scopes could be stacked later)
        self.env = {}

    # === Program ===
    def visit_Program(self, node: Program):
        for stmt in node.body:
            stmt.accept(self)

    def visit_Main(self, node: Main):
        for stmt in node.body:
            stmt.accept(self)

    def visit_Prog(self, node: Prog):
        # Prog is like Main but named
        for stmt in node.body:
            stmt.accept(self)

    # === Veil Mode ===
    def visit_Task(self, node: Task):
        print(f"[Task: {node.intention.name}] Tool={node.tool.name}")
        node.logic.accept(self)

    def visit_Intention(self, node: Intention):
        return node.name

    def visit_Tool(self, node: Tool):
        return node.name

    def visit_Logic(self, node: Logic):
        for stmt in node.body:
            stmt.accept(self)

    # === Statements ===
    def visit_Declaration(self, node: Declaration):
        value = node.expr.accept(self)
        self.env[node.name] = value
        return value

    def visit_Assignment(self, node: Assignment):
        value = node.expr.accept(self)
        if node.name not in self.env:
            raise Exception(f"Variable '{node.name}' not declared")
        self.env[node.name] = value
        return value

    def visit_Print(self, node: Print):
        value = node.expr.accept(self)
        print(value)

    def visit_Return(self, node: Return):
        return node.expr.accept(self)

    def visit_If(self, node: If):
        cond = node.condition.accept(self)
        if cond:
            for stmt in node.then_body:
                stmt.accept(self)
        elif node.else_body:
            for stmt in node.else_body:
                stmt.accept(self)

    def visit_Loop(self, node: Loop):
        start = node.start.accept(self)
        end = node.end.accept(self)
        for i in range(start, end):
            self.env[node.var] = i
            for stmt in node.body:
                stmt.accept(self)

    def visit_TryCatch(self, node: TryCatch):
        try:
            for stmt in node.try_body:
                stmt.accept(self)
        except Exception as e:
            print(f"[Caught Exception: {e}]")
            for stmt in node.catch_body:
                stmt.accept(self)

    def visit_Async(self, node: Async):
        # Just run synchronously for now
        print("[Async Start]")
        for stmt in node.body:
            stmt.accept(self)
        print("[Async End]")

    def visit_Await(self, node: Await):
        print(f"[Await {node.name}]")

    # === Expressions ===
    def visit_BinaryOp(self, node: BinaryOp):
        left = node.left.accept(self)
        right = node.right.accept(self)
        if node.op == "+": return left + right
        if node.op == "-": return left - right
        if node.op == "*": return left * right
        if node.op == "/": return left // right if isinstance(left, int) else left / right
        if node.op == "==": return left == right
        if node.op == "!=": return left != right
        if node.op == "<": return left < right
        if node.op == ">": return left > right
        if node.op == "<=": return left <= right
        if node.op == ">=": return left >= right
        raise Exception(f"Unsupported operator: {node.op}")

    def visit_UnaryOp(self, node: UnaryOp):
        val = node.operand.accept(self)
        if node.op == "-": return -val
        if node.op == "+": return +val
        return val

    def visit_Literal(self, node: Literal):
        return node.value

    def visit_Identifier(self, node: Identifier):
        if node.name not in self.env:
            raise Exception(f"Undefined variable '{node.name}'")
        return self.env[node.name]
