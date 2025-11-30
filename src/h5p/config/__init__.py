"""H5P Pipeline Configuration Module"""

from .milestones import MILESTONE_CONFIGS, get_milestone_config
from .content_types import CONTENT_TYPE_SCHEMAS, get_content_type_schema

__all__ = [
    "MILESTONE_CONFIGS",
    "get_milestone_config",
    "CONTENT_TYPE_SCHEMAS",
    "get_content_type_schema",
]
