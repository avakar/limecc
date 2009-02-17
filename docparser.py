#TODO: documentation

"""
>>> class Test:
...     def p_root(self, minus, int_digits, float_digits):
...         ''' float = ["-"], { digit }, '.', { digit }; '''
...         return (minus, int_digits, float_digits)
>>> p = DocParser(Test)
>>> print p.parse('-111.11')
('-', ['1', '1', '1'], ['1', '1'])
>>> print p.parse('111.11')
(None, ['1', '1', '1'], ['1', '1'])
>>> print p.parse('128.12')
(None, ['1', '2', '8'], ['1', '2'])
"""

from ebnf_grammar import ebnf_parse
from grammar import Grammar
from lrparser import Parser, default_matchers

class DocParser:
    def __init__(self, cls, k=1, matches=default_matchers):
        rules = []
        root_rules = None
        counter = 0
        class_rules, counter = ebnf_parse(cls.__doc__, counter=counter) if cls.__doc__ else ([], 0)
        
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
                
        self.cls = cls
        root_rules.extend(rules)
        root_rules.extend(class_rules)
        self.grammar = Grammar(*root_rules)
        self.parser = Parser(self.grammar, k, matchers=matches)
        
    def parse(self, input, context=None):
        return self.parser.parse(input, context=context or self.cls())

if __name__ == '__main__':
    import doctest
    doctest.testmod()
