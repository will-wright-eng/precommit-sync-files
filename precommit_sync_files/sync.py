import hashlib
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SyncError(Exception):
    pass


class ConfigError(SyncError):
    pass


class SourceFetchError(SyncError):
    pass


class FileComparisonError(SyncError):
    pass


def load_config(config_path: Optional[Path] = None) -> Dict:
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.exists():
        raise ConfigError(
            ".sync-files.toml not found. The hook is a no-op if config is missing."
        )

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    except ValueError as e:
        # tomllib raises ValueError for TOML decode errors
        raise ConfigError(f"Failed to parse .sync-files.toml: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read .sync-files.toml: {e}")

    # Validate required fields
    if not isinstance(config, dict):
        raise ConfigError("Configuration must be a TOML table")

    if "source" not in config:
        raise ConfigError("Missing required field: source")
    if not isinstance(config["source"], dict):
        raise ConfigError("Field 'source' must be a dictionary")
    if "repo" not in config["source"]:
        raise ConfigError("Missing required field: source.repo")
    if "ref" not in config["source"]:
        raise ConfigError("Missing required field: source.ref")

    if "files" not in config:
        raise ConfigError("Missing required field: files")
    if not isinstance(config["files"], list):
        raise ConfigError("Field 'files' must be a list")
    if len(config["files"]) == 0:
        raise ConfigError("Field 'files' must contain at least one file mapping")

    for i, file_entry in enumerate(config["files"]):
        if not isinstance(file_entry, dict):
            raise ConfigError(f"files[{i}] must be a dictionary")
        if "src" not in file_entry:
            raise ConfigError(f"files[{i}] missing required field: src")
        if "dst" not in file_entry:
            raise ConfigError(f"files[{i}] missing required field: dst")

    # Set default options
    if "options" not in config:
        config["options"] = {}
    if "mode" not in config["options"]:
        config["options"]["mode"] = "check"

    if config["options"]["mode"] not in ("check", "write"):
        raise ConfigError("options.mode must be 'check' or 'write'")

    # When running as a pre-commit hook, override the ref with the hook's own version
    # This ensures files are fetched from the same tag/version as the hook itself
    hook_version = get_hook_version()
    if hook_version is not None:
        config["source"]["ref"] = hook_version

    return config


def find_config_file() -> Optional[Path]:
    current = Path.cwd()
    while current != current.parent:
        config_path = current / ".sync-files.toml"
        if config_path.exists():
            return config_path
        current = current.parent
    return None


