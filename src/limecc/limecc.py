#!/usr/bin/env python

"""
This is the main script that accepts the grammar file and generates
the C++ header file containing the parser and potentially the lexer.
"""

from lime_grammar import parse_lime_grammar, make_lime_parser
from lrparser import InvalidGrammarError, ActionConflictError

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
    opts.add_option('--print-states', action="store_true", dest="print_states", default=False, help='The file to store the generated parser/lexer to')
    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error('exactly one filename must be specified')

    fname = args[0]

    import sys
    import os.path
    if not options.output:
        options.output = os.path.splitext(fname)[0] + '.hpp'

    fname = os.path.abspath(fname)
    input = open(fname, 'r').read()

    try:
        g = parse_lime_grammar(input, filename=fname)
        p = make_lime_parser(g, keep_states=options.print_states)

        if options.print_states:
            for i, state in enumerate(p.states):
                print "0x%x(%d):" % (i, i)
                print state

        if not options.parse:
            from lime_cpp import lime_cpp
            open(options.output, 'w').write(lime_cpp(p))
        else:
            print p.lexparse(options.parse, shift_visitor=print_shift, postreduce_visitor=print_reduce)
    except ActionConflictError, e:
        print e
        print 'Counter-example:', ', '.join((str(sym) for sym in e.counterexample()))
        return 1
    except Exception, e:
        print >>sys.stderr, '%s(%d): error : %s' % (fname, line, msg)
        import traceback
        traceback.print_exc(sys.stderr)
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(_main())
