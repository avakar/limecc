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
    def __init__(self):
        self.outedges = set()

class Edge:
    """
    An edge of a finite automaton. Leads between two FA states.
    Optionally, the edge can be labeled.
    """
    def __init__(self, f, t, label=None):
        self.source = f
        self.target = t
        self.label = label

class Fa:
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
    def __init__(self):
        """
        Initialized the FA to contain no states (and thus no edges).
        """
        self.states = []
        self.edges = set()
        self.initial = set()
        self.accept_labels = {}

    def __str__(self):
        res = []
        state_indexes = dict([(state, i) for i, state in enumerate(self.states)])
        for i, state in enumerate(self.states):
            accept_label = self.accept_labels.get(state)
            res.append('%s%d' % ('%r ' % accept_label if accept_label is not None else ' ', i))
            if state in self.initial:
                res.append('initial')
            for edge in state.outedges:
                res.append('    %d %r' % (
                    state_indexes[edge.target],
                    edge.label if edge.label is not None else 'epsilon'))
        return '\n'.join(res)

    def add_fa(self, fa):
        """
        Adds the states and edges of another FA to this FA. The remote
        FA should be thrown away right after the joining.
        """
        self.states.extend(fa.states)
        self.edges.update(fa.edges)
        self.accept_labels.update(fa.accept_labels)

    def new_edge(self, s1, s2, label=None):
        """
        Joins two states with a new edge and applies an optional label
        to it. Returns the new edge.
        """
        edge = Edge(s1, s2, label)
        s1.outedges.add(edge)
        self.edges.add(edge)
        return edge

    def new_state(self):
        """
        Creates a new state. If a template state is provided,
        the new state is a duplicate of the template.
        Returns the new state.
        """
        new_state = State()
        self.states.append(new_state)
        return new_state

    def remove_edge(self, edge):
        """
        Removes an edge from the FA.
        """
        self.edges.remove(edge)
        edge.source.outedges.remove(edge)

def convert_enfa_to_dfa(enfa, accept_combine=min):
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
            for edge in state.outedges:
                if edge.label is not None:
                    continue
                if edge.target in res:
                    continue
                q.append(edge.target)
                res.add(edge.target)
        return res

    dfa = Fa()
    state_map = {}
    inv_state_map = {}

    def _get_state(states):
        states = frozenset(states)
        if states not in state_map:
            res = dfa.new_state()
            state_map[states] = res
            inv_state_map[res] = states
        else:
            res = state_map[states]
        return res

    initial = _get_state(_epsilon_closure(enfa.initial))
    q = [initial]
    dfa.initial = set(q)
    processed = set(q)
    while q:
        current = q.pop()
        state_set = inv_state_map[current]
        edges = {}
        for state in state_set:
            for edge in state.outedges:
                if edge.label is not None:
                    if edge.target not in edges:
                        edges[edge.target] = edge.label
                    else:
                        edges[edge.target] &= edge.label
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
            dfa.new_edge(current, dfa_target, current_set)
            if dfa_target not in processed:
                processed.add(dfa_target)
                q.append(dfa_target)

            for target in edges.keys():
                reduced = edges[target] - current_set
                if not reduced:
                    del edges[target]
                else:
                    edges[target] = reduced
    for state in dfa.states:
        enfa_states = inv_state_map[state]
        for enfa_state in enfa_states:
            if enfa_state not in enfa.accept_labels:
                continue
            enfa_label = enfa.accept_labels[enfa_state]
            if state not in dfa.accept_labels:
                dfa.accept_labels[state] = enfa_label
            else:
                dfa.accept_labels[state] = accept_combine(dfa.accept_labels[state], enfa_label)
    return dfa

def minimize_enfa(fa, accept_combine=min):
    """
    Converts an NFA with epsilon edges to a minimal DFA. The requirements
    on the edge and accept labels are the same as with
    the convert_enfa_to_dfa function.
    """
    fa = convert_enfa_to_dfa(fa, accept_combine)

    # initialize the partition by splitting the state according to the accept label
    no_accept = set()
    accept_label_map = {}
    for state in fa.states:
        if state not in fa.accept_labels:
            no_accept.add(state)
        else:
            acc_label = fa.accept_labels[state]
            accept_label_map.setdefault(acc_label, set()).add(state)

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
                for edge in state.outedges:
                    edge_map[edge] = edge.label

            for edges, charset in _get_maximum_charsets(edge_map):
                target_map = {}
                for edge in edges:
                    target_map.setdefault(partition_map[edge.target], set()).add(edge.source)
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

    new_fa = Fa()

    new_state_map = {}
    for state_class in partition:
        new_state = new_fa.new_state()
        new_state_map[state_class] = new_state

    for state_class, source in new_state_map.iteritems():
        edge_map = {}
        for state in state_class:
            for edge in state.outedges:
                edge_map[edge] = edge.label

        target_map = {}
        for edges, charset in _get_maximum_charsets(edge_map):
            target = partition_map[next(iter(edges)).target]
            assert all((partition_map[edge.target] == target for edge in edges))
            if new_state_map[target] not in target_map:
                target_map[new_state_map[target]] = charset
            else:
                target_map[new_state_map[target]] |= charset

        for target, charset in target_map.iteritems():
            new_fa.new_edge(source, target, charset)

    new_fa.initial = set([new_state_map[partition_map[next(iter(fa.initial))]]])
    for state, accept_label in fa.accept_labels.iteritems():
        new_fa.accept_labels[new_state_map[partition_map[state]]] = accept_label
    return new_fa

def union_fa(fas):
    """
    Builds a FA that accepts a union of languages of the provided FAs.
    """
    final_fa = Fa()
    final_init = final_fa.new_state()
    final_fa.initial = set([final_init])
    for fa in fas:
        final_fa.add_fa(fa)
        for init in fa.initial:
            final_fa.new_edge(final_init, init)
    return final_fa

if __name__ == '__main__':
    import doctest
    doctest.testmod()
