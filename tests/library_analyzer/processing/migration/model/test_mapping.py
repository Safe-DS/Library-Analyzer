from inspect import cleandoc

from library_analyzer.processing.api.model import API, Class, ClassDocumentation
from library_analyzer.processing.migration.model import (
    APIMapping,
    ManyToManyMapping,
    ManyToOneMapping,
    OneToManyMapping,
    OneToOneMapping,
    SimpleDiffer,
)


def test_one_to_one_mapping() -> None:
    apiv1 = API("test", "test", "1.0")
    apiv2 = API("test", "test", "2.0")
    class_1 = Class(
        id="test/test.Test",
        qname="Test",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("This is a test", "This is a test"),
        code="",
        instance_attributes=[],
    )
    apiv1.add_class(class_1)
    apiv2.add_class(class_1)
    differ = SimpleDiffer(
        None,
        [],
        apiv1,
        apiv2,
    )
    mappings = APIMapping(apiv1, apiv2, differ).map_api()

    assert len(mappings) == 1
    assert isinstance(mappings[0], OneToOneMapping)
    assert mappings[0].get_apiv1_elements() == mappings[0].get_apiv2_elements()
    assert mappings[0].get_apiv1_elements() == [class_1]


def test_one_to_many_and_many_to_one_mappings() -> None:
    apiv1, apiv2, class_1, class_2, class_3 = create_apis()
    differ = SimpleDiffer(
        None,
        [],
        apiv1,
        apiv2,
    )

    mappings = APIMapping(apiv1, apiv2, differ).map_api()
    assert len(mappings) == 1
    assert isinstance(mappings[0], OneToManyMapping)
    assert mappings[0].get_apiv1_elements()[0] == class_1
    assert len(mappings[0].get_apiv2_elements()) == 2
    assert mappings[0].get_apiv2_elements() == [class_2, class_3]

    apiv1, apiv2 = apiv2, apiv1
    differ = SimpleDiffer(
        None,
        [],
        apiv1,
        apiv2,
    )
    mappings = APIMapping(apiv1, apiv2, differ).map_api()
    assert len(mappings) == 1
    assert isinstance(mappings[0], ManyToOneMapping)
    assert len(mappings[0].get_apiv1_elements()) == 2
    assert sorted(mappings[0].get_apiv1_elements(), key=lambda class_: class_.id) == [class_2, class_3]  # type: ignore
    assert mappings[0].get_apiv2_elements()[0] == class_1


def test_many_to_many_mapping() -> None:
    apiv1, apiv2, class_1, class_2, class_3 = create_apis()
    class_4 = Class(
        id="test/test.TestC",
        qname="TestC",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("This is a test", "This is a test"),
        code="",
        instance_attributes=[],
    )
    apiv1.add_class(class_4)
    differ = SimpleDiffer(
        None,
        [],
        apiv1,
        apiv2,
    )
    mappings = APIMapping(apiv1, apiv2, differ).map_api()
    assert len(mappings) == 1
    assert isinstance(mappings[0], ManyToManyMapping)
    assert len(mappings[0].get_apiv1_elements()) == 2
    assert len(mappings[0].get_apiv2_elements()) == 2
    assert sorted(mappings[0].get_apiv1_elements(), key=lambda class_: class_.id) == [class_1, class_4]  # type: ignore
    assert mappings[0].get_apiv2_elements() == [class_2, class_3]


def test_too_different_mapping() -> None:
    apiv1 = API("test", "test", "1.0")
    class_1 = Class(
        id="test/test/Test",
        qname="Test",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("This is a test", "This is a test"),
        code="",
        instance_attributes=[],
    )
    apiv1.add_class(class_1)
    apiv2 = API("test", "test", "2.0")
    class_2 = Class(
        id="test/package/NotSimilarClass_",
        qname="NotSimilarClass_",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("not similar to the other class", "not similar to the other class"),
        code=cleandoc(
            """

        class NotSimilarClass:
            self.i = 5

            self.d = 12.01

            self.x = "s"

            self.f = ""

            pass

        """,
        ),
        instance_attributes=[],
    )
    apiv2.add_class(class_2)
    differ = SimpleDiffer(
        None,
        [],
        apiv1,
        apiv2,
    )
    api_mapping = APIMapping(apiv1, apiv2, differ)
    mappings = api_mapping.map_api()
    assert (
        differ.compute_class_similarity(class_1, class_2) < api_mapping.threshold_of_similarity_for_creation_of_mappings
    )
    assert len(mappings) == 0


def create_apis() -> tuple[API, API, Class, Class, Class]:
    class_1 = Class(
        id="test/test.Test",
        qname="Test",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("This is a test", "This is a test"),
        code="",
        instance_attributes=[],
    )
    apiv1 = API("test", "test", "1.0")
    apiv1.add_class(class_1)
    class_2 = Class(
        id="test/test.TestA",
        qname="TestA",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("This is a test", "This is a test"),
        code="",
        instance_attributes=[],
    )
    class_3 = Class(
        id="test/test.TestB",
        qname="TestB",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        documentation=ClassDocumentation("This is a test", "This is a test"),
        code="",
        instance_attributes=[],
    )
    apiv2 = API("test", "test", "2.0")
    apiv2.add_class(class_2)
    apiv2.add_class(class_3)
    return apiv1, apiv2, class_1, class_2, class_3
