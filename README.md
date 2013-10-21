The limecc parser generator
===========================

limecc is a lexer and parser generator similar to other tools like cyacc, bison and especially [lemon][1] from which limecc sources inspiration. Grammars are written in a language called Lime, which describes lexical tokens, grammar productions, and sematic actions. The generator produces C++ code for the corresponding lexer and parser.

Installation
------------

Since limecc is written in pure Python, you can just simply fetch it from PyPI.

    easy_install limecc

Usage example
-------------

The Lime language was designed to be concise, yet self-descriptive. The following grammar description produces a simple calculator.

    WS :: discard
    WS ~= {\s+}
    NUM :: {double}
    NUM ~= {[0-9]+}(x) { return atoi(x.c_str()); }

    expr :: {double}
    expr ::= mul.
    expr(E) ::= expr(E1) "+" mul(E2). { E = E1 + E2; }
    expr(E) ::= expr(E1) "-" mul(E2). { E = E1 - E2; }

    mul :: {double}
    mul ::= term.
    mul(E) ::= mul(E1) "*" term(E2). { E = E1 * E2; }
    mul(E) ::= mul(E1) "/" term(E2). { E = E1 / E2; }

    term :: {double}
    term ::= atom.
    term ::= "+" atom.
    term(A) ::= "-" atom(E). { A = -E; }

    atom :: {double}
    atom ::= NUM.
    atom(A) ::= "(" expr(E) ")".

Lexical tokens -- ofter referred to as the terminals symbols -- can be defined in one of two ways: using the `~=` operator with a regular expression, or with a quoted string literal.

All symbols have types. The `WS` terminals have the special type of `discard`, which causes the lexer to throw them away. Such tokens cannot appear in a syntactic production as they are invisible to the parser. The terminal `NUM` has the C++ type `double`. The semantic action associated with the terminal converts the textual representation of the token to its numeric form. Quoted literals have the special type of `void`, which allows them to appear in the grammar, but makes them invisible to the semantic actions.

Semantic actions that are attached to production rules can refer to values of right-hand-side symbols using their name. Having names for symbols make the actions easier to read and understand.

Semantic actions can be omitted if exactly one right-hand-side symbol has a non-void type. In such case, reducing the rule will propagate that symbol's value to the left-hand-side symbol. For instance, the production `term ::= atom.` is equivalent to the production `term(A) ::= atom(B). { A = B; }`.

The first symbol on the left-hand-side of a production rule is considered the root of the grammar; in this case it the symbol `expr`.

You can compile the above grammar as follows.

    limecc calc.y

This command will produce `calc.hpp`, a C++ file the `parser` class. Use the class as follows.

    #include "calc.hpp"
    #include <iostream>
    #include <string>

    int main()
    {
        std::string line;
        while (std::getline(std::cin, line))
        {
            try
            {
                parser p;
                p.push_data(line.data(), line.data() + line.size());
                std::cout << p.finish() << "\n";
            }
            catch (...)
            {
                std::cerr << "error: Invalid syntax.\n";
            }
        }
    }

  [1]: http://www.sqlite.org/src/doc/trunk/doc/lemon.html
  [2]: ./docs/grammar.md
