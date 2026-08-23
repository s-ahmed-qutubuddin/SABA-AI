import ast, operator as op
_OPS={ast.Add:op.add,ast.Sub:op.sub,ast.Mult:op.mul,ast.Div:op.truediv,ast.Pow:op.pow,ast.Mod:op.mod,ast.USub:op.neg}

def calculate(expr):
    node=ast.parse(expr, mode='eval').body
    def ev(n):
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return n.value
        if isinstance(n,ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n,ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.left),ev(n.right))
        raise ValueError('Unsupported expression')
    return ev(node)
