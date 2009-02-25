#TODO: documentation

"""
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

def _augment_parserclass(cls, k, imbue_default_matchers):
    from ebnf_grammar import ebnf_parse

    rules = []
    root_rules = []
    if imbue_default_matchers:
        from matchers import default_matchers
        matchers = dict(default_matchers)
    else:
        matchers = {}
    class_rules, counter = ebnf_parse(cls.__doc__, counter=0) if cls.__doc__ else ([], 0)
    
    for name in dir(cls):
        value = getattr(cls, name)
        if isinstance(value, _Matcher):
            matchers[name] = value.fn
            matchers['-' + name] = value
        elif isinstance(value, _Action):
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
    from lrparser import Parser
    grammar = Grammar(*root_rules)
    cls.parser = Parser(grammar, k)
    
    cls.parser.imbue_matchers(matchers)

def _augment_parse(self, input, **kwargs):
    return self.parser.parse(input, context=self, **kwargs)
    
def _augment_imbue_matchers(self, *args, **kwargs):
    return self.parser.imbue_matchers(*args, **kwargs)

class _DecoratedMethod:
    def __init__(self, fn):
        self.fn = fn

class _Matcher(_DecoratedMethod):
    pass
    
class _Action(_DecoratedMethod):
    pass

def matcher(fn):
    return _Matcher(fn)
    
def action(fn):
    return _Action(fn)

class parser_LR:
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
