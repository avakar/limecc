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

from grammar import Rule, Grammar
from lrparser import make_lrparser
from simple_lexer import simple_lexer, Token
import types, sys
from fa import union_fa, minimize_enfa
from regex_parser import parse_regex, make_enfa_from_regex, make_dfa_from_literal

class LexerConflictError(Exception):
    def __init__(self, rule1, rule2):
        Exception.__init__(self, 'Conflict merging %r and %r' % (rule1, rule2))
        self.rule1 = rule1
        self.rule2 = rule2

class LexRegex:
    def __init__(self, regex):
        self.regex = regex

    def __eq__(self, other):
        return isinstance(other, LexRegex) and self.regex == other.regex

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(self.regex)

    def __str__(self):
        return '{%s}' % self.regex

    def __repr__(self):
        return 'LexRegex(%r)' % self.regex

class LexLiteral:
    def __init__(self, literal):
        self.literal = literal

    def __eq__(self, other):
        return isinstance(other, LexLiteral) and self.literal == other.literal

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(self.literal)

    def __repr__(self):
        return 'LexLiteral(%r)' % self.literal

    def __str__(self):
        return '"' + self.literal + '"'

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
            elif ch == '{':
                self.snippet += 1
            return 'SNIPPET'

        if self.comment:
            if ch == '\n':
                self.comment = False
            return False

        if ch == self.quote:
            self.quote = None
            return
        if self.quote:
            return 'QL'
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
            return 'ID'

        if ch in '~:=.':
            return 'op'

        return ''

def _make_rule(lhs, lhs_name, rhs_list, rule_action):
    r = Rule(lhs, tuple((rhs for rhs, rhs_name in rhs_list)))
    if rule_action != ():
        r.lime_action = rule_action.value
        r.lime_action_pos = rule_action.pos
    else:
        r.lime_action = None
        r.lime_action_pos = None
    r.lhs_name = lhs_name
    r.rhs_names = [rhs_name for rhs, rhs_name in rhs_list]
    return r

class _ParsedGrammar:
    pass

