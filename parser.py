from grammar import Grammar, Rule
from fifo import FirstTable

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

class InvalidGrammarError(BaseException):
	pass

class ParsingError(BaseException):
	pass
	
class Parser:
	def __init__(self, rules, k):
		if len(rules) == 0:
			raise InvalidGrammarError('There must be at least one rule in a grammar.')

		grammar = Grammar()

		# Augment the grammar with a special rule: 'S -> R',
		# where S is a new non-terminal (in this case '').
		grammar.add_rule('', rules[0].left)
		grammar.extend(rules)
			
		first = FirstTable(grammar, k)
		
		def _close_itemset(itemset):
			i = 0
			while i < len(itemset):
				curitem = itemset[i]
				
				for next_lookahead in curitem.next_lookaheads(first):
					for next_rule in grammar.rules(curitem.next_token()):
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
		
		itemset = [_Item(grammar[0], 0, ())]
		_close_itemset(itemset)

		states = [set(itemset)]
		
		goto_table = {}
		
		done = False
		while not done:
			done = True
			
			i = 0
			while i < len(states):
				itemset = states[i]
				
				for symbol in grammar.symbols():
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
				raise InvalidGrammarError('LR(%i) table conflict at %s: actions %s, %s trying to add %s' % (k, key, action_table[key], action, item))
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
				elif grammar.is_terminal(nt):
					for la in item.lookaheads(first):
						add_action(state_id, la, ('shift',), item)
		
		assert accepting_state != None
		self.goto = goto_table
		self.action = action_table
		self.accepting_state = accepting_state
		self.k = k

	def parse(self, sentence, extract=lambda x: x):
		it = iter(sentence)
		buf = []
		while len(buf) < self.k:
			try:
				buf.append(it.next())
			except StopIteration:
				return
					
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
				raise ParsingError()

			action = self.action[key]
			if action[0] == 'reduce':
				rule = action[1]
				del states[-len(rule.right):]
				states.append(self.goto[states[-1], rule.left])
				
				new_ast = rule.action(*asts[-len(rule.right):])
				del asts[-len(rule.right):]
				asts.append(new_ast)
				
			else: # shift
				tok = get_shift_token()
				if tok == None:
					if state == self.accepting_state:
						assert len(asts) == 1
						return asts[0]
					else:
						raise ParsingError('Reached the end of file prematurely.')

				states.append(self.goto[state, extract(tok)])
				asts.append(tok)
	
if __name__ == '__main__':
	parser = Parser([
		Rule('E', ('E', '*', 'B'), lambda x, _, y: x * y),
		Rule('E', ('E', '+', 'B'), lambda x, _, y: x + y),
		Rule('E', 'B'),
		Rule('B', '0', int),
		Rule('B', '1', int)
	], k=0)

	import sys
	line = sys.stdin.readline()
	print parser.parse(line.strip())
