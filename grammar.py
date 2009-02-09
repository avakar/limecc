def _default_action(*args):
	if len(args) == 1:
		return args[0]
	else:
		return tuple(args)

class Rule:
	def __init__(self, left, right, action=_default_action):
		if type(right) != tuple:
			right = (right,)
		self.left = left
		self.right = right
		self.action = action
		
	def __str__(self):
		out = [self.left, '::=']
		out.extend(self.right)
		return ' '.join(out)
	
	def __repr__(self):
		return ''.join(("'", self.__str__(), "'"))

# TODO: caching
class Grammar:
	def __init__(self, *rules):
		self._rules = []
		self._nonterms = set()
		self._symbols = set()
		
		for rule in rules:
			self.add_rule(*rule)
		
	def __getitem__(self, key):
		return self._rules[key]
		
	def __len__(self):
		return len(self._rules)
		
	def __iter__(self):
		return iter(self._rules)
		
	def __str__(self):
		return '\n'.join(str(rule) for rule in self._rules)
		
	def add(self, rule):
		self._rules.append(rule)
		self._nonterms.add(rule.left)
		self._symbols.add(rule.left)
		for symbol in rule.right:
			self._symbols.add(symbol)
	
	def add_rule(self, left, *right):
		self.add(Rule(left, right))
		
	def extend(self, rules):
		for rule in rules:
			self.add(rule)

	def rules(self, left):
		for rule in self._rules:
			if rule.left == left:
				yield rule
				
	def is_terminal(self, token):
		return token not in self._nonterms

	def nonterms(self):
		return self._nonterms
		
	def symbols(self):
		return self._symbols
		
if __name__ == '__main__':
	g = Grammar(
		('E', 'E', '*', 'B'),
		('E', 'E', '+', 'B'),
		('E', 'B'),
		('B', '0'),
		('B', '1')
	)
	
	print g
	print
	print 'Non-terminals:', g.nonterms()
	print 'Terminals:', g.symbols()
