"""
This is the main script that accepts the grammar file and generates
the C++ header file containing the parser and potentially the lexer.
"""

def _main(options, fname):
    import os.path
    if not options.output:
        options.output = os.path.splitext(fname)[0] + '.hpp'

    input = open(fname, 'r').read()

    import sys
    def _error(msg, line=1):
        print >>sys.stderr, '%s(%d): error : %s' % (fname, line, msg)

    try:
        from lime_grammar import parse_lime_grammar
        g = parse_lime_grammar(input)

        from lime_parser import make_lime_parser
        from lrparser import InvalidGrammarError
        p = make_lime_parser(g)

        from lime_cpp import lime_cpp
        open(options.output, 'w').write(lime_cpp(p))
    except Exception, e:
        _error(e)
        import traceback
        traceback.print_exc(sys.stderr)
        return 1

if __name__ == '__main__':
    from optparse import OptionParser
    opts = OptionParser(
        usage='usage: %prog [options] filename)')
    opts.add_option('-o', '--output', help='The file to store the generated parser/lexer to')
    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error('exactly one filename must be specified')

    import sys
    sys.exit(_main(options, args[0]))
