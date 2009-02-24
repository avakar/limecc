#TODO: documentation

"""
>>> class Test:
...     def p_root(self, minus, int_digits, float_digits):
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

def _augment_parserclass(cls, k):
    from ebnf_grammar import ebnf_parse

    rules = []
    root_rules = []
    class_rules, counter = ebnf_parse(cls.__doc__, counter=0) if cls.__doc__ else ([], 0)
    
    for name in dir(cls):
        if name[:2] != 'p_':
            continue
        action = getattr(cls, name)
        grammar = action.__doc__
        if not grammar:
            continue
        if name == 'p_root':
            root_rules, counter = ebnf_parse(grammar, action, counter=counter)
        else:
            new_rules, counter = ebnf_parse(grammar, action, counter=counter)
            rules.extend(new_rules)
            
    root_rules.extend(class_rules)
    root_rules.extend(rules)

    from grammar import Grammar
    from lrparser import Parser
    grammar = Grammar(*root_rules)
    cls.parser = Parser(grammar, k)

def _augment_parse(self, input, **kwargs):
    return self.parser.parse(input, context=self, **kwargs)
    
def _augment_imbue_matchers(self, *args, **kwargs):
    return self.parser.imbue_matchers(*args, **kwargs)

class parser_LR:
    def __init__(self, k):
        self.k = k
        
    def __call__(self, cls):
        _augment_parserclass(cls, self.k)
        cls.parse = _augment_parse
        cls.imbue_matchers = _augment_imbue_matchers
        return cls

if __name__ == '__main__':
    import doctest
    doctest.testmod()
