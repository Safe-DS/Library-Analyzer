import inspect

import astroid


def get_full_docstring(declaration: astroid.ClassDef | astroid.FunctionDef) -> str:
    """
    Return the full docstring of the given declaration.

    Indentation is cleaned up. If no docstring is available, an empty string is returned.
    """
    doc_node = declaration.doc_node
    if doc_node is None:
        return ""
    return inspect.cleandoc(doc_node.value)
