from library_analyzer.processing.annotations.model import (
    AbstractAnnotation,
    BoundaryAnnotation,
    EnumReviewResult,
    Interval,
)
from library_analyzer.processing.api.model import (
    Parameter,
    ParameterAssignment,
    ParameterDocumentation,
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


def migrate_boundary_annotation_data_one_to_one_mapping() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    parameterv1 = Parameter(
        id_="test/test.boundary.test1.testA",
        name="testA",
        qname="test.boundary.test1.testA",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", ""),
    )
    parameterv2 = Parameter(
        id_="test/test.boundary.test1.testB",
        name="testB",
        qname="test.boundary.test1.testB",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", ""),
    )
    boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test1.testA",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    migrated_boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test1.testB",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    return (
        OneToOneMapping(1.0, parameterv1, parameterv2),
        boundary_annotation,
        [migrated_boundary_annotation],
    )


def migrate_boundary_annotation_data_one_to_one_mapping_int_to_float() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    parameterv1 = Parameter(
        id_="test/test.boundary.test2.testA",
        name="testA",
        qname="test.boundary.test2.testA",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", "int in the range of (0, 10)"),
    )
    parameterv2 = Parameter(
        id_="test/test.boundary.test2.testB",
        name="testB",
        qname="test.boundary.test2.testB",
        default_value="1.0",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("float", "1.0", "float in the range of [1.0, 9.0]"),
    )

    mapping = OneToOneMapping(1.0, parameterv1, parameterv2)

    boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test2.testA",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=0,
            upperIntervalLimit=10,
            upperLimitType=0,
            isDiscrete=True,
        ),
    )
    migrated_boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test2.testB",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment=get_migration_text(boundary_annotation, mapping),
        reviewResult=EnumReviewResult.UNSURE,
        interval=Interval(
            lowerIntervalLimit=0.0,
            lowerLimitType=0,
            upperIntervalLimit=10.0,
            upperLimitType=0,
            isDiscrete=False,
        ),
    )

    return (
        mapping,
        boundary_annotation,
        [migrated_boundary_annotation],
    )


def migrate_boundary_annotation_data_one_to_one_mapping_float_to_int() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    parameterv1 = Parameter(
        id_="test/test.boundary.test3.testA",
        name="testA",
        qname="test.boundary.test3.testA",
        default_value="1.0",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("float", "1.0", "float in the range of [0.5, 9.5]"),
    )
    parameterv2 = Parameter(
        id_="test/test.boundary.test3.testB",
        name="testB",
        qname="test.boundary.test3.testB",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", "int in the range of (0, 10)"),
    )

    mapping = OneToOneMapping(1.0, parameterv1, parameterv2)

    boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test3.testA",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0.5,
            lowerLimitType=0,
            upperIntervalLimit=9.5,
            upperLimitType=0,
            isDiscrete=False,
        ),
    )
    migrated_boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test3.testB",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment=get_migration_text(boundary_annotation, mapping),
        reviewResult=EnumReviewResult.UNSURE,
        interval=Interval(
            lowerIntervalLimit=1,
            lowerLimitType=1,
            upperIntervalLimit=9,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    return (
        mapping,
        boundary_annotation,
        [migrated_boundary_annotation],
    )


def migrate_boundary_annotation_data_one_to_many_mapping() -> (
    tuple[
        Mapping,
        AbstractAnnotation,
        list[AbstractAnnotation],
    ]
):
    parameterv1 = Parameter(
        id_="test/test.boundary.test4.testv1",
        name="testA",
        qname="test.boundary.test4.testv1",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", "int in the range of (0, 10)"),
    )
    parameterv2_a = Parameter(
        id_="test/test.boundary.test4.testA",
        name="testA",
        qname="test.boundary.test4.testA",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", "int in the range of (0, 10)"),
    )
    parameterv2_b = Parameter(
        id_="test/test.boundary.test4.testB",
        name="testB",
        qname="test.boundary.test4.testB",
        default_value="1.0",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("float", "1.0", "float in the range of (0.0, 10.0)"),
    )
    parameterv2_c = Parameter(
        id_="test/test.boundary.test4.testC",
        name="testC",
        qname="test.boundary.test4.testC",
        default_value=None,
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("", "", ""),
    )

    mapping = OneToManyMapping(1.0, parameterv1, [parameterv2_a, parameterv2_b, parameterv2_c])

    boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.test4.testv1",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    migrated_boundary_annotation_a = BoundaryAnnotation(
        target="test/test.boundary.test4.testA",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    migrated_boundary_annotation_b = BoundaryAnnotation(
        target="test/test.boundary.test4.testB",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment=get_migration_text(boundary_annotation, mapping),
        reviewResult=EnumReviewResult.UNSURE,
        interval=Interval(
            lowerIntervalLimit=0.0,
            lowerLimitType=1,
            upperIntervalLimit=10.0,
            upperLimitType=1,
            isDiscrete=False,
        ),
    )
    migrated_boundary_annotation_c = BoundaryAnnotation(
        target="test/test.boundary.test4.testC",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment=get_migration_text(boundary_annotation, mapping),
        reviewResult=EnumReviewResult.UNSURE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    return (
        mapping,
        boundary_annotation,
        [
            migrated_boundary_annotation_a,
            migrated_boundary_annotation_b,
            migrated_boundary_annotation_c,
        ],
    )


def migrate_boundary_annotation_data_duplicated() -> (
    tuple[
        Mapping,
        list[AbstractAnnotation],
        list[AbstractAnnotation],
    ]
):
    parameterv1 = Parameter(
        id_="test/test.boundary.duplicate.testA",
        name="testA",
        qname="test.boundary.duplicate.testA",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", ""),
    )
    parameterv1_2 = Parameter(
        id_="test/test.boundary.duplicate.testA_2",
        name="testA_2",
        qname="test.boundary.duplicate.testA_2",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", ""),
    )
    parameterv2 = Parameter(
        id_="test/test.boundary.duplicate.testB",
        name="testB",
        qname="test.boundary.duplicate.testB",
        default_value="1",
        assigned_by=ParameterAssignment.POSITION_OR_NAME,
        is_public=True,
        documentation=ParameterDocumentation("int", "1", ""),
    )
    boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.duplicate.testA",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    boundary_annotation_2 = BoundaryAnnotation(
        target="test/test.boundary.duplicate.testA_2",
        authors=["testauthor"],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    migrated_boundary_annotation = BoundaryAnnotation(
        target="test/test.boundary.duplicate.testB",
        authors=["testauthor", migration_author],
        reviewers=[],
        comment="",
        reviewResult=EnumReviewResult.NONE,
        interval=Interval(
            lowerIntervalLimit=0,
            lowerLimitType=1,
            upperIntervalLimit=10,
            upperLimitType=1,
            isDiscrete=True,
        ),
    )
    return (
        ManyToOneMapping(1.0, [parameterv1, parameterv1_2], parameterv2),
        [boundary_annotation, boundary_annotation_2],
        [migrated_boundary_annotation],
    )
