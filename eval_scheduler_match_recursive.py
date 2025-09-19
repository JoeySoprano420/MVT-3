# eval_scheduler_match_recursive.py
import asyncio
from ast_nodes import *
from visitor import ASTVisitor

class EvalVisitor(ASTVisitor):
    def __init__(self):
        self.env = {}
        self.loop = asyncio.get_event_loop()
        self.tasks = {}

    def visit_Match(self, node: Match):
        value = node.expr.accept(self)
        if asyncio.iscoroutine(value):
            value = self.loop.run_until_complete(value)

        for case in node.cases:
            env_snapshot = self.env.copy()  # rollback if pattern fails
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
            self.env = env_snapshot  # reset if this case fails

    # === Recursive Pattern Matcher ===
    def _match_pattern(self, pattern, value):
        # Wildcard
        if pattern == "_":
            return True

        # Identifier binding
        if isinstance(pattern, str):
            self.env[pattern] = value
            return True

        # Array / list pattern
        if isinstance(pattern, list):
            if not isinstance(value, (list, tuple)):
                return False
            if len(pattern) > len(value):
                return False
            for p, v in zip(pattern, value):
                if not self._match_pattern(p, v):
                    return False
            return True

        # Object pattern
        if isinstance(pattern, ObjectPattern):
            if not isinstance(value, dict):
                return False
            for slot in pattern.slots:
                if slot.key not in value:
                    if slot.default:
                        self.env[slot.name] = slot.default.accept(self)
                        if slot.alias:
                            self.env[slot.alias] = self.env[slot.name]
                        continue
                    return False
                v = value[slot.key]
                # nested object or value
                if isinstance(slot.name, (ObjectPattern, list)):
                    if not self._match_pattern(slot.name, v):
                        return False
                else:
                    self.env[slot.name] = v
                    if slot.alias:
                        self.env[slot.alias] = v
            return True

        # Slots
        if isinstance(pattern, DestructureSlot):
            v = value
            if v is None and pattern.default:
                v = pattern.default.accept(self)
            self.env[pattern.name] = v
            return True

        if isinstance(pattern, AliasSlot):
            v = value
            if v is None and pattern.default:
                v = pattern.default.accept(self)
            self.env[pattern.name] = v
            self.env[pattern.alias] = v
            return True

        if isinstance(pattern, RestSlot):
            self.env[pattern.name] = value if value is not None else []
            return True

        return False
