import pytest
from library_analyzer.processing.annotations.model import (
    ANNOTATION_SCHEMA_VERSION,
    AbstractAnnotation,
    AnnotationStore,
    BoundaryAnnotation,
    CalledAfterAnnotation,
    CompleteAnnotation,
    ConstantAnnotation,
    DependencyAnnotation,
    DescriptionAnnotation,
    EnumAnnotation,
    EnumPair,
    EnumReviewResult,
    ExpertAnnotation,
    GroupAnnotation,
    Interval,
    MoveAnnotation,
    OmittedAnnotation,
    OptionalAnnotation,
    PureAnnotation,
    RemoveAnnotation,
    RenameAnnotation,
    RequiredAnnotation,
    TodoAnnotation,
    ValueAnnotation,
)
from library_analyzer.processing.api import (
    Condition,
    Action
)


def test_annotation_store() -> None:
    annotations = AnnotationStore()
    annotations.removeAnnotations.append(
        RemoveAnnotation(
            target="test/remove",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.UNSURE,
        ),
    )
    annotations.valueAnnotations.append(
        RequiredAnnotation(
            target="test/required",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.CORRECT,
        ),
    )
    annotations.valueAnnotations.append(
        OptionalAnnotation(
            target="test/optional",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            defaultValueType=ValueAnnotation.DefaultValueType.STRING,
            defaultValue="test",
        ),
    )
    annotations.valueAnnotations.append(
        ConstantAnnotation(
            target="test/constant",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            defaultValueType=ValueAnnotation.DefaultValueType.STRING,
            defaultValue="test",
        ),
    )
    annotations.boundaryAnnotations.append(
        BoundaryAnnotation(
            target="test/boundary",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            interval=Interval(
                lowerIntervalLimit=0,
                lowerLimitType=0,
                upperIntervalLimit=0,
                upperLimitType=0,
                isDiscrete=False,
            ),
        ),
    )
    annotations.enumAnnotations.append(
        EnumAnnotation(
            target="test/enum",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            enumName="test",
            pairs=[EnumPair("test", "test")],
        ),
    )
    annotations.calledAfterAnnotations.append(
        CalledAfterAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            calledAfterName="functionName",
        ),
    )
    annotations.completeAnnotations.append(
        CompleteAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
        ),
    )
    annotations.dependencyAnnotations.append(
        DependencyAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            has_dependent_parameter=["test/test/test"],
            is_depending_on=["test/test/test"],
            condition=Condition("If test=test", "test"),
            action=Action("this will be set to test")
        )
    )
    annotations.descriptionAnnotations.append(
        DescriptionAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            newDescription="description",
        ),
    )
    annotations.groupAnnotations.append(
        GroupAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            groupName="newParameter",
            parameters=["a", "b", "c"],
        ),
    )
    annotations.moveAnnotations.append(
        MoveAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            destination="moved.package",
        ),
    )
    annotations.pureAnnotations.append(
        PureAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
        ),
    )
    annotations.renameAnnotations.append(
        RenameAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            newName="testName",
        ),
    )
    annotations.todoAnnotations.append(
        TodoAnnotation(
            target="test/test",
            authors=["$autogen$"],
            reviewers=[],
            comment="Autogenerated",
            reviewResult=EnumReviewResult.NONE,
            newTodo="TODO replace me",
        ),
    )
    annotations.expertAnnotations.append(
        ExpertAnnotation(
            target="test/expert",
            authors=["$autogen$"],
            reviewers=[],
            comment="",
            reviewResult=EnumReviewResult.NONE,
        ),
    )
    json_store = {
        "schemaVersion": ANNOTATION_SCHEMA_VERSION,
        "boundaryAnnotations": {
            "test/boundary": {
                "target": "test/boundary",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "interval": {
                    "isDiscrete": False,
                    "lowerIntervalLimit": 0,
                    "lowerLimitType": 0,
                    "upperIntervalLimit": 0,
                    "upperLimitType": 0,
                },
            },
        },
        "enumAnnotations": {
            "test/enum": {
                "target": "test/enum",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "enumName": "test",
                "pairs": [{"instanceName": "test", "stringValue": "test"}],
            },
        },
        "expertAnnotations": {
            "test/expert": {
                "target": "test/expert",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "",
                "reviewResult": "",
            },
        },
        "removeAnnotations": {
            "test/remove": {
                "target": "test/remove",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "unsure",
            },
        },
        "valueAnnotations": {
            "test/constant": {
                "target": "test/constant",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "variant": "constant",
                "defaultValueType": "string",
                "defaultValue": "test",
            },
            "test/optional": {
                "target": "test/optional",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "variant": "optional",
                "defaultValueType": "string",
                "defaultValue": "test",
            },
            "test/required": {
                "target": "test/required",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "correct",
                "variant": "required",
            },
        },
        "calledAfterAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "calledAfterName": "functionName",
                "comment": "Autogenerated",
                "reviewResult": "",
                "reviewers": [],
                "target": "test/test",
            },
        },
        "completeAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "reviewers": [],
                "target": "test/test",
            },
        },
        "dependencyAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "reviewers": [],
                "target": "test/test",
                "has_dependent_parameter": ["test/test/test"],
                "is_depending_on": ["test/test/test"],
                "condition": {
                    "variant": Condition.Variant.CONDITION,
                    "condition": "If test=test",
                    "dependee": "test",
                    "combined_with": ""
                },
                "action": {
                    "variant": Action.Variant.ACTION,
                    "action": "this will be set to test"
                }
            }
        },
        "descriptionAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "newDescription": "description",
                "reviewers": [],
                "target": "test/test",
            },
        },
        "groupAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "groupName": "newParameter",
                "parameters": ["a", "b", "c"],
                "reviewers": [],
                "target": "test/test",
            },
        },
        "moveAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "destination": "moved.package",
                "reviewers": [],
                "target": "test/test",
            },
        },
        "pureAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "reviewers": [],
                "target": "test/test",
            },
        },
        "renameAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "newName": "testName",
                "reviewers": [],
                "target": "test/test",
            },
        },
        "todoAnnotations": {
            "test/test": {
                "authors": ["$autogen$"],
                "comment": "Autogenerated",
                "reviewResult": "",
                "newTodo": "TODO replace me",
                "reviewers": [],
                "target": "test/test",
            },
        },
    }
    assert annotations.to_dict() == json_store
    assert AnnotationStore.from_dict(json_store).to_dict() == json_store


