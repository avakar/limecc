from lime_grammar import LexDiscard, LexRegex
from dfa import make_dfa_from_literal

def _make_lexer(g, dfa):
    labels = []
    edges = []
    states = []

    lstates = []
    state_map = {}
    for i, state in enumerate(dfa.states):
        state_map[state] = i
        lstates.append(state)
    init_idx = state_map[next(iter(dfa.initial))]
    if init_idx != 0:
        lstates[0], lstates[init_idx] = lstates[init_idx], lstates[0]
        state_map[lstates[0]] = 0
        state_map[lstates[init_idx]] = init_idx

    for state in lstates:
        edge_first = len(edges)
        for edge in state.outedges:
            label_first = len(labels)
            seq_start = seq_end = None

            for ch in sorted(edge.label):
                if seq_start is None:
                    seq_start = seq_end = ch
                    continue
                if ord(seq_end) + 1 != ord(ch):
                    labels.append((seq_start, seq_end))
                    seq_start = seq_end = ch
                else:
                    seq_end = ch
            if seq_start is not None:
                labels.append((seq_start, seq_end))

            edges.append((label_first, len(labels), state_map[edge.target]))
        if state in dfa.accept_labels:
            accept_label = '&stub_%d' % dfa.accept_labels[state]
        else:
            accept_label = '0'
        states.append((edge_first, len(edges), accept_label))

    action_stubs = []
    action_functions = []
    for i, lex_rule in enumerate(g.lex_rules):
        (lhs, lhs_name), (rhs, rhs_name), action = lex_rule
        if (rhs_name is None) != (action is None):
            raise RuntimeError('XXX')
        
        action_stub = ['static void stub_%s(basic_lexer & l, TokenSink & token_sink)' % i, '{']
        if not isinstance(g.sym_annot.get(lhs), LexDiscard):
            if lhs not in g.sym_annot:
                action_stub.append('    token_sink.push_token(tok::%s);' % lhs.lower())
            else:
                action_stub.append('    %s res;' % g.sym_annot[lhs])
                params = []
                if lhs_name is not None:
                    params.append('res')
                if rhs_name is not None:
                    params.append('l.m_token')
                params = ', '.join(params)
                if lhs_name is not None:
                    action_stub.append('    l.m_actions.action_%d(%s);' % (i, params))
                else:
                    action_stub.append('    res = l.m_actions.action_%d(%s);' % (i, params))
                action_stub.append('    token_sink.push_token(tok::%s, res);' % lhs.lower())
        action_stub.append('}')
        action_stubs.append('\n    '.join(action_stub))

        if action is not None:
            params = []
            if lhs_name is not None:
                params.append('%s & %s' % (sym_annot[lhs], lhs_name))
                ret_type = 'void'
            else:
                ret_type = g.sym_annot[lhs]
            if rhs_name is not None:
                params.append('std::string & %s' % rhs_name)
            action_function = [
                '%s action_%d(%s)' % (ret_type, i, ', '.join(params)),
                '{',
                action,
                '}'
                ]
            action_functions.append('\n        '.join(action_function))

    sd = {}
    sd['labels'] = '\n            '.join(('{ %d, %d },' % (ord(first), ord(last)) for first, last in labels ))
    sd['edges'] = '\n            '.join(('{ %d, %d, %d },' % edge for edge in edges ))
    sd['states'] = '\n            '.join(('{ %d, %d, %s },' % state for state in states ))
    sd['action_stubs'] = '\n    '.join(action_stubs)
    sd['action_functions'] = '\n    '.join(action_functions)
    return lex_templ.substitute(sd)

