class Rule:
    """Represents a single production rule of a grammar.
    
    Rules are usually written using some sort of BNF-like notation,
    for example, 'list ::= list item' would be a valid rule. A rule
    always has a single non-terminal symbol on the left and a list
    (possibly empty) of arbitrary symbols on the right. The above rule
    would be constructed as follows.
    
    >>> r = Rule('list', 'list', 'item')
    >>> print r
    list ::= list item
    
    Note that terminal and non-terminal symbols are written
    using the same syntax -- the differentiation only occurs
    at the grammar level. The symbols standing on the left side of some rule
    are considered non-terminal.
    
    A rule may have no symbols on the right, such rules produce empty strings.
    
    >>> print Rule('e')
    e ::= <empty>
    
    The left and right symbols can be accessed via 'left' and 'right' members.
    
    >>> r.left, r.right
    ('list', ('list', 'item'))
    
    Every rule has an associated semantic action, which combines data
    from the right-hand-side symbols. The number of arguments
    of this function and the number of symbols on the right plus one must match.
    The first argument is called a context and represents arbitrary data passed to the parser.
    The default action is to make a tuple.
    
    >>> r.action(None, [], 1)
    ([], 1)
    
    A custom semantic action is associated in constructor.
    
    >>> r = Rule('list', 'list', 'item', action=lambda c, l, i: l + [i])
    >>> r.action(None, [], 1)
    [1]
    """

    def __init__(self, left, *right, **kwarg):
        self.left = left
        self.right = right
        self.action = kwarg.get('action', lambda ctx, *args: args)
    
    def __str__(self):
        """
        >>> print Rule('a', 'b', 'c')
        a ::= b c
        >>> print Rule('a')
        a ::= <empty>
        """
        
        if self.right:
            out = [self.left, '::=']
            out.extend(self.right)
        else:
            out = [self.left, '::= <empty>']
        return ' '.join(out)
    
    def __repr__(self):
        """
        >>> print repr(Rule('a', 'b', 'c'))
        Rule('a', 'b', 'c')
        """
        
        out = [repr(self.left)]
        out.extend(repr(s) for s in self.right)
        return 'Rule(%s)' % ', '.join(out)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
