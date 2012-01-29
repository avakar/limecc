def make_lime_parser(g):
    from lrparser import Parser
    p = Parser(g)

    from dfa import make_dfa_from_literal
    from regex_parser import (make_multi_dfa, minimize_enfa,
        regex_parser, make_enfa_from_regex)
    from lime_grammar import LexRegex

    fas = []
    for i, lex_rule in enumerate(g.lex_rules):
        (lhs, lhs_name), (rhs, rhs_name), action = lex_rule
        if isinstance(rhs, LexRegex):
            g2 = regex_parser(rhs.regex)
            fa = make_enfa_from_regex(g2, i)
        else:
            fa = make_dfa_from_literal(rhs.literal, i)
        fas.append(fa)
    dfa = make_multi_dfa(fas)
    dfa = minimize_enfa(dfa)
    p.lexer = dfa
    return p
