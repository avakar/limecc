from grammar import Rule, Grammar
from docparser import parser_LR, action, matcher
from fa import State, Edge, Fa, union_fa, _Lit

class _Empty:
    pass

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

    rep = atom;

    atom = _lparen, alt, _rparen;
    atom = literal;
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
    def range_inv(self, range_elems):
        """
        literal = _lbracket, _circumflex, { range_elem }, _rbracket;
        """
        charset = set()
        for elem in range_elems:
            charset.update(elem.charset)
        return _Lit(charset, inv=True)

    @action
    def escaped(self, esc):
        """
        literal = esc;
        range_elem = esc;
        """
        if esc == 'd':
            return _Lit('0123456789')
        elif esc == 's':
            return _Lit(' \n\r\t\v\f')
        elif esc == 'n':
            return _Lit('\n')
        elif esc == 'w':
            return _Lit('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        else:
            return _Lit(esc)

    @action
    def range_elem_ch(self, ch):
        """
        range_elem = ch;
        """
        return _Lit(ch)

    @action
    def range_elem_range(self, ch1, ch2):
        """
        range_elem = ch, _minus, ch;
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
    def rep_q(self, atom):
        """
        rep = atom, _q;
        """
        return _Alt(_Empty(), atom)

    @action
    def concat_empty(self):
        """
        concat = ;
        """
        return _Empty()

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
        elif ch == '?':
            yield ('q', ch)
        elif ch == '^':
            yield ('circumflex', ch)
        else:
            yield ('ch', ch)
    if esc:
        yield ('ch', ch)

class invertible_set:
    def __init__(self, iterable, inv=False):
        self.base = set(iterable)
        self.inv = inv

    def __repr__(self):
        if self.inv:
            return 'invertible_set(%r, inv=True)' % sorted(self.base)
        else:
            return 'invertible_set(%r)' % sorted(self.base)

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

    while True:
        for edge in fa.get_edges():
            source, target, r = edge.source, edge.target, edge.label
            if isinstance(r, _Alt):
                fa.remove_edge(edge)
                a = fa.new_state(target)
                fa.new_edge(source, target, r.lhs)
                fa.new_edge(source, a, r.rhs)
                break
            elif isinstance(r, _Concat):
                fa.remove_edge(edge)
                a = fa.new_state()
                fa.new_edge(source, a, r.lhs)
                fa.new_edge(a, target, r.rhs)
                break
            elif isinstance(r, _Rep):
                fa.remove_edge(edge)
                a = fa.new_state()
                fa.new_edge(source, a)
                fa.new_edge(a, target)
                fa.new_edge(a, a, r.term)
                break
            elif isinstance(r, _Empty):
                fa.remove_edge(edge)
                fa.new_edge(source, target)
                break
        else:
            break

    return fa

def regex_parser(input):
    p = _RegexParser()
    def _extract_second(token):
        return token[1] if isinstance(token, tuple) else token
    return p.parse(_regex_lexer(input), extract_value=_extract_second)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
