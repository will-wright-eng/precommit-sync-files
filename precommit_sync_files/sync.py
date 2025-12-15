import hashlib
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from precommit_sync_files.exceptions import (
    ConfigError,
    FileComparisonError,
)
from precommit_sync_files.git_repo import GitRepository


def load_config(config_path: Optional[Path] = None) -> Dict:
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.exists():
        raise ConfigError(
            '.sync-files.toml not found. The hook is a no-op if config is missing.'
        )

    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
    except ValueError as e:
        # tomllib raises ValueError for TOML decode errors
        raise ConfigError(f'Failed to parse .sync-files.toml: {e}') from e
    except Exception as e:
        raise ConfigError(f'Failed to read .sync-files.toml: {e}') from e

    # Validate required fields
    if not isinstance(config, dict):
        raise ConfigError('Configuration must be a TOML table')

    if 'source' not in config:
        raise ConfigError('Missing required field: source')
    if not isinstance(config['source'], dict):
        raise ConfigError("Field 'source' must be a dictionary")
    if 'repo' not in config['source']:
        raise ConfigError('Missing required field: source.repo')
    if 'ref' not in config['source']:
        raise ConfigError('Missing required field: source.ref')

    if 'files' not in config:
        raise ConfigError('Missing required field: files')
    if not isinstance(config['files'], list):
        raise ConfigError("Field 'files' must be a list")
    if len(config['files']) == 0:
        raise ConfigError("Field 'files' must contain at least one file mapping")

    for i, file_entry in enumerate(config['files']):
        if not isinstance(file_entry, dict):
            raise ConfigError(f'files[{i}] must be a dictionary')
        if 'src' not in file_entry:
            raise ConfigError(f'files[{i}] missing required field: src')
        if 'dst' not in file_entry:
            raise ConfigError(f'files[{i}] missing required field: dst')

    # Set default options
    if 'options' not in config:
        config['options'] = {}
    if 'mode' not in config['options']:
        config['options']['mode'] = 'check'

    if config['options']['mode'] not in ('check', 'write'):
        raise ConfigError("options.mode must be 'check' or 'write'")

    # When running as a pre-commit hook, override the ref with the hook's own version
    # This ensures files are fetched from the same tag/version as the hook itself
    hook_version = get_hook_version()
    if hook_version is not None:
        config['source']['ref'] = hook_version

    return config


def find_config_file() -> Optional[Path]:
    current = Path.cwd()
    while current != current.parent:
        config_path = current / '.sync-files.toml'
        if config_path.exists():
            return config_path
        current = current.parent
    return None


def get_hook_version() -> Optional[str]:
    try:
        # Get the directory where this module is located
        module_file = Path(__file__).resolve()
        module_path_str = str(module_file)

        # Check if we're in a pre-commit cache directory
        # Pre-commit cache paths typically contain ".cache/pre-commit"
        if '.cache/pre-commit' not in module_path_str:
            return None

        # Find the repository root by walking up from the module file
        # Pre-commit cache structure:
        # ~/.cache/pre-commit/<repohash>/<repohash>/ (the actual repo checkout)
        # or
        # ~/.cache/pre-commit/<repohash>/py_env-*/lib/python*/site-packages/ (if installed as package)
        git_repo = GitRepository()
        repo_root = git_repo.find_repo_root(module_file.parent)

        if repo_root is None:
            return None

        # Get version using GitRepository
        return git_repo.get_version(repo_root)
    except Exception:
        # If anything goes wrong, return None (fall back to config file ref)
        pass

    return None


def fetch_source_repo(repo_url: str, ref: str, work_dir: Path) -> Path:
    git_repo = GitRepository()
    return git_repo.clone_repo(repo_url, ref, work_dir)


def compute_file_hash(file_path: Path) -> str:
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()
    except IOError as e:
        raise FileComparisonError(f'Failed to read file {file_path}: {e}') from e


def compare_files(
    source_file: Path, dest_file: Path, repo_root: Path
) -> Tuple[bool, Optional[str]]:
    source_path = source_file
    dest_path = repo_root / dest_file

    # Check if source file exists
    if not source_path.exists():
        return (
            False,
            f'Source file {source_file} does not exist in source repository',
        )

    # Check if destination file exists
    if not dest_path.exists():
        return (
            False,
            f'Destination file {dest_file} does not exist in consuming repository',
        )

    # Compare hashes
    try:
        source_hash = compute_file_hash(source_path)
        dest_hash = compute_file_hash(dest_path)
    except FileComparisonError as e:
        return (False, str(e))

    if source_hash == dest_hash:
        return (True, None)

    return (
        False,
        f'File {dest_file} differs from source (hash mismatch)',
    )


def sync_file(source_file: Path, dest_file: Path, repo_root: Path) -> None:
    dest_path = repo_root / dest_file

    # Create parent directories if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(source_file, dest_path)
    except (IOError, OSError) as e:
        raise FileComparisonError(
            f'Failed to copy {source_file} to {dest_path}: {e}'
        ) from e


def sync_files(
    config: Dict, repo_root: Optional[Path] = None, write_mode: bool = False
) -> Tuple[List[str], List[str]]:
    if repo_root is None:
        repo_root = Path.cwd()

    repo_url = config['source']['repo']
    ref = config['source']['ref']
    files = config['files']
    mode = config['options']['mode']

    # Use write_mode if explicitly set, otherwise use config mode
    should_write = write_mode or (mode == 'write')

    errors = []
    warnings = []

    # Create temporary directory for source repo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_repo = fetch_source_repo(repo_url, ref, temp_path)

        mismatches = []

        for file_entry in files:
            src_path = file_entry['src']
            dst_path = file_entry['dst']

            source_file = source_repo / src_path
            are_equal, diff_msg = compare_files(source_file, Path(dst_path), repo_root)

            if not are_equal:
                mismatches.append((source_file, dst_path, diff_msg))

        if mismatches:
            if should_write:
                # Write mode: overwrite files
                for source_file, dst_path, diff_msg in mismatches:
                    try:
                        sync_file(source_file, Path(dst_path), repo_root)
                        warnings.append(f'Synced {dst_path}: {diff_msg}')
                    except FileComparisonError as e:
                        errors.append(str(e))
            else:
                # Check mode: fail with errors
                for _source_file, dst_path, diff_msg in mismatches:
                    errors.append(f'{dst_path}: {diff_msg}')

    return errors, warnings
