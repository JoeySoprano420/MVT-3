# eval_scheduler_combinators.py
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

        # register built-ins
        self.env["map"] = self._builtin_map
        self.env["filter"] = self._builtin_filter
        self.env["reduce"] = self._builtin_reduce

    # === Built-in combinators ===
    async def _builtin_map(self, arr, fn):
        tasks = []
        for v in arr:
            res = fn(v)
            if asyncio.iscoroutine(res):
                tasks.append(res)
            else:
                async def wrap(val): return val
                tasks.append(wrap(res))
        return await asyncio.gather(*tasks)

    async def _builtin_filter(self, arr, fn):
        tasks = []
        for v in arr:
            res = fn(v)
            if asyncio.iscoroutine(res):
                tasks.append(res)
            else:
                async def wrap(val): return val
                tasks.append(wrap(res))
        results = await asyncio.gather(*tasks)
        return [v for v, keep in zip(arr, results) if keep]

    async def _builtin_reduce(self, arr, fn, init):
        acc = init
        for v in arr:
            res = fn(acc, v)
            if asyncio.iscoroutine(res):
                acc = await res
            else:
                acc = res
        return acc

    # === Call (supports higher-order async) ===
    def visit_Call(self, node: Call):
        target = node.name
        if isinstance(target, str):
            fn = self.env.get(target) or self.funcs.get(target) or self.async_funcs.get(target)
            if fn is None:
                raise Exception(f"Undefined function '{target}'")
        else:
            fn = target.accept(self)

        arg_values = [a.accept(self) for a in node.args]
        arg_values = [self.loop.run_until_complete(v) if asyncio.iscoroutine(v) else v
                      for v in arg_values]

        if asyncio.iscoroutinefunction(fn):
            return fn(*arg_values)
        else:
            return fn(*arg_values)
