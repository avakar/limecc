#TODO: documentation

def extract_grammar(cls):
    """
    Extracts the grammar associted with a class.
    The extraction is exactly the one used when generating
    parser using the @parser_LR decorator.
    
    >>> class Test:
    ...     @action
    ...     def root(self, minus, int_digits, float_digits):
    ...         ''' float = ["-"], { digit }, '.', { digit }; '''
    ...         return (minus, int_digits, float_digits)
    >>> print extract_grammar(Test)
    'float' = '@1', '@2', '.', '@4';
    '@4' = ;
    '@4' = '@4', '@5';
    '@5' = 'digit';
    '@2' = ;
    '@2' = '@2', '@3';
    '@3' = 'digit';
    '@1' = ;
    '@1' = '-';
    """
    from ebnf_grammar import ebnf_parse

    rules = []
    root_rules = []
    class_rules, counter = ebnf_parse(cls.__doc__, counter=0) if cls.__doc__ else ([], 0)
    
    for name in dir(cls):
        value = getattr(cls, name)
        if isinstance(value, _Action):
            grammar = value.fn.__doc__
            if not grammar:
                continue
            if name == 'root':
                root_rules, counter = ebnf_parse(grammar, value.fn, counter=counter)
            else:
                new_rules, counter = ebnf_parse(grammar, value.fn, counter=counter)
                rules.extend(new_rules)
    
    root_rules.extend(class_rules)
    root_rules.extend(rules)

    from grammar import Grammar
    return Grammar(*root_rules)

def _augment_parserclass(cls, k, imbue_default_matchers):
    if imbue_default_matchers:
        from matchers import default_matchers
        matchers = dict(default_matchers)
    else:
        matchers = {}
    
    for name in dir(cls):
        value = getattr(cls, name)
        if isinstance(value, _Matcher):
            matchers[name] = value.fn
            matchers['-' + name] = value
    
    from lrparser import Parser
    grammar = extract_grammar(cls)
    cls.parser = Parser(grammar, k)
    
    cls.parser.imbue_matchers(matchers)

def _augment_parse(self, input, **kwargs):
    return self.parser.parse(input, context=self, **kwargs)
    
def _augment_imbue_matchers(self, *args, **kwargs):
    return self.parser.imbue_matchers(*args, **kwargs)

class _DecoratedMethod:
    def __init__(self, fn):
        self.fn = fn
    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

class _Matcher(_DecoratedMethod):
    pass
    
class _Action(_DecoratedMethod):
    pass

def matcher(fn):
    """
    A decorator used to mark class methods that are to be used
    as matchers should the class be augmented with @parser_LR(k) decorator.
    """
    return _Matcher(fn)

def action(fn):
    """
    A decorator used to mark class methods that are to be used
    as semantic actions should the class be augmented with @parser_LR(k) decorator.
    The docstring of marked methods are interpreted with an EBNF parser.
    """
    return _Action(fn)

class parser_LR:
    """
    A class decorator, which converts a class into a LR(k) parser.
    
    >>> class Test:
    ...     @action
    ...     def root(self, minus, int_digits, float_digits):
    ...         ''' float = ["-"], { digit }, '.', { digit }; '''
    ...         return (minus, int_digits, float_digits)
    >>> Test = parser_LR(1)(Test)
    >>> p = Test()
    >>> p.imbue_matchers()
    >>> print p.parse('-111.11')
    ('-', ['1', '1', '1'], ['1', '1'])
    >>> print p.parse('111.11')
    (None, ['1', '1', '1'], ['1', '1'])
    >>> print p.parse('128.12')
    (None, ['1', '2', '8'], ['1', '2'])

    >>> @parser_LR(1)
    ... class Test2:
    ...     '''root = { "a" };'''
    >>> Test2().parse('aaa')
    ['a', 'a', 'a']
    """
    def __init__(self, k, default_matchers=False):
        self.k = k
        self.default_matchers = default_matchers
        
    def __call__(self, cls):
        _augment_parserclass(cls, self.k, self.default_matchers)
        cls.parse = _augment_parse
        cls.imbue_matchers = _augment_imbue_matchers
        return cls

if __name__ == '__main__':
    import doctest
    doctest.testmod()
