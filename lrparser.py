#TODO: document matchers properly.

from grammar import Grammar, Rule
from first import First
from matchers import default_matchers

class InvalidGrammarError(Exception):
    """Raised during a construction of a parser, if the grammar is not LR(k)."""

class ActionConflictError(InvalidGrammarError):
    """Raised during a construction of a parser, if the grammar is not LR(k)."""
    def __init__(self, message, relevant_state, states):
        InvalidGrammarError.__init__(self, message)
        self.states = states
        self.relevant_state = relevant_state
    
    def pretty_states(self):
        """Returns a string with pretty-printed itemsets."""
        res = []
        for state in self.states:
            for item in state.itemset:
                res.append(str(item))
                res.append('\n')
            res.append('\n')
        return ''.join(res)
    
    def relevant_state_trace(self):
        state = self.relevant_state
        
        res = []
        while state != None:
            res.append(str(state))
            
            next_id = state.parent_id
            state = self.states[next_id] if next_id != None else None
        
        return '\n'.join(res)

class ParsingError(Exception):
    """Raised by a parser if the input word is not a sentence of the grammar."""
    def __init__(self, message, position):
        self.position = position
        Exception.__init__(self, message)
    def __str__(self):
        return '%s, position %d' % (self.args[0], self.position)
    
def extract_first(token):
    """Returns the argument or, if it is a tuple, its first member.
    
    >>> extract_first('list')
    'list'
    >>> extract_first(('item', 42))
    'item'
    """
    return token[0] if isinstance(token, tuple) else token

def extract_second(token):
    """Returns the argument or, if it is a tuple, its second member.
    
    >>> extract_first('list')
    'list'
    >>> extract_first(('item', 42))
    42
    """
    return token[1] if isinstance(token, tuple) else token

