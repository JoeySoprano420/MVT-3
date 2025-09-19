# eval_scheduler_hof.py
import asyncio
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.funcs = {}
        self.async_funcs = {}
        self.loop = asyncio.get_event_loop()
        self.tasks = {}

    # === Async Lambda Definition ===
    def visit_AsyncLambda(self, node: AsyncLambda):
        async def fn(*args):
            call_env = self.env.copy()
            for pattern, value in zip(node.params, args):
                self._bind_values(pattern, value)
            result = None
            for stmt in node.body:
                res = stmt.accept(self)
                if isinstance(res, Return):
                    result = res.expr.accept(self)
                    break
            self.env = call_env
            return result
        return fn

    # === Named Async Routine ===
    def visit_AsyncRoutine(self, node: AsyncRoutine):
        async def fn(*args):
            call_env = self.env.copy()
            for pattern, value in zip(node.params, args):
                self._bind_values(pattern, value)
            result = None
            for stmt in node.body:
                res = stmt.accept(self)
                if isinstance(res, Return):
                    result = res.expr.accept(self)
                    break
            self.env = call_env
            return result
        self.async_funcs[node.name] = fn
        return fn

    # === Call (sync or async, direct or variable) ===
    def visit_Call(self, node: Call):
        target = node.name
        if isinstance(target, str):
            if target in self.funcs:
                fn = self.funcs[target]
            elif target in self.async_funcs:
                fn = self.async_funcs[target]
            elif target in self.env and callable(self.env[target]):
                fn = self.env[target]
            else:
                raise Exception(f"Undefined function '{target}'")
        else:
            fn = target.accept(self)

        # Evaluate args
        arg_values = [a.accept(self) for a in node.args]
        arg_values = [self.loop.run_until_complete(v) if asyncio.iscoroutine(v) else v
                      for v in arg_values]

        if asyncio.iscoroutinefunction(fn):
            return fn(*arg_values)
        else:
            return fn(*arg_values)

    # === Await ===
    async def _await_task(self, expr):
        v = expr.accept(self) if hasattr(expr, "accept") else expr
        if asyncio.iscoroutine(v):
            return await v
        return v

    def visit_Await(self, node: Await):
        return self._await_task(node.name)

    # === Binding helpers (reuse) ===
    def _bind_values(self, names, values):
        if isinstance(names, list):
            for n, v in zip(names, values):
                self._bind_values(n, v)
        elif isinstance(names, ObjectPattern):
            for slot in names.slots:
                v = values.get(slot.key)
                if v is None and slot.default:
                    v = slot.default.accept(self)
                self.env[slot.name] = v
                if slot.alias:
                    self.env[slot.alias] = v
        elif isinstance(names, DestructureSlot):
            v = values
            if v is None and names.default:
                v = names.default.accept(self)
            self.env[names.name] = v
        elif isinstance(names, AliasSlot):
            v = values
            if v is None and names.default:
                v = names.default.accept(self)
            self.env[names.name] = v
            self.env[names.alias] = v
        elif isinstance(names, RestSlot):
            self.env[names.name] = list(values)
        else:
            self.env[names] = values

    # === Literals, Return, Identifiers ===
    def visit_Literal(self, node: Literal):
        return node.value

    def visit_Return(self, node: Return):
        return node

    def visit_Identifier(self, node: Identifier):
        if node.name not in self.env:
            raise Exception(f"Undefined variable '{node.name}'")
        return self.env[node.name]
