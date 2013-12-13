"""
This module provides the make_lrparser function, which creates
a parser from a grammar in LR(k) form and return an object providing
a single function, `parse`. Most often, `k` is set to 1.

    >>> g1 = Grammar(
    ...     Rule('list', ()),
    ...     Rule('list', ('list', 'item'))
    ...     )
    >>> p1 = make_lrparser(g1)

Parsing
-------
The `parse` function expects an iterable yielding tokens.

Whenever a reduction occurs, the parser calls the semantic action
associated with the rule through which the reduction is happening.
Remember that through the default action, the parsing will yield
a simple parse tree.

    >>> p1.parse([])
    ()
    >>> p1.parse(['item'])
    ((), 'item')
    >>> p1.parse(['item', 'item'])
    (((), 'item'), 'item')

Modify the semantic actions to get the required results.

    >>> g2 = Grammar(
    ...     Rule('list', (), lambda ctx: 0),
    ...     Rule('list', ('list', 'item'), lambda ctx, l, i: l + 1)
    ...     )
    >>> p2 = make_lrparser(g2)
    >>> p2.parse([])
    0
    >>> p2.parse(['item'])
    1
    >>> p2.parse(['item', 'item'])
    2

    >>> def append_list(ctx, l, i):
    ...     l.append(i)
    ...     return l
    >>> g3 = Grammar(
    ...     Rule('list', (), lambda ctx: []),
    ...     Rule('list', ('list', 'item'), append_list)
    ...     )
    >>> p3 = make_lrparser(g3)
    >>> p3.parse([])
    []
    >>> p3.parse(['item'])
    ['item']
    >>> p3.parse(['item', 'item'])
    ['item', 'item']

Typically, tokens will be complex objects, containing not only
the terminal symbol name, but also a value and potentially a source
text position.

During parsing, the parser uses `extract_symbol` function to recover
the name of the terminal symbol and `extract_value` to recover
the token's value. The token values are passed to semantic actions.

The default `extract_symbol` and `extract_value` functions are designed
off-the-shelf to work with tuples and user-defined objects.

 1. For tuples, the first member is assumed to be the symbol name
    and the second member the token's value. The rest of the tuple
    is ignored and may contain additional information.
 2. For objects, the symbol is read from the `symbol` member,
    while the value is read from `value` member. If the object
    doesn't have the `value` member, the object itself is used
    as the token's value.
 3. Otherwise, the token is assumed to represent both the symbol
    and the value.

    >>> class Tok:
    ...     def __init__(self, val):
    ...         self.symbol = 'item'
    ...         self.value = val
    >>> p1.parse([Tok('a'), Tok('b'), Tok('c')])
    ((((), 'a'), 'b'), 'c')
    >>> p3.parse([Tok('a'), Tok('b'), Tok('c')])
    ['a', 'b', 'c']

You can override both the `extract_symbol` and `extract_value`
by passing your custom versions to the `parse` method.

    >>> p3.parse('abc', extract_symbol=lambda tok: 'item')
    ['a', 'b', 'c']

The context passed to the semantic actions is `None` by default,
but can be changed with the `context` parameter passed to the `parse`
method.

Errors during parser construction
---------------------------------
Errors during parser construction and parsing itself are signaled with
exceptions. The `make_lrparser` function with raise `ActionConflictError`
if the grammar turns out not to be LR(k).

    >>> g = Grammar(
    ...     Rule('root', ('header', 'list',)),
    ...     Rule('list', ()),
    ...     Rule('list', ('item',)),
    ...     Rule('list', ('list', 'item')),
    ...     )
    >>> make_lrparser(g, k=0) # doctest: +ELLIPSIS
    Traceback (most recent call last):
       ...
    ActionConflictError: shift/reduce conflict during LR(0) parser construction

The `ActionConflictError` contains details about the LR conflict,
in particular

 * the grammar `g` that failed to be LR(k),
 * the list of LR(k) `states` constructed from the grammar, and
 * `conflicting_state`, the state in which the conflict occurred.

To debug the problem, the exception object provides the methods
`format_trace` and its companion, `print_trace`. These methods
print a sequence of states, which form a counterexample and
also highlight the conflicting items.

    >>> try:
    ...     make_lrparser(g, k=0)
    ... except ActionConflictError, e:
    ...     err = e
    >>> print err.format_trace()
     '' = . 'root';
    >'root' = . 'header', 'list';
    <BLANKLINE>
     'root' = 'header' . 'list';
    >'list' = . ;
    >'list' = . 'item';
     'list' = . 'list', 'item';

In the above example, the last state has two items highlighted;
a shift/reduce conflict can be seen. By following the list of states,
a counterexample can be constructed: ['header', 'item'],

LR tables and states
--------------------
Internally, the object returned from `make_lrparser` contains a list
of LR parser states, which is followed during parsing. The state list
can however be used directly, e.g. to compile a LR parser in another
language (wink, wink).

The states are stored in the `states` member variable as a list
of `State` objects. A state object contains the corresponding action
and goto tables.

See the documentation for the `State` class for more information.
"""

