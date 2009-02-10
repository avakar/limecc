from rule import Rule

class Grammar:
    """Represents a set of production rules.
    
    Each rule is encapsulated by an instance of the 'Rule' class.
    The rules can be added during construction through or later
    using the 'add' and 'extend' methods.
    
    The grammar also tracks the root non-terminal, which is defined
    to be the left symbol of the first rule. For an empty grammar,
    there is no root and Grammar.root() will return None.
    
    >>> g = Grammar()
    >>> print g.root()
    None

    >>> g = Grammar(Rule('list'))
    >>> g.add(Rule('list', 'list', 'item'))
    >>> print g
    list ::= <empty>
    list ::= list item
    >>> g.root()
    'list'
    
    Grammars expose their rules using the standard list interface.
    There is, however, no support for splices and the list of rules
    can only be mutated through calls to 'add' and 'extend'.
    
    >>> g[0]
    Rule('list')
    >>> len(g)
    2
    >>> for rule in g: print rule
    list ::= <empty>
    list ::= list item
    
    Symbols are considered non-terminal (with respect to a grammar) if
    they stand on the left side of some rule. All other symbols are considered terminal.
    A grammar can test a symbol for its terminality. It also exposes a list of
    all non-terminals and a list of all referenced symbols.
    
    >>> g.add(Rule('root', 'list'))
    >>> [g.is_terminal(symbol) for symbol in ('list', 'root', 'item', 'unreferenced')]
    [False, False, True, True]
    >>> sorted(list(g.symbols()))
    ['item', 'list', 'root']
    >>> sorted(list(g.nonterms()))
    ['list', 'root']
    
    The grammar also allows fast access to a set of rules with a given symbol on the left.
    
    >>> for rule in g.rules('list'): print rule
    list ::= <empty>
    list ::= list item
    >>> for rule in g.rules('unreferenced'): print rule
    >>> for rule in g.rules('root'): print rule
    root ::= list
    """
    def __init__(self, *rules):
        self._rules = []
        self._rule_cache = {}
        self._nonterms = set()
        self._symbols = set()
        
        for rule in rules:
            self.add(rule)
        
    def __getitem__(self, key):
        return self._rules[key]
        
    def __len__(self):
        return len(self._rules)
        
    def __iter__(self):
        return iter(self._rules)
        
    def __str__(self):
        """
        >>> print Grammar(Rule('a', 'b', 'c'), Rule('a', 'c', 'b'))
        a ::= b c
        a ::= c b
        """
        return '\n'.join(str(rule) for rule in self._rules)
    
    def __repr__(self):
        """
        >>> print repr(Grammar(Rule('a', 'b', 'c'), Rule('a', 'c', 'b')))
        Grammar(Rule('a', 'b', 'c'), Rule('a', 'c', 'b'))
        """
        return 'Grammar(%s)' % ', '.join(repr(rule) for rule in self._rules)
        
    def add(self, rule):
        """Adds a rule to the grammar."""
        self._rules.append(rule)
        self._nonterms.add(rule.left)
        self._symbols.add(rule.left)
        self._rule_cache.setdefault(rule.left, []).append(rule)
        
        for symbol in rule.right:
            self._symbols.add(symbol)
    
    def extend(self, rules):
        """Extends the grammar by the given set of rules."""
        for rule in rules:
            self.add(rule)

    def rules(self, left):
        """Retrieves the set of rules with a given non-terminal on the left.
        
        >>> g = Grammar(Rule('a', 'b'), Rule('b', 'c'), Rule('b', 'd'))
        >>> for rule in g.rules('a'): print rule
        a ::= b
        >>> for rule in g.rules('c'): print rule
        >>> for rule in g.rules('b'): print rule
        b ::= c
        b ::= d
        """
        return self._rule_cache.get(left, ())
    
    def is_terminal(self, token):
        """Tests the symbol for terminality.
        
        All non-terminal symbols are considered terminal,
        regardless of whether they are referenced by the grammar.
        
        >>> g = Grammar(Rule('a', 'b'), Rule('b', 'c'))
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
        
    def root(self):
        """Returns the root non-terminal.
        
        >>> g = Grammar()
        >>> print g.root()
        None
        >>> g.add(Rule('a', 'b'))
        >>> print g.root()
        a
        """
        return self._rules[0].left if self._rules else None
        
if __name__ == "__main__":
    import doctest
    doctest.testmod()