def get_hook_version() -> Optional[str]:
    """
    Detect the version/tag of the hook itself when running as a pre-commit hook.

    When pre-commit installs a hook, it clones the repository at the specified rev
    into a cache directory. We can detect this and get the git tag/version.

    Returns:
        The git tag/version of the hook, or None if not running as a pre-commit hook
        or if the version cannot be determined.
    """
    try:
        # Get the directory where this module is located
        module_file = Path(__file__).resolve()
        module_path_str = str(module_file)

        # Check if we're in a pre-commit cache directory
        # Pre-commit cache paths typically contain ".cache/pre-commit"
        if ".cache/pre-commit" not in module_path_str:
            return None

        # Find the repository root by walking up from the module file
        # Pre-commit cache structure:
        # ~/.cache/pre-commit/<repohash>/<repohash>/ (the actual repo checkout)
        # or
        # ~/.cache/pre-commit/<repohash>/py_env-*/lib/python*/site-packages/ (if installed as package)
        current = module_file.parent
        max_depth = 15  # Limit search depth
        depth = 0

        # Look for a directory that looks like a repo hash (long hex string)
        # or contains a .git directory
        while current != current.parent and depth < max_depth:
            git_dir = current / ".git"

            # Check if this directory has a .git folder (it's a git repo)
            if git_dir.exists():
                # Try to get the git tag/version
                try:
                    # First, try to get the exact tag at HEAD
                    result = subprocess.run(
                        ["git", "describe", "--tags", "--exact-match", "HEAD"],
                        cwd=current,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        tag = result.stdout.strip()
                        if tag:
                            return tag

                    # If that fails, try to get the nearest tag
                    result = subprocess.run(
                        ["git", "describe", "--tags", "--abbrev=0", "HEAD"],
                        cwd=current,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        tag = result.stdout.strip()
                        if tag:
                            return tag

                    # As a last resort, check what ref HEAD points to
                    # This might be a tag if we're in detached HEAD state
                    result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=current,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        commit_sha = result.stdout.strip()
                        # Try to find tags pointing to this commit
                        result = subprocess.run(
                            ["git", "tag", "--points-at", commit_sha],
                            cwd=current,
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if result.returncode == 0:
                            tags = result.stdout.strip().split("\n")
                            # Return the first tag (prefer version tags starting with 'v')
                            for tag in tags:
                                if tag and tag.startswith("v"):
                                    return tag
                            if tags and tags[0]:
                                return tags[0]
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                break

            current = current.parent
            depth += 1
    except Exception:
        # If anything goes wrong, return None (fall back to config file ref)
        pass

    return None


def fetch_source_repo(repo_url: str, ref: str, work_dir: Path) -> Path:
    repo_dir = work_dir / "source_repo"

    # Remove existing directory if present
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    # First, try cloning with branch/tag (works for branches and tags)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(repo_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        return repo_dir
    except subprocess.CalledProcessError:
        # If that fails, it might be a commit SHA
        # Clone with --no-single-branch to allow fetching any ref
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--no-single-branch",
                    repo_url,
                    str(repo_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            # Fetch the specific ref (might be a commit SHA or tag on another branch)
            subprocess.run(
                ["git", "fetch", "--depth", "1", "origin", ref],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            # Checkout the ref
            subprocess.run(
                ["git", "checkout", ref],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e2:
            raise SourceFetchError(
                f"Failed to fetch source repository {repo_url} at ref {ref}: {e2.stderr}"
            )

    return repo_dir


def compute_file_hash(file_path: Path) -> str:
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()
    except IOError as e:
        raise FileComparisonError(f"Failed to read file {file_path}: {e}")


def compare_files(
    source_file: Path, dest_file: Path, repo_root: Path
) -> Tuple[bool, Optional[str]]:
    """
    Compare source and destination files using SHA-256 hashes.

    Args:
        source_file: Path to source file (relative to source repo root)
        dest_file: Path to destination file (relative to consuming repo root)
        repo_root: Root of consuming repository
    """
    source_path = source_file
    dest_path = repo_root / dest_file

    # Check if source file exists
    if not source_path.exists():
        return (
            False,
            f"Source file {source_file} does not exist in source repository",
        )

    # Check if destination file exists
    if not dest_path.exists():
        return (
            False,
            f"Destination file {dest_file} does not exist in consuming repository",
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
        f"File {dest_file} differs from source (hash mismatch)",
    )


def sync_file(source_file: Path, dest_file: Path, repo_root: Path) -> None:
    """
    Copy source file to destination, creating parent directories if needed.

    Args:
        source_file: Path to source file (absolute)
        dest_file: Path to destination file (relative to repo root)
        repo_root: Root of consuming repository
    """
    dest_path = repo_root / dest_file

    # Create parent directories if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(source_file, dest_path)
    except (IOError, OSError) as e:
        raise FileComparisonError(f"Failed to copy {source_file} to {dest_path}: {e}")


def sync_files(
    config: Dict, repo_root: Optional[Path] = None, write_mode: bool = False
) -> Tuple[List[str], List[str]]:
    """
    Main sync function that orchestrates file synchronization.

    Args:
        config: Configuration dictionary
        repo_root: Root of consuming repository (defaults to current directory)
        write_mode: If True, overwrite files instead of failing
    """
    if repo_root is None:
        repo_root = Path.cwd()

    repo_url = config["source"]["repo"]
    ref = config["source"]["ref"]
    files = config["files"]
    mode = config["options"]["mode"]

    # Use write_mode if explicitly set, otherwise use config mode
    should_write = write_mode or (mode == "write")

    errors = []
    warnings = []

    # Create temporary directory for source repo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_repo = fetch_source_repo(repo_url, ref, temp_path)

        mismatches = []

        for file_entry in files:
            src_path = file_entry["src"]
            dst_path = file_entry["dst"]

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
                        warnings.append(f"Synced {dst_path}: {diff_msg}")
                    except FileComparisonError as e:
                        errors.append(str(e))
            else:
                # Check mode: fail with errors
                for source_file, dst_path, diff_msg in mismatches:
                    errors.append(f"{dst_path}: {diff_msg}")

    return errors, warnings
