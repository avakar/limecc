"""
Provides a conversion between EBNF (ISO 14977:1996) and Rule objects.

The core functionality is provided via the 'ebnf_parse' function,
which receives a string representing the ebnf grammar
and returns the list of corresponding Rule objects.

>>> grammar_in_ebnf = 'list = { item }; item = "i";'
>>> for rule in ebnf_parse(grammar_in_ebnf):
...     print rule
list ::= @2
@2 ::= <empty>
@2 ::= @2 @1
@1 ::= item
item ::= i

The helper function 'parse_from_ebnf' uses 'ebnf_parse'
to generate the list of Rule objects, constructs a grammar, a parser
and finally uses the parser to parse an input.

The following subset of the ISO specification is supported:

grammar = { rule };
rule = symbol, '=', [ list of alternatives ], ';';
list of alternatives = item sequence, { '|', item sequence }
item sequence = item, { ',', item };
item = symbol | quoted literal
    | '(', list of alternatives, ')'    # grouping
    | '[', list of alternatives, ']'    # optionality
    | '{', list of alternatives, '}';   # repetition
symbol = identifier, { identifier };

The symbol on the left side of the first rule is considered the starting symbol
and the corresponding Rule object will be the first in the result list.

Actions associated with the returned Rule objects group the subexpressions
in the following manner.

For a list of alternatives 'X = a_1 | a_2;', the value of 'X' is 
that of the alternative.

>>> parse_from_ebnf('a', 'root = "a" | "b";')
('a',)

For a sequential composition 'X = a_1, a_2;'
the value of 'X' is a tuple of values of subexpressions. Literals quoted
with apostrophes and symbols whose name starts with an underscore are ommited
from the tuple.

>>> parse_from_ebnf('ab', 'root = "a", "b" | "c";')
('a', 'b')
>>> parse_from_ebnf('ab', '''root = "a", 'b' | "c";''')
('a',)
>>> parse_from_ebnf('c', 'root = "a", "b" | "c";')
('c',)

Optional subexpressions have the value of the nested subexpression
or None if it's missing. 

>>> parse_from_ebnf('a', 'root = "a", ["b"] | "c";')
('a', None)
>>> parse_from_ebnf('ab', 'root = "a", ["b"] | "c";')
('a', 'b')

The repetition introduces a list.

>>> parse_from_ebnf('a', 'root = "a", {"b"} | "c";')
('a', [])
>>> parse_from_ebnf('abb', 'root = "a", {"b"} | "c";')
('a', ['b', 'b'])

The grouping has the same value as the subexpression,
except when the value is a one-tuple. In that case, is is unboxed.

>>> parse_from_ebnf('a', 'root = {("a")};')
(['a'],)
>>> parse_from_ebnf('ab', 'root = {("a", "b")};')
([('a', 'b')],)

The optional argument 'action' is called after each ebnf reduction
to tranform the value of the corresponding nonterminal.

>>> parse_from_ebnf('aaa', 'root = { "a" };', action=lambda self, list: '.'.join(list))
'a.a.a'
"""

from rule import Rule
from grammar import Grammar
from lrparser import Parser
from simple_lexer import simple_lexer

class _Item:
    def __init__(self, syms, visibility, rules):
        self.syms = syms
        self.visibility = visibility
        self.rules = rules
        
    def __repr__(self):
        return repr((self.syms, self.rules))
        
class _ActionFilter:
    def __init__(self, action, visibilities):
        self.action = action
        self.visibilities = visibilities
        
    def __call__(self, self2, *args):
        return self.action(self2, *(arg for j, arg in enumerate(args) if self.visibilities[j]))

class _AltList:
    def __init__(self, item):
        self.items = [item.syms]
        self.visibilities = [item.visibility]
        self.rules = item.rules

    def __repr__(self):
        return repr((self.items, self.visibilities, self.rules))

    def make_rules(self, unique, action=lambda self, *args: tuple(args) if len(args) != 1 else args[0]):
        for i, item in enumerate(self.items):
            self.rules.append(Rule(unique, *item,
                action=_ActionFilter(action, self.visibilities[i])))
        return self.rules

