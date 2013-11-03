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
from lime_lexer import LimeLexer
from fa import union_fa, minimize_enfa
from regex_parser import parse_regex, make_enfa_from_regex, make_dfa_from_literal

class LexerConflictError(Exception):
    def __init__(self, rule1, rule2):
        Exception.__init__(self, 'Conflict merging %r and %r' % (rule1, rule2))
        self.rule1 = rule1
        self.rule2 = rule2

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
        self._processed_implicit_tokens = set()
        self._parser = None

    def parse(self, *args, **kw):
        if self._parser is None:
            self._parser = make_lrparser(self.grammar)
        return self._parser.parse(*args, context=self, **kw)

    def _update_implicit_tokens(self, g):
        for lex_rhs, token_name in self._implicit_tokens.iteritems():
            if token_name not in self._processed_implicit_tokens:
                g.lex_rules.append(((token_name, None), (lex_rhs, None), None, None))
                g.token_comments[token_name] = lex_rhs
                self._processed_implicit_tokens.add(token_name)

    def _grammar_empty(self):
        g = _ParsedGrammar()
        g.rules = []
        g.extra_symbols = []
        g.context_lexer = False
        g.lex_rules = []
        g.sym_annot = {}
        g.token_comments = {}
        g.user_include = None
        g.token_type = None # XXX: perhaps default_type?
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
        self._update_implicit_tokens(g)
        return g

    def _grammar_lex(self, g, rule):
        g.lex_rules.append(rule)
        g.extra_symbols.append(rule[0][0])
        return g

    def _lex_stmt(self, lhs, _eq, rhs):
        return (lhs, rhs, None, None)
    def _lex_stmt_with_action(self, lhs, _eq, rhs, action):
        return (lhs, rhs, action.value, action.pos)

    def _lex_lhs(self, lhs):
        return (lhs, None)
    def _lex_lhs_with_name(self, lhs, _lparen, lhs_name, _rparen):
        return (lhs, lhs_name)

    def _lex_rhs_snip(self, rhs):
        return (LexRegex(rhs.value), None)
    def _lex_rhs_snip_with_name(self, rhs, _lparen, rhs_name, _rparen):
        return (LexRegex(rhs.value), rhs_name)

    def _lex_rhs_lit(self, rhs):
        return (LexLiteral(rhs), None)
    def _lex_rhs_lit_with_name(self, rhs, _lparen, rhs_name, _rparen):
        return (LexLiteral(rhs), rhs_name)

    def _stmt_type(self, lhs, _cc, type):
        return (lhs, type.value)

    def _stmt_type_void(self, lhs, _cc, type):
        if type == 'discard':
            return lhs, LexDiscard()
        if type == 'void':
            return (lhs, None)
        raise RuntimeError("Expected 'void', 'discard' or a snippet.");

    def _stmt_rule(self, lhs, _cc, rhs_list, _dot, action):
        return _make_rule(lhs, None, rhs_list, action)
    def _stmt_rule2(self, lhs, _lp, lhs_name, _rp, _cc, rhs_list, _dot, action):
        return _make_rule(lhs, lhs_name, rhs_list, action)

    def _rhs_list_start(self):
        return []
    def _rhs_list_append(self, lst, item):
        lst.extend(item)
        return lst

    def _named_item(self, sym):
        return [(sym, None)]
    def _named_item_with_name(self, sym, _lp, annot, _rp):
        return [(sym, annot)]

    def _named_item_lit(self, snippet):
        snippet = snippet.strip()
        snippet = LexLiteral(snippet)
        return self._lex_rhs(snippet)

    def _named_item_snippet(self, snippet):
        snippet = snippet.value.strip()
        snippet = LexRegex(snippet)
        return self._lex_rhs(snippet)

    def _lex_rhs(self, rhs):
        tok_name = self._implicit_tokens.get(rhs)
        if not tok_name:
            tok_name = '_implicit_%d' % len(self._implicit_tokens)
            self._implicit_tokens[rhs] = tok_name
        return [(tok_name, None)]

    def _make_grammar(self, pg):
        g = Grammar(*pg.rules, symbols=pg.extra_symbols)
        g.context_lexer = pg.context_lexer
        g.lex_rules = pg.lex_rules
        g.sym_annot = pg.sym_annot
        g.token_comments = pg.token_comments
        g.user_include = pg.user_include
        g.token_type = pg.token_type
        return g

    grammar = Grammar(
        Rule('root', ('grammar',), action=_make_grammar),
        Rule('grammar', (), action=_grammar_empty),
        Rule('grammar', ('grammar', 'kw_include', 'SNIPPET'), action=_grammar_kw_user_include),
        Rule('grammar', ('grammar', 'kw_token_type', 'SNIPPET'), action=_grammar_kw_token_type),
        Rule('grammar', ('grammar', 'kw_context_lexer'), action=_grammar_kw_context_lexer),
        Rule('grammar', ('grammar', 'type_stmt'), action=_grammar_type),
        Rule('grammar', ('grammar', 'rule_stmt'), action=_grammar_rule),
        Rule('grammar', ('grammar', 'lex_stmt'), action=_grammar_lex),
        Rule('rule_action', ()),
        Rule('rule_action', ('SNIPPET',)),
        Rule('lex_stmt', ('lex_lhs', '~=', 'lex_rhs'), action=_lex_stmt),
        Rule('lex_stmt', ('lex_lhs', '~=', 'lex_rhs', 'SNIPPET'), action=_lex_stmt_with_action),
        Rule('lex_lhs', ('ID',), action=_lex_lhs),
        Rule('lex_lhs', ('ID', '(', 'ID', ')'), action=_lex_lhs_with_name),
        Rule('lex_rhs', ('SNIPPET',), action=_lex_rhs_snip),
        Rule('lex_rhs', ('SNIPPET', '(', 'ID', ')'), action=_lex_rhs_snip_with_name),
        Rule('lex_rhs', ('QL',), action=_lex_rhs_lit),
        Rule('lex_rhs', ('QL', '(', 'ID', ')'), action=_lex_rhs_lit_with_name),
        Rule('type_stmt', ('ID', '::', 'SNIPPET'), action=_stmt_type),
        Rule('type_stmt', ('ID', '::', 'ID'), action=_stmt_type_void),
        Rule('rule_stmt', ('ID', '::=', 'rhs_list', '.', 'rule_action'), action=_stmt_rule),
        Rule('rule_stmt', ('ID', '(', 'ID', ')', '::=', 'rhs_list', '.', 'rule_action'), action=_stmt_rule2),
        Rule('rhs_list', (), action=_rhs_list_start),
        Rule('rhs_list', ('rhs_list', 'named_item'), action=_rhs_list_append),
        Rule('named_item', ('ID',), action=_named_item),
        Rule('named_item', ('ID', '(', 'ID', ')'), action=_named_item_with_name),
        Rule('named_item', ('QL',), action=_named_item_lit),
        Rule('named_item', ('SNIPPET',), action=_named_item_snippet)
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
        if isinstance(annot, LexDiscard):
            continue
        yield (tok_id, tok)

def _lexparse(p, text, **kw):
    if not p.grammar.context_lexer:
        lex = LimeLexer(p.lexer)
        return p.parse(_lex(p, lex, text), **kw)
    else:
        lex = LimeLexer(p.states[0].lexer)
        def update_lex(state):
            lex.set_dfa(state.lexer)
        return p.parse(_lex(p, lex, text), state_visitor=update_lex, **kw)

def _build_multidfa(lex_rules, allowed_syms=None):
    fas = []
    rule_fa_list = []
    priorities = {}
    for i, lex_rule in enumerate(lex_rules):
        (lhs, lhs_name), (rhs, rhs_name), action, pos = lex_rule
        if allowed_syms is not None and lhs not in allowed_syms:
            continue
        if isinstance(rhs, LexRegex):
            g2 = parse_regex(rhs.regex)
            fa = make_enfa_from_regex(g2, i)
            priorities[i] = 0
        else:
            fa = make_dfa_from_literal(rhs.literal, i)
            priorities[i] = 1
        fas.append(fa)
        rule_fa_list.append((lhs, rhs, fa))

    def _combine_accept_labels(lhs, rhs):
        lhs_prio = priorities[lhs]
        rhs_prio = priorities[rhs]
        if lhs_prio == rhs_prio:
            raise LexerConflictError(lex_rules[lhs][1][0], lex_rules[rhs][1][0])
        return lhs if lhs_prio > rhs_prio else rhs

    enfa = union_fa(fas)
    return rule_fa_list, minimize_enfa(enfa, _combine_accept_labels)

def make_lime_parser(g, **kw):
    p = make_lrparser(g, **kw)

    g = p.grammar
    if g.context_lexer:
        # Discard tokens are always enabled
        discard_terms = set((term for term in g.terminals() if isinstance(g.sym_annot.get(term), LexDiscard)))

        # Walk the goto/action tables and determine the list of possible tokens for each state
        lex_map = {}
        term_lists = []
        for state in p.states:
            terms = set((sym for sym in state.goto if sym in g.terminals())) | discard_terms
            for lookahead in state.action:
                terms |= set(lookahead)
            terms = frozenset(terms)
            if terms not in lex_map:
                lex_map[terms] = len(term_lists)
                state.lexer_id = len(term_lists)
                term_lists.append(terms)
            else:
                state.lexer_id = lex_map[terms]

        p.lexers = [_build_multidfa(g.lex_rules, set(term_list))[1] for term_list in term_lists]
        for state in p.states:
            state.lexer = p.lexers[state.lexer_id]
    else:
        p.lex_dfas, p.lexer = _build_multidfa(g.lex_rules)

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
