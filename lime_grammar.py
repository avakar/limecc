"""Provides a the grammar parser for the LIME grammar compiler.

The parser converts LIME grammar to Rule objects. LIME grammar
is a simplified EBNF-like grammar that borrows a few key principles
from the LEMON grammar compiler and adds a few more.

LIME grammar is a sequence of grammar rules and directives.
The rules are of the form `LHS ::= RHS;`, where `LHS` is a non-terminal
and `RHS` is a sequence of (terminal or non-terminal) symbols.
The only directive currently recognized is the `LHS :: { type }`
directive, which assigns a type (of the target language) to a non-terminal.

Each symbol in a rule can be annotated with a piece of
code that is not interpreted by the parser, but is passed on in
the corresponding Rule object.
"""

from rule import Rule
from grammar import Grammar
from lrparser import Parser
from docparser import parser_LR, action, matcher
from simple_lexer import simple_lexer

class LexDiscard:
    pass

class LexRegex:
    def __init__(self, regex):
        self.regex = regex

    def __eq__(self, other):
        return isinstance(other, LexRegex) and self.regex == other.regex

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(self.regex)

class LexLiteral:
    def __init__(self, literal):
        self.literal = literal

    def __eq__(self, other):
        return isinstance(other, LexLiteral) and self.literal == other.literal

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(self.literal)

class _LimeLexerClassify:
    def __init__(self):
        self.quote = None
        self.comment = False
        self.snippet = 0
        self.escape = False

    def __call__(self, ch):
        if self.snippet != 0:
            if ch == '}':
                self.snippet -= 1
                if not self.snippet:
                    return
            elif ch == '{':
                self.snippet += 1
            return 'snippet'

        if self.comment:
            if ch == '\n':
                self.comment = False
            return False

        if ch == self.quote:
            self.quote = None
            return
        if self.quote:
            return 'ql'
        if ch in '\'"':
            self.quote = ch
            return

        if ch == '{':
            self.snippet = 1
            return

        if ch == '#':
            self.comment = True
            return

        if ch.isspace():
            return

        if ch.isalnum() or ch in '_-%':
            return 'id'

        return ''

def _make_rule(lhs, lhs_name, rhs_list, rule_action):
    r = Rule(lhs, tuple((rhs for rhs, rhs_name in rhs_list)))
    r.lime_action = rule_action
    r.lhs_name = lhs_name
    r.rhs_names = [rhs_name for rhs, rhs_name in rhs_list]
    return r

