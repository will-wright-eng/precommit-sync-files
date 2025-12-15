import sys

from precommit_sync_files.exceptions import (
    ConfigError,
    FileComparisonError,
    SourceFetchError,
    SyncError,
)
from precommit_sync_files.sync import sync_files
from precommit_sync_files.log import get_logger
from precommit_sync_files import __version__


def main() -> int:
    # Parse arguments
    write_mode = '--write' in sys.argv[1:]
    debug_mode = '--debug' in sys.argv[1:]

    logger = get_logger(__name__, debug_mode)
    logger.info('Starting precommit-sync-files')
    logger.info(f'Version: {__version__}')

    try:
        # Load configuration
        from precommit_sync_files.sync import load_config

        config = load_config()
    except ConfigError as e:
        # Missing config is a no-op (per design doc)
        if '.sync-files.toml not found' in str(e):
            return 0
        logger.error(f'Configuration error: {e}')
        return 1

    try:
        # Perform sync
        errors, warnings = sync_files(config, write_mode=write_mode)

        # Print warnings
        for warning in warnings:
            logger.warning(f'Warning: {warning}')

        # Print errors and exit
        if errors:
            logger.error('File synchronization check failed:')
            for error in errors:
                logger.error(f'  - {error}')
            if not write_mode:
                logger.error('Run with --write to automatically sync files.')
            return 1

        if warnings:
            # In write mode, warnings indicate successful syncs
            logger.warning('Files synchronized successfully:')
            for warning in warnings:
                logger.warning(f'  - {warning}')

        return 0

    except (SourceFetchError, FileComparisonError, SyncError) as e:
        logger.error(f'Sync error: {e}')
        return 1
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        import traceback

        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
