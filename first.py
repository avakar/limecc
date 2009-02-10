"""
This module defines some basic operations on words and sets of words.

A word is any iterable of symbols (strings), i.e. ('list', 'item') is a word.
The iterable must support slices, joining with operator + and must return
their length through the 'len' function.
"""

from rule import Rule
from grammar import Grammar

def first(word, k=1):
    """Returns FIRST_k(word).
    
    The implied grammar is taken to be empty and all symbols are treated as terminals.
    See <http://www.jambe.co.nz/UNI/FirstAndFollowSets.html> for more information.
    
    >>> first('hello, world', k=7)
    'hello, '
    >>> first(('list', 'item', 'item', 'item', 'item'), k=2)
    ('list', 'item')
    """
    return word[:k]

def oplus(left, right, k=1):
    """Returns the set { FIRST_k(vw) | v in left, w in right } and the length of its shortest member.
    
    The 'left' and 'right' are iterables of words.
    The function return type is a pair (s, l), where 's' is the first-set
    and 'l' is the length of its shortest member. If 's' is empty, 'l' is set equal to 'k'.
    The type of 's' is unspecified, but is guaranteed to be an iterable of words
    and to support operators 'in' and 'not in'.
    
    >>> s, l = oplus(['ab', 'ac', ''], ['zz', 'y', ''], k=3)
    >>> sorted(list(s))
    ['', 'ab', 'aby', 'abz', 'ac', 'acy', 'acz', 'y', 'zz']
    >>> l
    0
    
    >>> s, l = oplus(['ab', 'ac'], ['zz', 'y'], k=3)
    >>> sorted(list(s))
    ['aby', 'abz', 'acy', 'acz']
    >>> l
    3
    """
    res = set()
    min_len = k
    for lword in left:
        for rword in right:
            w = first(lword + rword, k)
            if len(w) < min_len:
                min_len = len(w)
            res.add(w)
    return res, min_len
    
class First:
    """Represents the first-set for a given grammar.
    
    The grammar and 'k' parameter are passed during construction.
    
    >>> g = Grammar(Rule('list'), Rule('list', 'list', 'item'))
    >>> f = First(g, k=2)
    >>> f.grammar
    Grammar(Rule('list'), Rule('list', 'list', 'item'))
    
    The objects are callable and, for a given word 'w', return the set
    { FIRST_k(u) | w =>* u, u terminal }.
    
    >>> sorted(list(f(('item', 'item', 'item'))))
    [('item', 'item')]
    >>> sorted(list(f(())))
    [()]
    >>> sorted(list(f(('list',))))
    [(), ('item',), ('item', 'item')]
    """
    def __init__(self, grammar, k=1):
        """
        Given a grammar and a 'k', constructs the first-set table for all non-terminals.
        The table is then used by the '__call__' method.
        
        For the construction algorithm, see the Dragon book.
        """
        self.grammar = Grammar(*grammar)
        self.k = k

        self.table = dict((nonterm, set()) for nonterm in grammar.nonterms())

        # The sets in the table start empty and are iteratively filled.
        # The termination is guaranteed by the existence of the least fixed point.
        done = False
        while not done:
            done = True
            for rule in grammar:
                for word in self(rule.right):
                    if word not in self.table[rule.left]:
                        self.table[rule.left].add(word)
                        done = False
    
    def __call__(self, word):
        """Returns FIRST_k(word) with respect to the associated grammar."""
        res = set([()])
        for symbol in word:
            if symbol not in self.table:
                rset = set([(symbol,)])
            else:
                rset = self.table[symbol]
            res, c = oplus(res, rset, self.k)
            if c == self.k:
                break
        
        return res

if __name__ == "__main__":
    import doctest
    doctest.testmod()
