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
