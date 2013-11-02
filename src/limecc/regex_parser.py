from grammar import Rule, Grammar
from lrparser import make_lrparser
from fa import Fa, State

class Lit:
    def __init__(self, charset, inv=False):
        self.charset = frozenset(charset)
        self.inv = inv

    def __repr__(self):
        if self.inv:
            return 'Lit(%r, inv=True)' % (sorted(self.charset),)
        else:
            return 'Lit(%r)' % (sorted(self.charset),)

    def __nonzero__(self):
        return bool(self.charset) or self.inv

    def __sub__(self, other):
        if not self.inv and not other.inv:
            return Lit(self.charset - other.charset, False)
        elif self.inv and not other.inv:
            return Lit(self.charset | other.charset, True)
        elif not self.inv and other.inv:
            return Lit(self.charset & other.charset, False)
        else:
            return Lit(other.charset - self.charset, False)

    def __and__(self, other):
        if not self.inv and not other.inv:
            return Lit(self.charset & other.charset, False)
        elif self.inv and not other.inv:
            return Lit(other.charset - self.charset, False)
        elif not self.inv and other.inv:
            return Lit(self.charset - other.charset, False)
        else:
            return Lit(self.charset | other.charset, True)

    def __or__(self, other):
        if not self.inv and not other.inv:
            return Lit(self.charset | other.charset, False)
        elif self.inv and not other.inv:
            return Lit(self.charset - other.charset, True)
        elif not self.inv and other.inv:
            return Lit(other.charset - self.charset, True)
        else:
            return Lit(self.charset & other.charset, True)

    def __contains__(self, ch):
        return self.inv != (ch in self.charset)

class Rep:
    def __init__(self, term):
        self.term = term

    def __repr__(self):
        return 'Rep({0})'.format(repr(self.term))

class Alt:
    def __init__(self, *terms):
        self.terms = terms

    def __repr__(self):
        return 'Alt({0})'.format(', '.join((repr(t) for t in self.terms)))

class Cat:
    def __init__(self, *terms):
        self.terms = tuple(terms)

    def __repr__(self):
        return 'Cat({0})'.format(', '.join((repr(t) for t in self.terms)))

_escape_map = {
    'd': '0123456789',
    's': ' \n\r\t\v\f',
    'w': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',
    }

_regex_grammar = Grammar(
    Rule('alt', ('cat',)),
    Rule('alt', ('alt', '|', 'cat'), lambda self, lhs, _pipe, rhs: Alt(lhs, rhs) if not isinstance(lhs, Alt) else Alt(*(lhs.terms + (rhs,)))),

    Rule('cat', (), lambda self: None),
    Rule('cat', ('cat', 'rep'), lambda self, cat, rep: rep if cat is None else Cat(*(cat.terms + (rep,))) if isinstance(cat, Cat) else Cat(cat, rep)),

    Rule('rep', ('atom',)),
    Rule('rep', ('atom', '*'), lambda self, atom, _star: Rep(atom)),
    Rule('rep', ('atom', '+'), lambda self, atom, _plus: Cat(atom, Rep(atom))),
    Rule('rep', ('atom', '?'), lambda self, atom, _q: Alt(None, atom)),

    Rule('atom', ('(', 'alt', ')'), lambda self, _l, alt, _r: alt),
    Rule('atom', ('.',), lambda self, _dot: Lit('', inv=True)),
    Rule('atom', ('c',), lambda self, ch: Lit(ch)),
    Rule('atom', ('esc',), lambda self, ch: Lit(_escape_map.get(ch, ch))),
    Rule('atom', ('[', 'range', ']'), lambda self, _l, range, _r: Lit(range)),
    Rule('atom', ('[', '^', 'range', ']'), lambda self, _l, _c, range, _r: Lit(range, inv=True)),

    Rule('range', (), lambda self: ''),
    Rule('range', ('range', 'range_elem'), lambda self, range, elem: range + elem),

    Rule('range_elem', ('c',), lambda self, ch: ch),
    Rule('range_elem', ('c', '-', 'c'), lambda self, lhs, _m, rhs: ''.join((chr(c) for c in xrange(ord(lhs), ord(rhs)+1)))),
    Rule('range_elem', ('esc',), lambda self, ch: _escape_map.get(ch, ch)),
    )

def _regex_lexer(input):
    esc = False
    for ch in input:
        if esc:
            yield ('esc', ch)
            esc = False
        elif ch == '\\':
            esc = True
        elif ch in '+*[]()-|?^.':
            yield (ch, ch)
        else:
            yield ('c', ch)
    if esc:
        yield ('c', '\\')

_regex_parser = None

def parse_regex(input):
    global _regex_parser
    if _regex_parser is None:
        _regex_parser = make_lrparser(_regex_grammar)
    return _regex_parser.parse(_regex_lexer(input))

def make_dfa_from_literal(lit, accept_label=True):
    """
    Create a DFA from a sequence. The FA will have `n+1` states,
    where `n` is the length of the sequence. The states will be connected
    to form a chain that begins with the only inital state and ends
    with an accepting state labeled by the provided label.
    """
    fa = Fa()
    init = State()
    fa.initial = set([init])
    for ch in lit:
        s = State()
        init.connect_to(s, Lit([ch]))
        init = s
    fa.accept_labels = { init: accept_label }
    return fa

def make_enfa_from_regex(regex, accept_label):
    fa = Fa()
    initial = State()
    fa.initial = set([initial])
    final = State()
    fa.accept_labels[final] = accept_label

    def add_regex_edge(src, sink, r):
        if isinstance(r, Alt):
            for term in r.terms:
                mid = State()
                add_regex_edge(src, mid, term)
                mid.connect_to(sink, None)
        elif isinstance(r, Rep):
            mid = State()
            src.connect_to(mid, None)
            mid.connect_to(sink, None)
            add_regex_edge(mid, mid, r.term)
        elif isinstance(r, Cat):
            if r.terms:
                for term in r.terms[:-1]:
                    mid = State()
                    add_regex_edge(src, mid, term)
                    src = mid
                add_regex_edge(src, sink, r.terms[-1])
        else:
            src.connect_to(sink, r)

    add_regex_edge(initial, final, regex)
    return fa

if __name__ == '__main__':
    import doctest
    doctest.testmod()
