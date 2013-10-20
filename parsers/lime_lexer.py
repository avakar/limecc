class LimeLexer:
    def __init__(self, dfa):
        self.set_dfa(dfa)

    def tokens(self, s):
        state = iter(self.dfa.initial).next()

        tok_start = 0
        for i, ch in enumerate(s):
            for e in state.outedges:
                if ch in e.label:
                    state = e.target
                    break
            else:
                yield s[tok_start:i], self.dfa.accept_labels.get(state)
                tok_start = i
                state = iter(self.dfa.initial).next()
                for e in state.outedges:
                    if ch in e.label:
                        state = e.target
                        break
                else:
                    raise RuntimeError('Invalid character encountered at position %d: %c' % (i, ch))

        yield s[tok_start:], self.dfa.accept_labels.get(state)

    def set_dfa(self, dfa):
        assert len(dfa.initial) == 1
        self.dfa = dfa
