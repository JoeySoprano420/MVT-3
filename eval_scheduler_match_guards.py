# eval_scheduler_match_guards.py
import asyncio
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.tasks = {}

    # === Match with Guards ===
    def visit_Match(self, node: Match):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)

        for case in node.cases:
            if self._match_pattern(case.pattern, value):
                guard_ok = True
                if case.guard:
                    guard_val = case.guard.accept(self)
                    if asyncio.iscoroutine(guard_val):
                        guard_val = self.loop.run_until_complete(guard_val)
                    guard_ok = bool(guard_val)
                if guard_ok:
                    for stmt in case.body:
                        res = stmt.accept(self)
                        if asyncio.iscoroutine(res):
                            self.loop.run_until_complete(res)
                    return
        # nothing matched → do nothing

    def _match_pattern(self, pattern, value):
        if pattern == "_":
            return True
        if isinstance(pattern, str):
            self.env[pattern] = value
            return True
        if isinstance(pattern, list):
            if not isinstance(value, (list, tuple)):
                return False
            if len(pattern) > len(value):
                return False
            self._bind_values(pattern, value)
            return True
        if isinstance(pattern, ObjectPattern):
            if not isinstance(value, dict):
                return False
            try:
                self._bind_values(pattern, value)
                return True
            except Exception:
                return False
        return False
