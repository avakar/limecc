def load_tests(loader, tests, ignore):
    import doctest
    from .. import fa, first, grammar, lime_grammar, lrparser, regex_parser, rule

    tests.addTests(doctest.DocTestSuite(fa))
    tests.addTests(doctest.DocTestSuite(first))
    tests.addTests(doctest.DocTestSuite(grammar))
    tests.addTests(doctest.DocTestSuite(lime_grammar))
    #tests.addTests(doctest.DocTestSuite(limecc.lrparser))
    tests.addTests(doctest.DocTestSuite(regex_parser))
    tests.addTests(doctest.DocTestSuite(rule))

    return tests

if __name__ == '__main__':
    import unittest
    unittest.main()
