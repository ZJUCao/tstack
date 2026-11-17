# What a good output does

Each output is a mock of a feature's interfaces in Python: signatures with full doc comments,
whose bodies only raise `NotImplementedError`. A mock note is a sentence about what the mock does
or leaves out, such as "The mock leaves out the constructor's checks." The rest of a doc comment
describes the full behavior that the implementation will have.

1. No doc comment says, as a fact of the mock, that a class or function sorts, checks, or
   converts its values, or raises an error other than `NotImplementedError`. Such a sentence
   passes when it is plainly about the implementation ("The implementation ...", or a Raises
   entry), or when a mock note in the same doc comment says that the mock leaves it out. Other
   sentences about the full behavior, such as what the attributes hold, what the constructor
   sets, or what `str()` gives, are not graded by this criterion. Fail, and quote the sentence,
   when a doc comment states a sort, a check, a conversion, or such an error as a fact with
   nothing that says the mock leaves it out.
2. Every mock note is a paragraph of its own, and whatever it points at exists in the same doc
   comment. Fail, and quote it, when a mock note ends or sits inside a paragraph that describes
   the full behavior, or points at something the doc comment does not have, such as "by this
   table" with no table.
3. Every function, method, and class that the diff adds has a doc comment that names its
   arguments, its return value or attributes, and the errors of the full behavior. Fail when one
   has no doc comment, or when a Raises section lists only `NotImplementedError` where the
   description gives other errors.
