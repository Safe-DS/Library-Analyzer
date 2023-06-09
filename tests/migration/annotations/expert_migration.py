from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    EnumReviewResult,
    ExpertAnnotation,
    TodoAnnotation,
)
from library_analyzer.processing.api.model import (
    Class,
    ClassDocstring,
    Function,
    FunctionDocstring,
    Parameter,
    ParameterAssignment,
    ParameterDocstring,
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


def migrate_expert_annotation_data__function() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    functionv1 = Function(
        id="test/test.expert.test1.test/test",
        qname="test.expert.test1.test.test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    functionv2 = Function(
        id="test/test.expert.test1.test/new_test",
        qname="test.expert.test1.test.new_test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    mapping = OneToOneMapping(1.0, functionv1, functionv2)

    annotationv1 = ExpertAnnotation(
        target="test/test.expert.test1.test/test",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2 = ExpertAnnotation(
        target="test/test.expert.test1.test/new_test",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    return mapping, annotationv1, [annotationv2]


def migrate_expert_annotation_data__class() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    classv1 = Class(
        id="test/test.expert.test2.test/ExpertTestClass",
        qname="test.expert.test2.test.ExpertTestClass",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        docstring=ClassDocstring(),
        code="class ExpertTestClass:\n    pass",
        instance_attributes=[],
    )
    classv2 = Class(
        id="test/test.expert.test2.test/NewExpertTestClass",
        qname="test.expert.test2.test.NewExpertTestClass",
        decorators=[],
        superclasses=[],
        is_public=True,
        reexported_by=[],
        docstring=ClassDocstring(),
        code="class NewExpertTestClass:\n    pass",
        instance_attributes=[],
    )
    functionv2 = Function(
        id="test/test.expert.test2.test/test",
        qname="test.expert.test2.test.test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    mapping = OneToManyMapping(1.0, classv1, [classv2, functionv2])

    annotationv1 = ExpertAnnotation(
        target="test/test.expert.test2.test/ExpertTestClass",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2 = ExpertAnnotation(
        target="test/test.expert.test2.test/NewExpertTestClass",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2_function = TodoAnnotation(
        target="test/test.expert.test2.test/test",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        newTodo=get_migration_text(annotationv1, mapping, for_todo_annotation=True),
    )
    return mapping, annotationv1, [annotationv2, annotationv2_function]


def migrate_expert_annotation_data__parameter() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    parameterv1 = Parameter(
        id_="test/test.expert/test3/testA",
        name="testA",
        qname="test.expert.test3.testA",
        default_value="'this is a string'",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        docstring=ParameterDocstring("str", "this is a string", ""),
    )
    parameterv2 = Parameter(
        id_="test/test.expert/test3/testB",
        name="testB",
        qname="test.expert.test3.testB",
        default_value="'test string'",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        docstring=ParameterDocstring("str", "'test string'", ""),
    )
    mapping = OneToOneMapping(1.0, parameterv1, parameterv2)
    annotationv1 = ExpertAnnotation(
        target="test/test.expert/test3/testA",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2 = ExpertAnnotation(
        target="test/test.expert/test3/testB",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    return mapping, annotationv1, [annotationv2]


def migrate_expert_annotation_data_duplicated() -> (
    tuple[
        Mapping,
        list[AbstractAnnotation],
        list[AbstractAnnotation],
    ]
):
    functionv1 = Function(
        id="test/test.expert.duplicate.test/test",
        qname="test.expert.duplicate.test.test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )
    functionv1_2 = Function(
        id="test/test.expert.duplicate.test/test_2",
        qname="test.expert.duplicate.test.test_2",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    functionv2 = Function(
        id="test/test.expert.duplicate.test/new_test",
        qname="test.expert.duplicate.test.new_test",
        decorators=[],
        parameters=[],
        results=[],
        is_public=True,
        reexported_by=[],
        docstring=FunctionDocstring(),
        code="",
    )

    mapping = ManyToOneMapping(1.0, [functionv1, functionv1_2], functionv2)

    annotationv1 = ExpertAnnotation(
        target="test/test.expert.duplicate.test/test",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv1_2 = ExpertAnnotation(
        target="test/test.expert.duplicate.test/test_2",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    annotationv2 = ExpertAnnotation(
        target="test/test.expert.duplicate.test/new_test",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
    )
    return mapping, [annotationv1, annotationv1_2], [annotationv2]
