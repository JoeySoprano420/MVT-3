# eval_scheduler_join.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.tasks = {}  # name -> asyncio.Task

    # === Async Execution ===
    async def _run_async_block(self, name, body):
        print(f"[Async {name} Start]")
        result = None
        for stmt in body:
            res = stmt.accept(self)
            if isinstance(res, Return):
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

    # === Await Single or Parallel ===
    async def _await_task(self, name):
        if isinstance(name, list):  # parallel await
            print(f"[Await {name}] waiting in parallel...")
            coros = [self.tasks[n] for n in name if n in self.tasks]
            results = await asyncio.gather(*coros)
            print(f"[Await {name}] complete with values: {results}")
            return results
        else:  # single
            if name not in self.tasks:
                print(f"[Await {name}] (no such task)")
                return None
            print(f"[Await {name}] waiting...")
            result = await self.tasks[name]
            print(f"[Await {name}] complete with value: {result}")
            return result

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

    # === Declaration / Assignment with tuple binding ===
    def visit_Declaration(self, node: Declaration):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)

        if isinstance(node.name, list):  # destructuring
            if not isinstance(value, (list, tuple)):
                raise Exception("Parallel await did not return list/tuple")
            for n, v in zip(node.name, value):
                self.env[n] = v
            return value
        else:
            self.env[node.name] = value
            return value

    def visit_Assignment(self, node: Assignment):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)

        if isinstance(node.name, list):  # destructuring
            if not isinstance(value, (list, tuple)):
                raise Exception("Parallel await did not return list/tuple")
            for n, v in zip(node.name, value):
                if n not in self.env:
                    raise Exception(f"Variable '{n}' not declared")
                self.env[n] = v
            return value
        else:
            if node.name not in self.env:
                raise Exception(f"Variable '{node.name}' not declared")
            self.env[node.name] = value
            return value

    # === Expressions ===
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
