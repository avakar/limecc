from rule import Rule

class Grammar:
    """Represents a set of production rules.
    
    Each rule is encapsulated by an instance of the 'Rule' class.
    The rules are supplied during construction.
    
    The grammar also tracks the root non-terminal, which is either
    set explicitly during construction, or assumed to be the left
    hand side symbol of the first rule. For an empty grammar,
    there is no root and Grammar.root() will return None.
    
    >>> g = Grammar()
    >>> print g.root()
    None

    >>> g = Grammar(
    ...     Rule('list'),
    ...     Rule('list', ('list', 'item')))
    >>> print g
    'list' = ;
    'list' = 'list', 'item';
    >>> g.root()
    'list'
    
    Grammars expose their rules using the standard list interface.
    
    >>> g[0]
    Rule('list')
    >>> len(g)
    2
    >>> for rule in g: print rule
    'list' = ;
    'list' = 'list', 'item';
    
    Symbols are considered non-terminal (with respect to a grammar) if
    they stand on the left side of some rule. All other symbols are considered terminal.
    A grammar can test a symbol for its terminality. It also exposes a list of
    all non-terminals and a list of all referenced symbols.
    
    >>> g = Grammar(
    ...     Rule('list'),
    ...     Rule('list', ('list', 'item')),
    ...     Rule('root', ('list',)))
    >>> [g.is_terminal(symbol) for symbol in ('list', 'root', 'item', 'unreferenced')]
    [False, False, True, True]
    >>> sorted(list(g.symbols()))
    ['item', 'list', 'root']
    >>> sorted(list(g.nonterms()))
    ['list', 'root']
    
    The grammar also allows fast access to a set of rules with a given symbol on the left.
    
    >>> for rule in g.rules('list'): print rule
    'list' = ;
    'list' = 'list', 'item';
    >>> for rule in g.rules('unreferenced'): print rule
    >>> for rule in g.rules('root'): print rule
    'root' = 'list';
    """
    def __init__(self, *rules, **kw):
        if any((opt not in ('root', 'symbols') for opt in kw)) or any((not isinstance(rule, Rule) for rule in rules)):
            raise AttributeError('Unknown argument')

        self._rules = rules
        self._nonterms = frozenset((rule.left for rule in self._rules))

        symbols = []
        for rule in self._rules:
            symbols.append(rule.left)
            symbols.extend(rule.right)

        if 'symbols' in kw:
            symbols.extend(kw['symbols'])

        self._symbols = frozenset(symbols)
        self._root = kw.get('root', self._rules[0].left if self._rules else None)

        self._rule_cache = {}
        for left in self._nonterms:
            self._rule_cache[left] = tuple([rule for rule in self._rules if rule.left == left])

    def __getitem__(self, index):
        return self._rules[index]
        
    def __len__(self):
        return len(self._rules)
        
    def __iter__(self):
        return iter(self._rules)
        
    def __str__(self):
        """
        >>> print Grammar(Rule('a', ('b', 'c')), Rule('a', ('c', 'b')))
        'a' = 'b', 'c';
        'a' = 'c', 'b';
        """
        return '\n'.join(str(rule) for rule in self._rules)
    
    def __repr__(self):
        """
        >>> print repr(Grammar(Rule('a', ('b', 'c')), Rule('a', ('c', 'b'))))
        Grammar(Rule('a', ('b', 'c')), Rule('a', ('c', 'b')))
        """
        return 'Grammar(%s)' % ', '.join(repr(rule) for rule in self._rules)
        
    def rules(self, left):
        """Retrieves the set of rules with a given non-terminal on the left.
        
        >>> g = Grammar(Rule('a', ('b',)), Rule('b', ('c',)), Rule('b', ('d',)))
        >>> for rule in g.rules('a'): print rule
        'a' = 'b';
        >>> for rule in g.rules('c'): print rule
        >>> for rule in g.rules('b'): print rule
        'b' = 'c';
        'b' = 'd';
        """
        return self._rule_cache.get(left, ())
    
    def is_terminal(self, token):
        """Tests the symbol for terminality.
        
        All non-terminal symbols are considered terminal,
        regardless of whether they are referenced by the grammar.
        
        >>> g = Grammar(Rule('a', ('b',)), Rule('b', ('c',)))
        >>> tuple(g.is_terminal(sym) for sym in 'abcd')
        (False, False, True, True)
        """
        return token not in self._nonterms

    def nonterms(self):
        """Returns an iterable representing the set of all non-terminal symbols."""
        return self._nonterms

    def symbols(self):
        """Returns an iterable representing the current set of all referenced symbols."""
        return self._symbols

    def terminals(self):
        """Returns an iterable representing the current set of all terminal symbols."""
        return self._symbols - self._nonterms

    def root(self):
        """Returns the root non-terminal.
        
        >>> g = Grammar()
        >>> print g.root()
        None
        >>> g = Grammar(Rule('a', ('b',)))
        >>> print g.root()
        a
        """
        return self._root
        
if __name__ == "__main__":
    import doctest
    doctest.testmod()
