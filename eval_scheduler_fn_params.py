# eval_scheduler_fn_params.py
import asyncio
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.funcs = {}     # name -> Routine
        self.loop = asyncio.get_event_loop()
        self.tasks = {}

    # === Routine definition ===
    def visit_Routine(self, node: Routine):
        self.funcs[node.name] = node
        return None

    # === Function call ===
    def visit_Call(self, node: Call):
        if node.name not in self.funcs:
            raise Exception(f"Undefined function '{node.name}'")

        routine = self.funcs[node.name]
        # Evaluate arguments
        arg_values = [a.accept(self) for a in node.args]
        arg_values = [self.loop.run_until_complete(v) if asyncio.iscoroutine(v) else v
                      for v in arg_values]

        # Local environment for call
        call_env = self.env.copy()

        # Destructure args into parameters
        for pattern, value in zip(routine.params, arg_values):
            self._bind_values(pattern, value)

        # Execute body
        result = None
        for stmt in routine.body:
            res = stmt.accept(self)
            if isinstance(res, Return):
                result = res.expr.accept(self)
                break
        self.env = call_env  # restore outer env
        return result

    # === Destructuring (arrays/objects/defaults/rest/aliases) ===
    def _bind_values(self, names, values):
        # identical to previous destructuring logic (supporting list, ObjectPattern, etc.)
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

    # === Expressions ===
    def visit_Literal(self, node: Literal):
        return node.value

    def visit_Return(self, node: Return):
        return node
