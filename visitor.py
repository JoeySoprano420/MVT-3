# visitor.py
class ASTVisitor:
    def generic_visit(self, node):
        raise Exception(f"No visit_{node.__class__.__name__} defined")

    def visit_Program(self, node): pass
    def visit_Main(self, node): pass
    def visit_Prog(self, node): pass
    def visit_Task(self, node): pass
    def visit_Intention(self, node): pass
    def visit_Tool(self, node): pass
    def visit_Logic(self, node): pass
    def visit_Declaration(self, node): pass
    def visit_Assignment(self, node): pass
    def visit_Print(self, node): pass
    def visit_Return(self, node): pass
    def visit_If(self, node): pass
    def visit_Loop(self, node): pass
    def visit_TryCatch(self, node): pass
    def visit_Async(self, node): pass
    def visit_Await(self, node): pass
    def visit_BinaryOp(self, node): pass
    def visit_UnaryOp(self, node): pass
    def visit_Literal(self, node): pass
    def visit_Identifier(self, node): pass
