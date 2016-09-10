def load_tests(loader, tests, ignore):
    import doctest

    import limecc.fa
    import limecc.first
    import limecc.grammar
    import limecc.lime_grammar
    import limecc.lrparser
    import limecc.regex_parser
    import limecc.rule

    tests.addTests(doctest.DocTestSuite(limecc.fa))
    tests.addTests(doctest.DocTestSuite(limecc.first))
    tests.addTests(doctest.DocTestSuite(limecc.grammar))
    tests.addTests(doctest.DocTestSuite(limecc.lime_grammar))
    #tests.addTests(doctest.DocTestSuite(limecc.lrparser))
    tests.addTests(doctest.DocTestSuite(limecc.regex_parser))
    tests.addTests(doctest.DocTestSuite(limecc.rule))

    return tests

if __name__ == '__main__':
    import unittest
    unittest.main()
