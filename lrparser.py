from grammar import Grammar, Rule
from first import First

class InvalidGrammarError(BaseException):
    """Raised during a construction of a parser, if the grammar is not LR(k)."""
    def __init__(self, message, states=None):
        BaseException.__init__(self, message)
        self.states = states

class ParsingError(BaseException):
    """Raised by a parser if the input word is not a sentence of the grammar."""
    pass
    
def _any_matcher(ch):
    return True

default_matches = { 'any': _any_matcher, 'space': str.isspace, 'digit': str.isdigit, 'alnum': str.isalnum }

class Parser:
    """Represents a LR(k) parser.
    
    The parser is created with a grammar and a 'k'. The LR parsing tables
    are created during construction. If the grammar is not LR(k),
    an InvalidGrammarException is raised.
    
    >>> not_a_lr0_grammar = Grammar(Rule('list'), Rule('list', 'item', 'list'))
    >>> Parser(not_a_lr0_grammar, k=0) # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    InvalidGrammarError: LR(0) table conflict ...

    >>> lr0_grammar = Grammar(
    ...     Rule('list', action=lambda c: [] if c == None else [c]),
    ...     Rule('list', 'list', 'item', action=lambda c, l, i: l + [i]))
    >>> p = Parser(lr0_grammar, k=0)
    >>> print p.grammar
    list ::= <empty>
    list ::= list item
    
    The method 'parse' will accept an iterable of tokens (which are arbitrary objects)
    and an extraction function. The extraction function should return the terminal symbol
    associated with the token. By default, the extraction function return the object itself
    or the first first field if it is a tuple. Whenever the parser reduces a word to a non-terminal,
    an action associated with the reduction rule is executed. This way Abstract Syntax Trees
    or other objects can be constructed. The parse method returns the result of an action
    associated with the topmost reduction rule.
    
    Optionally, the 'parse' function will accept a 'context' keyword argument.
    This is passed to an action when reduction occurs. By default, context is None.
    
    >>> p.parse(())
    []
    >>> p.parse(('item', 'item', 'item', 'item'))
    ['item', 'item', 'item', 'item']
    >>> p.parse('spam', extract=lambda x: 'item')
    ['s', 'p', 'a', 'm']
    >>> p.parse('gg', extract=lambda x: 'item', context='e')
    ['e', 'g', 'g']
    
    If an error occurs during parsing, a ParsingError is raised.
    
    >>> p.parse('spam')
    Traceback (most recent call last):
        ...
    ParsingError: Unexpected input token: 's'
    """
    
    def __init__(self, grammar, k=1, keep_states=False, matches=default_matches):
        
        if grammar.root() == None:
            raise InvalidGrammarError('There must be at least one rule in the grammar.')
            
        self.grammar = Grammar(*grammar)
        self.k = k
        
        # Augment the grammar with a special rule: 'S -> R',
        # where S is a new non-terminal (in this case '').
        aug_grammar = Grammar(Rule('', grammar.root()), *grammar)
            
        first = First(aug_grammar, k)
        
        def _close_itemset(itemset):
            i = 0
            while i < len(itemset):
                curitem = itemset[i]
                
                for next_lookahead in curitem.next_lookaheads(first):
                    for next_rule in aug_grammar.rules(curitem.next_token()):
                        newitem = _Item(next_rule, 0, next_lookahead)
                        if newitem not in itemset:
                            itemset.append(newitem)
                
                i += 1
            return _State(itemset)
                
        def _goto(state, symbol):
            res = [_Item(item.rule, item.index + 1, item.lookahead) for item in state.itemset if item.next_token() == symbol]
            return _close_itemset(res)
        
        itemset = [_Item(aug_grammar[0], 0, ())]
        states = [_close_itemset(itemset)]
        
        i = 0
        while i < len(states):
            state = states[i]
            
            for symbol in aug_grammar.symbols():
                newstate = _goto(state, symbol)
                if not newstate.itemset:
                    continue
                    
                for j, oldstate in enumerate(states):
                    if newstate.itemset == oldstate.itemset:
                        state.goto[symbol] = j
                        break
                else:
                    state.goto[symbol] = len(states)
                    states.append(newstate)
            
            i += 1
        
        accepting_state = None
        
        def add_action(state, lookahead, action, item):
            if lookahead in state.action and state.action[lookahead] != action:
                raise InvalidGrammarError('LR(%i) table conflict at %s: actions %s, %s trying to add %s'
                    % (k, lookahead, state.action[lookahead], action, item), states)
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
        
        # fixup matches
        for state in states:
            for lookahead, action in state.action.iteritems():
                new_lookahead = tuple((matches[symbol] if symbol in matches else _SymbolMatcher(symbol)) for symbol in lookahead)
                state.action_match.append((new_lookahead, action))
            del state.action
            
            new_goto = {}
            for symbol, next_state in state.goto.iteritems():
                if symbol in matches:
                    state.goto_match.append((matches[symbol], next_state))
                else:
                    new_goto[symbol] = next_state
            state.goto = new_goto
        
        assert accepting_state != None
        self.accepting_state = accepting_state
        self.states = states
        self.k = k
        
        if not keep_states:
            for state in states:
                del state.itemset

    def parse(self, sentence, context=None, extract=lambda arg: arg[0] if type(arg) == tuple else arg, prereduce_visitor=None, postreduce_visitor=None):
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
        while True:
            state_id = stack[-1]
            state = self.states[state_id]
            
            key = tuple(extract(token) for token in buf)
            action = state.get_action(key)
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
                
                stack.append(self.states[stack[-1]].get_next_state(action.left))
                asts.append(new_ast)
            else:   # shift
                tok = get_shift_token()
                if tok == None:
                    if state_id == self.accepting_state:
                        assert len(asts) == 1
                        return asts[0]
                    else:
                        raise ParsingError('Reached the end of file prematurely.')
                
                key = extract(tok)
                stack.append(state.get_next_state(key))
                asts.append(tok)

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
        out = [self.rule.left, '::=']
        out.extend(self.rule.right)
        out.insert(self.index + 2, '.')
        return ' '.join(out) + ' ' + str(self.lookahead)
    
    def __repr__(self):
        return ''.join(("'", self.__str__(), "'"))
    
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
        return '<SM %s>' % self.symbol

class _State:
    """Represents a single state of a LR(k) parser.
    
    There are two tables of interest. The 'goto' table is a dict mapping
    symbols to state identifiers.
    
    The 'action' table maps lookahead strings to actions. An action
    is either 'None', corresponding to a shift, or a Rule object,
    corresponding to a reduce.
    """
    
    def __init__(self, itemset):
        self.itemset = set(itemset)
        self.goto = {}
        self.action = {}
        
        self.action_match = []
        self.goto_match = []

    def get_action(self, lookahead):
        for match_list, action in self.action_match:
            if len(match_list) != len(lookahead):
                continue

            if all(match(symbol) for match, symbol in zip(match_list, lookahead)):
                return action
        
        raise ParsingError('Unexpected input token: %s' % repr(lookahead))

    def get_next_state(self, symbol):
        if symbol in self.goto:
            return self.goto[symbol]
            
        for match, next_state in self.goto_match:
            if match(symbol):
                return next_state
        
        raise ParsingError('Unexpected input token: %s' % repr(symbol))
        

if __name__ == "__main__":
    import doctest
    doctest.testmod()