from grammar import Grammar, Rule
from first import First
import sys

def _extract_symbol(token):
    return token[0] if isinstance(token, tuple) else getattr(token, 'symbol', token)

def _extract_value(token):
    return token[1] if isinstance(token, tuple) else getattr(token, 'value', token)

class InvalidGrammarError(Exception):
    """Raised during a construction of a parser, if the grammar is not LR(k)."""

class ActionConflictError(Exception):
    """Raised during a construction of a parser, if the grammar is not LR(k)."""
    def __init__(self, message, conflicting_state, states, g, item1, item2):
        Exception.__init__(self, message)
        self.states = states
        self.conflicting_state = conflicting_state
        self.g = g
        self.item1 = item1
        self.item2 = item2

    def format_trace(self):
        state = self.conflicting_state

        res = []
        res.append('\n'.join([('>' if i in (self.item1, self.item2) else ' ') + str(item) for i, item in enumerate(state.itemlist)]))

        while True:
            parent_symbol = state.parent_symbol
            next_id = state.parent_id
            state = self.states[next_id] if next_id != None else None
            if state is None:
                break
            res.append('\n'.join([('>' if item.next_token() == parent_symbol else ' ') + str(item) for i, item in enumerate(state.itemlist)]))

        return '\n\n'.join(reversed(res))

    def print_trace(self, file=sys.stderr):
        print >>file, self.format_trace()

    def counterexample(self):
        trace = []
        st = self.conflicting_state
        while st.parent_id:
            trace.append(st.parent_symbol)
            st = self.states[st.parent_id]
        trace.append(st.parent_symbol)
        if hasattr(self.g, 'token_comments'):
            trace = [self.g.token_comments.get(sym, sym) for sym in trace]
        return tuple(reversed(trace))

class ParsingError(Exception):
    """Raised by a parser if the input word is not a sentence of the grammar."""
    def __init__(self, message, position):
        self.position = position
        Exception.__init__(self, message)
    def __str__(self):
        return '%s, position %d' % (self.args[0], self.position)

