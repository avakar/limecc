from lime_grammar import LexDiscard, LexRegex
from regex_parser import make_dfa_from_literal

def _make_lexer(g, dfas, class_name):
    multiedges = []
    multistate = []
    multilabels = []
    for dfa_id, dfa in enumerate(dfas):
        edges = []
        labels = []
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

                for ch in sorted(edge.label.charset):
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

                edges.append((label_first, len(labels), state_map[edge.target], "true" if edge.label.inv else "false"))
            if state in dfa.accept_labels:
                accept_label = '&stub_%d' % dfa.accept_labels[state]
            else:
                accept_label = '0'
            states.append((edge_first, len(edges), accept_label))
        multistate.append(states)
        multilabels.append(labels)
        multiedges.append(edges)

    action_stubs = []
    action_functions = []
    for i, lex_rule in enumerate(g.lex_rules):
        (lhs, lhs_name), (rhs, rhs_name), action, rule_pos = lex_rule
        if (rhs_name is None) != (action is None):
            raise RuntimeError('XXX 1')
        
        action_stub = ['static void stub_%s(%s & l)' % (i, class_name), '{']
        if not isinstance(g.sym_annot.get(lhs), LexDiscard):
            if action is None:
                if g.sym_annot.get(lhs) is None:
                    action_stub.append('    l.push_token(tok::%s);' % lhs.lower())
                else:
                    action_stub.append('    l.push_token(tok::%s, (%s)l.m_token);'
                        % (lhs.lower(), g.sym_annot[lhs]))
            else:
                action_stub.append('    %s res;' % g.sym_annot[lhs])
                params = []
                if lhs_name is not None:
                    params.append('res')
                if rhs_name is not None:
                    params.append('l.m_token')
                params = ', '.join(params)
                if lhs_name is not None:
                    action_stub.append('    l.m_lex_actions.action_%d(%s);' % (i, params))
                else:
                    action_stub.append('    res = l.m_lex_actions.action_%d(%s);' % (i, params))
                action_stub.append('    l.push_token(tok::%s, res);' % lhs.lower())
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
            if rule_pos is not None:
                action_function.insert(2, '#line %d "%s"' % (rule_pos.line, rule_pos.filename.replace('\\', '\\\\')))
            action_functions.append('\n        '.join(action_function))

    sd = {}

    arrays = ["static label_t const labels_%d[] = { %s };" % (i, ''.join(('{ %d, %d },' % (ord(first), ord(last)) for first, last in labels))) for i, labels in enumerate(multilabels)]
    arrays.append("static label_t const * const labels[] = { %s };" % ', '.join(("labels_%d" % i for i in xrange(len(multilabels)))))
    sd['labels'] = '\n        '.join(arrays)

    arrays = ["static edge_t const edges_%d[] = { %s };" % (i, ''.join(('{ %d, %d, %d, %s },' % edge for edge in edges ))) for i, edges in enumerate(multiedges)]
    arrays.append("static edge_t const * const edges[] = { %s };" % ', '.join(("edges_%d" % i for i in xrange(len(multiedges)))))
    sd['edges'] = '\n        '.join(arrays)

    arrays = ["static lex_state_t const states_%d[] = { %s };" % (i, ''.join(('{ %d, %d, %s },' % state for state in states ))) for i, states in enumerate(multistate)]
    arrays.append("static lex_state_t const * const states[] = { %s };" % ', '.join(("states_%d" % i for i in xrange(len(multiedges)))))
    sd['states'] = '\n        '.join(arrays)

    sd['action_stubs'] = '\n    '.join(action_stubs)
    sd['action_functions'] = '\n    '.join(action_functions)
    sd['class_name'] = class_name

    return {
        'lexer_public': lex_templ_public.substitute(sd),
        'lexer_private': lex_templ_private.substitute(sd),
        'lexer_ctor_init': ': m_lex_state(0)',
        'lexer_ctor': '        this->set_dfa(0);',
    }