class LimeGrammar:
    def __init__(self):
        self._implicit_tokens = {}
        self._parser = None

    def parse(self, *args, **kw):
        if self._parser is None:
            self._parser = make_lrparser(self.grammar)
        return self._parser.parse(*args, context=self, **kw)

    def _grammar_empty(self):
        g = _ParsedGrammar()
        g.rules = []
        g.extra_symbols = []
        g.context_lexer = False
        g.lex_rules = []
        g.sym_annot = {}
        g.user_include = None
        g.token_type = None # XXX: perhaps default_type?
        g.tests = []
        g.discards = []
        g.root = None
        return g

    def _grammar_kw_user_include(self, g, _kw, incl):
        g.user_include = incl.value
        g.user_include_pos = incl.pos
        return g

    def _grammar_kw_token_type(self, g, _kw, token_type):
        g.token_type = token_type.value
        g.token_type_pos = token_type.pos
        return g

    def _grammar_kw_context_lexer(self, g, _kw):
        g.context_lexer = True
        return g

    def _grammar_type(self, g, type):
        g.sym_annot[type[0]] = type[1]
        return g

    def _grammar_rule(self, g, rule):
        g.rules.append(rule)
        g.tokens = [lex_rhs for lex_rhs, tok_id in sorted(self._implicit_tokens.iteritems(), key=lambda x: x[1])]
        return g

    def _stmt_type(self, lhs, _cc, type):
        return (lhs, type.value)

    def _stmt_type_void(self, lhs, _cc, type):
        if type == 'void':
            return (lhs, None)
        raise RuntimeError("Expected 'void' or a snippet.");

    def _stmt_rule(self, lhs, _cc, rhs_list, _dot, action):
        return _make_rule(lhs, None, rhs_list, action)
    def _stmt_rule2(self, lhs, _lp, lhs_name, _rp, _cc, rhs_list, _dot, action):
        return _make_rule(lhs, lhs_name, rhs_list, action)

    def _rhs_list_start(self):
        return []
    def _rhs_list_append(self, lst, item):
        lst.append(item)
        return lst

    def _named_item(self, sym):
        return (sym, None)
    def _named_item_with_name(self, sym, _lp, annot, _rp):
        return (sym, annot)

    def _named_item_lit(self, lit):
        return self._lex_rhs(LexLiteral(lit))

    def _named_item_lit_with_name(self, lit, _lp, annot, _rp):
        return self._lex_rhs(LexLiteral(lit), annot)

    def _named_item_snippet(self, snippet):
        return self._lex_rhs(LexRegex(snippet.value.strip()))

    def _named_item_snippet_with_name(self, snippet, _lp, annot, _rp):
        return self._lex_rhs(LexRegex(snippet.value.strip()), annot)

    def _lex_rhs(self, rhs, annot=None):
        tok_id = self._implicit_tokens.get(rhs)
        if tok_id is None:
            tok_id = len(self._implicit_tokens)
            self._implicit_tokens[rhs] = tok_id
        return (tok_id, annot)

    def _make_grammar(self, pg):
        g = Grammar(*pg.rules, root=pg.root, symbols=pg.extra_symbols)
        g.context_lexer = pg.context_lexer
        g.tokens = pg.tokens
        g.sym_annot = pg.sym_annot
        g.user_include = pg.user_include
        g.token_type = pg.token_type
        g.tests = pg.tests
        g.discards = pg.discards
        return g

    def _test_list_new(self):
        return []

    def _test_list_id(self, tl, id):
        tl.append(id)
        return tl

    def _test_list_lit(self, tl, lit):
        tl.append(LexLiteral(lit))
        return tl

    def _grammar_kw_test_accept(self, g, _kw, sym, tl, _dot):
        g.tests.append((sym, tl, True))
        return g

    def _grammar_kw_test_reject(self, g, _kw, _not, sym, tl, _dot):
        g.tests.append((sym, tl, False))
        return g

    def _grammar_kw_discard_snip(self, g, _kw, snip):
        g.discards.append(LexRegex(snip.value))
        return g

    def _grammar_kw_discard_ql(self, g, _kw, ql):
        g.discards.append(LexLiteral(ql))
        return g

    def _grammar_kw_root(self, g, _kw, rule):
        return self._grammar_rule(
            self._grammar_kw_root_id(g, _kw, rule.left),
            rule)

    def _grammar_kw_root_id(self, g, _kw, rule):
        if g.root is not None:
            raise RuntimeError('Multiple root specifiers')
        g.root = rule
        return g

    grammar = Grammar(
        Rule('root', ('grammar',), action=_make_grammar),
        Rule('grammar', (), action=_grammar_empty),
        Rule('grammar', ('grammar', 'kw_include', 'SNIPPET'), action=_grammar_kw_user_include),
        Rule('grammar', ('grammar', 'kw_token_type', 'SNIPPET'), action=_grammar_kw_token_type),
        Rule('grammar', ('grammar', 'kw_context_lexer'), action=_grammar_kw_context_lexer),
        Rule('grammar', ('grammar', 'kw_discard', 'SNIPPET'), action=_grammar_kw_discard_snip),
        Rule('grammar', ('grammar', 'kw_discard', 'QL'), action=_grammar_kw_discard_ql),
        Rule('grammar', ('grammar', 'kw_test', 'ID', 'test_list', '.'), action=_grammar_kw_test_accept),
        Rule('grammar', ('grammar', 'kw_test', '~', 'ID', 'test_list', '.'), action=_grammar_kw_test_reject),
        Rule('grammar', ('grammar', 'kw_root', 'rule_stmt'), action=_grammar_kw_root),
        Rule('grammar', ('grammar', 'kw_root', 'ID', '.'), action=_grammar_kw_root_id),
        Rule('grammar', ('grammar', 'type_stmt'), action=_grammar_type),
        Rule('grammar', ('grammar', 'rule_stmt'), action=_grammar_rule),
        Rule('rule_action', ()),
        Rule('rule_action', ('SNIPPET',)),
        Rule('type_stmt', ('ID', '::', 'SNIPPET'), action=_stmt_type),
        Rule('type_stmt', ('ID', '::', 'ID'), action=_stmt_type_void),
        Rule('rule_stmt', ('ID', '::=', 'rhs_list', '.', 'rule_action'), action=_stmt_rule),
        Rule('rule_stmt', ('ID', '(', 'ID', ')', '::=', 'rhs_list', '.', 'rule_action'), action=_stmt_rule2),
        Rule('rhs_list', (), action=_rhs_list_start),
        Rule('rhs_list', ('rhs_list', 'named_item'), action=_rhs_list_append),
        Rule('named_item', ('ID',), action=_named_item),
        Rule('named_item', ('ID', '(', 'ID', ')'), action=_named_item_with_name),
        Rule('named_item', ('QL',), action=_named_item_lit),
        Rule('named_item', ('QL', '(', 'ID', ')'), action=_named_item_lit_with_name),
        Rule('named_item', ('SNIPPET',), action=_named_item_snippet),
        Rule('named_item', ('SNIPPET', '(', 'ID', ')'), action=_named_item_snippet_with_name),
        Rule('test_list', (), action=_test_list_new),
        Rule('test_list', ('test_list', 'ID'), action=_test_list_id),
        Rule('test_list', ('test_list', 'SNIPPET'), action=_test_list_lit),
        Rule('test_list', ('test_list', 'QL'), action=_test_list_lit),
        )

def _lime_lexer(input, filename=None):
    for tok in simple_lexer(input, _LimeLexerClassify(), filename=filename):
        if tok.symbol == 'op':
            yield Token(tok.value, tok.value, tok.pos)
        elif tok.symbol == 'ID' and tok.value[:1] == '%':
            yield Token('kw_' + tok.value[1:], tok.value, tok.pos)
        elif tok.symbol == 'SNIPPET':
            yield Token('SNIPPET', tok.value[:-1], tok.pos)
        else:
            yield tok

