#ifndef PARSER
#define PARSER

#include <cassert>
#include <vector>
#include <stdexcept> // XXX

namespace tok {

enum token_kind {
    eof,
    _implicit_0,
    _implicit_1,
    _implicit_2,
    _implicit_3,
    _implicit_4,
    _implicit_5,
    num
};

}

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
            { 40, 40 },
            { 9, 13 },
            { 32, 32 },
            { 47, 47 },
            { 43, 43 },
            { 41, 41 },
            { 48, 57 },
            { 45, 45 },
            { 42, 42 },
            { 9, 13 },
            { 32, 32 },
            { 48, 57 },
        };

        static edge_t const edges[] = {
            { 0, 1, 4 },
            { 1, 3, 2 },
            { 3, 4, 8 },
            { 4, 5, 7 },
            { 5, 6, 3 },
            { 6, 7, 6 },
            { 7, 8, 1 },
            { 8, 9, 5 },
            { 9, 11, 2 },
            { 11, 12, 6 },
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
            { 0, 8, 0 },
            { 8, 8, &stub_6 },
            { 8, 9, &stub_0 },
            { 9, 9, &stub_2 },
            { 9, 9, &stub_3 },
            { 9, 9, &stub_5 },
            { 9, 10, &stub_1 },
            { 10, 10, &stub_4 },
            { 10, 10, &stub_7 },
        };

        return states[m_state];
    }

    void dispatch_actions(TokenSink & token_sink)
    {
        state_t const & state = this->get_state();
        if (state.accept != 0)
            state.accept(*this, token_sink);
    }

    static void stub_0(basic_lexer & l, TokenSink & token_sink)
    {
    }
    static void stub_1(basic_lexer & l, TokenSink & token_sink)
    {
        double res;
        res = l.m_actions.action_1(l.m_token);
        token_sink.push_token(tok::num, res);
    }
    static void stub_2(basic_lexer & l, TokenSink & token_sink)
    {
        token_sink.push_token(tok::_implicit_5);
    }
    static void stub_3(basic_lexer & l, TokenSink & token_sink)
    {
        token_sink.push_token(tok::_implicit_4);
    }
    static void stub_4(basic_lexer & l, TokenSink & token_sink)
    {
        token_sink.push_token(tok::_implicit_0);
    }
    static void stub_5(basic_lexer & l, TokenSink & token_sink)
    {
        token_sink.push_token(tok::_implicit_2);
    }
    static void stub_6(basic_lexer & l, TokenSink & token_sink)
    {
        token_sink.push_token(tok::_implicit_1);
    }
    static void stub_7(basic_lexer & l, TokenSink & token_sink)
    {
        token_sink.push_token(tok::_implicit_3);
    }

    struct actions_t
    {
        double action_1(std::string & x)
        {
         return atoi(x.c_str()); 
        }
    };

    actions_t m_actions;
    std::size_t m_state;
    std::string m_token;
};


class parser
{
public:
    typedef int state_t;
    typedef double root_type;

    parser()
    {
        m_state_stack.push_back(0);
    }

    void push_token(tok::token_kind kind, double const & value)
    {
        this->do_reduce(kind);
        this->do_shift(kind);
        m_ast_stack_0.push_back(value);
    }
    void push_token(tok::token_kind kind)
    {
        this->do_reduce(kind);
        this->do_shift(kind);
    }

    root_type & finish()
    {
        this->do_reduce(tok::eof);
        if (m_state_stack.size() == 2 && m_ast_stack_0.size() == 1)
            return m_ast_stack_0[0];
        else
            throw std::runtime_error("TODO");
    }


private:
    typedef parser self_type;

