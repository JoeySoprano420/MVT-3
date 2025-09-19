# eval_scheduler.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=8)  # adjustable pool
        self.tasks = {}  # store async tasks by name

    # === Program Root ===
    def visit_Program(self, node: Program):
        results = []
        for stmt in node.body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                results.append(res)
        if results:
            self.loop.run_until_complete(asyncio.gather(*results))

    def visit_Main(self, node: Main):
        results = []
        for stmt in node.body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                results.append(res)
        if results:
            self.loop.run_until_complete(asyncio.gather(*results))

    # === Veil Mode ===
    def visit_Task(self, node: Task):
        print(f"[Task: {node.intention.name}] Tool={node.tool.name}")
        return node.logic.accept(self)

    def visit_Logic(self, node: Logic):
        results = []
        for stmt in node.body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                results.append(res)
        if results:
            self.loop.run_until_complete(asyncio.gather(*results))

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

    # === Async / Await with Scheduling ===
    async def _run_async_block(self, name, body):
        print(f"[Async {name} Start]")
        for stmt in body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                await res
        print(f"[Async {name} End]")
        return f"{name}-result"

    def visit_Async(self, node: Async):
        # Name task by memory id if not explicit
        name = f"task_{id(node)}"
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
        print(f"[Await {name}] complete: {result}")
        return result

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

    # === Fiber Simulation ===
    async def _fiber(self, func, *args):
        """Simulated lightweight fiber"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    def run_fiber(self, func, *args):
        """Public entrypoint for fiber tasks"""
        coro = self._fiber(func, *args)
        return self.loop.run_until_complete(coro)

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

# eval_scheduler_named.py
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

    # === Async / Await with Task Naming ===
    async def _run_async_block(self, name, body):
        print(f"[Async {name} Start]")
        for stmt in body:
            res = stmt.accept(self)
            if asyncio.iscoroutine(res):
                await res
        print(f"[Async {name} End]")
        return f"{name}-result"

    def visit_Async(self, node: Async):
        # Name fallback: explicit name or auto-generated
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
        print(f"[Await {name}] complete: {result}")
        return result

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

    # === (other methods same as before, shortened here for clarity) ===
    def visit_Print(self, node: Print):
        value = node.expr.accept(self)
        print(value)

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

    def visit_Literal(self, node: Literal):
        return node.value

    def visit_Identifier(self, node: Identifier):
        if node.name not in self.env:
            raise Exception(f"Undefined variable '{node.name}'")
        return self.env[node.name]

# eval_scheduler_objects.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.tasks = {}

    # === Async ===
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

    # === Await ===
    async def _await_task(self, name):
        if isinstance(name, list):
            results = []
            for n in name:
                if isinstance(n, list):
                    results.append(await self._await_task(n))
                else:
                    if n not in self.tasks:
                        print(f"[Await {n}] (no such task)")
                        results.append(None)
                    else:
                        print(f"[Await {n}] waiting...")
                        results.append(await self.tasks[n])
                        print(f"[Await {n}] complete")
            return results
        else:
            if name not in self.tasks:
                print(f"[Await {name}] (no such task)")
                return None
            print(f"[Await {name}] waiting...")
            result = await self.tasks[name]
            print(f"[Await {name}] complete with value: {result}")
            return result

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

    # === Binding logic: arrays + objects ===
    def _bind_values(self, names, values):
        # Array-like destructuring
        if isinstance(names, list):
            if not isinstance(values, (list, tuple)):
                raise Exception("Mismatch: expected list/tuple in destructuring")
            i = 0
            for n in names:
                if isinstance(n, RestSlot):
                    self.env[n.name] = list(values[i:])
                    break
                else:
                    v = values[i] if i < len(values) else None
                    self._bind_values(n, v)
                i += 1

        # Object-like destructuring
        elif isinstance(names, ObjectPattern):
            if not isinstance(values, dict):
                raise Exception("Mismatch: expected dict/object in destructuring")
            for slot in names.slots:
                v = values.get(slot.key)
                if v is None and slot.default:
                    v = slot.default.accept(self)
                self.env[slot.name] = v
                if slot.alias:
                    self.env[slot.alias] = v

        # Slot with default
        elif isinstance(names, DestructureSlot):
            v = values
            if v is None and names.default:
                v = names.default.accept(self)
            self.env[names.name] = v

        # Slot with alias
        elif isinstance(names, AliasSlot):
            v = values
            if v is None and names.default:
                v = names.default.accept(self)
            self.env[names.name] = v
            self.env[names.alias] = v

        # Rest fallback
        elif isinstance(names, RestSlot):
            self.env[names.name] = [] if values is None else list(values)

        # Primitive variable
        else:
            self.env[names] = values

    def visit_Declaration(self, node: Declaration):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)
        self._bind_values(node.name, value)
        return value

    def visit_Assignment(self, node: Assignment):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)
        self._bind_values(node.name, value)
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

