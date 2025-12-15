import sys

from precommit_sync_files.sync import (
    ConfigError,
    FileComparisonError,
    SourceFetchError,
    SyncError,
    sync_files,
)
from precommit_sync_files.log import get_logger


def main() -> int:
    # Parse arguments
    write_mode = "--write" in sys.argv[1:]
    debug_mode = "--debug" in sys.argv[1:]

    logger = get_logger(__name__, debug_mode)

    try:
        # Load configuration
        from precommit_sync_files.sync import load_config

        config = load_config()
    except ConfigError as e:
        # Missing config is a no-op (per design doc)
        if ".sync-files.toml not found" in str(e):
            return 0
        logger.debug(f"Configuration error: {e}", file=sys.stderr)
        return 1

    try:
        # Perform sync
        errors, warnings = sync_files(config, write_mode=write_mode)

        # Print warnings
        for warning in warnings:
            logger.debug(f"Warning: {warning}", file=sys.stderr)

        # Print errors and exit
        if errors:
            logger.debug("File synchronization check failed:", file=sys.stderr)
            for error in errors:
                logger.debug(f"  - {error}", file=sys.stderr)
            if not write_mode:
                logger.debug(
                    "\nRun with --write to automatically sync files.",
                    file=sys.stderr,
                )
            return 1

        if warnings:
            # In write mode, warnings indicate successful syncs
            logger.debug("Files synchronized successfully:", file=sys.stderr)
            for warning in warnings:
                logger.debug(f"  - {warning}", file=sys.stderr)

        return 0

    except (SourceFetchError, FileComparisonError, SyncError) as e:
        logger.debug(f"Sync error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.debug(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
