"""
Finite automaton engine. Contains classes to represent FAs
and algorithms to convert between DFAs, NFAs and regexes.

>>> nature_fa = make_dfa_from_literal('nature')
>>> endnature_fa = make_dfa_from_literal('endnature')
>>> union = union_fa([nature_fa, endnature_fa])
>>> fa = minimize_enfa(union)
>>> len(fa.states)
10
"""

class State:
    """
    A state of a finite automaton. Contains references
    to the sets of incoming and outgoing edges.
    """
    def __init__(self, accept=None):
        self.outedges = set()
        self.accept = accept

    def connect_to(self, target, label=None):
        self.outedges.add((target, label))

class Automaton:
    """
    A finite automaton consists of a set of states and a set of edges
    that interconnect them.
    
    Edges can be labeled. The labels are in now way interpreted,
    some algorithms, however, expect that the labels can be combined
    using the standard set operators &, | and -. Furthermore,
    epsilon edges are supposed to be labeled with None.

    The FA can have zero or more initial states and zero or more accepting
    states. The accepting states are labeled -- as with edge labels,
    some algorithms expect accept labels to behave like sets. Accepting
    states are stored in a dict that maps them to the corresponding label.
    """
    def __init__(self, *initial):
        self.initial = frozenset(initial)

    def reachable_states(self):
        res = set(self.initial)
        q = list(self.initial)
        while q:
            state = q.pop()
            for target, label in state.outedges:
                if target not in res:
                    res.add(target)
                    q.append(target)
        return res

def _combine(lhs, rhs):
    if lhs is None:
        return rhs
    if rhs is None:
        return lhs
    return min(lhs, rhs)

def convert_enfa_to_dfa(enfa, accept_combine=_combine):
    """
    Converts an NFA with epsilon edges (labeled with None) to a DFA.
    The function expects edge labels that are not None to be sets
    and accepting state labels to be combinable using the accept_combine
    function passed as a parameter.
    """
    def _epsilon_closure(states):
        q = list(states)
        res = set(q)
        while q:
            state = q.pop()
            for target, label in state.outedges:
                if label is not None:
                    continue
                if target in res:
                    continue
                q.append(target)
                res.add(target)
        return res

    state_map = {}
    inv_state_map = {}

    def _get_state(states):
        states = frozenset(states)
        if states not in state_map:
            res = State()
            state_map[states] = res
            inv_state_map[res] = states
        else:
            res = state_map[states]
        return res

    initial = _get_state(_epsilon_closure(enfa.initial))
    dfa = Automaton(initial)
    q = [initial]
    processed = set(q)
    while q:
        current = q.pop()
        state_set = inv_state_map[current]
        edges = {}
        for state in state_set:
            for target, label in state.outedges:
                if label is not None:
                    if target not in edges:
                        edges[target] = label
                    else:
                        edges[target] &= label
        while edges:
            it = edges.iteritems()
            target, s = next(it)
            targets = set([target])
            current_set = s
            for target, next_set in it:
                s = current_set & next_set
                if s:
                    current_set = s
                    targets.add(target)
            dfa_target = _get_state(_epsilon_closure(targets))
            current.connect_to(dfa_target, current_set)
            if dfa_target not in processed:
                processed.add(dfa_target)
                q.append(dfa_target)

            for target in edges.keys():
                reduced = edges[target] - current_set
                if not reduced:
                    del edges[target]
                else:
                    edges[target] = reduced
    for state in dfa.reachable_states():
        enfa_states = inv_state_map[state]
        state.accept = reduce(accept_combine, (enfa_state.accept for enfa_state in enfa_states))
    return dfa

def minimize_enfa(fa, accept_combine=_combine):
    """
    Converts an NFA with epsilon edges to a minimal DFA. The requirements
    on the edge and accept labels are the same as with
    the convert_enfa_to_dfa function.
    """
    fa = convert_enfa_to_dfa(fa, accept_combine)

    # initialize the partition by splitting the state according to the accept label
    no_accept = set()
    accept_label_map = {}
    for state in fa.reachable_states():
        if state.accept is None:
            no_accept.add(state)
        else:
            accept_label_map.setdefault(state.accept, set()).add(state)

    partition = set([frozenset(no_accept)])
    for states in accept_label_map.itervalues():
        partition.add(frozenset(states))

    def _get_maximum_charsets(item_charset_map):
        item_charset_map = dict(item_charset_map)
        while item_charset_map:
            it = item_charset_map.iteritems()
            item, charset = it.next()
            items = set([item])
            current_charset = charset
            for item, charset in it:
                charset = current_charset & charset
                if charset:
                    current_charset = charset
                    items.add(item)

            yield items, current_charset

            for item in item_charset_map.keys():
                reduced = item_charset_map[item] - current_charset
                if not reduced:
                    del item_charset_map[item]
                else:
                    item_charset_map[item] = reduced

    def _create_partition_map(partition):
        partition_map = {}
        for state_class in partition:
            for state in state_class:
                partition_map[state] = state_class
        return partition_map

    # iterate and refine
    while True:
        partition_map = _create_partition_map(partition)

        new_partition = set()
        for state_class in partition:
            sibling_map = {}
            for state in state_class:
                sibling_map[state] = set(state_class)

            edge_map = {}
            for state in state_class:
                for target, label in state.outedges:
                    edge_map[(state, target)] = label

            for edges, charset in _get_maximum_charsets(edge_map):
                target_map = {}
                for source, target in edges:
                    target_map.setdefault(partition_map[target], set()).add(source)
                for part, source_set in target_map.iteritems():
                    for source, siblings in sibling_map.iteritems():
                        if source in source_set:
                            siblings &= source_set
                        else:
                            siblings -= source_set

            for sibling_set in sibling_map.itervalues():
                new_partition.add(frozenset(sibling_set))

        if partition == new_partition:
            break
        partition = new_partition

    # partition is refined
    partition_map = _create_partition_map(partition)

    new_state_map = {}
    for state_class in partition:
        new_state = State(accept=next(iter(state_class)).accept)
        new_state_map[state_class] = new_state

    for state_class, source in new_state_map.iteritems():
        target_labels = {}
        for state in state_class:
            for target, label in state.outedges:
                target_labels[target] = label

        target_map = {}
        for targets, charset in _get_maximum_charsets(target_labels):
            target = partition_map[next(iter(targets))]
            assert all((partition_map[tg] == target for tg in targets))
            if new_state_map[target] not in target_map:
                target_map[new_state_map[target]] = charset
            else:
                target_map[new_state_map[target]] |= charset

        for target, charset in target_map.iteritems():
            source.connect_to(target, charset)

    return Automaton(new_state_map[partition_map[next(iter(fa.initial))]])

def union_fa(fas):
    """
    Builds a FA that accepts a union of languages of the provided FAs.
    """
    final_init = State()
    final_fa = Automaton(final_init)
    for fa in fas:
        for init in fa.initial:
            final_init.connect_to(init)
    return final_fa

if __name__ == '__main__':
    import doctest
    doctest.testmod()
