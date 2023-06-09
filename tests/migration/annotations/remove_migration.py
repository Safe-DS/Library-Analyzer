from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    RemoveAnnotation,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import (
    Class,
    ClassDocstring,
    Function,
    FunctionDocstring,
)
from library_analyzer.processing.migration.annotations import (
    get_migration_text,
    migration_author,
)
from library_analyzer.processing.migration.model import (
    ManyToOneMapping,
    Mapping,
    OneToManyMapping,
    OneToOneMapping,
)


def migrate_remove_annotation_data_one_to_one_mapping() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    functionv1 = Function(
        id="test/test.remove.test1.test/test",
        qname="test.remove.test1.test.test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    functionv2 = Function(
        id="test/test.remove.test1.test/new_test",
        qname="test.remove.test1.test.new_test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    mapping = OneToOneMapping(1.0, functionv1, functionv2)

    annotationv1 = RemoveAnnotation(
        target="test/test.remove.test1.test/test",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2 = RemoveAnnotation(
        target="test/test.remove.test1.test/new_test",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    return mapping, annotationv1, [annotationv2]


def migrate_remove_annotation_data_one_to_many_mapping() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    classv1 = Class(
        id="test/test.remove.test2.test/RemoveTestClass",
        qname="test.remove.test2.test.RemoveTestClass",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        docstring=ClassDocstring(),
        code="class RemoveTestClass:\n    pass",
        instance_attributes=[],
    )
    classv2_a = Class(
        id="test/test.remove.test2.test/NewRemoveTestClass",
        qname="test.remove.test2.test.NewRemoveTestClass",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        docstring=ClassDocstring(),
        code="class NewRemoveTestClass:\n    pass",
        instance_attributes=[],
    )
    classv2_b = Class(
        id="test/test.remove.test2.test/NewRemoveTestClass2",
        qname="test.remove.test2.test.NewRemoveTestClass2",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        docstring=ClassDocstring(),
        code="class NewRemoveTestClass2:\n    pass",
        instance_attributes=[],
    )
    functionv2 = Function(
        id="test/test.remove.test2.test/TestClass/new_test",
        qname="test.remove.test2.test.TestClass.new_test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    mapping = OneToManyMapping(1.0, classv1, [classv2_a, classv2_b, functionv2])

    annotationv1 = RemoveAnnotation(
        target="test/test.remove.test2.test/RemoveTestClass",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2_a = RemoveAnnotation(
        target="test/test.remove.test2.test/NewRemoveTestClass",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2_b = RemoveAnnotation(
        target="test/test.remove.test2.test/NewRemoveTestClass2",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2_c = TodoAnnotation(
        target="test/test.remove.test2.test/TestClass/new_test",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        newTodo=get_migration_text(annotationv1, mapping, for_todo_annotation=True),
    )
    return mapping, annotationv1, [annotationv2_a, annotationv2_b, annotationv2_c]


def migrate_remove_annotation_data_duplicated() -> (
    tuple[
        Mapping,
        list[AbstractAnnotation],
        list[AbstractAnnotation],
    ]
):
    functionv1 = Function(
        id="test/test.remove.duplicate.test/test",
        qname="test.remove.duplicate.test.test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )
    functionv1_2 = Function(
        id="test/test.remove.duplicate.test/test_2",
        qname="test.remove.duplicate.test.test_2",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    functionv2 = Function(
        id="test/test.remove.duplicate.test/new_test",
        qname="test.remove.duplicate.test.new_test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    mapping = ManyToOneMapping(1.0, [functionv1, functionv1_2], functionv2)

    annotationv1 = RemoveAnnotation(
        target="test/test.remove.duplicate.test/test",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv1_2 = RemoveAnnotation(
        target="test/test.remove.duplicate.test/test_2",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2 = RemoveAnnotation(
        target="test/test.remove.duplicate.test/new_test",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    return mapping, [annotationv1, annotationv1_2], [annotationv2]