def _extract(tok):
    return tok.value if tok.symbol != 'SNIPPET' else tok

def parse_lime_grammar(input, filename=None):
    p = LimeGrammar()
    return p.parse(_lime_lexer(input, filename=filename), extract_value=_extract)

def _lex(p, lex, text):
    g = p.grammar
    for tok, tok_id in lex.tokens(text):
        tok_id = g.lex_rules[tok_id][0][0]
        annot = g.sym_annot.get(tok_id)
        yield (tok_id, tok)

class _LimeLexer:
    def __init__(self, dfa):
        self.set_dfa(dfa)

    def tokens(self, s):
        state = iter(self.dfa.initial).next()

        tok_start = 0
        for i, ch in enumerate(s):
            for e in state.outedges:
                if ch in e.label:
                    state = e.target
                    break
            else:
                yield s[tok_start:i], self.dfa.accept_labels.get(state)
                tok_start = i
                state = iter(self.dfa.initial).next()
                for e in state.outedges:
                    if ch in e.label:
                        state = e.target
                        break
                else:
                    raise RuntimeError('Invalid character encountered at position %d: %c' % (i, ch))

        yield s[tok_start:], self.dfa.accept_labels.get(state)

    def set_dfa(self, dfa):
        assert len(dfa.initial) == 1
        self.dfa = dfa

def _lexparse(p, text, **kw):
    if not p.grammar.context_lexer:
        lex = _LimeLexer(p.lexer)
        return p.parse(_lex(p, lex, text), **kw)
    else:
        lex = _LimeLexer(p.states[0].lexer)
        def update_lex(state):
            lex.set_dfa(state.lexer)
        return p.parse(_lex(p, lex, text), state_visitor=update_lex, **kw)

class _LexDfaAccept:
    def __init__(self, token_id, prio, tokens):
        self.token_id = token_id
        self.prio = prio
        self.tokens = frozenset(tokens)

    def __str__(self):
        return '%d [%s]' % (self.token_id, ', '.join((str(tok) for tok in self.tokens)))

def make_lime_parser(g, **kw):
    p = make_lrparser(g, **kw)
    g = p.grammar

    def process_token(token, token_id):
        if isinstance(token, LexRegex):
            accept = _LexDfaAccept(token_id, 0, [token])
            g = parse_regex(token.regex)
            dfa = make_enfa_from_regex(g, accept)
        else:
            assert isinstance(token, LexLiteral)
            accept = _LexDfaAccept(token_id, 1, [token])
            dfa = make_dfa_from_literal(token.literal, accept)
        return dfa

    fas = []
    for token_id, token in enumerate(g.tokens):
        dfa = process_token(token, token_id)
        fas.append(dfa)
    p.discard_id = len(fas)
    for discard in g.discards:
        dfa = process_token(discard, p.discard_id)
        fas.append(dfa)

    def combine_accept_labels(lhs, rhs):
        if lhs.token_id == rhs.token_id:
            return _LexDfaAccept(lhs.token_id, max(lhs.prio, rhs.prio), lhs.tokens | rhs.tokens)
        if lhs.prio == rhs.prio:
            raise LexerConflictError(lhs.token, rhs.token)
        return lhs if lhs.prio > rhs.prio else rhs

    if not g.context_lexer:
        p.lex_dfas = fas
        p.lexers = [minimize_enfa(union_fa(fas), combine_accept_labels)]
        for state in p.states:
            state.lexer_id = 0
    else:
        # Walk the goto/action tables and determine the list of possible tokens for each state
        lex_map = {}
        term_lists = []
        for state in p.states:
            terms = set((sym for sym in state.goto if sym in g.terminals()))
            terms.add(p.discard_id)
            for lookahead in state.action:
                terms |= set(lookahead)
            terms = frozenset(terms)
            if terms not in lex_map:
                lex_map[terms] = len(term_lists)
                state.lexer_id = len(term_lists)
                term_lists.append(terms)
            else:
                state.lexer_id = lex_map[terms]

        p.lexers = []
        for term_list in term_lists:
            lex_dfas = [fa for token_id, fa in enumerate(fas) if token_id in term_list]
            p.lexers.append(minimize_enfa(union_fa(lex_dfas), combine_accept_labels))

    p.lexparse = types.MethodType(_lexparse, p)
    return p

def print_grammar_as_lime(grammar, translate=lambda x: x, file=sys.stdout):
    def _format_symbol(sym):
        tran_sym = translate(sym)
        if tran_sym is None:
            if all(((ch.isalnum() or ch in '_-%') for ch in sym)):
                return sym
            else:
                return '"%s"' % sym
        else:
            return tran_sym

    for rule in grammar:
        file.write('%s ::= %s.\n' % (rule.left, ' '.join((_format_symbol(sym) for sym in rule.right))))

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
    p = make_lrparser(g)

#    import doctest
#    doctest.testmod()