lex_templ = """\
template <typename TokenSink>
class basic_lexer
{
public:
    basic_lexer()
        : m_state(0)
    {
    }

    void push_data(char const * first, char const * last, TokenSink & token_sink)
    {
        static label_t const labels[] = {
            $labels
        };

        static edge_t const edges[] = {
            $edges
        };

        for (; first != last; ++first)
        {
            bool target_state_found = false;
            while (!target_state_found)
            {
                state_t const & state = this->get_state();
                for (std::size_t edge_idx = state.edge_first;
                    !target_state_found && edge_idx != state.edge_last;
                    ++edge_idx)
                {
                    edge_t const & edge = edges[edge_idx];

                    bool success = false;
                    for (std::size_t i = edge.label_first; !success && i != edge.label_last; ++i)
                    {
                        if (labels[i].range_first <= *first && *first <= labels[i].range_last)
                            success = true;
                    }

                    if (success)
                    {
                        m_state = edge.target;
                        target_state_found = true;
                    }
                }

                if (!target_state_found)
                {
                    if (m_state == 0)
                    {
                        target_state_found = true;
                    }
                    else
                    {
                        this->dispatch_actions(token_sink);
                        m_token.clear();
                        m_state = 0;
                    }
                }
                else
                {
                    m_token.append(1, *first);
                }
            }
        }
    }

    void finish(TokenSink & token_sink)
    {
        this->dispatch_actions(token_sink);
    }

private:
    struct label_t
    {
        char range_first;
        char range_last;
    };

    struct edge_t
    {
        std::size_t label_first;
        std::size_t label_last;
        std::size_t target;
    };

    typedef void (*action_t)(basic_lexer &, TokenSink &);

    struct state_t
    {
        std::size_t edge_first;
        std::size_t edge_last;
        action_t accept;
    };

    state_t const & get_state() const
    {
        static state_t const states[] = {
            $states
        };

        return states[m_state];
    }

    void dispatch_actions(TokenSink & token_sink)
    {
        state_t const & state = this->get_state();
        if (state.accept != 0)
            state.accept(*this, token_sink);
    }

    $action_stubs

    struct actions_t
    {
        $action_functions
    };

    actions_t m_actions;
    std::size_t m_state;
    std::string m_token;
};
"""

