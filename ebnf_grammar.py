"""
Provides a conversion between EBNF (ISO 14977:1996) and Rule objects.

The core functionality is provided via the 'ebnf_parse' function,
which receives a string representing the ebnf grammar
and returns the list of corresponding Rule objects.

>>> grammar_in_ebnf = 'list = { item }; item = "i";'
>>> for rule in ebnf_parse(grammar_in_ebnf):
...     print rule
list ::= @1
@1 ::= <empty>
@1 ::= @1 @2
@2 ::= item
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
'a'

For a sequential composition 'X = a_1, a_2;'
the value of 'X' is a tuple of values of subexpressions. Literals quoted
with apostrophes and symbols whose name starts with an underscore are ommited
from the tuple.

>>> parse_from_ebnf('ab', 'root = "a", "b" | "c";')
('a', 'b')
>>> parse_from_ebnf('ab', '''root = "a", 'b' | "c";''')
'a'
>>> parse_from_ebnf('c', 'root = "a", "b" | "c";')
'c'

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
except when the value is a one-tuple. In that case, the tuple is unboxed.

>>> parse_from_ebnf('a', 'root = {("a")};')
['a']
>>> parse_from_ebnf('ab', 'root = {("a", "b")};')
[('a', 'b')]

As an extension to the ISO-specified EBNF format, the postfix '+' operator
can be used to indicate "one or more" repetitions.

>>> parse_from_ebnf('aaa', 'root = "a"+;')
['a', 'a', 'a']
>>> parse_from_ebnf('a', 'root = "a"+;')
['a']
>>> parse_from_ebnf('', 'root = "a"+;') #doctest: +ELLIPSIS
Traceback (most recent call last):
    ...
ParsingError: ...

The optional argument 'action' is called after each ebnf reduction
to tranform the value of the corresponding nonterminal.

>>> parse_from_ebnf('aaa', 'root = { "a" };', action=lambda self, list: '.'.join(list))
'a.a.a'

>>> parse_from_ebnf(['id', 'id', 'nb', 'id'], 'quickbook = block, { _nb, block }; block = { id };')
(['id', 'id'], [['id']])
"""

from rule import Rule
from grammar import Grammar
from lrparser import Parser
from simple_lexer import simple_lexer

class _Item:
    """Represents the right side of a production rule (i.e. a partial rule).
    
    An item carries the list of symbols. For each symbol there is
    a boolean value representing its visibility. The value of
    an invisible symbol will not be passed as an argument to
    the associated semantic action.
    
    There also is a list of rules on which the partial rule depends.
    """
    def __init__(self, syms, visibility, rules):
        self.syms = syms
        self.visibility = visibility
        self.rules = rules
    
    def __repr__(self):
        return repr((self.syms, self.visibility, self.rules))
    
    def concat(self, item):
        self.syms.extend(item.syms)
        self.visibility.extend(item.visibility)
        self.rules.extend(item.rules)

def _pretty_forward_args(self, *args):
    if len(args) == 1:
        return args[0]
    return args

class _AltList:
    """Represents a set of alternative partial rules that are to be
    completed by a common nonterminal.
    """
    def __init__(self, *items):
        """Constructs an alt-list from a list of _Item objects."""
        self.items = [item.syms for item in items]
        self.visibilities = [item.visibility for item in items]
        self.rules = []
        for item in items:
            self.rules.extend(item.rules)

    def __repr__(self):
        return repr((self.items, self.visibilities, self.rules))
        
    def append(self, item):
        """Appends an additional partial rule (an _Item object) to the list of alternatives."""
        self.items.append(item.syms)
        self.visibilities.append(item.visibility)
        self.rules.extend(item.rules)

    def reduce(self, nonterm, visible=True, action=_pretty_forward_args):
        """Reduces the alt-list to a single item.
        
        The 'nonterm' symbol will be used as a left-hand-side symbol for all alternative rules.
        The alt-list will be reduced to a single partial rule consisting of a visible symbol 'nonterm'.
        The newly created _Item object objects will be returned.
        """
        rules = self.rules
        for item, visibility in zip(self.items, self.visibilities):
            rules.append(Rule(nonterm, item, action=_ActionFilter(action, visibility)))
        
        del self.rules
        del self.items
        del self.visibilities
        
        return _Item([nonterm], [visible], rules)

class _ActionFilter:
    """A forwarder with argument filtering.
    
    The filter carries a list of boolean values representing visibility.
    An invisible argument is discarded before forwarding.
    """
    def __init__(self, action, visibility):
        """
        The filter will forward the arguments to the 'action' callable.
        The corresponding 'visibility' list controls which arguments are forwarded
        and which are discarded.
        """
        self.action = action
        self.visibility = visibility
        
    def __call__(self, context, *args):
        """Forwards the call, filtering invisible arguments out."""
        return self.action(context, *(arg for arg, visible in zip(args, self.visibility) if visible))

def _make_empty_list(self):
    return []

def _make_one_item_list(self, item):
    return [item]

def _make_none(self):
    return None

def _concat_list(self, list, item):
    list.append(item)
    return list
    
def _id(self, item):
    return item
    
def _extract_identifier(self, id_token):
    return id_token[1]
    
def _concat_symbols(self, symbol, id):
    return ' '.join((symbol, id[1]))

