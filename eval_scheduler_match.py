# eval_scheduler_match.py
import asyncio
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.tasks = {}

    # (reuse async/await logic from previous version…)

    # === Pattern Matching ===
    def visit_Match(self, node: Match):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)

        for case in node.cases:
            if self._match_pattern(case.pattern, value):
                for stmt in case.body:
                    res = stmt.accept(self)
                    if asyncio.iscoroutine(res):
                        self.loop.run_until_complete(res)
                return
        # no case matched → do nothing

    def _match_pattern(self, pattern, value):
        # Wildcard
        if pattern == "_":
            return True
        # Variable name
        if isinstance(pattern, str):
            self.env[pattern] = value
            return True
        # Array pattern
        if isinstance(pattern, list):
            if not isinstance(value, (list, tuple)):
                return False
            if len(pattern) > len(value):
                return False
            # bind with destructure semantics
            self._bind_values(pattern, value)
            return True
        # Object pattern
        if isinstance(pattern, ObjectPattern):
            if not isinstance(value, dict):
                return False
            try:
                self._bind_values(pattern, value)
                return True
            except Exception:
                return False
        return False