lex_templ_public = """\
    void set_dfa(std::size_t n)
    {
        m_dfa = n;
    }

    void push_data(char const * first, char const * last)
    {
        $labels

        $edges

        for (; first != last; ++first)
        {
            bool target_state_found = false;
            while (!target_state_found)
            {
                lex_state_t const & state = this->get_state();
                for (std::size_t edge_idx = state.edge_first;
                    !target_state_found && edge_idx != state.edge_last;
                    ++edge_idx)
                {
                    edge_t const & edge = edges[m_dfa][edge_idx];

                    bool success = edge.invert;
                    if (edge.invert)
                    {
                        for (std::size_t i = edge.label_first; success && i != edge.label_last; ++i)
                        {
                            if (labels[m_dfa][i].range_first <= *first && *first <= labels[m_dfa][i].range_last)
                                success = false;
                        }
                    }
                    else
                    {
                        for (std::size_t i = edge.label_first; !success && i != edge.label_last; ++i)
                        {
                            if (labels[m_dfa][i].range_first <= *first && *first <= labels[m_dfa][i].range_last)
                                success = true;
                        }
                    }

                    if (success)
                    {
                        m_lex_state = edge.target;
                        target_state_found = true;
                    }
                }

                if (!target_state_found)
                {
                    if (m_lex_state == 0)
                    {
                        target_state_found = true;
                    }
                    else
                    {
                        this->dispatch_actions();
                        m_token.clear();
                        m_lex_state = 0;
                    }
                }
                else
                {
                    m_token.append(1, *first);
                }
            }
        }
    }

    void lex_finish()
    {
        this->dispatch_actions();
    }
"""

lex_templ_private = """
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
        bool invert;
    };

    typedef void (*action_t)($class_name &);

    struct lex_state_t
    {
        std::size_t edge_first;
        std::size_t edge_last;
        action_t accept;
    };

    lex_state_t const & get_state() const
    {
        $states

        return states[m_dfa][m_lex_state];
    }

    void dispatch_actions()
    {
        lex_state_t const & state = this->get_state();
        if (state.accept != 0)
            state.accept(*this);
    }

    $action_stubs

    struct actions_t
    {
        $action_functions
    };

    actions_t m_lex_actions;
    std::size_t m_dfa;
    std::size_t m_lex_state;
    std::string m_token;
"""

def lime_cpp(p):
    g = p.grammar

    sym_annot = dict(g.sym_annot.iteritems())
    for sym in g.symbols():
        if sym not in sym_annot:
            if g.is_terminal(sym) and g.token_type is not None:
                sym_annot[sym] = g.token_type.strip()
            else:
                sym_annot[sym] = None
        else:
            if sym_annot[sym] is not None and not isinstance(sym_annot[sym], LexDiscard):
                sym_annot[sym] = sym_annot[sym].strip()

    syms_by_type = {}
    for sym, annot in sym_annot.iteritems():
        syms_by_type.setdefault(annot, []).append(sym)

    annot_indexes = dict([(annot, i) for i, annot in enumerate(syms_by_type.iterkeys())])
    nonterm_indexes = dict([(nonterm, i) for i, nonterm in enumerate(g.nonterms())])
    term_indexes = dict([(term, i) for i, term in enumerate(g.terminals())])

    ast_stacks = ['std::vector<%s > m_ast_stack_%d;' % (annot, i)
        for annot, i in annot_indexes.iteritems() if annot is not None and not isinstance(annot, LexDiscard)]

    tokens = [term.lower() for term in g.terminals()]
    token_lines = []
    for term in g.terminals():
        if g.token_comments.get(term) is not None:
            token_lines.append('%s, // %s' % (term.lower(), g.token_comments[term]))
        else:
            token_lines.append('%s,' % term.lower())

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

        if rule.lime_action is None:
            # This must be either a typed non-terminal with exactly one
            # typed rhs symbol, or a void non-terminal with no typed rhs symbols
            if sym_annot[rule.left] is not None:
                if (len(idx_counts) != 1 or idx_counts.values()[0] != 1
                        or idx_counts.keys()[0] != annot_indexes[sym_annot[rule.left]]):
                    raise RuntimeError('XXX 2') # This should probably be done before the generation begins

        modify_inplace = rule.lhs_name is not None and any((rule.lhs_name == rhs for rhs in rule.rhs_names))
        if rule.lime_action is not None:
            if not modify_inplace and sym_annot[rule.left] is not None:
                f.append('    %s res[1] = {};' % sym_annot[rule.left])
            if rule.lhs_name or sym_annot[rule.left] is None:
                f.append('    self.m_actions.a%d(' % i)
            else:
                f.append('    res[0] = self.m_actions.a%d(' % i)
            params = []
            if not modify_inplace and rule.lhs_name and sym_annot[rule.left] is not None:
                params.append('        res[0]')
            used_indexes = {}
            for right, rhs_name in zip(rule.right, rule.rhs_names):
                idx = annot_indexes[sym_annot[right]]
                used_indexes.setdefault(idx, 0)
                # XXX: do this beforehand
                if rhs_name and sym_annot[right] is None:
                    raise RuntimeError('A symbol has a name, yet it has no type: %s' % right)
                if rhs_name:
                    params.append(
                        '            self.m_ast_stack_%d.end()[-%d]' % (
                        idx, idx_counts[idx] - used_indexes[idx]))
                if modify_inplace and rhs_name == rule.lhs_name:
                    inplace_swap_stack = idx
                    inplace_swap = used_indexes[idx]
                used_indexes[idx] += 1
            f.append(',\n'.join(params))
            f.append('    );')

            if modify_inplace and inplace_swap:
                f.append('    using std::swap; swap(self.m_ast_stack_%d.end()[-%d], self.m_ast_stack_%d.end()[-%d]);'
                    % (inplace_swap_stack, idx_counts[inplace_swap_stack],
                    inplace_swap_stack, idx_counts[inplace_swap_stack] - inplace_swap))
            for idx, count in idx_counts.iteritems():
                if modify_inplace and idx == inplace_swap_stack:
                    count -= 1
                if count != 0:
                    f.append('    self.m_ast_stack_%d.erase(self.m_ast_stack_%d.end() - %d, self.m_ast_stack_%d.end());'
                        % (idx, idx, count, idx))
            if not modify_inplace and sym_annot[rule.left] is not None:
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
        if not modify_inplace:
            _add_param(rule.left, rule.lhs_name)
        for sym, sym_name in zip(rule.right, rule.rhs_names):
            _add_param(sym, sym_name)

        if rule.lime_action is not None:
            if not rule.lhs_name and sym_annot[rule.left] is not None:
                ret_type = sym_annot[rule.left]
            else:
                ret_type = 'void'
            if rule.lime_action_pos:
                line = '#line %d "%s"\n' % (rule.lime_action_pos.line, rule.lime_action_pos.filename.replace('\\', '\\\\'))
            else:
                line = ''
            lime_actions.append("%s a%d(%s)\n%s{%s}\n" % (ret_type, i, ', '.join(param_list), line, rule.lime_action))

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
        if isinstance(type, LexDiscard):
            continue
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
        this->lex_finish(); // XXX: only when we have lexer
        this->do_reduce(tok::eof);
        if (m_state_stack.size() == 2 && %s.size() == 1)
            return %s[0];
        else
            throw std::runtime_error("Unexpected end of file");
    }
