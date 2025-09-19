# eval_scheduler_bind.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.tasks = {}  # map task names -> asyncio.Task

    # === Async / Await with Return Support ===
    async def _run_async_block(self, name, body):
        print(f"[Async {name} Start]")
        result = None
        for stmt in body:
            res = stmt.accept(self)
            if isinstance(res, Return):  # special handling
                result = res.expr.accept(self)
                break
            if asyncio.iscoroutine(res):
                result = await res
            else:
                result = res
        print(f"[Async {name} End]")
        return result

    def visit_Async(self, node: Async):
        name = node.name or f"task_{id(node)}"
        coro = self._run_async_block(name, node.body)
        task = self.loop.create_task(coro)
        self.tasks[name] = task
        return task

    async def _await_task(self, name: str):
        if name not in self.tasks:
            print(f"[Await {name}] (no such task)")
            return None
        print(f"[Await {name}] waiting...")
        result = await self.tasks[name]
        print(f"[Await {name}] complete with value: {result}")
        return result

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

    # === Declarations and Assignments ===
    def visit_Declaration(self, node: Declaration):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):  # await inside declaration
            value = self.loop.run_until_complete(value)
        self.env[node.name] = value
        return value

    def visit_Assignment(self, node: Assignment):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):  # await inside assignment
            value = self.loop.run_until_complete(value)
        if node.name not in self.env:
            raise Exception(f"Variable '{node.name}' not declared")
        self.env[node.name] = value
        return value

    # === Return handling ===
    def visit_Return(self, node: Return):
        return node  # handled inside async runner

    # === Expressions & Literals ===
    def visit_BinaryOp(self, node: BinaryOp):
        left = node.left.accept(self)
        right = node.right.accept(self)
        if node.op == "+": return left + right
        if node.op == "-": return left - right
        if node.op == "*": return left * right
        if node.op == "/": return left // right if isinstance(left, int) else left / right
        return None

    def visit_Literal(self, node: Literal):
        return node.value

    def visit_Identifier(self, node: Identifier):
        if node.name not in self.env:
            raise Exception(f"Undefined variable '{node.name}'")
        return self.env[node.name]

    def visit_Print(self, node: Print):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)
        print(value)
