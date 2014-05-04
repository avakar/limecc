from lime_grammar import LexRegex
from jinja2 import Template

hpp_templ = Template(r"""
#ifndef PARSER_HPP
#define PARSER_HPP

{{user_include}}#include <cstdlib>
#include <vector>
#include <utility>

class {{class_name}}
{
public:
    {{class_name}}();
    void push_data(char const * first, char const * last);

    {%- if root_type is defined %}
    typedef {{root_type}} root_type;
    root_type & finish();
    {%- else %}
    void finish();
    {%- endif %}

private:
    enum class lex_token_t
    {
        none,
        {%- for lex_token in lex_tokens %}
        {{lex_token.name}}, // {{lex_token.comment}}
        {%- endfor %}
        invalid,
        discard,
    };

    struct lex_label_t
    {
        char range_first;
        char range_last;
    };

    struct lex_edge_t
    {
        std::size_t label_first;
        std::size_t label_last;
        bool label_invert;
        std::size_t target;
    };

    struct lex_state_t
    {
        std::size_t edge_first;
        std::size_t edge_last;
        lex_token_t accept;
    };

    typedef int state_t;
    typedef {{class_name}} self_type;

    void reset_lex(std::size_t lexer_id);
    lex_token_t lex(char const *& first, char const * last);
    lex_token_t lex_finish();
    std::string last_lex_token() const;
    lex_state_t const & get_lex_state(std::size_t lex_state) const;

    void do_shift(lex_token_t tok);
    void do_reduce(lex_token_t lookahead);
{% for rf in reduce_functions %}
    static int r{{loop.index0}}(self_type & self);    // {{rf.comment}}
    {%- endfor %}

    void process_token(lex_token_t token)
    {
        static struct {
            bool store;
        } const token_info[] = {
            {%- for t in lex_tokens %}
            { {% if t.store %}true{% else %}false{% endif %} },
            {%- endfor %}
        };

        switch (token)
        {
        case lex_token_t::none:
            break;
        case lex_token_t::invalid:
            throw std::runtime_error("Unexpected token");
        default:
            this->do_reduce(token);
            if (token_info[static_cast<int>(token) - 1].store)
                m_ast_stack_{{lex_stack}}.push_back(m_last_token);
            this->do_shift(token);
        }
    }

    struct actions
    {
        {%- for action in lime_actions %}
        static {{action.ret_type}} a{{action.id}}({% for p in action.params %}{{'%s & %s'|format(p.type, p.name)}}{% if not loop.last %}, {% endif %}{% endfor %});
        {%- endfor %}
    };

    std::vector<state_t> m_state_stack;

    {%- for st in ast_stacks %}
    std::vector<{{st.type}} > m_ast_stack_{{st.i}};
    {%- endfor %}

    std::size_t m_lex_state;
    std::size_t m_initial_state;
    std::string m_token;
    std::string m_last_token;
};

inline {{class_name}}::{{class_name}}()
{
    this->reset_lex(0);
    m_state_stack.push_back(0);
}

inline void {{class_name}}::push_data(char const * first, char const * last)
{
    while (first != last)
    {
        lex_token_t token = this->lex(first, last);
        this->process_token(token);
    }
}

{%- if root_type is defined %}
inline {{class_name}}::root_type & {{class_name}}::finish()
{
    lex_token_t token = this->lex_finish();
    this->process_token(token);
    this->do_reduce(lex_token_t::none);
    if (m_state_stack.size() == 2 && m_ast_stack_{{root_stack}}.size() == 1)
        return m_ast_stack_{{root_stack}}[0];
    else
        throw std::runtime_error("Unexpected end of file");
}
{%- else %}
inline void {{class_name}}::finish()
{
    lex_token_t token = this->lex_finish();
    this->process_token(token);
    this->do_reduce(lex_token_t::none);
    if (m_state_stack.size() != 2)
        throw std::runtime_error("Unexpected end of file");
}
{%- endif %}

inline void {{class_name}}::reset_lex(std::size_t lexer_id)
{
    static std::size_t const lexers[] = {
    {%- for lexer_id in lexer_ids %}
        {{lexer_id}},
    {%- endfor %}
    };

    m_lex_state = m_initial_state = lexers[lexer_id];
}

inline {{class_name}}::lex_state_t const & {{class_name}}::get_lex_state(std::size_t lex_state) const
{
    static lex_state_t const states[] = {
        {%- for ll in lex_states %}
        /* {{loop.index0}} */ { {{ll.first_edge}}, {{ll.last_edge}}, lex_token_t::{{ll.accept_token}} },
        {%- endfor %}
    };

    return states[lex_state];
}

inline {{class_name}}::lex_token_t {{class_name}}::lex(char const *& first, char const * last)
{
    static lex_label_t const labels[] = {
        {%- for lex_label in lex_labels %}
        /* {{loop.index0}} */ { {{lex_label.first}}, {{lex_label.last}} },
        {%- endfor %}
    };

    static lex_edge_t const edges[] = {
        {%- for lex_edge in lex_edges %}
        /* {{loop.index0}} */ { {{lex_edge.first_label}}, {{lex_edge.last_label}}, {% if lex_edge.invert %}true{% else %}false{% endif %}, {{lex_edge.target}} },
        {%- endfor %}
    };

    for (char const * cur = first; cur != last; )
    {
        bool target_state_found = false;

        lex_state_t const & state = this->get_lex_state(m_lex_state);
        for (std::size_t edge_idx = state.edge_first; edge_idx != state.edge_last; ++edge_idx)
        {
            lex_edge_t const & edge = edges[edge_idx];

            target_state_found = edge.label_invert;
            if (edge.label_invert)
            {
                for (std::size_t i = edge.label_first; target_state_found && i != edge.label_last; ++i)
                {
                    if (labels[i].range_first <= *cur && *cur <= labels[i].range_last)
                        target_state_found = false;
                }
            }
            else
            {
                for (std::size_t i = edge.label_first; !target_state_found && i != edge.label_last; ++i)
                {
                    if (labels[i].range_first <= *cur && *cur <= labels[i].range_last)
                        target_state_found = true;
                }
            }

            if (target_state_found)
            {
                m_lex_state = edge.target;
                break;
            }
        }

        if (!target_state_found)
        {
            lex_token_t token;
            switch (state.accept)
            {
            case lex_token_t::none:
                token = lex_token_t::invalid;
                ++cur;
                break;
            case lex_token_t::invalid:
                token = lex_token_t::invalid;
                break;
            case lex_token_t::discard:
                m_lex_state = m_initial_state;
                first = cur;
                m_token.clear();
                continue;
            default:
                token = state.accept;
                m_lex_state = m_initial_state;
            }

            m_token.append(first, cur);
            m_last_token.swap(m_token);
            m_token.clear();
            first = cur;
            return token;
        }

        ++cur;
    }

    m_token.append(first, last);
    first = last;
    return lex_token_t::none;
}

inline {{class_name}}::lex_token_t {{class_name}}::lex_finish()
{
    lex_state_t const & state = this->get_lex_state(m_lex_state);

    lex_token_t token;
    switch (state.accept)
    {
    case lex_token_t::none:
        token = lex_token_t::invalid;
        break;
    case lex_token_t::invalid:
        token = lex_token_t::none;
        break;
    case lex_token_t::discard:
        m_lex_state = m_initial_state;
        m_token.clear();
        token = lex_token_t::none;
        break;
    default:
        token = state.accept;
    }

    m_last_token.swap(m_token);
    m_token.clear();
    return token;
}

inline std::string {{class_name}}::last_lex_token() const
{
    return m_last_token;
}

inline void {{class_name}}::do_shift(lex_token_t kind)
{
    static state_t const goto_table[{{term_goto_table|length}}][{{state_count}}] = {
        {%- for row in term_goto_table %}
        {
            {%- for rowpart in row|batch(16) %}
            {{rowpart|join(', ')}},
            {%- endfor %}
        },
        {%- endfor %}
    };
    std::size_t new_state = goto_table[static_cast<int>(kind)-1][m_state_stack.back()];
    if (new_state == 0)
        throw std::runtime_error("Unexpected token");
    m_state_stack.push_back(new_state);

    {%- if lexer_ids|length > 1 %}
    this->reset_dfa(new_state);
    {%- endif %}
}

inline void {{class_name}}::do_reduce(lex_token_t lookahead)
{
    typedef int (*reduce_fn)(self_type &);
    static reduce_fn const action_table[{{action_table|length}}][{{state_count}}] = {
        {%- for row in action_table %}
        {
            {%- for rowpart in row|batch(16) %}
            {% for action in rowpart %}{% if action is not none %}&r{{action}}, {% else %}0, {% endif %}{% endfor %}
            {%- endfor %}
        },
        {%- endfor %}
    };

    static state_t const goto_table[{{nonterm_goto_table|length}}][{{state_count}}] = {
        {%- for row in nonterm_goto_table %}
        {
            {%- for rowpart in row|batch(16) %}
            {{rowpart|join(', ')}},
            {%- endfor %}
        },
        {%- endfor %}
    };

    for (;;)
    {
        state_t state = m_state_stack.back();
        reduce_fn fn = action_table[static_cast<int>(lookahead)][state];
        if (!fn)
            break;
        int nonterm = fn(*this);
        state = m_state_stack.back();
        m_state_stack.push_back(goto_table[nonterm][state]);
    }
}

{% for rf in reduce_functions %}
inline int {{class_name}}::r{{loop.index0}}(self_type & self)
{
    // {{rf.comment}}
    {%- if rf.has_action %}
    {%- if rf.returns or rf.returns_param %}
    {{rf.return_type}} res[1] = {};
    {%- endif %}
    {% if rf.returns %}res[0] = {% endif %}actions::a{{loop.index0}}(
        {%- if rf.returns_param %}
        res[0]{% if rf.params %},{% endif %}
        {%- endif %}
        {%- for param in rf.params %}
        self.m_ast_stack_{{param.stack}}.end()[-{{param.index}}]{% if not loop.last %},{% endif %}
        {%- endfor %}
    );
    {%- endif %}
    {%- if rf.swap is defined %}
    using std::swap;
    swap(self.m_ast_stack_{{rf.swap.stack}}.end()[-{{rf.swap.lhs}}], self.m_ast_stack_{{rf.swap.stack}}.end()[-{{rf.swap.rhs}}]);
    {%- endif %}
    {%- for e in rf.erase %}
    {%- if e.count == 1 %}
    self.m_ast_stack_{{e.stack}}.pop_back();
    {%- elif e.count > 1 %}
    self.m_ast_stack_{{e.stack}}.erase(self.m_ast_stack_{{e.stack}}.end() - {{e.count}}, self.m_ast_stack_{{e.stack}}.end());
    {%- endif %}
    {%- endfor %}
    {%- if rf.returns or rf.returns_param %}
    self.m_ast_stack_{{rf.target_stack}}.push_back(res[0]);
    {%- endif %}
    {%- if rf.rule_length > 1 %}
    self.m_state_stack.erase(self.m_state_stack.end() - {{rf.rule_length}}, self.m_state_stack.end());
    {%- elif rf.rule_length == 1 %}
    self.m_state_stack.pop_back();
    {%- endif %}
    return {{rf.nonterm_index}};
}
{% endfor %}

{%- for action in lime_actions %}
inline {{action.ret_type}} {{class_name}}::actions::a{{action.id}}({% for p in action.params %}{{'%s & %s'|format(p.type, p.name)}}{% if not loop.last %}, {% endif %}{% endfor %})
{%- if action.line is defined %}
#line {{action.line}} "{{action.filename|replace('\\', '\\\\')}}"
{%- endif %}
{{'{'}}{{action.snippet}}{{'}'}}
{%- endfor %}

#endif // PARSER_HPP
""".lstrip())

