class _Classify:
    def __init__(self):
        self.quote = None
        self.comment = False
        
    def __call__(self, ch):
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
            return ''
        
        if ch == '#':
            self.comment = True
            return
    
        if ch.isspace():
            return
        
        if ch.isalnum() or ch in '_-':
            return 'id'
        
        return ''

class TokenPos:
    def __init__(self, filename, line, col):
        self.filename = filename
        self.line = line
        self.col = col

    def __str__(self):
        return "%s(%d)" % (self.filename, self.line)

class Token:
    def __init__(self, kind, text, pos=None):
        self.tok = (kind, text)
        self._pos = pos

    def __iter__(self):
        return iter(self.tok)

    def __len__(self):
        return len(self.tok)

    def __eq__(self, rhs):
        if isinstance(rhs, Token):
            return self.tok == rhs.tok
        return self.tok == rhs

    def __hash__(self):
        return hash(self.tok)

    def __str__(self):
        return str(self.tok)

    def __repr__(self):
        if self.pos is not None:
            return 'Token(%r, %r, %r)' % (self.tok[0], self.tok[1], self._pos)
        else:
            return 'Token(%r, %r)' % self.tok

    def __getitem__(self, i):
        return self.tok[i]

    def kind(self):
        return self.tok[0]

    def text(self):
        return self.tok[1]

    def pos(self):
        return self._pos

def simple_lexer(input, classify=None, filename=None):
    """Provides a simple lexer.
    
    >>> list(simple_lexer('spam, eggs # comment'))
    [('id', 'spam'), ',', ('id', 'eggs')]
    >>> list(simple_lexer('monty python'))
    [('id', 'monty'), ('id', 'python')]
    >>> list(simple_lexer('  "spam and eggs"  '))
    ['"', ('ql', 'spam and eggs')]
    """
    
    classify = classify or _Classify()
    
    lit = ''
    last_cl = None

    line_no = 1
    column_no = 1
    tok_pos = TokenPos(filename, 1, 1)
    for ch in input:
        cl = classify(ch)
        if cl is not False:
            if lit and cl != last_cl:
                yield Token(last_cl, lit, tok_pos)
                tok_pos = TokenPos(filename, line_no, column_no)
                lit = ''
        
            last_cl = cl
            if cl == '':
                yield Token(ch, ch, tok_pos)
                tok_pos = TokenPos(filename, line_no, column_no)
            elif cl:
                lit += ch

        if ch == '\n':
            line_no += 1
            column_no = 1
        else:
            column_no += 1

    if lit:
        yield Token(last_cl, lit, tok_pos)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
