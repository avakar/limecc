#ifndef PARSER_HPP
#define PARSER_HPP

#include <cstdlib>
#include <vector>
#include <utility>

class parser
{
public:
    parser();
    void push_data(char const * first, char const * last);
    typedef double root_type;
    root_type & finish();

private:
    enum class lex_token_t
    {
        none,
        _0, // "+"
        _1, // "-"
        _2, // "*"
        _3, // "/"
        _4, // "("
        _5, // ")"
        _6, // {[0-9]+}
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
    typedef parser self_type;

    void reset_lex(std::size_t lexer_id);
    lex_token_t lex(char const *& first, char const * last);
    lex_token_t lex_finish();
    std::string last_lex_token() const;
    lex_state_t const & get_lex_state(std::size_t lex_state) const;

    void do_shift(lex_token_t tok);
    void do_reduce(lex_token_t lookahead);

    static int r0(self_type & self);    // 'expr' = 'mul';
    static int r1(self_type & self);    // 'expr' = 'expr', 0, 'mul';
    static int r2(self_type & self);    // 'expr' = 'expr', 1, 'mul';
    static int r3(self_type & self);    // 'mul' = 'term';
    static int r4(self_type & self);    // 'mul' = 'mul', 2, 'term';
    static int r5(self_type & self);    // 'mul' = 'mul', 3, 'term';
    static int r6(self_type & self);    // 'term' = 'atom';
    static int r7(self_type & self);    // 'term' = 0, 'atom';
    static int r8(self_type & self);    // 'term' = 1, 'atom';
    static int r9(self_type & self);    // 'atom' = 'NUM';
    static int r10(self_type & self);    // 'atom' = 4, 'expr', 5;
    static int r11(self_type & self);    // 'NUM' = 6;

    void process_token(lex_token_t token)
    {
        static struct {
            bool store;
        } const token_info[] = {
            { false },
            { false },
            { false },
            { false },
            { false },
            { false },
            { true },
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
                m_ast_stack_2.push_back(m_last_token);
            this->do_shift(token);
        }
    }

    struct actions
    {
        static void a1(double & E, double & E1, double & E2);
        static void a2(double & E, double & E1, double & E2);
        static void a4(double & E, double & E1, double & E2);
        static void a5(double & E, double & E1, double & E2);
        static void a8(double & A, double & E);
        static double a11(std::string & x);
    };

    std::vector<state_t> m_state_stack;
    std::vector<double > m_ast_stack_0;
    std::vector<std::string > m_ast_stack_2;

