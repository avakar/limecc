from ebnf_grammar import ebnf_parse
from grammar import Grammar
from lrparser import Parser

class Test:
    def p_root(self, minus, int_digits, float_digits):
        """ float = ["-"], { "1" }, '.', { "1" }; """
        return (minus, int_digits, float_digits)

class DocParser:
    def __init__(self, cls):
        rules = []
        for name in dir(cls):
            if name[:2] != 'p_':
                continue
            action = getattr(cls, name)
            grammar = action.__doc__
            print grammar
            if not grammar:
                continue
            rules.extend(ebnf_parse(grammar, action))
        self.cls = cls
        self.grammar = Grammar(*rules)
        self.parser = Parser(self.grammar)
        
    def parse(self, input, context=None):
        return self.parser.parse(input, context=context or self.cls())

if __name__ == '__main__':
    p = DocParser(Test)
    print p.grammar
    print p.parse('-111.11')
    print p.parse('111.11')
