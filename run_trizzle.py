# run_trizzle.py
from ast_nodes import *
from eval_visitor import EvalVisitor

# Program: Fibonacci(0..5)
prog = Program([
    Main([
        Declaration("n", Literal(5)),
        Declaration("a", Literal(0)),
        Declaration("b", Literal(1)),
        Loop("i", Literal(0), Identifier("n"), [
            Print(Identifier("a")),
            Assignment("a", Identifier("b")),
            Assignment("b", BinaryOp(Identifier("a"), "+", Identifier("b")))
        ])
    ])
])

interpreter = EvalVisitor()
prog.accept(interpreter)
