from typing import List, Optional
from .ast import Node

class Expr(Node):
    pass

class Rule(Node):
    sym: str
    expr: Expr

class Choice(Expr):
    exprs: List[Expr]

class Seq(Expr):
    exprs: List[Expr]

class Lookahead(Expr):
    expr: Expr

class Notahead(Expr):
    expr: Expr

class Opt(Expr):
    expr: Expr

class Star(Expr):
    expr: Expr

class Plus(Expr):
    expr: Expr

class NamedItem(Expr):
    param: Optional[str]

class Symbol(NamedItem):
    name: str

class Literal(NamedItem):
    value: str

class Snippet(NamedItem):
    value: str
