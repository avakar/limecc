from rule import Rule
from grammar import Grammar
from lrparser import Parser
from docparser import parser_LR, action, matcher
from simple_lexer import simple_lexer
from dfa import *

class _Lit:
    def __init__(self, charset):
        self.charset = set(charset)

    def __str__(self):
        return str(sorted(self.charset))

    def __repr__(self):
        return repr(sorted(self.charset))

class _Rep:
    def __init__(self, term):
        self.term = term

class _Alt:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

class _Concat:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

@parser_LR(1)
class _RegexParser:
    """
    root = alt;
    alt = concat;

    concat = rep;

    rep = atom;

    atom = _lparen, alt, _rparen;
    atom = literal;

    ch_or_esc = ch | esc;
    """

    @action
    def ch(self, ch):
        """
        literal = ch;
        """
        return _Lit(ch)

    @action
    def range(self, range_elems):
        """
        literal = _lbracket, { range_elem }, _rbracket;
        """
        charset = set()
        for elem in range_elems:
            charset.update(elem.charset)
        return _Lit(charset)

    @action
    def escaped(self, esc):
        """
        literal = esc;
        """
        if esc == 'd':
            return _Lit('0123456789')
        elif esc == 's':
            return _Lit(' \n\r\t\v\f')
        elif esc == 'w':
            return _Lit('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        else:
            return _Lit(esc)

    @action
    def range_elem_ch(self, ch):
        """
        range_elem = ch_or_esc;
        """
        return _Lit(ch)

    @action
    def range_elem_range(self, ch1, ch2):
        """
        range_elem = ch_or_esc, _minus, ch_or_esc;
        """
        ch1 = ord(ch1)
        ch2 = ord(ch2)
        if ch1 > ch2:
            ch1, ch2 = ch2, ch1
        return _Lit(set([chr(ch) for ch in xrange(ch1, ch2+1)]))

    @action
    def rep(self, atom):
        """
        rep = atom, _star;
        """
        return _Rep(atom)

    @action
    def rep_plus(self, atom):
        """
        rep = atom, _plus;
        """
        return _Concat(atom, _Rep(atom))

    @action
    def concat(self, lhs, rhs):
        """
        concat = concat, rep;
        """
        return _Concat(lhs, rhs)

    @action
    def alt(self, lhs, rhs):
        """
        alt = alt, _pipe, concat;
        """
        return _Alt(lhs, rhs)

def _regex_lexer(input):
    esc = False
    for ch in input:
        if esc:
            yield ('esc', ch)
            esc = False
        elif ch == '\\':
            esc = True
        elif ch == '+':
            yield ('plus', ch)
        elif ch == '*':
            yield ('star', ch)
        elif ch == '[':
            yield ('lbracket', ch)
        elif ch == ']':
            yield ('rbracket', ch)
        elif ch == '(':
            yield ('lparen', ch)
        elif ch == ')':
            yield ('rparen', ch)
        elif ch == '-':
            yield ('minus', ch)
        elif ch == '|':
            yield ('pipe', ch)
        else:
            yield ('ch', ch)
    if esc:
        yield ('ch', ch)

def make_enfa_from_regex(regex, accept_label):
    fa = Fa()
    initial = fa.new_state()
    fa.initial = set([initial])
    acc = fa.new_state()
    a = fa.new_state()
    b = fa.new_state()

    fa.new_edge(initial, a)
    fa.new_edge(a, b, regex)
    fa.new_edge(b, acc)
    fa.accept_labels[acc] = accept_label

    # The NFA now looks like this
    # 0 --epsilon--> 2 --regex--> 3 --epsilon--> 1

    changed = True
    while changed:
        changed = False
        for edge in fa.get_edges():
            source, target, r = edge.source, edge.target, edge.label
            fa.remove_edge(edge)
            if isinstance(r, _Alt):
                a = fa.new_state(target)
                fa.new_edge(source, target, r.lhs)
                fa.new_edge(source, a, r.rhs)
                changed = True
            elif isinstance(r, _Concat):
                a = fa.new_state()
                fa.new_edge(source, a, r.lhs)
                fa.new_edge(a, target, r.rhs)
                changed = True
            elif isinstance(r, _Rep):
                a = fa.new_state()
                fa.new_edge(source, a)
                fa.new_edge(a, target)
                fa.new_edge(a, a, r.term)
                changed = True
            else:
                fa.new_edge(source, target, r)

    for edge in fa.get_edges():
        if edge.label is not None:
            edge.label = frozenset(edge.label.charset)

    return fa

def make_multi_dfa(fas):
    final_fa = Fa()
    final_init = final_fa.new_state()
    final_fa.initial = set([final_init])
    for fa in fas:
        final_fa.add_fa(fa)
        final_fa.new_edge(final_init, next(iter(fa.initial)))
    return final_fa

def regex_parser(input):
    p = _RegexParser()
    from lrparser import extract_second
    return p.parse(_regex_lexer(input), extract_value=extract_second)

if __name__ == "__main__":
    fa = make_multi_dfa([
        (r'endmodule', 0),
        (r'module', 1),
        (r'discipline', 2),
        (r'enddiscipline', 3),
        (r'nature', 4),
        (r'endnature', 5)
        ])
    print fa
    fa = minimize_enfa(fa)
    print '-------------------------------'
    print fa

