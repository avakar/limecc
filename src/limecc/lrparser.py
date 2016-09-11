"""
This module provides the `make_lrparser` function, which creates
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
exceptions. The `make_lrparser` function will raise `ActionConflictError`
if the grammar turns out not to be LR(k).

    >>> g4 = Grammar(
    ...     Rule('root', ('header', 'list',)),
    ...     Rule('list', ()),
    ...     Rule('list', ('item',)),
    ...     Rule('list', ('list', 'item')),
    ...     )
    >>> make_lrparser(g4, k=0)
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
    ...     make_lrparser(g4, k=0)
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

Sentential forms
----------------

The LR parser may be requested to accept sentential forms (i.e. sequences
of terminal and non-terminal symbols) as well as terminal words. Set
`sentential_forms` parameter to true when calling `make_lrparser` function.

    >>> sp1 = make_lrparser(g1, sentential_forms=True)
    >>> sp1.parse(['list', 'item'])
    ('list', 'item')
    >>> sp1.parse(['list', 'list'])
    Traceback (most recent call last):
        ...
    ParsingError: Unexpected input token: ('list',), position 1

Keep in mind that supporting sentential forms will make the resulting parser
larger and slower. On the other hand, such a parser will be useful when
performing tests on a grammar.

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

from .rule import Rule
from .grammar import Grammar
from .first import First
import sys

def _extract_symbol(token):
    return token[0] if isinstance(token, tuple) else getattr(token, 'symbol', token)

def _extract_value(token):
    return token[1] if isinstance(token, tuple) else getattr(token, 'value', token)

def _extract_location(token, token_index=None):
    return token[2] if isinstance(token, tuple) else getattr(token, 'pos', token_index)

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
        res.append('\n'.join([('>' if i in (self.item1, self.item2) else ' ') + _format_trace(self.g, item) for i, item in enumerate(state.itemlist)]))

        while True:
            parent_symbol = state.parent_symbol
            next_id = state.parent_id
            state = self.states[next_id] if next_id != None else None
            if state is None:
                break
            res.append('\n'.join([('>' if _next_token(self.g, item) == parent_symbol else ' ') + _format_trace(self.g, item) for i, item in enumerate(state.itemlist)]))

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

class ParsingError(RuntimeError):
    """Raised by a parser if the input word is not a sentence of the grammar."""
    def __init__(self, message, pos=None):
        RuntimeError.__init__(self, message)
        self.pos = pos
    def format(self, severity='error'):
        return '%s: %s: %s' % (self.pos, severity, self.message)
    def __str__(self):
        return self.format()

class UnexpectedTokenError(ParsingError):
    def __init__(self, token, pos=None):
        pos = _extract_location(token, pos)
        ParsingError.__init__(self, 'unexpected token: %r (%r)' % (_extract_value(token), _extract_symbol(token)), pos)
        self.token = token

class PrematureEndOfFileError(ParsingError):
    """Raised when an end of file is reached prematurely."""

def _next_token(g, item):
    return item.rule.right[item.index] if not item.final else None

def _format_item(g, item, symbol_repr=repr):
    right_syms = [symbol_repr(symbol) for symbol in item.rule.right]
    if item.index == 0:
        if not right_syms:
            right_syms = ['. ']
        else:
            right_syms[0] = '. ' + right_syms[0]
    elif item.index == len(right_syms):
        right_syms[item.index - 1] = right_syms[item.index - 1] + ' . '
    else:
        right_syms[item.index - 1] = right_syms[item.index - 1] + ' . ' + right_syms[item.index]
        del right_syms[self.index]

    lookahead = ''.join((' (', ', '.join((symbol_repr(token) for token in item.lookahead)), ')')) if item.lookahead else ''
    return ''.join((repr(item.rule.left), ' = ', ', '.join(right_syms), ';', lookahead))

def _print_state(g, state, symbol_repr=repr):
    res = []
    for item in state.itemlist:
        res.append(_format_item(g, item, symbol_repr=symbol_repr))
    return '\n'.join(res)

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
    
    def __init__(self, grammar, k=1, keep_states=False, root=None, sentential_forms=False):
        if len(grammar) == 0:
            raise InvalidGrammarError('The grammar needs at least one rule.')

        if root is None:
            root = [grammar[0].left]
        else:
            if any((sym not in grammar.symbols() for sym in root)):
                raise InvalidGrammarError('The root sentential form is invalid')

        self.grammar = grammar
        self.k = k
        self.root = tuple(root)
        
        # Augment the grammar with a special rule: 'S -> R',
        # where S is a new non-terminal (in this case '').
        aug_grammar = Grammar(Rule('', self.root), *grammar)
        
        first = First(aug_grammar, k, nonterms=sentential_forms)
        
        kernel0 = frozenset([_Item(aug_grammar[0], 0, ())])
        state0 = State(kernel0, aug_grammar, first)
        states = [state0]

        i = 0
        state_kernel_map = { kernel0: 0 }
        while i < len(states):
            state = states[i]

            parts = {}
            for item in state.itemset:
                sym = _next_token(aug_grammar, item)
                if sym is None:
                    continue
                part = parts.setdefault(sym, [])
                part.append(_Item(item.rule, item.index + 1, item.lookahead))

            for symbol, kernel in parts.iteritems():
                kernel = frozenset(kernel)
                oldstate_index = state_kernel_map.get(kernel)
                if oldstate_index is not None:
                    state.goto[symbol] = oldstate_index
                    continue

                newstate = State(kernel, aug_grammar, first)
                state_kernel_map[kernel] = len(states)

                state.goto[symbol] = len(states)
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
                nt = _next_token(aug_grammar, item)
                if nt is None:
                    if item.rule.left == '':
                        accepting_state = state_id
                        add_action(state, item.lookahead, None, item_index)
                    else:
                        add_action(state, item.lookahead, item.rule, item_index)
                elif sentential_forms or aug_grammar.is_terminal(nt):
                    word = item.rule.right[item.index:] + item.lookahead
                    for w in first(word[1:]):
                        w = (word[:1] + w)[:k]
                        add_action(state, w, None, item_index)

        assert accepting_state != None
        
        self.accepting_state = accepting_state
        self.states = states
        self.k = k
        
        if not keep_states:
            for state in states:
                del state.itemset
                
    def parse(self, sentence, context=None, extract_symbol=_extract_symbol,
            extract_value=_extract_value, prereduce_visitor=None, postreduce_visitor=None,
            shift_visitor=None, state_visitor=None, reducer=None):

        def default_reducer(rule, ctx, *args):
            return rule.action(ctx, *args)
        reducer = reducer or default_reducer

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
            if key in state.action:
                action = state.action[key]
            else:
                assert lookahead
                raise UnexpectedTokenError(lookahead[0], token_counter)

            if action:   # reduce
                if len(action.right) > 0:
                    if prereduce_visitor:
                        prereduce_visitor(*asts[-len(action.right):])
                    new_ast = reducer(action, context, *asts[-len(action.right):])
                    if postreduce_visitor:
                        new_ast = postreduce_visitor(action, new_ast)
                    del stack[-len(action.right):]
                    del asts[-len(action.right):]
                else:
                    if prereduce_visitor:
                        prereduce_visitor()
                    new_ast = reducer(action, context)
                    if postreduce_visitor:
                        new_ast = postreduce_visitor(action, new_ast)
                
                next_state = self.states[stack[-1]].get_next_state(action.left, token_counter)
                assert next_state is not None
                stack.append(next_state)
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
                        raise PrematureEndOfFileError()
                token_counter += 1
                
                key = extract_symbol(tok)

                next_state = state.get_next_state(key, token_counter)
                if next_state is None:
                    raise UnexpectedTokenError(tok, token_counter)

                stack.append(next_state)
                asts.append(extract_value(tok))

class State:
    """Represents a single state of a LR(k) parser.
    
    There are two tables of interest. The 'goto' table is a dict mapping
    symbols to state identifiers.
    
    The 'action' table maps lookahead strings to actions. An action
    is either 'None', corresponding to a shift, or a Rule object,
    corresponding to a reduce.
    """
    
    def __init__(self, kernel, grammar, first):
        self.kernel = frozenset(kernel)
        self._close(kernel, grammar, first)
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
    
    def get_next_state(self, symbol, counters):
        return self.goto.get(symbol)
        
    def _close(self, kernel, grammar, first):
        """Given a list of items, returns the corresponding closed State object."""
        i = 0

        itemset = set(kernel)
        itemlist = list(kernel)
        while i < len(itemlist):
            curitem = itemlist[i]
            
            rule_suffix = curitem.rule.right[curitem.index + 1:]
            for next_lookahead in first(rule_suffix + curitem.lookahead):
                for next_rule in grammar.rules(_next_token(grammar, curitem)):
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

class _SymbolMatcher:
    def __init__(self, symbol):
        self.symbol = symbol
        
    def __call__(self, symbol):
        return self.symbol == symbol
        
    def __repr__(self):
        return '_SymbolMatcher(%s)' % self.symbol

def make_lrparser(g, k=1, keep_states=False, root=None, sentential_forms=False):
    return _LrParser(g, k=k, keep_states=keep_states, root=root, sentential_forms=sentential_forms)