def _concat_list(self, list, item):
    list.append(item)
    return list

class _Context:
    def __init__(self, action):
        self.counter = 0
        self.action = action
    
    def unique(self):
        self.counter += 1
        return '@%d' % self.counter
    
    def item_sym(self, sym):
        return _Item([sym], [True], [])
    
    def item_lit(self, quote, lit):
        visible = quote == '"'
        return _Item([ch for ch in lit[1]], [visible for ch in lit[1]], [])
        
    def item_group(self, _1, alt_list, _2):
        new_sym = self.unique()
        return _Item([new_sym], [True], alt_list.make_rules(new_sym))
        
    def item_rep(self, _1, alt_list, _2):
        new_sym = self.unique()
        rules = alt_list.make_rules(new_sym)
        rep_sym = self.unique()
        rules.append(Rule(rep_sym, rep_sym, new_sym, action=_concat_list))
        rules.append(Rule(rep_sym, action=lambda self: []))
        return _Item([rep_sym], [True], rules)

    def item_opt(self, _1, alt_list, _2):
        new_sym = self.unique()
        rules = alt_list.make_rules(new_sym)
        rules.append(Rule(new_sym, action=lambda self: None))
        return _Item([new_sym], [True], rules)

    def seq_list_concat(self, seq_list, _1, item):
        seq_list.rules.extend(item.rules)
        seq_list.visibility.extend(item.visibility)
        seq_list.syms.extend(item.syms)
        return seq_list
        
    def new_alt_list(self, seq_list):
        return _AltList(seq_list)
        
    def append_alt_list(self, alt_list, _1, seq_list):
        alt_list.rules.extend(seq_list.rules)
        alt_list.visibilities.append(seq_list.visibility)
        alt_list.items.append(seq_list.syms)
        return alt_list
        
    def empty_rule(self, sym, _1, _2):
        return [Rule(sym, action=self.action)]
        
    def make_rule(self, sym, _1, alt_list, _2):
        return alt_list.make_rules(sym, self.action)
        
    def append_rule(self, rule_list, rule):
        rule.reverse()
        rule_list.extend(rule)
        return rule_list

_ebnf_grammar = Grammar(
    Rule('rule_list', action=lambda self: []),
    Rule('rule_list', 'rule_list', 'rule', action=_Context.append_rule),
    
    Rule('rule', 'sym', '=', ';', action=_Context.empty_rule),
    Rule('rule', 'sym', '=', 'alt_list', ';', action=_Context.make_rule),
    
    Rule('alt_list', 'seq_list', action=_Context.new_alt_list),
    Rule('alt_list', 'alt_list', '|', 'seq_list', action=_Context.append_alt_list),
    
    Rule('seq_list', 'item', action=lambda self, item: item),
    Rule('seq_list', 'seq_list', ',', 'item', action=_Context.seq_list_concat),
    
    Rule('item', 'sym', action=_Context.item_sym),
    Rule('item', '\'', 'ql', action=_Context.item_lit),
    Rule('item', '"', 'ql', action=_Context.item_lit),
    Rule('item', '(', 'alt_list', ')', action=_Context.item_group),
    Rule('item', '{', 'alt_list', '}', action=_Context.item_rep),
    Rule('item', '[', 'alt_list', ']', action=_Context.item_opt),
    
    Rule('sym', 'id', action=lambda self, id: id[1]),
    Rule('sym', 'sym', 'id', action=lambda self, sym, id: ' '.join((sym, id[1])))
    )
    
_ebnf_parser = Parser(_ebnf_grammar, k=1)

def ebnf_parse(input, action=lambda self, *args: args):
    """Parses an EBNF grammar and returns a corresponding list of Rule objects."""
    return _ebnf_parser.parse(simple_lexer(input), context=_Context(action))

def parse_from_ebnf(input, ebnf, action=lambda self, *args: args):
    """Parses an EBNF grammar, creates a parser for it and parses an input with it."""
    return Parser(Grammar(*ebnf_parse(ebnf, action=action))).parse(input)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
