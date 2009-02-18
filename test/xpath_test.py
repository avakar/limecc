"""
This is a simple benchmark made in accordance to the following article
<http://www.python.org/community/sigs/retired/parser-sig/towards-standard/>.
"""

from yapylr.docparser import DocParser
from yapylr.simple_lexer import simple_lexer
from yapylr.lrparser import InvalidGrammarError

class _XPathParser:
    """
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
    """

    def p_root(self, lines):
        """
        root = Expr;
        """

_xpath_parser = DocParser(_XPathParser, k=1)

def parse_xpath(input):
    return _xpath_parser.parse(input)

if __name__ == '__main__':
    exprs = [
        "child::para",
        "child::*",
        "child::text()",
        "child::node()",
        "attribute::name",
        "attribute::*",
        "descendant::para",
        "ancestor::div",
        "ancestor-or-self::div",
        "descendant-or-self::para",
        "self::para",
        "child::chapter/descendant::para",
        "child::*/child::para",
        "/",
        "/descendant::para",
        "/descendant::olist/child::item",
        "child::para[position()=1]",
        "child::para[position()=last()]",
        "child::para[position()=last()-1]",
        "child::para[position()>1]",
        "following-sibling::chapter[position()=1]",
        "preceding-sibling::chapter[position()=1]",
        "/descendant::figure[position()=42]",
        "/child::doc/child::chapter[position()=5]/child::section[position()=2]",
        'child::para[attribute::type="warning"]',
        "child::para[attribute::type='warning'][position()=5]",
        'child::para[position()=5][attribute::type="warning"]',
        "child::chapter[child::title='Introduction']",
        "child::chapter[child::title]",
        "child::*[self::chapter or self::appendix]",
        "child::*[self::chapter or self::appendix][position()=last()]",
        "//element[descendant::y[.='z']][1]"
        ]

