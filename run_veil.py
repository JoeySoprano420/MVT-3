# run_veil.py
from ast_nodes import *
from eval_visitor import EvalVisitor

task = Program([
    Task(
        Intention("greet_user", []),
        Tool("console"),
        Logic([
            Print(Literal("Hello, World!"))
        ])
    )
])

interpreter = EvalVisitor()
task.accept(interpreter)