class _ParsingContext:
    """A parsing state of an EBNF syntax parser."""

    def __init__(self, action, counter):
        self.counter = counter
        self.action = action
    
    def new_nonterm(self):
        self.counter += 1
        return '@%d' % self.counter
    
    def item_sym(self, sym):
        """
        item ::= symbol
        
        The symbol is considered invisible if it starts with an underscore.
        """
        if sym[0] == '_':
            return _Item([sym[1:]], [False], [])
        else:
            return _Item([sym], [True], [])
    
    def item_lit(self, quote, lit):
        """
        item ::= '\'' ql
        item ::= '"' ql
        
        A quoted literal is visible if it is enclosed in double quotes
        (as opposed to apostrophes).
        
        The 'lit' argument is a terminal token, a tuple ('ql', value).
        """
        visible = quote == '"'
        return _Item([ch for ch in lit[1]], [visible for ch in lit[1]], [])
    
    def item_group(self, _1, alt_list, _2):
        """
        item ::= ( alt_list )
        """
        new_nonterm = self.new_nonterm()
        return alt_list.reduce(new_nonterm, visible=True)
        
    def item_rep(self, _1, alt_list, _2):
        """
        item ::= { alt_list }
        """
        rep_sym = self.new_nonterm()
        item = alt_list.reduce(self.new_nonterm(), visible=True)
        item.rules.append(Rule(rep_sym, (rep_sym, item.syms[0]), action=_concat_list))
        item.rules.append(Rule(rep_sym, action=_make_empty_list))
        return _Item([rep_sym], [True], item.rules)

    def item_kleene_plus(self, item, _1):
        """
        item ::= item '+'
        """
        rep_sym = self.new_nonterm()
        item.rules.append(Rule(rep_sym, [rep_sym] + item.syms, action=_concat_list))
        item.rules.append(Rule(rep_sym, item.syms, action=_make_one_item_list))
        return _Item([rep_sym], [True], item.rules)

    def item_kleene_star(self, item, _1):
        """
        item ::= item '*'
        """
        rep_sym = self.new_nonterm()
        item.rules.append(Rule(rep_sym, [rep_sym] + item.syms, action=_concat_list))
        item.rules.append(Rule(rep_sym, action=_make_empty_list))
        return _Item([rep_sym], [True], item.rules)

    def item_opt(self, _1, alt_list, _2):
        """
        item ::= [ alt_list ]
        """
        item = alt_list.reduce(self.new_nonterm(), visible=True)
        item.rules.append(Rule(item.syms[0], action=_make_none))
        return item

    def seq_list_concat(self, seq_list, _1, item):
        """
        seq_list ::= seq_list , item
        
        Both seq_list and item are _Item objects.
        """
        seq_list.concat(item)
        return seq_list
        
    def new_alt_list(self, seq_list):
        """
        alt_list ::= seq_list
        """
        return _AltList(seq_list)
        
    def append_alt_list(self, alt_list, _1, seq_list):
        """
        alt_list ::= alt_list | seq_list
        """
        alt_list.append(seq_list)
        return alt_list
        
    def empty_rule(self, sym, _1, _2):
        """
        rule ::= sym = ;
        """
        return [Rule(sym, action=self.action)]
        
    def make_rule(self, sym, _1, alt_list, _2):
        """
        rule ::= sym = alt_list ;
        """
        item = alt_list.reduce(sym, action=self.action)
        return item.rules
        
    def append_rule(self, rule_list, rule):
        """
        rule_list ::= rule_list rule
        """
        rule.reverse()
        rule_list.extend(rule)
        return rule_list

_ebnf_grammar = Grammar(
    Rule('rule_list', action=_make_empty_list),
    Rule('rule_list', ('rule_list', 'rule'), action=_ParsingContext.append_rule),
    
    Rule('rule', ('sym', '=', ';'), action=_ParsingContext.empty_rule),
    Rule('rule', ('sym', '=', 'alt_list', ';'), action=_ParsingContext.make_rule),
    
    Rule('alt_list', ('seq_list',),  action=_ParsingContext.new_alt_list),
    Rule('alt_list', ('alt_list', '|', 'seq_list'), action=_ParsingContext.append_alt_list),
    
    Rule('seq_list', ('item',), action=_id),
    Rule('seq_list', ('seq_list', ',', 'item'), action=_ParsingContext.seq_list_concat),
    
    Rule('item', ('sym',), action=_ParsingContext.item_sym),
    Rule('item', ('\'', 'ql'), action=_ParsingContext.item_lit),
    Rule('item', ('"', 'ql'), action=_ParsingContext.item_lit),
    Rule('item', ('(', 'alt_list', ')'), action=_ParsingContext.item_group),
    Rule('item', ('{', 'alt_list', '}'), action=_ParsingContext.item_rep),
    Rule('item', ('[', 'alt_list', ']'), action=_ParsingContext.item_opt),
    Rule('item', ('item', '+'), action=_ParsingContext.item_kleene_plus),
    Rule('item', ('item', '*'), action=_ParsingContext.item_kleene_star),
    
    Rule('sym', ('id',), action=_extract_identifier),
    Rule('sym', ('sym', 'id'), action=_concat_symbols)
    )
    
_ebnf_parser = Parser(_ebnf_grammar, k=1)

def ebnf_parse(input, action=_pretty_forward_args, counter=None):
    """Parses an EBNF grammar and returns a corresponding list of Rule objects."""
    context = _ParsingContext(action, counter=counter or 0)
    rules = _ebnf_parser.parse(simple_lexer(input), context=context)
    return (rules, context.counter) if counter != None else rules

def parse_from_ebnf(input, ebnf, action=_pretty_forward_args):
    """Parses an EBNF grammar, creates a parser for it and parses an input with it."""
    return Parser(Grammar(*ebnf_parse(ebnf, action=action))).parse(input)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