def lime_cpp(p):
    g = p.grammar
    dfa = p.lexer
    lower_terminals = True

    sym_annot = dict(g.sym_annot.iteritems())
    for sym in g.symbols():
        if sym not in sym_annot:
            if g.is_terminal(sym) and g.token_type is not None:
                sym_annot[sym] = g.token_type.strip()
            else:
                sym_annot[sym] = None
        else:
            if sym_annot[sym] is not None:
                sym_annot[sym] = sym_annot[sym].strip()

    syms_by_type = {}
    for sym, annot in sym_annot.iteritems():
        syms_by_type.setdefault(annot, []).append(sym)

    annot_indexes = dict([(annot, i) for i, annot in enumerate(syms_by_type.iterkeys())])
    nonterm_indexes = dict([(nonterm, i) for i, nonterm in enumerate(g.nonterms())])
    term_indexes = dict([(term, i) for i, term in enumerate(g.terminals())])

    ast_stacks = ['std::vector<%s> m_ast_stack_%d;' % (annot, i)
        for annot, i in annot_indexes.iteritems() if annot is not None and not isinstance(annot, LexDiscard)]

    if lower_terminals:
        tokens = [term.lower() for term in g.terminals()]
    else:
        tokens = sorted(g.terminals())

    root_type = sym_annot.get(g.root())

    rule_count = len(g)
    state_count = len(p.states)

    rule_indexes = {}
    reduce_functions = []
    lime_actions = []
    for i, rule in enumerate(g):
        rule_indexes[rule] = i

        f = ["static int r%d(self_type & self)" % i, '{']
        f.append('    // %s' % str(rule))

        idx_counts = {}
        for right in rule.right:
            if sym_annot[right] is None:
                continue
            idx = annot_indexes[sym_annot[right]]
            idx_counts.setdefault(idx, 0)
            idx_counts[idx] += 1

        if (not rule.lime_action
                and (len(idx_counts) != 1 or idx_counts.values()[0] != 1
                or idx_counts.keys()[0] != annot_indexes[sym_annot[rule.left]])):
            raise RuntimeError('XXX') # This should probably be done before the generation begins

        if rule.lime_action:
            if sym_annot[rule.left] is not None:
                f.append('    %s res[1] = {};' % sym_annot[rule.left])
            f.append('    self.m_actions.a%d(' % i)
            params = []
            if rule.lhs_name and sym_annot[rule.left] is not None:
                params.append('        res[0]')
            used_indexes = {}
            for right, rhs_name in zip(rule.right, rule.rhs_names):
                idx = annot_indexes[sym_annot[right]]
                used_indexes.setdefault(idx, 0)
                # XXX: do this beforehand
                if rhs_name and sym_annot[right] is None:
                    raise RuntimeError('XXX')
                if rhs_name:
                    params.append(
                        '            self.m_ast_stack_%d.end()[-%d]' % (
                        idx, idx_counts[idx] - used_indexes[idx]))
                used_indexes[idx] += 1
            f.append(',\n'.join(params))
            f.append('    );')

        if rule.lime_action:
            for idx, count in idx_counts.iteritems():
                f.append('    self.m_ast_stack_%d.erase(self.m_ast_stack_%d.end() - %d, self.m_ast_stack_%d.end());'
                    % (idx, idx, count, idx))
            f.append('    self.m_ast_stack_%d.push_back(res[0]);' % annot_indexes[sym_annot[rule.left]])
        if rule.right:
            f.append('    self.m_state_stack.erase(self.m_state_stack.end() - %d, self.m_state_stack.end());'
                % len(rule.right))
        f.append('    return %d;' % nonterm_indexes[rule.left])
        f.append('}')
        reduce_functions.append('\n    '.join(f))

        param_list = []
        def _add_param(sym, name):
            if name:
                param_list.append('%s & %s' % (sym_annot[sym], name) )
        _add_param(rule.left, rule.lhs_name)
        for sym, sym_name in zip(rule.right, rule.rhs_names):
            _add_param(sym, sym_name)

        if rule.lime_action:
            lime_actions.append("void a%d(%s)\n{%s}\n" % (i, ', '.join(param_list), rule.lime_action))
        else:
            lime_actions.append("void a%d(%s)\n{}\n" % (i, ', '.join(param_list)))

    def _get_action_row(lookahead):
        action_row = []
        for i, state in enumerate(p.states):
            r = state.action.get(lookahead)
            if r:
                action_row.append(rule_indexes[r])
            else:
                action_row.append(None)
        return action_row

    action_table = []
    action_table.append(_get_action_row(()))
    for term in g.terminals():
        action_table.append(_get_action_row((term,)))

    nonterm_goto_table = [None] * len(nonterm_indexes)
    for nonterm in g.nonterms():
        row = [state.goto.get(nonterm, 0) for state in p.states]
        nonterm_goto_table[nonterm_indexes[nonterm]] = row

    term_goto_table = [None] * len(term_indexes)
    for term in g.terminals():
        row = [state.goto.get(term, 0) for state in p.states]
        term_goto_table[term_indexes[term]] = row

    terms_by_type = {}
    for term in g.terminals():
        terms_by_type.setdefault(sym_annot[term], []).append(term)

    push_token_lines = []
    for type, terms in terms_by_type.iteritems():
        if type is None:
            push_token_lines.extend([
                "void push_token(tok::token_kind kind)",
                "{",
                "    this->do_reduce(kind);",
                "    this->do_shift(kind);",
                "}"])
        else:
            push_token_lines.extend([
                "void push_token(tok::token_kind kind, %s const & value)" % type,
                "{",
                "    this->do_reduce(kind);",
                "    this->do_shift(kind);",
                "    m_ast_stack_%d.push_back(value);" % annot_indexes[type],
                "}"])

    if root_type is not None:
        root_stack = 'm_ast_stack_%d' % annot_indexes[root_type]
        finish_function = '''\
    root_type & finish()
    {
        this->do_reduce(tok::eof);
        if (m_state_stack.size() == 2 && %s.size() == 1)
            return %s[0];
        else
            throw std::runtime_error("TODO");
    }
''' % (root_stack, root_stack)
    else:
        finish_function = '''\
    void finish()
    {
        this->do_reduce(tok::eof);
    }
'''

    sd = {}

    if g.lex_rules:
        sd['lexer'] = _make_lexer(g, dfa)
        sd['lexer_typedef'] = 'typedef basic_lexer<parser> lexer;'
    else:
        sd['lexer'] = ''
        sd['lexer_typedef'] = ''

    sd['user_include'] = ''
    sd['root_type'] = root_type
    sd['finish_function'] = finish_function
    sd['ast_stacks'] = '\n    '.join(ast_stacks)
    sd['tokens'] = ',\n    '.join(tokens)
    sd['reduce_functions'] = '\n    '.join(reduce_functions)
    sd['lime_actions'] = '\n'.join(lime_actions)
    sd['term_count'] = str(len(g.terminals())+1)
    sd['term_count_m1'] = str(len(g.terminals()))
    sd['nonterm_count'] = str(len(g.nonterms()))
    sd['state_count'] = str(len(p.states))
    sd['action_table'] = ' },\n            { '.join(
        [', '.join([('0' if item is None else ('&r%d' % item)) for item in row]) for row in action_table])
    sd['nonterm_goto_table'] = ' },\n            { '.join(
        [', '.join([('%d' % item) for item in row]) for row in nonterm_goto_table])
    sd['term_goto_table'] = ' },\n            { '.join(
        [', '.join([('%d' % item) for item in row]) for row in term_goto_table])
    sd['push_token_functions'] = '\n    '.join(push_token_lines)
    return templ.substitute(sd)

