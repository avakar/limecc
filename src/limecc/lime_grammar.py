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

from .grammar import Rule, Grammar
from .lrparser import make_lrparser, ParsingError
import types, sys
from .fa import union_fa, minimize_enfa
from .regex_parser import parse_regex, make_enfa_from_regex, make_dfa_from_literal

class LimeSpecParsingError(ParsingError):
    """Raised if there is a semantic error in the lime specification."""

class LimeLexingError(ParsingError):
    """Raised if an unexpected token is encountered when lexing with lime spec."""

class LexerConflictError(Exception):
    def __init__(self, rule1, rule2):
        Exception.__init__(self, 'Conflict merging %r and %r' % (rule1, rule2))
        self.rule1 = rule1
        self.rule2 = rule2

class LexRegex:
    def __init__(self, regex, pos=None):
        self.regex = regex
        self.pos = None

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
    def __init__(self, literal, pos=None):
        self.literal = literal
        self.pos = pos

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
        return (lhs.value, type.value)

    def _stmt_type_void(self, lhs, _cc, type):
        if type.value != 'void':
            raise LimeSpecParsingError('expected \'void\' or a snippet, got %r' % type.value, type.pos)
        return (lhs.value, None)

    def _stmt_rule(self, lhs, _cc, rhs_list, _dot, action):
        return _make_rule(lhs.value, None, rhs_list, action)
    def _stmt_rule2(self, lhs, _lp, lhs_name, _rp, _cc, rhs_list, _dot, action):
        return _make_rule(lhs.value, lhs_name.value, rhs_list, action)

    def _rhs_list_start(self):
        return []
    def _rhs_list_append(self, lst, item):
        lst.append(item)
        return lst

    def _named_item(self, sym):
        return (sym.value, None)
    def _named_item_with_name(self, sym, _lp, annot, _rp):
        return (sym.value, annot.value)

    def _named_item_lit(self, lit):
        return self._lex_rhs(LexLiteral(lit.value, lit.pos))

    def _named_item_lit_with_name(self, lit, _lp, annot, _rp):
        return self._lex_rhs(LexLiteral(lit.value, lit.pos), annot.value)

    def _named_item_snippet(self, snippet):
        return self._lex_rhs(LexRegex(snippet.value.strip()))

    def _named_item_snippet_with_name(self, snippet, _lp, annot, _rp):
        return self._lex_rhs(LexRegex(snippet.value.strip()), annot.value)

    def _lex_rhs(self, rhs, annot=None):
        tok_id = self._implicit_tokens.get(rhs)
        if tok_id is None:
            tok_id = len(self._implicit_tokens)
            self._implicit_tokens[rhs] = tok_id
        return (tok_id, annot)

    def _make_grammar(self, pg):
        g = Grammar(*pg.rules, symbols=pg.extra_symbols)
        g.context_lexer = pg.context_lexer
        g.tokens = pg.tokens
        g.sym_annot = pg.sym_annot
        g.user_include = pg.user_include
        g.token_type = pg.token_type
        g.tests = pg.tests
        g.discards = pg.discards
        g.root = pg.root

        g.token_names = {}
        for rule in pg.rules:
            if len(rule.right) == 1 and isinstance(rule.right[0], int):
                g.token_names[rule.right[0]] = rule.left

        return g

    def _test_list_new(self):
        return []

    def _test_list_id(self, tl, id):
        tl.append(id.value)
        return tl

    def _test_list_lit(self, tl, lit):
        tl.append(LexLiteral(lit.value, lit.pos))
        return tl

    def _grammar_kw_test(self, g, _kw, pattern, _sym, text, _dot):
        g.tests.append((pattern, text, _kw.pos))
        return g

    def _grammar_kw_discard_snip(self, g, _kw, snip):
        g.discards.append(LexRegex(snip.value, snip.pos))
        return g

    def _grammar_kw_discard_ql(self, g, _kw, ql):
        g.discards.append(LexLiteral(ql.value, ql.pos))
        return g

    def _grammar_set_root(self, g, root_name, pos):
        if g.root is not None:
            raise LimeSpecParsingError('multiple root specifiers', pos)
        g.root = [root_name]
        return g

    def _grammar_kw_root(self, g, _kw, rule):
        return self._grammar_rule(
            self._grammar_set_root(g, rule.left, _kw.pos),
            rule)

    def _grammar_kw_root_id(self, g, _kw, rule, _dot=None):
        return self._grammar_set_root(g, rule.value, _kw.pos)

    grammar = Grammar(
        Rule('root', ('grammar',), action=_make_grammar),
        Rule('grammar', (), action=_grammar_empty),
        Rule('grammar', ('grammar', 'kw_include', 'SNIPPET'), action=_grammar_kw_user_include),
        Rule('grammar', ('grammar', 'kw_token_type', 'SNIPPET'), action=_grammar_kw_token_type),
        Rule('grammar', ('grammar', 'kw_context_lexer'), action=_grammar_kw_context_lexer),
        Rule('grammar', ('grammar', 'kw_discard', 'SNIPPET'), action=_grammar_kw_discard_snip),
        Rule('grammar', ('grammar', 'kw_discard', 'QL'), action=_grammar_kw_discard_ql),
        Rule('grammar', ('grammar', 'kw_test', 'test_list', '::=', 'test_list', '.'), action=_grammar_kw_test),
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

class TokenPos:
    def __init__(self, filename, line, col):
        self.filename = filename
        self.line = line
        self.col = col

    def __str__(self):
        return "%s(%d)" % (self.filename, self.line)

    def __repr__(self):
        return "TokenPos(%r, %r, %r)" % (self.filename, self.line, self.col)

    def __add__(self, rhs):
        res = TokenPos(self.filename, self.line, self.col)
        pos = rhs.find('\n')
        while pos != -1:
            res.line += 1
            res.col = 1
            rhs = rhs[pos+1:]
            pos = rhs.find('\n')
        res.col += len(rhs)
        return res

class Token:
    def __init__(self, kind, text, pos=None):
        self.symbol = kind
        self.value = text
        self.pos = pos

    def __repr__(self):
        if self.pos is not None:
            return 'Token(%r, %r, %r)' % (self.symbol, self.value, self.pos)
        else:
            return 'Token(%r, %r)' % (self.symbol, self.value)

def _lime_lex_one(input, pos):
    ch = input[0]
    if ch.isspace():
        i = 1
        while i < len(input) and input[i].isspace():
            i += 1
        return None, i
    elif ch.isalpha() or ch in '_%':
        i = 1
        while i < len(input):
            ch = input[i]
            if not ch.isalnum() and ch not in '-_':
                break
            i += 1
        if input[0] != '%':
            return ('ID', 0, i), i
        else:
            return ('kw_' + input[1:i], 0, i), i
    elif ch == '{':
        i = 1
        while i < len(input) and input[i] == '{':
            i += 1
        depth = i
        close_brace = '}'*depth
        nest = 0
        while i < len(input):
            if input[i] == '{':
                nest += 1
            elif input[i] == '}':
                if nest <= 0 and input[i:].startswith(close_brace):
                    return ('SNIPPET', depth, i), i+depth
                nest -= 1
            i += 1
        raise LimeSpecParsingError('unclosed snippet', pos)
    elif ch in ('"', "'"):
        i = 1
        esc = False
        while i < len(input) and (esc or input[i] != input[0]):
            if esc:
                esc = False
            elif input[i] == '\\':
                esc = True
            elif input[i] == '\n':
                raise LimeSpecParsingError('end of line before closing quote', pos+input[:i])
            i += 1
        if i == len(input):
            raise LimeSpecParsingError('end of file before closing quote', pos)
        return ('QL', 1, i), i+1
    elif ch == '#':
        i = 1
        while i < len(input) and input[i] != '\n':
            i += 1
        return None, i+1
    elif ch in '()':
        return (input[0], 0, 1), 1
    else:
        i = 0
        while i < len(input) and input[i] in ':=.':
            i += 1
        if i == 0:
            raise LimeSpecParsingError('unexpected character: %r' % ch, pos)
        return (input[:i], 0, i), i

def _lime_lex(input, filename=None):
    input = str(input)
    tokpos = TokenPos(filename, 1, 1)
    while input:
        tokdef, next_input = _lime_lex_one(input, tokpos)
        if tokdef is not None:
            kind, start, stop = tokdef
            yield Token(kind, input[start:stop], tokpos + input[:start])
        tokpos = tokpos + input[:next_input]
        input = input[next_input:]

def _extract(tok):
    return tok.value if tok.symbol not in ('ID', 'QL', 'SNIPPET') and not tok.symbol.startswith('kw_') else tok

def parse_lime_grammar(input, filename=None):
    p = LimeGrammar()
    toks = _lime_lex(input, filename=filename)
    return p.parse(toks, extract_value=_extract)

class DfaEngine:
    """Executes a DFA over a provided text.
    
    Produces tokens in the form of (tok, content, pos),
    where tok is the value stored in the accepting state,
    potentially transformed by the extract function specified
    in the constructor. The content is the substring
    matching the token's production.
    """
    def __init__(self, dfa, extract=id):
        self._extract = extract
        self.set_dfa(dfa)

    def _get_token(self, s):
        assert s
        state = iter(self.dfa.initial).next()

        for i, ch in enumerate(s):
            for target, label in state.outedges:
                if ch in label:
                    state = target
                    break
            else:
                return self._extract(state.accept), s[0:i], s[i:]

        return self._extract(state.accept), s, ''

    def tokens(self, s, pos=None):
        while s:
            tok, tok_content, tail = self._get_token(s)
            if tok is None:
                s = tok_content or s[:1]
                raise LimeLexingError('unexpected: %r' % s, pos)
            yield (tok, tok_content, pos)
            if pos is not None:
                pos += tok_content
            s = tail

    def set_dfa(self, dfa):
        assert len(dfa.initial) == 1
        self.dfa = dfa

def _lexparse(p, text, token_filter=None, filename=None, pos=None, **kw):
    if pos is None and filename is not None:
        pos = TokenPos(filename, 1, 1)

    lex = DfaEngine(p.lexers[p.states[0].lexer_id], lambda x: x.token_id)

    toks = (filter(lambda tok: tok[0] != p.discard_id, lex.tokens(text, pos=pos)))

    if token_filter:
        rev = {}
        for k, v in p.grammar.token_names.iteritems():
            rev[v] = k

        def translate_toks(toks):
            for tok, text, pos in toks:
                yield p.grammar.token_names.get(tok, tok), text, pos

        def detranslate_toks(toks):
            for tok, text, pos in toks:
                yield rev.get(tok, tok), text, pos

        toks = detranslate_toks(token_filter(translate_toks(toks)))

    def update_lex(state):
        lex.set_dfa(p.lexers[state.lexer_id])
    return p.parse(toks, state_visitor=update_lex, **kw)

class _LexDfaAccept:
    def __init__(self, token_id, prio, tokens):
        self.token_id = token_id
        self.prio = prio
        self.tokens = frozenset(tokens)

    def __str__(self):
        return '%d [%s]' % (self.token_id, ', '.join((str(tok) for tok in self.tokens)))

def make_lime_parser(g, **kw):
    p = make_lrparser(g, root=g.root, **kw)
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