@parser_LR(1)
class _LimeGrammar:
    """
    rule_action = ;
    rule_action = snippet;
    """

    def __init__(self):
        self.implicit_tokens = {}

    @action
    def root(self, g):
        """
        root = grammar;
        """
        for lex_rhs, token_name in self.implicit_tokens.iteritems():
            g.lex_rules.append(((token_name, None), (lex_rhs, None), None))
        return g

    @action
    def grammar_empty(self):
        """
        grammar = ;
        """
        g = Grammar()
        g.lex_rules = []
        g.sym_annot = {}
        g.token_type = None # XXX: perhaps default_type?
        return g

    @action
    def grammar_kw_token_type(self, g, token_type):
        """
        grammar = grammar, _kw_token_type, snippet;
        """
        g.token_type = token_type
        return g

    @action
    def grammar_type(self, g, type):
        """
        grammar = grammar, type_stmt;
        """
        g.sym_annot[type[0]] = type[1]
        return g

    @action
    def grammar_rule(self, g, rule):
        """
        grammar = grammar, rule_stmt;
        """
        rule.id = len(g)
        g.add(rule)
        return g

    @action
    def grammar_lex(self, g, rule):
        """
        grammar = grammar, lex_stmt;
        """
        g.lex_rules.append(rule)
        return g

    @action
    def lex_stmt(self, lhs, rhs, action=None):
        """
        lex_stmt = lex_lhs, '~=', lex_rhs;
        lex_stmt = lex_lhs, '~=', lex_rhs, snippet;
        """
        return (lhs, rhs, action)

    @action
    def lex_lhs(self, lhs, lhs_name=None):
        """
        lex_lhs = id;
        lex_lhs = id, '(', id, ')';
        """
        return (lhs, lhs_name)

    @action
    def lex_rhs(self, rhs, rhs_name=None):
        """
        lex_rhs = snippet;
        lex_rhs = snippet, '(', id, ')';
        """
        return (LexRegex(rhs), rhs_name)

    @action
    def lex_rhs_lit(self, rhs, rhs_name=None):
        """
        lex_rhs = ql;
        lex_rhs = ql, '(', id, ')';
        """
        return (LexLiteral(rhs), rhs_name)

    @action
    def stmt_type(self, lhs, type):
        """
        type_stmt = id, '::', snippet;
        """
        return (lhs, type)

    @action
    def stmt_type_void(self, lhs, type):
        """
        type_stmt = id, '::', id;
        """
        if type == 'discard':
            return lhs, LexDiscard()
        if type == 'void':
            return (lhs, None)
        raise RuntimeError("Expected 'void', 'discard' or a snippet.");

    @action
    def stmt_rule(self, lhs, rhs_list, action):
        """
        rule_stmt = id, '::=', rhs_list, '.', rule_action;
        """
        return _make_rule(lhs, None, rhs_list, action)

    @action
    def stmt_rule2(self, lhs, lhs_name, rhs_list, action):
        """
        rule_stmt = id, '(', id, ')', '::=', rhs_list, '.', rule_action;
        """
        return _make_rule(lhs, lhs_name, rhs_list, action)

    @action
    def rhs_list_start(self, *args):
        """
        rhs_list = ;
        """
        return list(args)

    @action
    def rhs_list_append(self, lst, item):
        """
        rhs_list = rhs_list, named_item;
        """
        lst.extend(item)
        return lst

    @action
    def named_item(self, sym, annot=None):
        """
        named_item = id;
        named_item = id, '(', id, ')';
        """
        return [(sym, annot)]

    @action
    def named_item_lit(self, snippet):
        """
        named_item = ql;
        """
        snippet = snippet.strip()
        snippet = LexLiteral(snippet)
        return self._lex_rhs(snippet)

    @action
    def named_item_snippet(self, snippet):
        """
        named_item = snippet;
        """
        snippet = snippet.strip()
        snippet = LexRegex(snippet)
        return self._lex_rhs(snippet)

    def _lex_rhs(self, rhs):
        tok_name = self.implicit_tokens.get(rhs)
        if not tok_name:
            tok_name = '_implicit_%d' % len(self.implicit_tokens)
            self.implicit_tokens[rhs] = tok_name
        return [(tok_name, None)]

def lime_lexer(input):
    for tok in simple_lexer(input, _LimeLexerClassify()):
        if isinstance(tok, tuple) and tok[0] == 'id' and tok[1][:1] == '%':
            yield ('kw_' + tok[1][1:], tok[1])
        else:
            yield tok

def parse_lime_grammar(input):
    p = _LimeGrammar()
    from lrparser import extract_second
    return p.parse(lime_lexer(input), extract_value=extract_second)

if __name__ == "__main__":
    test = """
ws :: discard
ws ~= {\s}

num :: {double}
num ~= {\d+}(s) { return atoi(s.c_str()); }

expr :: {double}
expr ::= mul.
expr(E) ::= expr(E1) '+' mul(E2). { E = E1 + E2; }
expr(E) ::= expr(E1) '-' mul(E2). { E = E1 - E2; }

mul :: {double}
mul ::= term.
mul(E) ::= mul(E1) '*' term(E2). { E = E1 * E2; }
mul(E) ::= mul(E1) '/' term(E2). { E = E1 / E2; }

term :: {double}
term ::= atom.
term(A) ::= '+' atom(E). { A = E; }
term(A) ::= '-' atom(E). { A = -E; }

atom :: {double}
atom(A) ::= num(B). { A = B; }
atom(A) ::= '(' expr(E) ')'. { A = E; }

num(A) ::= digit(B). { A = B; }
num(A) ::= num(B) digit(C). { A = 10*B + C; }
num(A) ::= num(B) '_'. { A = B; }
"""

    g = parse_lime_grammar(test)
    p = Parser(g)

#    import doctest
#    doctest.testmod()
