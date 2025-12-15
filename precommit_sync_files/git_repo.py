import subprocess
from pathlib import Path
from typing import List, Optional

from precommit_sync_files.exceptions import SourceFetchError


class GitRepository:
    """Encapsulates git operations for repository management."""

    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir

    def _run_git_command(
        self, args: List[str], cwd: Optional[Path] = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        if cwd is None:
            cwd = self.work_dir

        return subprocess.run(
            args,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True,
        )

    def find_repo_root(self, start_path: Path, max_depth: int = 15) -> Optional[Path]:
        current = start_path
        depth = 0

        while current != current.parent and depth < max_depth:
            git_dir = current / '.git'
            if git_dir.exists():
                return current
            current = current.parent
            depth += 1

        return None

    def get_exact_tag_at_head(self, repo_path: Path) -> Optional[str]:
        try:
            result = self._run_git_command(
                ['git', 'describe', '--tags', '--exact-match', 'HEAD'],
                cwd=repo_path,
                check=False,
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                if tag:
                    return tag
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None

    def get_nearest_tag_at_head(self, repo_path: Path) -> Optional[str]:
        try:
            result = self._run_git_command(
                ['git', 'describe', '--tags', '--abbrev=0', 'HEAD'],
                cwd=repo_path,
                check=False,
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                if tag:
                    return tag
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None

    def get_commit_sha(self, repo_path: Path, ref: str = 'HEAD') -> Optional[str]:
        try:
            result = self._run_git_command(
                ['git', 'rev-parse', ref],
                cwd=repo_path,
                check=False,
            )
            if result.returncode == 0:
                commit_sha = result.stdout.strip()
                if commit_sha:
                    return commit_sha
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None

    def get_tags_at_commit(self, repo_path: Path, commit_sha: str) -> List[str]:
        try:
            result = self._run_git_command(
                ['git', 'tag', '--points-at', commit_sha],
                cwd=repo_path,
                check=False,
            )
            if result.returncode == 0:
                tags = result.stdout.strip().split('\n')
                # Filter out empty strings
                return [tag for tag in tags if tag]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return []

    def get_version(self, repo_path: Path) -> Optional[str]:
        """
        Get version using fallback strategy.

        Tries in order:
        1. Exact tag at HEAD
        2. Nearest tag at HEAD
        3. Tags at commit SHA (preferring tags starting with 'v')
        """
        # First, try to get the exact tag at HEAD
        tag = self.get_exact_tag_at_head(repo_path)
        if tag:
            return tag

        # If that fails, try to get the nearest tag
        tag = self.get_nearest_tag_at_head(repo_path)
        if tag:
            return tag

        # As a last resort, check what ref HEAD points to
        commit_sha = self.get_commit_sha(repo_path, 'HEAD')
        if commit_sha:
            tags = self.get_tags_at_commit(repo_path, commit_sha)
            if tags:
                # Return the first tag (prefer version tags starting with 'v')
                for tag in tags:
                    if tag.startswith('v'):
                        return tag
                return tags[0]

        return None

    def clone_with_branch(self, repo_url: str, ref: str, target_dir: Path) -> None:
        self._run_git_command(
            [
                'git',
                'clone',
                '--depth',
                '1',
                '--branch',
                ref,
                repo_url,
                str(target_dir),
            ],
            check=True,
        )

    def clone_shallow(self, repo_url: str, target_dir: Path) -> None:
        self._run_git_command(
            [
                'git',
                'clone',
                '--depth',
                '1',
                '--no-single-branch',
                repo_url,
                str(target_dir),
            ],
            check=True,
        )

    def fetch_ref(self, repo_path: Path, ref: str) -> None:
        self._run_git_command(
            ['git', 'fetch', '--depth', '1', 'origin', ref],
            cwd=repo_path,
            check=True,
        )

    def checkout_ref(self, repo_path: Path, ref: str) -> None:
        self._run_git_command(
            ['git', 'checkout', ref],
            cwd=repo_path,
            check=True,
        )

    def clone_repo(self, repo_url: str, ref: str, work_dir: Path) -> Path:
        """
        Clone repository with fallback strategy for different ref types.

        First tries cloning with branch/tag (works for branches and tags).
        If that fails, falls back to shallow clone + fetch + checkout
        (works for commit SHAs or tags on other branches).
        """

        repo_dir = work_dir / 'source_repo'

        # Remove existing directory if present
        if repo_dir.exists():
            import shutil

            shutil.rmtree(repo_dir)

        # First, try cloning with branch/tag (works for branches and tags)
        try:
            self.clone_with_branch(repo_url, ref, repo_dir)
            return repo_dir
        except subprocess.CalledProcessError:
            # If that fails, it might be a commit SHA
            # Clone with --no-single-branch to allow fetching any ref
            try:
                self.clone_shallow(repo_url, repo_dir)
                # Fetch the specific ref (might be a commit SHA or tag on another branch)
                self.fetch_ref(repo_dir, ref)
                # Checkout the ref
                self.checkout_ref(repo_dir, ref)
            except subprocess.CalledProcessError as e:
                raise SourceFetchError(
                    f'Failed to fetch source repository {repo_url} at ref {ref}: {e.stderr}'
                ) from e

        return repo_dir
