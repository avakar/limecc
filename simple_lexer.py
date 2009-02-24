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
        if ch in '\'"':
            self.quote = ch
            return ''
        if self.quote:
            return 'ql'
        
        if ch == '#':
            self.comment = True
            return
    
        if ch.isspace():
            return
        
        if ch.isalnum() or ch in '_-':
            return 'id'
        
        return ''

def simple_lexer(input, classify=None):
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
    for ch in input:
        cl = classify(ch)
        if cl == False:
            continue
        
        if lit and cl != last_cl:
            yield (last_cl, lit)
            lit = ''
        
        last_cl = cl
        if cl == '':
            yield ch
        elif cl:
            lit += ch
    if lit:
        yield (last_cl, lit)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