    void do_shift(tok::token_kind kind)
    {
        static state_t const goto_table[7][40] = {
            { 2, 0, 0, 10, 13, 0, 0, 0, 0, 0, 2, 2, 0, 0, 26, 13, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 13, 0, 13, 26, 0, 13, 13, 0, 0, 0, 0, 0, 0, 0 },
            { 7, 0, 0, 11, 18, 0, 0, 0, 0, 0, 7, 7, 0, 0, 28, 18, 0, 0, 0, 0, 0, 7, 7, 0, 0, 0, 18, 0, 18, 28, 0, 18, 18, 0, 0, 0, 0, 0, 0, 0 },
            { 0, 0, 0, 0, 0, 0, 0, 0, 21, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 31, 0, 0, 0, 21, 21, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 31, 31, 0, 0, 0 },
            { 0, 0, 0, 0, 0, 0, 0, 0, 22, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 22, 22, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 32, 0, 0, 0 },
            { 4, 0, 4, 0, 15, 0, 0, 4, 0, 0, 4, 4, 0, 15, 0, 15, 0, 0, 15, 0, 0, 4, 4, 0, 0, 0, 15, 0, 15, 0, 0, 15, 15, 0, 0, 0, 0, 0, 0, 0 },
            { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 27, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 37, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
            { 6, 0, 6, 0, 17, 0, 0, 6, 0, 0, 6, 6, 0, 17, 0, 17, 0, 0, 17, 0, 0, 6, 6, 0, 0, 0, 17, 0, 17, 0, 0, 17, 17, 0, 0, 0, 0, 0, 0, 0 },
        };
        m_state_stack.push_back(goto_table[kind-1][m_state_stack.back()]);
    }

    void do_reduce(tok::token_kind lookahead)
    {
        typedef int (*reduce_fn)(self_type &);
        static reduce_fn const action_table[8][40] = {
            { 0, &r3, 0, 0, 0, &r6, &r9, 0, &r0, &r7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, &r8, 0, 0, &r1, &r2, 0, 0, &r10, 0, 0, 0, 0, 0, &r4, &r5, 0, 0, 0, 0, 0 },
            { 0, &r3, 0, 0, 0, &r6, &r9, 0, &r0, &r7, 0, 0, &r3, 0, 0, 0, &r6, &r9, 0, &r0, &r8, 0, 0, &r1, &r2, &r7, 0, &r10, 0, 0, &r8, 0, 0, &r4, &r5, &r1, &r2, &r10, &r4, &r5 },
            { 0, &r3, 0, 0, 0, &r6, &r9, 0, &r0, &r7, 0, 0, &r3, 0, 0, 0, &r6, &r9, 0, &r0, &r8, 0, 0, &r1, &r2, &r7, 0, &r10, 0, 0, &r8, 0, 0, &r4, &r5, &r1, &r2, &r10, &r4, &r5 },
            { 0, &r3, 0, 0, 0, &r6, &r9, 0, 0, &r7, 0, 0, &r3, 0, 0, 0, &r6, &r9, 0, 0, &r8, 0, 0, 0, 0, &r7, 0, &r10, 0, 0, &r8, 0, 0, &r4, &r5, 0, 0, &r10, &r4, &r5 },
            { 0, &r3, 0, 0, 0, &r6, &r9, 0, 0, &r7, 0, 0, &r3, 0, 0, 0, &r6, &r9, 0, 0, &r8, 0, 0, 0, 0, &r7, 0, &r10, 0, 0, &r8, 0, 0, &r4, &r5, 0, 0, &r10, &r4, &r5 },
            { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
            { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, &r3, 0, 0, 0, &r6, &r9, 0, &r0, 0, 0, 0, 0, 0, &r7, 0, 0, 0, 0, &r8, 0, 0, 0, 0, &r1, &r2, &r10, &r4, &r5 },
            { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
        };

        static state_t const goto_table[4][40] = {
            { 3, 0, 0, 0, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 29, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
            { 1, 0, 0, 0, 12, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 12, 0, 0, 0, 0, 0, 33, 34, 0, 0, 0, 12, 0, 12, 0, 0, 38, 39, 0, 0, 0, 0, 0, 0, 0 },
            { 5, 0, 9, 0, 16, 0, 0, 20, 0, 0, 5, 5, 0, 25, 0, 16, 0, 0, 30, 0, 0, 5, 5, 0, 0, 0, 16, 0, 16, 0, 0, 16, 16, 0, 0, 0, 0, 0, 0, 0 },
            { 8, 0, 0, 0, 19, 0, 0, 0, 0, 0, 23, 24, 0, 0, 0, 19, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 35, 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },
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

    static int r0(self_type & self)
    {
        // 'expr' = 'mul';
        self.m_state_stack.erase(self.m_state_stack.end() - 1, self.m_state_stack.end());
        return 0;
    }
    static int r1(self_type & self)
    {
        // 'expr' = 'expr', '_implicit_0', 'mul';
        double res[1] = {};
        self.m_actions.a1(
            res[0],
            self.m_ast_stack_0.end()[-2],
            self.m_ast_stack_0.end()[-1]
        );
        self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
        self.m_ast_stack_0.push_back(res[0]);
        self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
        return 0;
    }
    static int r2(self_type & self)
    {
        // 'expr' = 'expr', '_implicit_1', 'mul';
        double res[1] = {};
        self.m_actions.a2(
            res[0],
            self.m_ast_stack_0.end()[-2],
            self.m_ast_stack_0.end()[-1]
        );
        self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
        self.m_ast_stack_0.push_back(res[0]);
        self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
        return 0;
    }
    static int r3(self_type & self)
    {
        // 'mul' = 'term';
        self.m_state_stack.erase(self.m_state_stack.end() - 1, self.m_state_stack.end());
        return 3;
    }
    static int r4(self_type & self)
    {
        // 'mul' = 'mul', '_implicit_2', 'term';
        double res[1] = {};
        self.m_actions.a4(
            res[0],
            self.m_ast_stack_0.end()[-2],
            self.m_ast_stack_0.end()[-1]
        );
        self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
        self.m_ast_stack_0.push_back(res[0]);
        self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
        return 3;
    }
    static int r5(self_type & self)
    {
        // 'mul' = 'mul', '_implicit_3', 'term';
        double res[1] = {};
        self.m_actions.a5(
            res[0],
            self.m_ast_stack_0.end()[-2],
            self.m_ast_stack_0.end()[-1]
        );
        self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 2, self.m_ast_stack_0.end());
        self.m_ast_stack_0.push_back(res[0]);
        self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
        return 3;
    }
    static int r6(self_type & self)
    {
        // 'term' = 'atom';
        self.m_state_stack.erase(self.m_state_stack.end() - 1, self.m_state_stack.end());
        return 1;
    }
    static int r7(self_type & self)
    {
        // 'term' = '_implicit_0', 'atom';
        self.m_state_stack.erase(self.m_state_stack.end() - 2, self.m_state_stack.end());
        return 1;
    }
    static int r8(self_type & self)
    {
        // 'term' = '_implicit_1', 'atom';
        double res[1] = {};
        self.m_actions.a8(
            res[0],
            self.m_ast_stack_0.end()[-1]
        );
        self.m_ast_stack_0.erase(self.m_ast_stack_0.end() - 1, self.m_ast_stack_0.end());
        self.m_ast_stack_0.push_back(res[0]);
        self.m_state_stack.erase(self.m_state_stack.end() - 2, self.m_state_stack.end());
        return 1;
    }
    static int r9(self_type & self)
    {
        // 'atom' = 'NUM';
        self.m_state_stack.erase(self.m_state_stack.end() - 1, self.m_state_stack.end());
        return 2;
    }
    static int r10(self_type & self)
    {
        // 'atom' = '_implicit_4', 'expr', '_implicit_5';
        self.m_state_stack.erase(self.m_state_stack.end() - 3, self.m_state_stack.end());
        return 2;
    }

    struct actions
    {
        void a0()
{}

void a1(double & E, double & E1, double & E2)
{ E = E1 + E2; }

void a2(double & E, double & E1, double & E2)
{ E = E1 - E2; }

void a3()
{}

void a4(double & E, double & E1, double & E2)
{ E = E1 * E2; }

void a5(double & E, double & E1, double & E2)
{ E = E1 / E2; }

void a6()
{}

void a7(double & A, double & E)
{}

void a8(double & A, double & E)
{ A = -E; }

void a9(double & A, double & B)
{}

void a10(double & A, double & E)
{}

    };

    std::vector<state_t> m_state_stack;
    std::vector<double> m_ast_stack_0;
    actions m_actions;
};

typedef basic_lexer<parser> lexer;

#endif // PARSER
