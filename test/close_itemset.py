from yapylr.ebnf_grammar import ebnf_parse
from yapylr.grammar import Grammar
from yapylr.first import First

grammar = Grammar(*ebnf_parse("""
LocationPath = RelativeLocationPath | AbsoluteLocationPath;
AbsoluteLocationPath = '/' | '/', RelativeLocationPath | AbbreviatedAbsoluteLocationPath;
RelativeLocationPath = Step | RelativeLocationPath, '/', Step | AbbreviatedRelativeLocationPath;
Step = Basis, predicates | AbbreviatedStep;
predicates =  { Predicate };
Basis = AXISNAME, AXISSUF, NodeTest | AbbreviatedBasis;
NodeTest = WILDCARDNAME | NODETYPE, '(', arglist, ')';
arglist = [ args ];
args = Expr | args, ',', Expr;
Predicate = '[', PredicateExpr, ']';
PredicateExpr = Expr;
AbbreviatedAbsoluteLocationPath = '//', RelativeLocationPath;
AbbreviatedRelativeLocationPath = RelativeLocationPath, '//', Step;
AbbreviatedStep = '.' | PARENT;
AbbreviatedBasis = NodeTest | '@', NodeTest;

Expr = OrExpr;
PrimaryExpr = VARIABLEREFERENCE | '(', Expr, ')' | LITERAL
    | NUMBER | FunctionCall;
FunctionCall = FUNCTIONNAME, '(', arglist, ')';
UnionExpr = PathExpr | UnionExpr, '|', PathExpr;
PathExpr = LocationPath | FilterExpr | FilterExpr, '/', RelativeLocationPath
    | FilterExpr, '//', RelativeLocationPath;
FilterExpr = PrimaryExpr | FilterExpr, Predicate;
OrExpr = AndExp | OrExpr, OR, AndExpr;
AndExpr = EqualityExpr | AndExpr, AND, EqualityExpr;
EqualityExpr = RelationalExpr | EqualityExpr, '=', RelationalExpr
    | EqualityExpr, NE, RelationalExpr;
RelationalExpr = AdditiveExpr | RelationalExpr, '<', AdditiveExpr
    | RelationalExpr, '>', AdditiveExpr
    | RelationalExpr, LE, AdditiveExpr
    | RelationalExpr, GE, AdditiveExpr;
AdditiveExpr = MultiplicativeExpr
    | AdditiveExpr, '+', MultiplicativeExpr
    | AdditiveExpr, '-', MultiplicativeExpr;
MultiplicativeExpr = UnaryExpr
    | MultiplicativeExpr, MULTIPLYOPERATOR, UnaryExpr
    | MultiplicativeExpr, DIV, UnaryExpr
    | MultiplicativeExpr, MOD, UnaryExpr
    | MultiplicativeExpr, QUO, UnaryExpr;
UnaryExpr = UnionExpr | '-', UnaryExpr;
"""))

first = First(grammar)

from yapylr.lrparser import _State, _Item
from yapylr.rule import Rule

r = Rule('MultiplicativeExpr', ('MultiplicativeExpr', 'QUO', 'UnaryExpr'))

kernel = [
    _Item(r, 2, ('NE',)),
    _Item(r, 2, ('<',)),
    _Item(r, 2, ('QUO',)),
    _Item(r, 2, ('DIV',)),
    _Item(r, 2, ('MOD',)),
    _Item(r, 2, ('=',)),
    _Item(r, 2, ('AND',)),
    _Item(r, 2, ('OR',)),
    _Item(r, 2, ('+',)),
    _Item(r, 2, ('MULTIPLYOPERATOR',)),
    _Item(r, 2, ('GE',)),
    _Item(r, 2, ('-',)),
    _Item(r, 2, ('>',)),
    _Item(r, 2, ('LE',)),
    _Item(r, 2, ()),
]

s = _State(kernel)

print "Starting the closure operation..."

from datetime import datetime
start = datetime.utcnow()
s.close(grammar, first)
stop = datetime.utcnow()
print stop - start
