"""Functions to migrate individual types of annotations."""

from ._constants import migration_author
from ._get_migration_text import get_migration_text
from ._migrate_boundary_annotation import migrate_boundary_annotation
from ._migrate_called_after_annotation import migrate_called_after_annotation
from ._migrate_description_annotation import migrate_description_annotation
from ._migrate_enum_annotation import migrate_enum_annotation
from ._migrate_expert_annotation import migrate_expert_annotation
from ._migrate_group_annotation import migrate_group_annotation
from ._migrate_move_annotation import migrate_move_annotation
from ._migrate_remove_annotation import migrate_remove_annotation
from ._migrate_rename_annotation import migrate_rename_annotation
from ._migrate_todo_annotation import migrate_todo_annotation
from ._migrate_value_annotation import migrate_value_annotation

__all__ = [
    "get_migration_text",
    "migration_author",
    "migrate_boundary_annotation",
    "migrate_called_after_annotation",
    "migrate_description_annotation",
    "migrate_enum_annotation",
    "migrate_expert_annotation",
    "migrate_group_annotation",
    "migrate_move_annotation",
    "migrate_remove_annotation",
    "migrate_rename_annotation",
    "migrate_todo_annotation",
    "migrate_value_annotation",
]
