from grammar import Grammar

def join(left_wordset, right_wordset, k):
	res = set()
	min_len = k
	for lword in left_wordset:
		for rword in right_wordset:
			w = list(lword)
			w.extend(rword)
			w = w[:k]
			if len(w) < min_len:
				min_len = len(w)
			res.add(tuple(w))
	return res, min_len
	
class FirstTable:
	def __init__(self, grammar, k):
		self.table = {}
		self.k = k

		for nonterm in grammar.nonterms():
			self.table[nonterm] = set()

		done = False
		while not done:
			done = True

			for rule in grammar:
				fi = self(rule.right)
			
				for word in fi:
					if word not in self.table[rule.left]:
						self.table[rule.left].add(word)
						done = False
		
	def _first1(self, token):
		if token not in self.table:
			return set([(token,)])
		return self.table[token]

	def __call__(self, word):
		res = set([()])
		for token in word:
			res, c = join(res, self._first1(token), self.k)
			if c == self.k:
				break

		return res

if __name__ == '__main__':
	g = Grammar(
		('E', 'E', '*', 'B'),
		('E', 'E', '+', 'B'),
		('E', 'B'),
		('B', '0'),
		('B', '1')
	)

	print g

	ft = FirstTable(g, 2)
	print ft.table

	print ft(('E', '*'))
