import sys

from precommit_sync_files.sync import (
    ConfigError,
    FileComparisonError,
    SourceFetchError,
    SyncError,
    sync_files,
)


def main() -> int:
    # Parse arguments
    write_mode = "--write" in sys.argv[1:]

    try:
        # Load configuration
        from precommit_sync_files.sync import load_config

        config = load_config()
    except ConfigError as e:
        # Missing config is a no-op (per design doc)
        if ".sync-files.toml not found" in str(e):
            return 0
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    try:
        # Perform sync
        errors, warnings = sync_files(config, write_mode=write_mode)

        # Print warnings
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)

        # Print errors and exit
        if errors:
            print("File synchronization check failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            if not write_mode:
                print(
                    "\nRun with --write to automatically sync files.",
                    file=sys.stderr,
                )
            return 1

        if warnings:
            # In write mode, warnings indicate successful syncs
            print("Files synchronized successfully:", file=sys.stderr)
            for warning in warnings:
                print(f"  - {warning}", file=sys.stderr)

        return 0

    except (SourceFetchError, FileComparisonError, SyncError) as e:
        print(f"Sync error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
