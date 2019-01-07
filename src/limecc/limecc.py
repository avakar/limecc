#!/usr/bin/env python

"""
This is the main script that accepts the grammar file and generates
the C++ header file containing the parser and potentially the lexer.
"""

from __future__ import print_function
from .lime_grammar import parse_lime_grammar, make_lime_parser, LimeGrammar, print_grammar_as_lime, LexerConflictError, LexLiteral
from .lrparser import ParsingError, InvalidGrammarError, ActionConflictError, make_lrparser, _extract_symbol
from .fa import minimize_enfa
import sys, os.path

def unbox_onetuples(*args):
    if len(args) == 1:
        return args[0]
    return args

def print_shift(tok):
    print('shift: {}'.format(tok))

def print_reduce(rule, ast):
    print('reduce: {} {}'.format(rule, ast))
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
        compiled = compile(g.user_include, '__main__', 'exec')
        eval(compiled, script_globs, script_globs)

    action_cache = {}
    def reducer(rule, ctx, *args):
        if rule.lime_action is not None:
            if rule.lime_action in action_cache:
                return action_cache[rule.lime_action](ctx, *args)
            lines = [' %s' % line for line in rule.lime_action.split('\n')]
            lines.insert(0, 'def _limecc_action(%s):' % ', '.join([name for name in rule.rhs_names if name]))

            compiled = compile('\n'.join(lines), '__main__', 'exec')
            eval(compiled, script_globs, script_globs)

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