@pytest.mark.parametrize(
    ("annotation", "d"),
    [
        (
            AbstractAnnotation(
                "test/test",
                ["$autogen$"],
                ["aclrian"],
                "Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": ["aclrian"],
                "comment": "Autogenerated",
                "reviewResult": "",
            },
        ),
        (
            BoundaryAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                interval=Interval(
                    lowerIntervalLimit=0,
                    lowerLimitType=0,
                    upperIntervalLimit=0,
                    upperLimitType=0,
                    isDiscrete=False,
                ),
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "interval": {
                    "lowerIntervalLimit": 0,
                    "lowerLimitType": 0,
                    "upperIntervalLimit": 0,
                    "upperLimitType": 0,
                    "isDiscrete": False,
                },
            },
        ),
        (
            ConstantAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                defaultValueType=ValueAnnotation.DefaultValueType.STRING,
                defaultValue="test",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "variant": "constant",
                "defaultValueType": "string",
                "defaultValue": "test",
            },
        ),
        (
            EnumAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                enumName="test",
                pairs=[EnumPair("test", "test")],
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "enumName": "test",
                "pairs": [{"instanceName": "test", "stringValue": "test"}],
            },
        ),
        (
            ExpertAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
            },
        ),
        (
            OmittedAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "variant": "omitted",
            },
        ),
        (
            OptionalAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                defaultValueType=ValueAnnotation.DefaultValueType.STRING,
                defaultValue="test",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "variant": "optional",
                "defaultValueType": "string",
                "defaultValue": "test",
            },
        ),
        (
            RemoveAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
            },
        ),
        (
            RequiredAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "variant": "required",
            },
        ),
        (
            CalledAfterAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                calledAfterName="functionName",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "calledAfterName": "functionName",
            },
        ),
        (
            CompleteAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
            },
        ),
        (
            DependencyAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                has_dependent_parameter=["test/test/test"],
                is_depending_on=["test/test/test"],
                condition=Condition("If test=test", "test"),
                action=Action("this will be set to test")
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "has_dependent_parameter": ["test/test/test"],
                "is_depending_on": ["test/test/test"],
                "condition": {
                    "variant": Condition.Variant.CONDITION,
                    "condition": "If test=test",
                    "dependee": "test",
                    "combined_with": ""
                },
                "action": {
                    "variant": Action.Variant.ACTION,
                    "action": "this will be set to test"
                }
            }
        ),
        (
            DescriptionAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                newDescription="description",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "newDescription": "description",
            },
        ),
        (
            GroupAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                groupName="newParameter",
                parameters=["a", "b", "c"],
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "groupName": "newParameter",
                "parameters": ["a", "b", "c"],
            },
        ),
        (
            MoveAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
                destination="moved.package",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
                "destination": "moved.package",
            },
        ),
        (
            PureAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.NONE,
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "",
            },
        ),
        (
            RenameAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.CORRECT,
                newName="testName",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "correct",
                "newName": "testName",
            },
        ),
        (
            TodoAnnotation(
                target="test/test",
                authors=["$autogen$"],
                reviewers=[],
                comment="Autogenerated",
                reviewResult=EnumReviewResult.UNSURE,
                newTodo="TODO replace me",
            ),
            {
                "target": "test/test",
                "authors": ["$autogen$"],
                "reviewers": [],
                "comment": "Autogenerated",
                "reviewResult": "unsure",
                "newTodo": "TODO replace me",
            },
        ),
    ],
    ids=[
        "test import and export of base annotation",
        "test import and export of boundary annotation",
        "test import and export of constant annotation",
        "test import and export of enum annotation",
        "test import and export of expert annotation",
        "test import and export of omitted annotation",
        "test import and export of optional annotation",
        "test import and export of remove annotation",
        "test import and export of required annotation",
        "test import and export of called after annotation",
        "test import and export of complete annotation",
        "test import and export of Dependency annotation",
        "test import and export of Description annotation",
        "test import and export of group annotation",
        "test import and export of move annotation",
        "test import and export of pure annotation",
        "test import and export of rename annotation",
        "test import and export of todo annotation",
    ],
)
def test_conversion_between_json_and_annotation(annotation: AbstractAnnotation, d: dict) -> None:
    assert annotation.to_dict() == d
    assert type(annotation).from_dict(d) == annotation
