#!/usr/bin/env python

"""
This is the main script that accepts the grammar file and generates
the C++ header file containing the parser and potentially the lexer.
"""

from lime_grammar import parse_lime_grammar, make_lime_parser, LimeGrammar, print_grammar_as_lime, LexerConflictError
from lrparser import InvalidGrammarError, ActionConflictError
from fa import minimize_enfa
import sys, os.path

def print_shift(tok):
    print 'shift:', tok

def print_reduce(rule, ast):
    print 'reduce:', rule

def _main():
    from optparse import OptionParser
    opts = OptionParser(
        usage='usage: %prog [options] filename')
    opts.add_option('-o', '--output', help='The file to store the generated parser/lexer to')
    opts.add_option('-p', '--parse', help='Parse the text and print its AST')
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
ID ~= {[a-zA-Z0-9_\\-]+}.
QL ~= <a single- or double- quoted literal>.
SNIPPET ~= <an arbitrary text enclosed in braces>.
"""
        print_grammar_as_lime(LimeGrammar.grammar, translate=_convert)

    for fname in args:
        output = options.output or os.path.splitext(fname)[0] + '.hpp'
        with open(fname, 'r') as fin:
            input = fin.read()

        try:
            g = parse_lime_grammar(input, filename=fname)
            p = make_lime_parser(g, keep_states=options.print_states)

            #if not options.no_tests:
            #    for test in g.tests:
            #        print test

            if options.print_dfas:
                for lhs, rhs, fa in p.lex_dfas:
                    print lhs, rhs
                    minimize_enfa(fa).print_graph()
                    print ''
                p.lexer.print_graph()

            if options.print_states:
                for i, state in enumerate(p.states):
                    print "0x%x(%d):" % (i, i)
                    print state

            if options.parse:
                print p.lexparse(options.parse, shift_visitor=print_shift, postreduce_visitor=print_reduce)

            if (not options.tests_only and not options.print_dfas and not options.print_states and not options.parse) or options.output:
                from lime_cpp import lime_cpp
                with open(output, 'w') as fout:
                    fout.write(lime_cpp(p))

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