class _LrParser(object):
    """Represents a LR(k) parser.
    
    The parser is created with a grammar and a 'k'. The LR parsing tables
    are created during construction. If the grammar is not LR(k),
    an InvalidGrammarException is raised.
    
    >>> not_a_lr0_grammar = Grammar(Rule('list'), Rule('list', ('item', 'list')))
    >>> _LrParser(not_a_lr0_grammar, k=0)
    Traceback (most recent call last):
        ...
    ActionConflictError: shift/reduce conflict during LR(0) parser construction

    >>> lr0_grammar = Grammar(
    ...     Rule('list', action=lambda self: []),
    ...     Rule('list', ('list', 'item'), action=lambda self, l, i: l + [i]))
    >>> p = _LrParser(lr0_grammar, k=0)
    
    The method 'parse' will accept an iterable of tokens, which are arbitrary objects.
    A token T is matched to a terminal symbol S in the following manner.
    Matching is done with the equality operator, i.e. 'S == extract_symbol(T)'.
    
    Whenever the parser reduces a word to a non-terminal, the associated semantic action is executed.
    This way Abstract Syntax Trees or other objects can be constructed. The parse method
    returns the result of an action associated with the topmost reduction rule.
    
    >>> p.parse(())
    []
    >>> p.parse(('item', 'item', 'item', 'item'))
    ['item', 'item', 'item', 'item']
    >>> p.parse('spam', extract_symbol=lambda x: 'item')
    ['s', 'p', 'a', 'm']
    
    Optionally, the 'parse' function will accept a 'context' keyword argument.
    This is passed to an action when reduction occurs. By default, context is None.
    
    If an error occurs during parsing, the ParsingError is raised.
    
    >>> p.parse('spam')
    Traceback (most recent call last):
        ...
    ParsingError: Unexpected input token: 's', position 1
    """
    
    def __init__(self, grammar, k=1, keep_states=False):
        if grammar.root() == None:
            raise InvalidGrammarError('The grammar needs a root non-terminal.')

        self.grammar = grammar
        self.k = k
        
        # Augment the grammar with a special rule: 'S -> R',
        # where S is a new non-terminal (in this case '').
        aug_grammar = Grammar(Rule('', (grammar.root(),)), *grammar)
        
        first = First(aug_grammar, k)
        
        def _goto(state, symbol):
            """Given a state and a symbol, constructs and returns the next state."""
            itemlist = [_Item(item.rule, item.index + 1, item.lookahead) for item in state.itemset if item.next_token() == symbol]
            if not itemlist:
                return None
            return State(itemlist, aug_grammar, first)
        
        state0 = State([_Item(aug_grammar[0], 0, ())], aug_grammar, first)
        states = [state0]
        state_map = { state0: 0 }
        
        i = 0
        while i < len(states):
            state = states[i]
            
            for symbol in aug_grammar.symbols():
                newstate = _goto(state, symbol)
                if newstate is None:
                    continue
                    
                oldstate_index = state_map.get(newstate)
                if oldstate_index is not None:
                    state.goto[symbol] = oldstate_index
                else:
                    state.goto[symbol] = len(states)
                    state_map[newstate] = len(states)
                    newstate.parent_id = i
                    newstate.parent_symbol = symbol
                    states.append(newstate)
            
            i += 1
        
        accepting_state = None
        
        def add_action(state, lookahead, action, new_item_index):
            new_item = state.itemlist[new_item_index]
            if lookahead in state.action and state.action[lookahead] != action:
                conflict_type = 'shift/reduce' if action is None or state.action[lookahead] is None else 'reduce/reduce'
                raise ActionConflictError('%s conflict during LR(%d) parser construction' % (conflict_type, k),
                    state, states, grammar, new_item_index, state.action_origin[lookahead])
            state.action[lookahead] = action
            state.action_origin[lookahead] = new_item_index
        
        for state_id, state in enumerate(states):
            for item_index, item in enumerate(state.itemlist):
                nt = item.next_token()
                if nt is None:
                    if item.rule.left == '':
                        accepting_state = state_id
                        add_action(state, item.lookahead, None, item_index)
                    else:
                        add_action(state, item.lookahead, item.rule, item_index)
                elif aug_grammar.is_terminal(nt):
                    for la in item.lookaheads(first):
                        add_action(state, la, None, item_index)
        
        assert accepting_state != None
        
        self.accepting_state = accepting_state
        self.states = states
        self.k = k
        
        if not keep_states:
            for state in states:
                del state.itemset
                
    def parse(self, sentence, context=None, extract_symbol=_extract_symbol,
            extract_value=_extract_value, prereduce_visitor=None, postreduce_visitor=None,
            shift_visitor=None, state_visitor=None):
        it = iter(sentence)

        lookahead = []
        if self.k == 0:
            def get_shift_token():
                try:
                    return it.next()
                except StopIteration:
                    return None
            def update_lookahead():
                pass
        elif self.k == 1:
            def get_shift_token():
                if not lookahead:
                    return None
                return lookahead.pop()
            def update_lookahead():
                if not lookahead:
                    try:
                        lookahead.append(it.next())
                    except StopIteration:
                        pass
        else:
            def update_lookahead():
                while len(lookahead) < self.k:
                    try:
                        lookahead.append(it.next())
                    except StopIteration:
                        break
                    
            def get_shift_token():
                if not lookahead:
                    return None
                return lookahead.pop(0)

        stack = [0]
        asts = []
        token_counter = 0
        while True:
            state_id = stack[-1]
            state = self.states[state_id]
            if state_visitor:
                state_visitor(state)

            update_lookahead()
            key = tuple(extract_symbol(token) for token in lookahead)
            action = state.get_action(key, token_counter)
            if action:   # reduce
                if len(action.right) > 0:
                    if prereduce_visitor:
                        prereduce_visitor(*asts[-len(action.right):])
                    new_ast = action.action(context, *asts[-len(action.right):])
                    if postreduce_visitor:
                        new_ast = postreduce_visitor(action, new_ast)
                    del stack[-len(action.right):]
                    del asts[-len(action.right):]
                else:
                    if prereduce_visitor:
                        prereduce_visitor()
                    new_ast = action.action(context)
                    if postreduce_visitor:
                        new_ast = postreduce_visitor(action, new_ast)
                
                stack.append(self.states[stack[-1]].get_next_state(action.left, token_counter))
                asts.append(new_ast)
            else:   # shift
                tok = get_shift_token()
                if shift_visitor:
                    shift_visitor(tok)
                if tok is None:
                    if state_id == self.accepting_state:
                        assert len(asts) == 1
                        return asts[0]
                    else:
                        raise ParsingError('Reached the end of file prematurely.', token_counter)
                token_counter += 1
                
                key = extract_symbol(tok)
                stack.append(state.get_next_state(key, token_counter))
                asts.append(extract_value(tok))

