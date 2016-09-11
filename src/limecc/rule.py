class Rule:
    """Represents a single production rule of a grammar.
    
    Rules are usually written using some sort of BNF-like notation,
    for example, 'list ::= list item' would be a valid rule. A rule
    always has a single non-terminal symbol on the left and a list
    (possibly empty) of arbitrary symbols on the right. The above rule
    would be constructed as follows.
    
    >>> r = Rule('list', ('list', 'item'))
    >>> print(r)
    'list' = 'list', 'item';
    
    The symbols can be arbitrary objects, not just strings. They must,
    however, be hashable. (Hashability is not enforced by the Rule class
    directly.)
    
    >>> print(Rule(0, (1, 2)))
    0 = 1, 2;
    
    Occasionaly, you must pass a one-tuple.
    
    >>> print(Rule('root', ('list',)))
    'root' = 'list';
    
    Note that terminal and non-terminal symbols are written
    using the same syntax -- the differentiation only occurs
    at the grammar level. The symbols standing on the left side of some rule
    are considered non-terminal.
    
    A rule can have no symbols on the right, such rules produce empty strings.
    
    >>> print(Rule('e', ()))
    'e' = ;
    
    The left and right symbols can be accessed via 'left' and 'right' members.
    
    >>> r.left, r.right
    ('list', ('list', 'item'))
    
    A rule can have an associated semantic action. The action is not interpreted in any
    way, but can be used to carry additional information in the rule. The default is None.
    
    >>> repr(r.action)
    'None'
    
    A custom semantic action is associated in constructor.
    
    >>> def concat_list(self, list, item):
    ...     list.append(item)
    ...     return list
    >>> r = Rule('list', ('list', 'item'), action=concat_list)
    >>> r.action(None, [], 1)
    [1]
    """

    def __init__(self, left, right, action=None):
        """
        Constructs a rule from the left symbol, an iterable of right symbols
        and an associated semantic action.
        """
        self.left = left
        self.right = tuple(right)
        self.action = action

    def __eq__(self, other):
        return (self.left, self.right, self.action) == (other.left, other.right, other.action)

    def __hash__(self):
        return hash((self.left, self.right, self.action))

    def __str__(self):
        """
        >>> print(Rule('a', ('b', 'c')))
        'a' = 'b', 'c';
        >>> print(Rule('a', ()))
        'a' = ;
        >>> def _custom_action(ctx): pass
        >>> print(Rule('a', (), _custom_action))
        'a' = ; {_custom_action}
        >>> print(Rule('a', (), lambda x: x))
        'a' = ; {<lambda>}
        """
        r = [repr(self.left), ' = ', ', '.join(repr(symbol) for symbol in self.right), ';']
        if self.action is not None:
            r.extend((' {', getattr(self.action, '__name__', ''), '}'))
        return ''.join(r)

    def __repr__(self):
        """
        >>> print(repr(Rule('a', ('b', 'c'))))
        Rule('a', ('b', 'c'))
        >>> print(repr(Rule('a', ())))
        Rule('a', ())
        >>> def _my_action(ctx): return None
        >>> print(repr(Rule('a', (), action=_my_action))) # doctest: +ELLIPSIS
        Rule('a', (), <function _my_action...>)
        >>> print(repr(Rule('a', (), action=lambda x: x))) # doctest: +ELLIPSIS
        Rule('a', (), <function <lambda>...>)
        """
        if self.action is not None:
            args = (self.left, self.right, self.action)
        else:
            args = (self.left, self.right)
        return 'Rule(%s)' % ', '.join((repr(arg) for arg in args))