def _make_lexer(p, class_name):
    def make_ranges(charset):
        res = []
        first = None
        last = None
        for ch in sorted(charset):
            if first is None:
                first = last = ord(ch)
            elif ord(ch) == last + 1:
                last += 1
            else:
                res.append((first, last))
                first = last = ord(ch)
        if first is not None:
            res.append((first, last))
        return res

    initial_states = []
    labels = []
    edges = []
    states = []
    for lexer in p.lexers:
        cur_states = []
        all_states = list(lexer.bfs_walk())
        state_map = dict([(state, i) for i, state in enumerate(all_states)])
        for state in all_states:
            cur_edges = []
            for target, label in state.outedges:
                cur_labels = make_ranges(label.charset)
                cur_edges.append({
                    'first_label': len(labels),
                    'last_label': len(labels) + len(cur_labels),
                    'invert': label.inv,
                    'target': state_map[target]
                    })
                labels.extend(({ 'first': first, 'last': last } for first, last in cur_labels))
            if state.accept is None:
                accept = 'none' if state in lexer.initial else 'invalid'
            elif state.accept.token_id == p.discard_id:
                accept = 'discard'
            else:
                accept = '_' + str(state.accept.token_id)
            cur_states.append({
                'first_edge': len(edges),
                'last_edge': len(edges) + len(cur_edges),
                'accept_token': accept
                })
            edges.extend(cur_edges)
        assert len(lexer.initial) == 1
        initial_states.append(len(states) + state_map[next(iter(lexer.initial))])
        states.extend(cur_states)

    return {
        'lexer_ids': initial_states,
        'lex_states': states,
        'lex_edges': edges,
        'lex_labels': labels,
        'lex_tokens': [{
            'name': '_%d' % i,
            'comment': str(p.grammar.tokens[i]),
            'store': isinstance(p.grammar.tokens[i], LexRegex)
            } for i in xrange(len(p.grammar.tokens))]
        }

