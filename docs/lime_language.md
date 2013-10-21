The Lime Language
=================

The Lime language is used to define terminal and non-terminal symbols, their types and associated semantic actions.

Lime tokens
-----------

Comments start with the hash symbol `#`, and extend up to the end of the line. There is no support for block comments.

All comments are discarded and behave as if they were replaced by a single space character.

    # This is a comment

Snippets are arbitrary blocks of text used to embed code, types or other textual chunks in the Lime grammar. Snippets start with a sequence of consecutive opening brace `{` characters and end with the same number of consecutive closing brace characters `}`. Usually, snippets are braced by a single brace on either side, unless the snippet itself contains unpaired braces.

Leading and trailing whitespace is trimmed from snippets.

    {} # An empty snippet
    {[0-9]+} # A snippet containing a regular expression
    { [0-9]+ } # The same snippet as above

Strings are runs of text enclosed in single or double quotes. There is no support for escaping for now.

    "This is a string."
    'And so is this.'

Identifiers are used for symbols and optionally for their names. They can contain letters, numbers, underscores and dashes. Do not start identifiers with numbers or dashes.
