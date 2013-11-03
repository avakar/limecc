"""
This module provides means to represent finite automata
and a set of routines to manipulate them.

States
------
A state of an automaton is represented by objects of type
`State`. States contain a set of edges connecting the state
to another (possibly the original). States are also
labeled by an accept label, which defaults to False.

    >>> s = State(accept=True)
    >>> print s
    <State, 0 outgoing, 1 reachable, accept=True>

    >>> s = State()
    >>> print s
    <State, 0 outgoing, 1 reachable>
    >>> s.reachable_states()
    [<State, 0 outgoing, 1 reachable>]
    >>> list(s.outedges)
    []

Edges can be labeled by arbitrary objects, which should
represent the set of input terminals for which the edge
is enabled. Various routines that manipulate automata
(e.g. `union_fa`, `minimize_fa` and so on) require that
the labels

 1. are `None` for epsilon edges, and
 2. all other edges are labeled by objects that support
    operators `&` that computes intersection, `|`
    that computes union, `-` that computes difference,
    can be coverted to bool and support `in` and `not in`
    operators.

States can be interconnected using the `connect_to` method.

    >>> s2 = State(accept=True)
    >>> s.connect_to(s2, label=set('abc'))
    >>> sorted(s.reachable_states())
    [<State, 1 outgoing, 2 reachable>, <State, 0 outgoing, 1 reachable, accept=True>]

You can visualize a graph starting at a specific state by
calling `format_graph` or `print_graph` method.

    >>> print s.format_graph()
    state 0
        edge to 1 over set(['a', 'c', 'b'])
    state 1
        accept True

Printing state graphs can also be more generically peformed
using the `format_reachable_states` functions.

    >>> print format_reachable_states([s], mark_initial=True)
    state 0 initial
        edge to 1 over set(['a', 'c', 'b'])
    state 1
        accept True

Multiple initial states can be specified.

    >>> print format_reachable_states([s, s2], mark_initial=True)
    state 0 initial
        edge to 1 over set(['a', 'c', 'b'])
    state 1 initial
        accept True

Automata
--------
Automata are simple objects of type `Automaton`, which merely
hold a set of initial states. Automata can share states.

    >>> a = Automaton(s)
    >>> print a
    <Automaton, 1 initial, 2 reachable>
    >>> print a.format_graph()
    state 0 initial
        edge to 1 over set(['a', 'c', 'b'])
    state 1
        accept True

You can always get the list of states of an automaton using
the `reachable_states` method.

    >>> print sorted(a.reachable_states())
    [<State, 1 outgoing, 2 reachable>, <State, 0 outgoing, 1 reachable, accept=True>]

An automaton is in a DFA form if

 1. it has exactly one initial state,
 2. there are no reachable epsilong edges, and
 3. for each state and each pair of that state's outgoing edges,
    the intersection of the edges' labels is empty, i.e. for edges
    `l1` and `l2`, the expression `bool(l1 & l2)` yields `False`.

You can convert an arbitrary automaton to DFA form with
`convert_enfa_to_dfa`. Minimizing an automaton with `minimize_enfa`
will also yield an automaton in a DFA form. Both routines
yield automata that do not share states with the input automata.

    >>> s3 = State(accept=True)
    >>> s2.connect_to(s3, set('abc'))
    >>> s2.connect_to(s2, set('abc'))
    >>> print a.format_graph()
    state 0 initial
        edge to 1 over set(['a', 'c', 'b'])
    state 1
        edge to 2 over set(['a', 'c', 'b'])
        edge to 1 over set(['a', 'c', 'b'])
        accept True
    state 2
        accept True
    >>> a = minimize_enfa(a)
    >>> print a.format_graph()
    state 0 initial
        edge to 1 over set(['a', 'c', 'b'])
    state 1
        edge to 1 over set(['a', 'c', 'b'])
        accept True
"""

import sys

def _reachable_states(initial_set):
    q = list(initial_set)
    res = set(q)
    while q:
        state = q.pop()
        for target, label in state.outedges:
            if target not in res:
                res.add(target)
                q.append(target)
    return list(res)

def _bfs_walk(initial_set):
    visited = set(initial_set)
    q = list(initial_set)
    while q:
        state = q.pop(0)
        yield state
        for target, label in state.outedges:
            if target not in visited:
                visited.add(target)
                q.append(target)

def format_reachable_states(initial_set, mark_initial=False):
    state_list = list(enumerate(_bfs_walk(initial_set)))
    state_map = {}
    for i, state in state_list:
        state_map[state] = i
    res = []
    for i, state in state_list:
        res.append('state %d' % i)
        res.append(' initial\n' if mark_initial and state in initial_set else '\n')
        for target, label in state.outedges:
            if label is None:
                res.append('    edge to %d\n' % (state_map[target],))
            else:
                res.append('    edge to %d over %s\n' % (state_map[target], str(label)))
        if state.accept is not None:
            res.append('    accept %s\n' % str(state.accept))
    return ''.join(res).rstrip()

class State:
    """
    A state of a finite automaton. Contains references
    to the sets of incoming and outgoing edges.
    """
    def __init__(self, accept=None):
        self.outedges = []
        self.accept = accept

    def __repr__(self):
        if self.accept is not None:
            return '<State, %d outgoing, %d reachable, accept=%r>' % (len(self.outedges), len(self.reachable_states()), self.accept)
        else:
            return '<State, %d outgoing, %d reachable>' % (len(self.outedges), len(self.reachable_states()))

    def connect_to(self, target, label=None):
        self.outedges.append((target, label))

    def format_graph(self):
        return format_reachable_states([self])

    def print_graph(self, file=sys.stderr):
        print >>file, self.format_graph()

    def reachable_states(self):
        return _reachable_states([self])

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

    def __repr__(self):
        return '<Automaton, %d initial, %d reachable>' % (len(self.initial), len(_reachable_states(self.initial)))

    def format_graph(self):
        return format_reachable_states(self.initial, mark_initial=True)

    def print_graph(self, file=sys.stdout):
        print >>file, self.format_graph()

    def reachable_states(self):
        return _reachable_states(self.initial)

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

    def precombine(lhs, rhs):
        if lhs is None:
            return rhs
        if rhs is None:
            return lhs
        if lhs == rhs:
            return lhs
        return accept_combine(lhs, rhs)

    for state in dfa.reachable_states():
        state.accept = reduce(precombine, (enfa_state.accept for enfa_state in inv_state_map[state]))
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
    initial = set()
    for fa in fas:
        initial.update(fa.initial)
    return Automaton(*initial)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
