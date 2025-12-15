"""Exception classes for precommit-sync-files."""


class SyncError(Exception):
    """Base exception for all sync-related errors."""


class ConfigError(SyncError):
    """Raised when there's a configuration error."""


class SourceFetchError(SyncError):
    """Raised when fetching the source repository fails."""


class FileComparisonError(SyncError):
    """Raised when file comparison or operations fail."""
