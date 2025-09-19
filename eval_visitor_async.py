# eval_visitor_async.py
import asyncio
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()

    # === Program Root ===
    def visit_Program(self, node: Program):
        for stmt in node.body:
            res = stmt.accept(self)
            # If coroutine, schedule it
            if asyncio.iscoroutine(res):
                self.loop.run_until_complete(res)

    def visit_Main(self, node: Main):
        for stmt in node.body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                self.loop.run_until_complete(res)

    # === Veil Mode ===
    def visit_Task(self, node: Task):
        print(f"[Task: {node.intention.name}] Tool={node.tool.name}")
        return node.logic.accept(self)

    def visit_Logic(self, node: Logic):
        for stmt in node.body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                self.loop.run_until_complete(res)

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
                res = stmt.accept(self)
                if asyncio.iscoroutine(res):
                    self.loop.run_until_complete(res)
        elif node.else_body:
            for stmt in node.else_body:
                res = stmt.accept(self)
                if asyncio.iscoroutine(res):
                    self.loop.run_until_complete(res)

    def visit_Loop(self, node: Loop):
        start = node.start.accept(self)
        end = node.end.accept(self)
        for i in range(start, end):
            self.env[node.var] = i
            for stmt in node.body:
                res = stmt.accept(self)
                if asyncio.iscoroutine(res):
                    self.loop.run_until_complete(res)

    def visit_TryCatch(self, node: TryCatch):
        try:
            for stmt in node.try_body:
                res = stmt.accept(self)
                if asyncio.iscoroutine(res):
                    self.loop.run_until_complete(res)
        except Exception as e:
            print(f"[Caught Exception: {e}]")
            for stmt in node.catch_body:
                res = stmt.accept(self)
                if asyncio.iscoroutine(res):
                    self.loop.run_until_complete(res)

    # === Async / Await ===
    async def _run_async_block(self, body):
        print("[Async Start]")
        for stmt in body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                await res
        print("[Async End]")

    def visit_Async(self, node: Async):
        return self._run_async_block(node.body)

    async def _await_task(self, name: str):
        print(f"[Await {name}] (simulated join)")
        # Could link to env[name] if tasks stored
        await asyncio.sleep(0.01)

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

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
