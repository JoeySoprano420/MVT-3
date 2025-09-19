# eval_scheduler_async_fn_params.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.funcs = {}      # sync routines
        self.async_funcs = {}  # async routines
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.tasks = {}

    # === Async Routine Definition ===
    def visit_AsyncRoutine(self, node: AsyncRoutine):
        self.async_funcs[node.name] = node
        return None

    # === Sync Routine Definition ===
    def visit_Routine(self, node: Routine):
        self.funcs[node.name] = node
        return None

    # === Call (sync or async) ===
    def visit_Call(self, node: Call):
        if node.name in self.funcs:
            return self._call_sync(self.funcs[node.name], node.args)
        elif node.name in self.async_funcs:
            return self._call_async(self.async_funcs[node.name], node.args)
        else:
            raise Exception(f"Undefined function '{node.name}'")

    # === Sync call ===
    def _call_sync(self, routine, args):
        arg_values = [a.accept(self) for a in args]
        arg_values = [self.loop.run_until_complete(v) if asyncio.iscoroutine(v) else v
                      for v in arg_values]
        call_env = self.env.copy()
        for pattern, value in zip(routine.params, arg_values):
            self._bind_values(pattern, value)
        result = None
        for stmt in routine.body:
            res = stmt.accept(self)
            if isinstance(res, Return):
                result = res.expr.accept(self)
                break
        self.env = call_env
        return result

    # === Async call ===
    def _call_async(self, routine, args):
        async def runner():
            arg_values = [a.accept(self) for a in args]
            arg_values = [await v if asyncio.iscoroutine(v) else v for v in arg_values]
            call_env = self.env.copy()
            for pattern, value in zip(routine.params, arg_values):
                self._bind_values(pattern, value)
            result = None
            for stmt in routine.body:
                res = stmt.accept(self)
                if isinstance(res, Return):
                    result = res.expr.accept(self)
                    break
            self.env = call_env
            return result
        return self.loop.create_task(runner())

    # === Destructuring (reuse from earlier) ===
    def _bind_values(self, names, values):
        if isinstance(names, list):
            if not isinstance(values, (list, tuple)):
                raise Exception("Expected list/tuple for destructure")
            i = 0
            for n in names:
                if isinstance(n, RestSlot):
                    self.env[n.name] = list(values[i:])
                    break
                else:
                    v = values[i] if i < len(values) else None
                    self._bind_values(n, v)
                i += 1

        elif isinstance(names, ObjectPattern):
            if not isinstance(values, dict):
                raise Exception("Expected dict for destructure")
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
            self.env[names.name] = [] if values is None else list(values)

        else:
            self.env[names] = values

    # === Literals ===
    def visit_Literal(self, node: Literal):
        return node.value

    def visit_Return(self, node: Return):
        return node
