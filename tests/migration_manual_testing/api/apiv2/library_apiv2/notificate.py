from .persons import Person

# apiv2: rename package to notification and use person instead of name and address


def send_message_to_person(person: Person, message: str) -> None:
    """Send a message to a person.

    Parameters
    ----------
    person : Person
    message : str
    """
    print("To: " + person.get_name() + "\n" + person.address + "\n" + message)  # noqa: T201