def lime_cpp(p):
    params = {
        'class_name': 'parser',
        'ast_stacks': [],
        'user_include': p.grammar.user_include or ''
        }
    params.update(_make_lexer(p, 'parser'))

    g = p.grammar
    sym_annot = dict(g.sym_annot.iteritems())
    for sym in g.symbols():
        if sym not in sym_annot:
            if g.is_terminal(sym) and g.token_type is not None:
                sym_annot[sym] = g.token_type.strip()
            else:
                if isinstance(sym, int) and isinstance(p.grammar.tokens[sym], LexRegex):
                    sym_annot[sym] = 'std::string'
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

    params['ast_stacks'] = [{'type': annot, 'i': i} for annot, i in annot_indexes.iteritems() if annot is not None]
    params['lex_stack'] = annot_indexes['std::string']

    assert len(p.root) == 1
    root_type = sym_annot.get(p.root[0])

    rule_count = len(g)
    state_count = len(p.states)

    rule_indexes = {}
    reduce_functions = []
    lime_actions = []
    rule_descs = []
    for i, rule in enumerate(g):
        rule_indexes[rule] = i

        ruledesc = {
            'i': i,
            'comment': str(rule)
            }

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
        ruledesc['has_action'] = rule.lime_action is not None
        if rule.lime_action is not None:
            ruledesc['return_type'] = sym_annot[rule.left]
            ruledesc['returns'] = not rule.lhs_name and sym_annot[rule.left] is not None
            ruledesc['returns_param'] = not modify_inplace and rule.lhs_name and sym_annot[rule.left] is not None

            used_indexes = {}
            param_list = []
            for right, rhs_name in zip(rule.right, rule.rhs_names):
                idx = annot_indexes[sym_annot[right]]
                used_indexes.setdefault(idx, 0)
                # XXX: do this beforehand
                if rhs_name and sym_annot[right] is None:
                    raise RuntimeError('A symbol has a name, yet it has no type: %s' % right)
                if rhs_name:
                    param_list.append({ 'stack': idx, 'index': idx_counts[idx] - used_indexes[idx] })
                if modify_inplace and rhs_name == rule.lhs_name:
                    inplace_swap_stack = idx
                    inplace_swap = used_indexes[idx]
                used_indexes[idx] += 1
            ruledesc['params'] = param_list

            if modify_inplace and inplace_swap:
                ruledesc['swap'] = {
                    'stack': inplace_swap_stack,
                    'lhs': idx_counts[inplace_swap_stack],
                    'rhs': idx_counts[inplace_swap_stack] - inplace_swap
                    }
            erase = []
            for idx, count in idx_counts.iteritems():
                if modify_inplace and idx == inplace_swap_stack:
                    count -= 1
                if count != 0:
                    erase.append({
                        'stack': idx,
                        'count': count
                    })
            ruledesc['erase'] = erase
            if not modify_inplace and sym_annot[rule.left] is not None:
                ruledesc['target_stack'] = annot_indexes[sym_annot[rule.left]]

        ruledesc['rule_length'] = len(rule.right)
        ruledesc['nonterm_index'] = nonterm_indexes[rule.left]
        reduce_functions.append(ruledesc)

        if rule.lime_action is not None:
            param_list = []
            def _add_param(sym, name):
                if name:
                    param_list.append({'type': sym_annot[sym], 'name': name })
            if not modify_inplace:
                _add_param(rule.left, rule.lhs_name)
            for sym, sym_name in zip(rule.right, rule.rhs_names):
                _add_param(sym, sym_name)

            action = {
                'ret_type': sym_annot[rule.left] if not rule.lhs_name and sym_annot[rule.left] is not None else 'void',
                'id': i,
                'params': param_list,
                'snippet': rule.lime_action
                }
            if rule.lime_action_pos:
                line = '#line %d "%s"\n' % (rule.lime_action_pos.line, rule.lime_action_pos.filename.replace('\\', '\\\\'))
                action.update({
                    'line': rule.lime_action_pos.line,
                    'filename': rule.lime_action_pos.filename
                    })

            lime_actions.append(action) #"%s a%d(%s)\n%s{%s}\n" % (ret_type, i, ', '.join(param_list), line, rule.lime_action))

    params['reduce_functions'] = reduce_functions
    params['lime_actions'] = lime_actions
    if root_type is not None:
        params['root_stack'] = annot_indexes[root_type]
        params['root_type'] = root_type

    def _get_action_row(lookahead):
        action_row = []
        for i, state in enumerate(p.states):
            r = state.action.get(lookahead)
            if r:
                action_row.append(rule_indexes[r])
            else:
                action_row.append(None)
        return action_row

    action_table = [None]*(len(term_indexes)+1)
    action_table[0] = _get_action_row(())
    for term, i in term_indexes.iteritems():
        action_table[i+1] = _get_action_row((term,))
    params['action_table'] = action_table

    nonterm_goto_table = [None] * len(nonterm_indexes)
    for nonterm in g.nonterms():
        row = [state.goto.get(nonterm, 0) for state in p.states]
        nonterm_goto_table[nonterm_indexes[nonterm]] = row
    params['nonterm_goto_table'] = nonterm_goto_table

    term_goto_table = [None] * len(term_indexes)
    for term in g.terminals():
        row = [state.goto.get(term, 0) for state in p.states]
        term_goto_table[term_indexes[term]] = row
    params['term_goto_table'] = term_goto_table
    params['state_count'] = len(p.states)

    return hpp_templ.render(**params)