class Parser(object):
    """Represents a LR(k) parser.
    
    The parser is created with a grammar and a 'k'. The LR parsing tables
    are created during construction. If the grammar is not LR(k),
    an InvalidGrammarException is raised.
    
    >>> not_a_lr0_grammar = Grammar(Rule('list'), Rule('list', ('item', 'list')))
    >>> Parser(not_a_lr0_grammar, k=0) # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ActionConflictError: LR(0) table conflict: ...

    >>> lr0_grammar = Grammar(
    ...     Rule('list', action=lambda self: []),
    ...     Rule('list', ('list', 'item'), action=lambda self, l, i: l + [i]))
    >>> p = Parser(lr0_grammar, k=0)
    >>> print p.grammar
    'list' = ;
    'list' = 'list', 'item';
    
    The method 'parse' will accept an iterable of tokens, which are arbitrary objects.
    A token T is matched to a terminal symbol S in the following manner. First,
    the terminal S is looked up in the 'matchers' dict, passed during parser's construction.
    If found, the match is successful if 'matchers[S](extract(T))' is true.
    Otherwise, matching is done with the equality operator, i.e. 'S == extract(T)'.
    The 'extract' function is passed to the 'parse' method and defaults to 'extract_first'.
    
    Whenever the parser reduces a word to a non-terminal, the associated semantic action is executed.
    This way Abstract Syntax Trees or other objects can be constructed. The parse method
    returns the result of an action associated with the topmost reduction rule.
    
    >>> p.parse(())
    []
    >>> p.parse(('item', 'item', 'item', 'item'))
    ['item', 'item', 'item', 'item']
    >>> p.parse('spam', extract=lambda x: 'item')
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
            raise InvalidGrammarError('There must be at least one rule in the grammar.')
        
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
                if newstate == None:
                    continue
                    
                oldstate_index = state_map.get(newstate)
                if oldstate_index != None:
                    state.goto[symbol] = oldstate_index
                else:
                    state.goto[symbol] = len(states)
                    state_map[newstate] = len(states)
                    newstate.parent_id = i
                    states.append(newstate)
            
            i += 1
        
        accepting_state = None
        
        def add_action(state, lookahead, action, item):
            if lookahead in state.action and state.action[lookahead] != action:
                raise ActionConflictError('LR(%d) table conflict: actions %s, %s trying to add %s'
                    % (k, state.action[lookahead], action, item), state, states)
            state.action[lookahead] = action
        
        for state_id, state in enumerate(states):
            for item in state.itemset:
                nt = item.next_token()
                if nt == None:
                    if item.rule.left == '':
                        accepting_state = state_id
                        add_action(state, item.lookahead, None, item)
                    else:
                        add_action(state, item.lookahead, item.rule, item)
                elif aug_grammar.is_terminal(nt):
                    for la in item.lookaheads(first):
                        add_action(state, la, None, item)
        
        assert accepting_state != None
        
        self.accepting_state = accepting_state
        self.states = states
        self.k = k
        
        if not keep_states:
            for state in states:
                del state.itemset
                
    def imbue_matchers(self, matchers=default_matchers):
        if matchers == None:
            matchers = dict()
        
        for state in self.states:
            state.action_match = []
            for lookahead, action in state.action.iteritems():
                new_lookahead = tuple((matchers[symbol] if symbol in matchers else _SymbolMatcher(symbol)) for symbol in lookahead)
                state.action_match.append((new_lookahead, action))
            
            state.goto_match = []
            for symbol, next_state in state.goto.iteritems():
                if symbol in matchers:
                    state.goto_match.append((matchers[symbol], next_state))

    def parse(self, sentence, context=None, extract=extract_first,
            extract_value=lambda x: x, prereduce_visitor=None, postreduce_visitor=None):
        it = iter(sentence)
        buf = []
        while len(buf) < self.k:
            try:
                buf.append(it.next())
            except StopIteration:
                break
                    
        def get_shift_token():
            if len(buf) == 0:
                try:
                    return it.next()
                except StopIteration:
                    return None
            else:
                res = buf.pop(0)
                try:
                    buf.append(it.next())
                except StopIteration:
                    pass
                return res
        
        stack = [0]
        asts = []
        token_counter = 0
        while True:
            state_id = stack[-1]
            state = self.states[state_id]
            
            key = tuple(extract(token) for token in buf)
            action = state.get_action(key, token_counter)
            if action:   # reduce
                if len(action.right) > 0:
                    if prereduce_visitor:
                        prereduce_visitor(*asts[-len(action.right):])
                    new_ast = action.action(context, *asts[-len(action.right):])
                    if postreduce_visitor:
                        postreduce_visitor(action, new_ast)
                    del stack[-len(action.right):]
                    del asts[-len(action.right):]
                else:
                    if prereduce_visitor:
                        prereduce_visitor()
                    new_ast = action.action(context)
                    if postreduce_visitor:
                        postreduce_visitor(action, new_ast)
                
                stack.append(self.states[stack[-1]].get_next_state(action.left, token_counter))
                asts.append(new_ast)
            else:   # shift
                tok = get_shift_token()
                if tok == None:
                    if state_id == self.accepting_state:
                        assert len(asts) == 1
                        return asts[0]
                    else:
                        raise ParsingError('Reached the end of file prematurely.', token_counter)
                token_counter += 1
                
                key = extract(tok)
                stack.append(state.get_next_state(key, token_counter))
                asts.append(extract_value(tok))

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
        
    def __str__(self):
        right_syms = [repr(symbol) for symbol in self.rule.right]
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
        return ''.join((repr(self.rule.left), ' = ', ', '.join(right_syms), '; ', str(self.lookahead)))
        
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

        self.goto = {}
        self.action = {}

        self.action_match = []
        self.goto_match = []

    def __eq__(self, other):
        if not isinstance(other, State):
            return False
        return self.itemset == other.itemset
        
    def __hash__(self):
        return hash(self.itemset)
        
    def __repr__(self):
        return repr(self.itemset)
    
    def __str__(self):
        res = []
        for item in self.itemset:
            res.append(('#' if not item.is_kernel() else ' ') + str(item) + '\n')
        res.sort()
        return ''.join(res)

    def get_action(self, lookahead, counters):
        if lookahead in self.action:
            return self.action[lookahead]
    
        for match_list, action in self.action_match:
            if len(match_list) != len(lookahead):
                continue

            if all(match(symbol) for match, symbol in zip(match_list, lookahead)):
                return action
        
        raise ParsingError('Unexpected input token: %s' % repr(lookahead), counters)

    def get_next_state(self, symbol, counters):
        if symbol in self.goto:
            return self.goto[symbol]
            
        for match, next_state in self.goto_match:
            if match(symbol):
                return next_state
        
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

if __name__ == "__main__":
    import doctest
    doctest.testmod()
