import spacy


def load_language(name: str) -> spacy.Language:
    """
    Safely load a Spacy language model.

    Parameters
    ----------
    name: str
        The name of the language model to load.

    Returns
    -------
    spacy.Language
        The loaded language model.
    """
    try:
        return spacy.load(name)
    except OSError:
        spacy.cli.download(name)
        return spacy.load(name)
