#!/home/gizmore/www/pygdo/.venv/bin/python
"""Notify Mira after watched files have been quiet for a debounce period."""

from __future__ import annotations

import argparse
import errno
import hashlib
import heapq
import json
import os
import select
import sys
import time
from pathlib import Path

from inotify_simple import INotify, flags

PROJECT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_DIR))

from gdo.mira.util import send_to_mira


IN_CLOSE_WRITE = flags.CLOSE_WRITE
IN_MOVED_TO = flags.MOVED_TO
IN_CREATE = flags.CREATE
IN_DELETE = flags.DELETE
IN_DELETE_SELF = flags.DELETE_SELF
IN_MOVE_SELF = flags.MOVE_SELF
IN_IGNORED = flags.IGNORED
IN_ISDIR = flags.ISDIR
WATCH_MASK = IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE | IN_DELETE | IN_DELETE_SELF | IN_MOVE_SELF
IGNORED_DIRS = {'.git', '__pycache__'}
ACKNOWLEDGEMENTS = Path('/home/mira/.pygdo/code-change-acknowledgements.json')


class ChangeAcknowledgements:
    """Remember exact source revisions that Mira already knows about."""

    def __init__(self, path: Path = ACKNOWLEDGEMENTS):
        self.path = path

    def load(self) -> dict[str, dict]:
        try:
            with self.path.open(encoding='utf-8') as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, entries: dict[str, dict]) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(entries, handle, sort_keys=True)
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)

    @staticmethod
    def digest(path: Path) -> str | None:
        try:
            with path.open('rb') as handle:
                return hashlib.file_digest(handle, 'sha256').hexdigest()
        except FileNotFoundError:
            return None

    def acknowledge(self, path: Path, expires_at: float) -> None:
        digest = self.digest(path)
        if digest is None:
            raise FileNotFoundError(path)
        entries = self.load()
        entry = entries.setdefault(str(path), {'revisions': []})
        revisions = entry.setdefault('revisions', [])
        revisions[:] = [revision for revision in revisions if revision.get('sha256') != digest]
        revisions.append({'sha256': digest, 'expires_at': expires_at})
        self.save(entries)

    def consume_if_known(self, path: Path) -> bool:
        entries = self.load()
        entry = entries.get(str(path))
        if entry is None:
            return False
        entries.pop(str(path), None)
        self.save(entries)
        revisions = entry.get('revisions')
        if revisions is None:  # Upgrade the one-revision format from earlier watcher versions.
            revisions = [entry]
        digest = self.digest(path)
        return any(revision.get('expires_at', 0) >= time.time() and revision.get('sha256') == digest for revision in revisions)


class Inotify:
    def __init__(self):
        self._inotify = INotify(nonblocking=True)
        self.fd = self._inotify.fd

    def add_watch(self, path: Path) -> int:
        try:
            return self._inotify.add_watch(str(path), WATCH_MASK)
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.ENOTDIR, errno.EACCES):
                return -1
            raise

    def read(self) -> list[tuple[int, int, str]]:
        try:
            events = self._inotify.read(timeout=0)
        except BlockingIOError:
            return []
        return [(event.wd, event.mask, event.name) for event in events]


