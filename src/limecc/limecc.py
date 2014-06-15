#!/usr/bin/env python

"""
This is the main script that accepts the grammar file and generates
the C++ header file containing the parser and potentially the lexer.
"""

from lime_grammar import parse_lime_grammar, make_lime_parser, LimeGrammar, print_grammar_as_lime, LexerConflictError, LexLiteral
from lrparser import ParsingError, InvalidGrammarError, ActionConflictError, make_lrparser, _extract_symbol
from fa import minimize_enfa
from rule import unbox_onetuples
import sys, os.path

def print_shift(tok):
    print 'shift:', tok

def print_reduce(rule, ast):
    print 'reduce:', rule, ast
    return ast

def make_parser(parser_spec, filename=None):
    if parser_spec is None and filename:
        parser_spec = open(filename, 'rb')

    if hasattr(parser_spec, 'read'):
        parser_spec = parser_spec.read()

    if isinstance(parser_spec, str):
        g = parse_lime_grammar(parser_spec, filename=filename)
        return make_lime_parser(g)
    else:
        return parser_spec

def execute(parser, text, filename=None, debug=False):
    if hasattr(text, 'read'):
        text = text.read()

    p = make_parser(parser, filename=filename)
    g = p.grammar

    script_globs = {}
    if g.user_include:
        exec g.user_include in script_globs, script_globs

    action_cache = {}
    def reducer(rule, ctx, *args):
        if rule.lime_action is not None:
            if rule.lime_action in action_cache:
                return action_cache[rule.lime_action](ctx, *args)
            lines = [' %s' % line for line in rule.lime_action.split('\n')]
            lines.insert(0, 'def _limecc_action(%s):' % ', '.join([name for name in rule.rhs_names if name]))
            exec '\n'.join(lines) in script_globs, script_globs

            fn = script_globs['_limecc_action']
            fnargs = [arg for arg, name in zip(args, rule.rhs_names) if name is not None]
            return fn(*fnargs)
        else:
            return unbox_onetuples(*args)

    if debug:
        return p.lexparse(text, reducer=reducer, token_filter=script_globs.get('token_filter'), filename=filename,
            shift_visitor=print_shift, postreduce_visitor=print_reduce)
    else:
        return p.lexparse(text, reducer=reducer, token_filter=script_globs.get('token_filter'), filename=filename)

def _main():
    from optparse import OptionParser
    opts = OptionParser(
        usage='usage: %prog [options] filename')
    opts.add_option('-o', '--output', help='The file to store the generated parser/lexer to')
    opts.add_option('-p', '--parse', help='Parse the text and print its AST')
    opts.add_option('-E', '--execute', help='Execute semantic actions (in Python)')
    opts.add_option('--print-dfas', action="store_true", default=False, help='Show the states of the lexer\'s DFA')
    opts.add_option('--print-states', action="store_true", dest="print_states", default=False, help='Show the states of the LR automaton')
    opts.add_option('--print-lime-grammar', action="store_true", dest="print_lime_grammar", default=False, help='Prints the grammar of the lime language')
    opts.add_option('--no-tests', action="store_true", default=False, help='Do not run tests')
    opts.add_option('--tests-only', action="store_true", default=False, help='Do not generate the parser, only run tests')

    if len(sys.argv) < 2:
        opts.print_help()
        return 0

    (options, args) = opts.parse_args()

    if options.output and len(args) != 1:
        print >>sys.stderr, 'error: only one source file can be passed if -o is given'
        return 1

    if options.print_lime_grammar:
        def _convert(sym):
            if sym.startswith('kw_'):
                return '"%%%s"' % sym[3:]
        print """\
ID ::= {[a-zA-Z0-9_\\-]+}.
QL ::= <a single- or double- quoted literal>.
SNIPPET ::= <an arbitrary text enclosed in braces>.
"""
        print_grammar_as_lime(LimeGrammar.grammar, translate=_convert)

    for fname in args:
        output = options.output or os.path.splitext(fname)[0] + '.hpp'
        with open(fname, 'r') as fin:
            input = fin.read()

        try:
            g = parse_lime_grammar(input, filename=fname)
            p = make_lime_parser(g, keep_states=options.print_states)

            if not options.no_tests:
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
                    except ParsingError, e:
                        print ParsingError('test failed: %s' % e.message, pos).format()

            if options.print_dfas:
                for token_id, fa in enumerate(p.lex_dfas):
                    print token_id, (p.grammar.tokens[token_id] if token_id < len(p.grammar.tokens) else '%discard')
                    minimize_enfa(fa).print_graph()
                    print ''
                for i, lexer in enumerate(p.lexers):
                    print 'lexer', i
                    lexer.print_graph()
                    print ''

            if options.print_states:
                def sym_trans(sym):
                    return str(p.grammar.tokens[sym]) if isinstance(sym, int) else str(sym)

                def lookahead_trans(la):
                    return '(' + ', '.join(sym_trans(sym) for sym in la) + ')'

                for i, state in enumerate(p.states):
                    print "0x%x(%d):" % (i, i)
                    print state.print_state(sym_trans)
                    for sym, next_state_id in sorted(state.goto.iteritems()):
                        print 'goto %d(0x%x) over %s' % (next_state_id, next_state_id, sym_trans(sym))
                    for la, action in sorted(state.action.iteritems()):
                        print 'action at %s: %s' % (lookahead_trans(la), repr(action))

            if options.parse:
                with open(options.parse, 'rb') as fin:
                    print p.lexparse(fin.read(), shift_visitor=print_shift, postreduce_visitor=print_reduce)

            if options.execute:
                with open(options.execute, 'rb') as fin:
                    print execute(p, fin)

            if (not options.tests_only and not options.print_dfas and not options.print_states and not options.parse and not options.execute) or options.output:
                from lime_cpp import lime_cpp
                with open(output, 'w') as fout:
                    fout.write(lime_cpp(p))

        except ParsingError, e:
            print str(e)
            return 1
        except LexerConflictError, e:
            print e.message
            return 1
        except ActionConflictError, e:
            print e.message
            e.print_trace()
            return 1
        except Exception, e:
            import traceback
            traceback.print_exc(sys.stderr)
            return 1

if __name__ == '__main__':
    sys.exit(_main())