class State:
    """Represents a single state of a LR(k) parser.
    
    There are two tables of interest. The 'goto' table is a dict mapping
    symbols to state identifiers.
    
    The 'action' table maps lookahead strings to actions. An action
    is either 'None', corresponding to a shift, or a Rule object,
    corresponding to a reduce.
    """
    
    def __init__(self, itemlist, grammar, first):
        self._close(itemlist, grammar, first)
        self.parent_id = None
        self.parent_symbol = None

        self.goto = {}
        self.action = {}
        self.action_origin = {}

    def __eq__(self, other):
        if not isinstance(other, State):
            return False
        return self.itemset == other.itemset
        
    def __hash__(self):
        return hash(self.itemset)
        
    def __repr__(self):
        return repr(self.itemlist)
    
    def print_state(self, symbol_repr=repr):
        res = []
        for item in self.itemlist:
            res.append(item.print_item(symbol_repr))
        return '\n'.join(res)

    def get_action(self, lookahead, counters):
        if lookahead in self.action:
            return self.action[lookahead]
        raise ParsingError('Unexpected input token: %s' % repr(lookahead), counters)

    def get_next_state(self, symbol, counters):
        if symbol in self.goto:
            return self.goto[symbol]
            
        raise ParsingError('Unexpected input token: %s' % repr(symbol), counters)
        
    def _close(self, itemset, grammar, first):
        """Given a list of items, returns the corresponding closed State object."""
        i = 0
        
        itemset = set(itemset)
        itemlist = list(itemset)
        while i < len(itemlist):
            curitem = itemlist[i]
            
            for next_lookahead in curitem.next_lookaheads(first):
                for next_rule in grammar.rules(curitem.next_token()):
                    newitem = _Item(next_rule, 0, next_lookahead)
                    if newitem not in itemset:
                        itemlist.append(newitem)
                        itemset.add(newitem)
            
            i += 1
            
        self.itemset = frozenset(itemset)
        self.itemlist = tuple(itemlist)

class _Item:
    def __init__(self, rule, index, lookahead):
        self.rule = rule
        self.index = index
        self.lookahead = lookahead
        
        self.final = len(self.rule.right) <= self.index
    
    def __cmp__(self, other):
        return cmp(
            (self.rule, self.index, self.lookahead),
            (other.rule, other.index, other.lookahead))
    
    def __hash__(self):
        return hash((self.rule, self.index, self.lookahead))
        
    def print_item(self, symbol_repr=repr):
        right_syms = [symbol_repr(symbol) for symbol in self.rule.right]
        if self.index == 0:
            if not right_syms:
                right_syms = ['. ']
            else:
                right_syms[0] = '. ' + right_syms[0]
        elif self.index == len(right_syms):
            right_syms[self.index - 1] = right_syms[self.index - 1] + ' . '
        else:
            right_syms[self.index - 1] = right_syms[self.index - 1] + ' . ' + right_syms[self.index]
            del right_syms[self.index]

        lookahead = ''.join((' (', ', '.join((symbol_repr(token) for token in self.lookahead)), ')')) if self.lookahead else ''
        return ''.join((repr(self.rule.left), ' = ', ', '.join(right_syms), ';', lookahead))
        
    def is_kernel(self):
        return self.index != 0 or self.rule.left == ''
    
    def next_token(self):
        return self.rule.right[self.index] if not self.final else None
    
    def next_lookaheads(self, first):
        rule_suffix = self.rule.right[self.index + 1:]
        word = rule_suffix + self.lookahead
        return first(word)
    
    def lookaheads(self, first):
        rule_suffix = self.rule.right[self.index:]
        word = rule_suffix + self.lookahead
        return first(word)

class _SymbolMatcher:
    def __init__(self, symbol):
        self.symbol = symbol
        
    def __call__(self, symbol):
        return self.symbol == symbol
        
    def __repr__(self):
        return '_SymbolMatcher(%s)' % self.symbol

def make_lrparser(g, k=1, keep_states=False):
    return _LrParser(g, k, keep_states)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
