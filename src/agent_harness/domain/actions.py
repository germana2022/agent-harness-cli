"""Action and capability taxonomy.

Actions are represented by immutable value objects, never free-form strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import InvalidDomainValue, validate_identifier


class ActionCategory(Enum):
    """Classification axis for actions."""

    READ = "read"
    LOCAL_WRITE = "local_write"
    EXECUTION = "execution"
    GIT_MUTATION = "git_mutation"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"


class Capability(Enum):
    """Stable capability identifiers."""

    REPOSITORY_METADATA_READ = "repository_metadata_read"
    ALLOWED_FILE_READ = "allowed_file_read"
    EXACT_SEARCH = "exact_search"
    LOCAL_WORKSPACE_WRITE = "local_workspace_write"
    COMMAND_EXECUTION = "command_execution"
    GIT_STATE_MUTATION = "git_state_mutation"
    LOCAL_COMMIT = "local_commit"
    EXTERNAL_PUSH = "external_push"
    PULL_REQUEST_CREATE_MODIFY = "pull_request_create_modify"
    ISSUE_TICKET_MODIFY = "issue_ticket_modify"
    COMMENT_PUBLICATION = "comment_publication"
    MIGRATION = "migration"
    DEPLOYMENT = "deployment"
    DESTRUCTIVE_DELETE_REVERT = "destructive_delete_revert"


CAPABILITY_CATEGORY: dict[Capability, ActionCategory] = {
    Capability.REPOSITORY_METADATA_READ: ActionCategory.READ,
    Capability.ALLOWED_FILE_READ: ActionCategory.READ,
    Capability.EXACT_SEARCH: ActionCategory.READ,
    Capability.LOCAL_WORKSPACE_WRITE: ActionCategory.LOCAL_WRITE,
    Capability.COMMAND_EXECUTION: ActionCategory.EXECUTION,
    Capability.GIT_STATE_MUTATION: ActionCategory.GIT_MUTATION,
    Capability.LOCAL_COMMIT: ActionCategory.GIT_MUTATION,
    Capability.EXTERNAL_PUSH: ActionCategory.EXTERNAL,
    Capability.PULL_REQUEST_CREATE_MODIFY: ActionCategory.EXTERNAL,
    Capability.ISSUE_TICKET_MODIFY: ActionCategory.EXTERNAL,
    Capability.COMMENT_PUBLICATION: ActionCategory.EXTERNAL,
    Capability.MIGRATION: ActionCategory.EXTERNAL,
    Capability.DEPLOYMENT: ActionCategory.EXTERNAL,
    Capability.DESTRUCTIVE_DELETE_REVERT: ActionCategory.DESTRUCTIVE,
}


@dataclass(frozen=True)
class TargetResource:
    """A normalized resource reference with no filesystem coupling."""

    ref: str
    resource_type: str = "target"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", validate_identifier(self.ref, "ref"))
        object.__setattr__(
            self,
            "resource_type",
            validate_identifier(self.resource_type, "resource_type"),
        )


@dataclass(frozen=True)
class ActionName:
    """An immutable action identified by capability, category, and target."""

    capability: Capability
    category: ActionCategory
    target: TargetResource

    def __post_init__(self) -> None:
        if not isinstance(self.capability, Capability):
            raise InvalidDomainValue("capability must be a Capability")
        if not isinstance(self.category, ActionCategory):
            raise InvalidDomainValue("category must be an ActionCategory")
        canonical = CAPABILITY_CATEGORY[self.capability]
        if self.category is not canonical:
            raise InvalidDomainValue(
                f"category for {self.capability.value} must be {canonical.value}"
            )
        if not isinstance(self.target, TargetResource):
            raise InvalidDomainValue("target must be a TargetResource")
