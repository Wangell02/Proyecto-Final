import ast

with open('PEA-Scraper/DLDD-MAFF-JDLA.py', 'r', encoding='utf-8') as f:
    code = f.read()

tree = ast.parse(code)

class Checker(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.scope_stack = []

    def visit_FunctionDef(self, node):
        self.scope_stack.append(node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.scope_stack.append(node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Break(self, node):
        if (3500 <= node.lineno <= 4700) or (6620 <= node.lineno <= 6680):
            self.violations.append((node.lineno, 'break'))
        self.generic_visit(node)

    def visit_Continue(self, node):
        if (3500 <= node.lineno <= 4700) or (6620 <= node.lineno <= 6680):
            self.violations.append((node.lineno, 'continue'))
        self.generic_visit(node)

    def visit_IfExp(self, node):
        if (3500 <= node.lineno <= 4700) or (6620 <= node.lineno <= 6680):
            self.violations.append((node.lineno, 'ternary IfExp'))
        self.generic_visit(node)

    def visit_Return(self, node):
        if (3500 <= node.lineno <= 4700) or (6620 <= node.lineno <= 6680):
            if self.scope_stack:
                fn = self.scope_stack[-1]
                # If function returns None or -> None
                returns_none = False
                if fn.returns:
                    if isinstance(fn.returns, ast.Constant) and fn.returns.value is None:
                        returns_none = True
                    elif isinstance(fn.returns, ast.Name) and fn.returns.id == 'None':
                        returns_none = True
                if returns_none and node.value is not None:
                    self.violations.append((node.lineno, f'return with value in void function {fn.name}'))
                elif returns_none and node.value is None:
                    # check if it's an early return inside a void function
                    # let's flag it to be safe
                    self.violations.append((node.lineno, f'return statement in void function {fn.name}'))
        self.generic_visit(node)

c = Checker()
c.visit(tree)
print("Violations found in modified regions:", len(c.violations))
for v in c.violations:
    print(v)