class CodeChangeWatcher:
    def __init__(self, root: Path, delay: float, suffix: str | None, event: str):
        self.root = root.resolve()
        self.delay = delay
        self.suffix = suffix
        self.event = event
        self.inotify = Inotify()
        self.paths: dict[int, Path] = {}
        self.deadlines: dict[Path, float] = {}
        self.queue: list[tuple[float, Path]] = []
        self.acknowledgements = ChangeAcknowledgements()

    @staticmethod
    def wanted_directory(path: Path) -> bool:
        return path.name not in IGNORED_DIRS

    def add_tree(self, directory: Path, report_existing: bool = False) -> None:
        if not directory.is_dir() or not self.wanted_directory(directory):
            return
        for current, directories, files in os.walk(directory):
            current_path = Path(current)
            directories[:] = [name for name in directories if name not in IGNORED_DIRS]
            watch = self.inotify.add_watch(current_path)
            if watch >= 0:
                self.paths[watch] = current_path
            if report_existing:
                for filename in files:
                    path = current_path / filename
                    if self.wanted_file(path):
                        self.changed(path)

    def changed(self, path: Path) -> None:
        path = path.resolve(strict=False)
        deadline = time.monotonic() + self.delay
        self.deadlines[path] = deadline
        heapq.heappush(self.queue, (deadline, path))

    def wanted_file(self, path: Path) -> bool:
        return self.suffix is None or path.suffix == self.suffix

    def flush_changes(self) -> None:
        now = time.monotonic()
        while self.queue and self.queue[0][0] <= now:
            deadline, path = heapq.heappop(self.queue)
            if self.deadlines.get(path) != deadline:
                continue
            del self.deadlines[path]
            if self.acknowledgements.consume_if_known(path):
                print(f'acknowledged: {path}', flush=True)
                continue
            try:
                send_to_mira(f'{self.event} {path}')
                print(f'notified: {path}', flush=True)
            except Exception as error:
                print(f'watch_code_changes: could not notify for {path}: {error}', file=sys.stderr, flush=True)

    def timeout(self) -> float | None:
        while self.queue and self.deadlines.get(self.queue[0][1]) != self.queue[0][0]:
            heapq.heappop(self.queue)
        if not self.queue:
            return None
        return max(0.0, self.queue[0][0] - time.monotonic())

    def handle_events(self) -> None:
        for watch, mask, name in self.inotify.read():
            directory = self.paths.get(watch)
            if mask & IN_IGNORED:
                self.paths.pop(watch, None)
                continue
            if directory is None:
                continue
            path = directory / name if name else directory
            if mask & IN_ISDIR:
                if mask & (IN_CREATE | IN_MOVED_TO):
                    self.add_tree(path, report_existing=True)
                continue
            if self.wanted_file(path) and mask & (IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE | IN_DELETE):
                self.changed(path)

    def run(self) -> None:
        self.add_tree(self.root)
        pattern = f'*{self.suffix}' if self.suffix else '*'
        print(f'watching {self.root}/**/{pattern} (debounce {self.delay:g}s; event {self.event})', flush=True)
        while True:
            ready, _unused, _errors = select.select([self.inotify.fd], [], [], self.timeout())
            if ready:
                self.handle_events()
            self.flush_changes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', default='/home/gizmore/www/pygdo', type=Path,
                        help='PyGDO project directory; its gdo/ subtree is watched by default')
    parser.add_argument('--root', type=Path,
                        help='watch this directory directly instead of <dir>/gdo')
    parser.add_argument('--all-files', action='store_true',
                        help='watch all regular files instead of only Python source')
    parser.add_argument('--event', default='$changes',
                        help='Mira event prefix to emit for a settled change')
    parser.add_argument('--time', default=180.0, type=float,
                        help='quiet time in seconds before notifying (default: 180)')
    parser.add_argument('--ack', type=Path, metavar='PATH',
                        help='acknowledge the current revision of one watched file and exit')
    args = parser.parse_args()
    if args.time <= 0:
        parser.error('--time must be positive')
    source_root = args.root.resolve() if args.root else args.dir.resolve() / 'gdo'
    if not source_root.is_dir():
        parser.error(f'no gdo directory under {args.dir}')
    if args.ack:
        path = args.ack.resolve(strict=False)
        if (not args.all_files and path.suffix != '.py') or not path.is_relative_to(source_root):
            parser.error(f'--ack path must be a watched file inside {source_root}')
        ChangeAcknowledgements().acknowledge(path, time.time() + max(60, args.time * 2))
        print(f'acknowledged revision: {path}')
        return 0
    CodeChangeWatcher(source_root, args.time, None if args.all_files else '.py', args.event).run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
