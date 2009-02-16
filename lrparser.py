from grammar import Grammar, Rule
from first import First

# TODO: Fix 'shift' and 'reduce' tokens (a bool perhaps?).

class InvalidGrammarError(BaseException):
    """Raised during a construction of a parser, if the grammar is not LR(k)."""
    def __init__(self, message, states=None):
        BaseException.__init__(self, message)
        self.states = states

class ParsingError(BaseException):
    """Raised by a parser if the input word is not a sentence of the grammar."""
    pass
    
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
    
    def __init__(self, grammar, k=1, keep_states=False):
        
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
                
        def _goto(itemset, symbol):
            res = []
            for item in itemset:
                if item.next_token() != symbol:
                    continue
                    
                res.append(_Item(item.rule, item.index + 1, item.lookahead))
                
            _close_itemset(res)
            return set(res)
        
        itemset = [_Item(aug_grammar[0], 0, ())]
        _close_itemset(itemset)
        
        states = [set(itemset)]
        
        goto_table = {}
        
        done = False
        while not done:
            done = True
            
            i = 0
            while i < len(states):
                itemset = states[i]
                
                for symbol in aug_grammar.symbols():
                    newstate = _goto(itemset, symbol)
                    if len(newstate) == 0:
                        continue
                        
                    for j, state in enumerate(states):
                        if newstate == state:
                            goto_table[i, symbol] = j
                            break
                    else:
                        goto_table[i, symbol] = len(states)
                        states.append(newstate)
                        done = False
                
                i += 1
        
        action_table = {}
        accepting_state = None
        
        def add_action(state_id, lookahead, action, item):
            key = (state_id, lookahead)
            if key in action_table and action_table[key] != action:
                raise InvalidGrammarError('LR(%i) table conflict at %s: actions %s, %s trying to add %s' % (k, key, action_table[key], action, item), states)
            action_table[key] = action
        
        for state_id, state in enumerate(states):
            for item in state:
                nt = item.next_token()
                if nt == None:
                    if item.rule.left == '':
                        accepting_state = state_id
                        add_action(state_id, item.lookahead, ('shift',), item)
                    else:
                        add_action(state_id, item.lookahead, ('reduce', item.rule), item)
                elif aug_grammar.is_terminal(nt):
                    for la in item.lookaheads(first):
                        add_action(state_id, la, ('shift',), item)
        
        assert accepting_state != None
        self.goto = goto_table
        self.action = action_table
        self.accepting_state = accepting_state
        self.k = k
        
        if keep_states:
            self.states = states

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
        
        states = [0]
        asts = []
        while True:
            state = states[-1]
            
            key = (state, tuple(extract(token) for token in buf))
            if key not in self.action:
                raise ParsingError('Unexpected input token: %s' % repr(tuple(buf)))
            
            action = self.action[key]
            if action[0] == 'reduce':
                rule = action[1]
                
                if len(rule.right) > 0:
                    if prereduce_visitor:
                        prereduce_visitor(*asts[-len(rule.right):])
                    new_ast = rule.action(context, *asts[-len(rule.right):])
                    if postreduce_visitor:
                        postreduce_visitor(rule, new_ast)
                    del states[-len(rule.right):]
                    del asts[-len(rule.right):]
                else:
                    if prereduce_visitor:
                        prereduce_visitor()
                    new_ast = rule.action(context)
                    if postreduce_visitor:
                        postreduce_visitor(rule, new_ast)
                
                states.append(self.goto[states[-1], rule.left])
                asts.append(new_ast)
            else: # shift
                tok = get_shift_token()
                if tok == None:
                    if state == self.accepting_state:
                        assert len(asts) == 1
                        return asts[0]
                    else:
                        raise ParsingError('Reached the end of file prematurely.')
                
                key = (state, extract(tok))
                if key not in self.goto:
                    raise ParsingError('Unexpected input token: %s' % repr(key[1]))
                
                states.append(self.goto[key])
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

if __name__ == "__main__":
    import doctest
    doctest.testmod()