templ = """\
#ifndef PARSER
#define PARSER

$user_include#include <cassert>
#include <vector>
#include <stdexcept> // XXX

namespace tok {

enum token_kind {
    eof,
    $tokens
};

}

$lexer

class parser
{
public:
    typedef int state_t;
    typedef $root_type root_type;

    parser()
    {
        m_state_stack.push_back(0);
    }

    $push_token_functions

$finish_function

private:
    typedef parser self_type;

    void do_shift(tok::token_kind kind)
    {
        static state_t const goto_table[$term_count_m1][$state_count] = {
            { $term_goto_table },
        };
        m_state_stack.push_back(goto_table[kind-1][m_state_stack.back()]);
    }

    void do_reduce(tok::token_kind lookahead)
    {
        typedef int (*reduce_fn)(self_type &);
        static reduce_fn const action_table[$term_count][$state_count] = {
            { $action_table },
        };

        static state_t const goto_table[$nonterm_count][$state_count] = {
            { $nonterm_goto_table },
        };

        for (;;)
        {
            state_t state = m_state_stack.back();
            reduce_fn fn = action_table[lookahead][state];
            if (!fn)
                break;
            int nonterm = fn(*this);
            state = m_state_stack.back();
            m_state_stack.push_back(goto_table[nonterm][state]);
        }
    }

    $reduce_functions

    struct actions
    {
        $lime_actions
    };

    std::vector<state_t> m_state_stack;
    $ast_stacks
    actions m_actions;
};

$lexer_typedef

#endif // PARSER
"""

from string import Template
templ = Template(templ)
lex_templ = Template(lex_templ)

if __name__ == "__main__":
    test = """
WS :: discard
WS ~= {\s+}
NUM :: {double}
NUM ~= {[0-9]+}(x) { return atoi(x.c_str()); }

expr :: {double}
expr ::= mul.
expr(E) ::= expr(E1) "+" mul(E2). { E = E1 + E2; }
expr(E) ::= expr(E1) "-" mul(E2). { E = E1 - E2; }

mul :: {double}
mul ::= term.
mul(E) ::= mul(E1) "*" term(E2). { E = E1 * E2; }
mul(E) ::= mul(E1) "/" term(E2). { E = E1 / E2; }

term :: {double}
term ::= atom.
term(A) ::= "+" atom(E).
term(A) ::= "-" atom(E). { A = -E; }

atom :: {double}
atom(A) ::= NUM(B).
atom(A) ::= "(" expr(E) ")".
"""

    from lime_grammar import parse_lime_grammar
    g = parse_lime_grammar(test)

#    from lrparser import Parser
#    p = Parser(g, keep_states=True)

#    from regex_parser import make_multi_dfa, minimize_enfa, regex_parser, make_enfa_from_regex

#    fas = []
#    for i, lex_rule in enumerate(g.lex_rules):
#        (lhs, lhs_name), (rhs, rhs_name), action = lex_rule
#        if isinstance(rhs, LexRegex):
#            g2 = regex_parser(rhs.regex)
#            fa = make_enfa_from_regex(g2, i)
#        else:
#            fa = make_dfa_from_literal(rhs.literal, i)
#        fas.append(fa)
#    dfa = make_multi_dfa(fas)
#    dfa = minimize_enfa(dfa)
#    print dfa

    from lime_parser import make_lime_parser
    p = make_lime_parser(g)
    print lime_cpp(p)

#    import doctest
#    doctest.testmod()
#    print _make_lexer(g, dfa)