''' % (root_stack, root_stack)
    else:
        finish_function = '''\
    void finish()
    {
        this->lex_finish(); // XXX: only when we have lexer
        this->do_reduce(tok::eof);
        if (m_state_stack.size() != 2)
            throw std::runtime_error("Unexpected end of file");
    }
'''

    sd = {}

    class_name = 'parser'
    if g.lex_rules:
        if not p.grammar.context_lexer:
            sd.update(_make_lexer(g, [p.lexer], class_name))
        else:
            sd.update(_make_lexer(g, p.lexers, class_name))
            
    else:
        sd['lexer_public'] = ''
        sd['lexer_private'] = ''

    if root_type is not None:
        sd['root_typedef'] = 'typedef %s root_type;' % root_type
    else:
        sd['root_typedef'] = ''

    if g.context_lexer:
        sd['set_dfa'] = "static std::size_t const next_dfa[] = { %s };\n        this->set_dfa(next_dfa[new_state]);" % ', '.join((str(state.lexer_id) for state in p.states))
    else:
        sd['set_dfa'] = ''

    sd['user_include'] = '' if g.user_include is None else g.user_include
    sd['finish_function'] = finish_function
    sd['ast_stacks'] = '\n    '.join(ast_stacks)
    sd['tokens'] = '\n    '.join(token_lines)
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
    sd['class_name'] = class_name
    return templ.substitute(sd)

templ = """\
#ifndef PARSER
#define PARSER

$user_include
#include <cassert>
#include <vector>
#include <stdexcept> // XXX

namespace tok {

enum token_kind {
    eof,
    $tokens
};

}

class $class_name
{
public:
    typedef int state_t;
    $root_typedef

    $class_name()
        $lexer_ctor_init
    {
$lexer_ctor
        m_state_stack.push_back(0);
    }

    $push_token_functions

$finish_function

$lexer_public

private:
    typedef $class_name self_type;

    void do_shift(tok::token_kind kind)
    {
        static state_t const goto_table[$term_count_m1][$state_count] = {
            { $term_goto_table },
        };
        std::size_t new_state = goto_table[kind-1][m_state_stack.back()];
        if (new_state == 0)
            throw std::runtime_error("Unexpected token");
        m_state_stack.push_back(new_state);

        $set_dfa
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

$lexer_private
};

#endif // PARSER
"""

from string import Template
templ = Template(templ)
lex_templ_public = Template(lex_templ_public)
lex_templ_private = Template(lex_templ_private)

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

    from lime_parser import make_lime_parser
    p = make_lime_parser(g)
    print lime_cpp(p)

#    import doctest
#    doctest.testmod()
