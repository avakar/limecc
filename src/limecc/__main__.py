from .lime_grammar import parse_lime_grammar, make_lime_parser, LimeGrammar, print_grammar_as_lime, LexerConflictError, LexLiteral
from .lrparser import ParsingError, InvalidGrammarError, ActionConflictError, make_lrparser, _extract_symbol
from .fa import minimize_enfa
import sys, os.path

def _main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument('-o', '--output', help='The file to store the generated parser/lexer to')
    ap.add_argument('-p', '--parse', help='Parse the text and print its AST')
    ap.add_argument('-E', '--execute', help='Execute semantic actions (in Python)')
    ap.add_argument('--print-dfas', action="store_true", help='Show the states of the lexer\'s DFA')
    ap.add_argument('--print-states', action="store_true", help='Show the states of the LR automaton')
    ap.add_argument('--print-lime-grammar', action="store_true", help='Prints the grammar of the lime language')
    ap.add_argument('--no-tests', action="store_true", help='Do not run tests')
    ap.add_argument('--tests-only', action="store_true", help='Do not generate the parser, only run tests')
    ap.add_argument('filename', nargs='+')
    args = ap.parse_args()

    if args.output and len(args.filename) != 1:
        print('error: only one source file can be passed if -o is given', file=sys.stderr)
        return 1

    if args.print_lime_grammar:
        def _convert(sym):
            if sym.startswith('kw_'):
                return '"%%%s"' % sym[3:]
        print("""\
ID ::= {[a-zA-Z0-9_\\-]+}.
QL ::= <a single- or double- quoted literal>.
SNIPPET ::= <an arbitrary text enclosed in braces>.
""")
        print_grammar_as_lime(LimeGrammar.grammar, translate=_convert)

    for fname in args.filename:
        output = args.output or os.path.splitext(fname)[0] + '.hpp'
        with open(fname, 'r') as fin:
            input = fin.read()

        try:
            g = parse_lime_grammar(input, filename=fname)
            p = make_lime_parser(g, keep_states=args.print_states)

            if not args.no_tests:
                def partial_lex(sentential_form):
                    for sym in sentential_form:
                        if isinstance(sym, LexLiteral):
                            for tok in _LimeLexer(p.lexers[0]).tokens(sym.literal, sym.pos):
                                if _extract_symbol(tok) != p.discard_id:
                                    yield tok
                        else:
                            yield sym

                for pattern, text, pos in g.tests:
                    test_parser = make_lrparser(g, root=pattern, sentential_forms=True)
                    try:
                        test_parser.parse(partial_lex(text))
                    except ParsingError as e:
                        print(ParsingError('test failed: %s' % e, pos).format())

            if args.print_dfas:
                for token_id, fa in enumerate(p.lex_dfas):
                    print('{} {}'.format(token_id, (p.grammar.tokens[token_id] if token_id < len(p.grammar.tokens) else '%discard')))
                    minimize_enfa(fa).print_graph()
                    print('')
                for i, lexer in enumerate(p.lexers):
                    print('lexer {}'.format(i))
                    lexer.print_graph()
                    print('')

            if args.print_states:
                def sym_trans(sym):
                    return str(p.grammar.tokens[sym]) if isinstance(sym, int) else str(sym)

                def lookahead_trans(la):
                    return '(' + ', '.join(sym_trans(sym) for sym in la) + ')'

                for i, state in enumerate(p.states):
                    print("0x%x(%d):" % (i, i))
                    print(state.print_state(sym_trans))
                    for sym, next_state_id in sorted(state.goto.iteritems()):
                        print('goto %d(0x%x) over %s' % (next_state_id, next_state_id, sym_trans(sym)))
                    for la, action in sorted(state.action.iteritems()):
                        print('action at %s: %s' % (lookahead_trans(la), repr(action)))

            if args.parse:
                with open(args.parse, 'rb') as fin:
                    print(p.lexparse(fin.read(), shift_visitor=print_shift, postreduce_visitor=print_reduce))

            if args.execute:
                with open(args.execute, 'rb') as fin:
                    print(execute(p, fin))

            if (not args.tests_only and not args.print_dfas and not args.print_states and not args.parse and not args.execute) or args.output:
                from .lime_cpp import lime_cpp
                with open(output, 'w') as fout:
                    fout.write(lime_cpp(p))

        except ParsingError as e:
            print(e)
            return 1
        except LexerConflictError as e:
            print(e)
            return 1
        except ActionConflictError as e:
            print(e)
            e.print_trace()
            return 1

if __name__ == '__main__':
    sys.exit(_main())