    std::size_t m_lex_state;
    std::size_t m_initial_state;
    std::string m_token;
    std::string m_last_token;
};

inline parser::parser()
{
    this->reset_lex(0);
    m_state_stack.push_back(0);
}

inline void parser::push_data(char const * first, char const * last)
{
    while (first != last)
    {
        lex_token_t token = this->lex(first, last);
        this->process_token(token);
    }
}
inline parser::root_type & parser::finish()
{
    lex_token_t token = this->lex_finish();
    this->process_token(token);
    this->do_reduce(lex_token_t::none);
    if (m_state_stack.size() == 2 && m_ast_stack_0.size() == 1)
        return m_ast_stack_0[0];
    else
        throw std::runtime_error("Unexpected end of file");
}

inline void parser::reset_lex(std::size_t lexer_id)
{
    static std::size_t const lexers[] = {
        0,
    };

    m_lex_state = m_initial_state = lexers[lexer_id];
}

inline parser::lex_state_t const & parser::get_lex_state(std::size_t lex_state) const
{
    static lex_state_t const states[] = {
        /* 0 */ { 0, 8, lex_token_t::none },
        /* 1 */ { 8, 8, lex_token_t::_4 },
        /* 2 */ { 8, 8, lex_token_t::_2 },
        /* 3 */ { 8, 8, lex_token_t::_3 },
        /* 4 */ { 8, 9, lex_token_t::_6 },
        /* 5 */ { 9, 9, lex_token_t::_1 },
        /* 6 */ { 9, 9, lex_token_t::_5 },
        /* 7 */ { 9, 9, lex_token_t::_0 },
        /* 8 */ { 9, 10, lex_token_t::discard },
    };

    return states[lex_state];
}

inline parser::lex_token_t parser::lex(char const *& first, char const * last)
{
    static lex_label_t const labels[] = {
        /* 0 */ { 40, 40 },
        /* 1 */ { 42, 42 },
        /* 2 */ { 47, 47 },
        /* 3 */ { 48, 57 },
        /* 4 */ { 45, 45 },
        /* 5 */ { 41, 41 },
        /* 6 */ { 43, 43 },
        /* 7 */ { 9, 13 },
        /* 8 */ { 32, 32 },
        /* 9 */ { 48, 57 },
        /* 10 */ { 9, 13 },
        /* 11 */ { 32, 32 },
    };

    static lex_edge_t const edges[] = {
        /* 0 */ { 0, 1, false, 1 },
        /* 1 */ { 1, 2, false, 2 },
        /* 2 */ { 2, 3, false, 3 },
        /* 3 */ { 3, 4, false, 4 },
        /* 4 */ { 4, 5, false, 5 },
        /* 5 */ { 5, 6, false, 6 },
        /* 6 */ { 6, 7, false, 7 },
        /* 7 */ { 7, 9, false, 8 },
        /* 8 */ { 9, 10, false, 4 },
        /* 9 */ { 10, 12, false, 8 },
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

inline parser::lex_token_t parser::lex_finish()
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

inline std::string parser::last_lex_token() const
{
    return m_last_token;
}

inline void parser::do_shift(lex_token_t kind)
{
    static state_t const goto_table[7][42] = {
        {
            4, 0, 0, 14, 0, 22, 0, 0, 0, 0, 0, 0, 0, 14, 0, 30,
            0, 0, 0, 0, 0, 4, 4, 4, 4, 0, 30, 0, 14, 0, 14, 14,
            14, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            1, 0, 0, 11, 0, 21, 0, 0, 0, 0, 0, 0, 0, 11, 0, 28,
            0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 28, 0, 11, 0, 11, 11,
            11, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            0, 0, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 24, 24, 0, 0, 0, 32, 32, 0, 0,
        },
        {
            0, 0, 0, 0, 0, 0, 0, 0, 23, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 31, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 23, 23, 0, 0, 0, 31, 31, 0, 0,
        },
        {
            3, 3, 0, 13, 3, 0, 0, 0, 0, 0, 0, 13, 0, 13, 13, 0,
            0, 0, 0, 0, 0, 3, 3, 3, 3, 0, 0, 0, 13, 0, 13, 13,
            13, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 29,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 37, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            9, 9, 0, 19, 9, 0, 0, 0, 0, 0, 0, 19, 0, 19, 19, 0,
            0, 0, 0, 0, 0, 9, 9, 9, 9, 0, 0, 0, 19, 0, 19, 19,
            19, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
    };
    std::size_t new_state = goto_table[static_cast<int>(kind)-1][m_state_stack.back()];
    if (new_state == 0)
        throw std::runtime_error("Unexpected token");
    m_state_stack.push_back(new_state);
}

inline void parser::do_reduce(lex_token_t lookahead)
{
    typedef int (*reduce_fn)(self_type &);
    static reduce_fn const action_table[8][42] = {
        {
            0, 0, &r3, 0, 0, 0, &r9, &r6, &r0, &r11, &r8, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, &r7, 0, 0, 0, 0, 0, 0, 0, 0, &r10, 0, 0, 
            0, &r2, &r1, &r5, &r4, 0, 0, 0, 0, 0, 
        },
        {
            0, 0, &r3, 0, 0, 0, &r9, &r6, &r0, &r11, &r8, 0, &r3, 0, 0, 0, 
            &r9, &r6, &r0, &r11, &r7, 0, 0, 0, 0, &r8, 0, &r7, 0, &r10, 0, 0, 
            0, &r2, &r1, &r5, &r4, &r10, &r2, &r1, &r5, &r4, 
        },
        {
            0, 0, &r3, 0, 0, 0, &r9, &r6, &r0, &r11, &r8, 0, &r3, 0, 0, 0, 
            &r9, &r6, &r0, &r11, &r7, 0, 0, 0, 0, &r8, 0, &r7, 0, &r10, 0, 0, 
            0, &r2, &r1, &r5, &r4, &r10, &r2, &r1, &r5, &r4, 
        },
        {
            0, 0, &r3, 0, 0, 0, &r9, &r6, 0, &r11, &r8, 0, &r3, 0, 0, 0, 
            &r9, &r6, 0, &r11, &r7, 0, 0, 0, 0, &r8, 0, &r7, 0, &r10, 0, 0, 
            0, 0, 0, &r5, &r4, &r10, 0, 0, &r5, &r4, 
        },
        {
            0, 0, &r3, 0, 0, 0, &r9, &r6, 0, &r11, &r8, 0, &r3, 0, 0, 0, 
            &r9, &r6, 0, &r11, &r7, 0, 0, 0, 0, &r8, 0, &r7, 0, &r10, 0, 0, 
            0, 0, 0, &r5, &r4, &r10, 0, 0, &r5, &r4, 
        },
        {
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
        },
        {
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, &r3, 0, 0, 0, 
            &r9, &r6, &r0, &r11, 0, 0, 0, 0, 0, &r8, 0, &r7, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, &r10, &r2, &r1, &r5, &r4, 
        },
        {
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
        },
    };

    static state_t const goto_table[5][42] = {
        {
            5, 0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 26, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            2, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0,
            0, 0, 0, 0, 0, 2, 2, 35, 36, 0, 0, 0, 12, 0, 12, 40,
            41, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            7, 10, 0, 17, 20, 0, 0, 0, 0, 0, 0, 25, 0, 17, 27, 0,
            0, 0, 0, 0, 0, 7, 7, 7, 7, 0, 0, 0, 17, 0, 17, 17,
            17, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            6, 6, 0, 16, 6, 0, 0, 0, 0, 0, 0, 16, 0, 16, 16, 0,
            0, 0, 0, 0, 0, 6, 6, 6, 6, 0, 0, 0, 16, 0, 16, 16,
            16, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
        {
            8, 0, 0, 18, 0, 0, 0, 0, 0, 0, 0, 0, 0, 18, 0, 0,
            0, 0, 0, 0, 0, 33, 34, 0, 0, 0, 0, 0, 38, 0, 39, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        },
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


inline int parser::r0(self_type & self)
{
    // 'expr' = 'mul';
    self.m_state_stack.pop_back();
    return 0;
}

inline int parser::r1(self_type & self)
{
    // 'expr' = 'expr', 0, 'mul';
    double res[1] = {};
    actions::a1(
        res[0],
        self.m_ast_stack_0.end()[-2],
        self.m_ast_stack_0.end()[-1]
    );
    self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
    self.m_ast_stack_0.push_back(res[0]);
    self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
    return 0;
}

inline int parser::r2(self_type & self)
{
    // 'expr' = 'expr', 1, 'mul';
    double res[1] = {};
    actions::a2(
        res[0],
        self.m_ast_stack_0.end()[-2],
        self.m_ast_stack_0.end()[-1]
    );
    self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
    self.m_ast_stack_0.push_back(res[0]);
    self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
    return 0;
}

inline int parser::r3(self_type & self)
{
    // 'mul' = 'term';
    self.m_state_stack.pop_back();
    return 4;
}

inline int parser::r4(self_type & self)
{
    // 'mul' = 'mul', 2, 'term';
    double res[1] = {};
    actions::a4(
        res[0],
        self.m_ast_stack_0.end()[-2],
        self.m_ast_stack_0.end()[-1]
    );
    self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
    self.m_ast_stack_0.push_back(res[0]);
    self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
    return 4;
}

inline int parser::r5(self_type & self)
{
    // 'mul' = 'mul', 3, 'term';
    double res[1] = {};
    actions::a5(
        res[0],
        self.m_ast_stack_0.end()[-2],
        self.m_ast_stack_0.end()[-1]
    );
    self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
    self.m_ast_stack_0.push_back(res[0]);
    self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
    return 4;
}

inline int parser::r6(self_type & self)
{
    // 'term' = 'atom';
    self.m_state_stack.pop_back();
    return 1;
}

inline int parser::r7(self_type & self)
{
    // 'term' = 0, 'atom';
    self.m_state_stack.erase(self.m_state_stack.end() - 2, self.m_state_stack.end());
    return 1;
}

inline int parser::r8(self_type & self)
{
    // 'term' = 1, 'atom';
    double res[1] = {};
    actions::a8(
        res[0],
        self.m_ast_stack_0.end()[-1]
    );
    self.m_ast_stack_0.pop_back();
    self.m_ast_stack_0.push_back(res[0]);
    self.m_state_stack.erase(self.m_state_stack.end() - 2, self.m_state_stack.end());
    return 1;
}

inline int parser::r9(self_type & self)
{
    // 'atom' = 'NUM';
    self.m_state_stack.pop_back();
    return 2;
}

inline int parser::r10(self_type & self)
{
    // 'atom' = 4, 'expr', 5;
    self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
    return 2;
}

inline int parser::r11(self_type & self)
{
    // 'NUM' = 6;
    double res[1] = {};
    res[0] = actions::a11(
        self.m_ast_stack_2.end()[-1]
    );
    self.m_ast_stack_2.pop_back();
    self.m_ast_stack_0.push_back(res[0]);
    self.m_state_stack.pop_back();
    return 3;
}

inline void parser::actions::a1(double & E, double & E1, double & E2)
#line 5 "C:\\devel\\checkouts\\limecc\\lime_example\\calc.y"
{ E = E1 + E2; }
inline void parser::actions::a2(double & E, double & E1, double & E2)
#line 6 "C:\\devel\\checkouts\\limecc\\lime_example\\calc.y"
{ E = E1 - E2; }
inline void parser::actions::a4(double & E, double & E1, double & E2)
#line 10 "C:\\devel\\checkouts\\limecc\\lime_example\\calc.y"
{ E = E1 * E2; }
inline void parser::actions::a5(double & E, double & E1, double & E2)
#line 11 "C:\\devel\\checkouts\\limecc\\lime_example\\calc.y"
{ E = E1 / E2; }
inline void parser::actions::a8(double & A, double & E)
#line 16 "C:\\devel\\checkouts\\limecc\\lime_example\\calc.y"
{ A = -E; }
inline double parser::actions::a11(std::string & x)
#line 23 "C:\\devel\\checkouts\\limecc\\lime_example\\calc.y"
{ return atoi(x.c_str()); }

#endif // PARSER_HPP