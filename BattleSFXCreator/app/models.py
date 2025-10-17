"""Data models for working with Battle SFX sequence folders."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional
import re


SEQ_EXTENSION = ".seq"


@dataclass
class SequenceFile:
    """Represents a single *.seq file inside an effect folder."""

    folder_path: Path
    filename: str
    display_label: Optional[str] = None
    _cached_text: Optional[str] = field(default=None, repr=False, compare=False)

    @property
    def path(self) -> Path:
        return self.folder_path / self.filename

    @property
    def identifier(self) -> str:
        return f"{self.folder_path.name}/{self.filename}"

    def read_text(self, *, use_cache: bool = True) -> str:
        if use_cache and self._cached_text is not None:
            return self._cached_text
        text = self.path.read_text(encoding="utf-8")
        self._cached_text = text
        return text

    def write_text(self, text: str) -> None:
        self.path.write_text(text, encoding="utf-8")
        self._cached_text = text

    def rename(self, new_name: str) -> Path:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("New name must not be empty")
        if not new_name.lower().endswith(SEQ_EXTENSION):
            new_name = f"{new_name}{SEQ_EXTENSION}"
        target = self.folder_path / new_name
        if target == self.path:
            return target
        if target.exists():
            raise FileExistsError(f"A sequence named '{target.name}' already exists")
        self.path.rename(target)
        self.filename = target.name
        self._cached_text = None
        return target


@dataclass
class SequenceFolder:
    """Container for the files inside an ef#### folder."""

    path: Path
    files: List[SequenceFile] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.name

    def add_file(self, seq_file: SequenceFile) -> None:
        self.files.append(seq_file)

    def iter_files(self) -> Iterator[SequenceFile]:
        for seq_file in sorted(self.files, key=lambda item: item.filename.lower()):
            yield seq_file


@dataclass
class SequenceDocument:
    """Loaded view of a directory containing battle SFX sequences."""

    root: Path
    folders: List[SequenceFolder] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path) -> "SequenceDocument":
        if not root.exists():
            raise FileNotFoundError(f"Directory '{root}' does not exist")
        if not root.is_dir():
            raise NotADirectoryError(f"{root} is not a directory")
        folders: List[SequenceFolder] = []
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir():
                continue
            folder = SequenceFolder(path=child)
            for file_path in sorted(child.glob(f"*{SEQ_EXTENSION}")):
                folder.add_file(
                    SequenceFile(
                        folder_path=child,
                        filename=file_path.name,
                        display_label=None,
                    )
                )
            folders.append(folder)
        if not folders:
            raise ValueError("No sequence folders were found")
        return cls(root=root, folders=folders)

    def suggest_new_folder_name(self, prefix: str = "ef") -> str:
        pattern = re.compile(rf"^{re.escape(prefix)}(\\d+)$", re.IGNORECASE)
        numbers: List[int] = []
        width = 4
        for folder in self.folders:
            match = pattern.match(folder.name)
            if match:
                value = int(match.group(1))
                numbers.append(value)
                width = max(width, len(match.group(1)))
        candidate = (max(numbers) + 1) if numbers else 0
        width = min(max(width, len(str(candidate))), 6)
        return f"{prefix}{candidate:0{width}d}"

    def create_folder(self, name: str) -> Path:
        target = self.root / name
        target.mkdir(parents=False, exist_ok=False)
        return target

    def create_sequence_file(self, folder_path: Path, filename: str, *, body: str = "") -> Path:
        folder_path.mkdir(parents=True, exist_ok=True)
        target = folder_path / filename
        if target.exists():
            raise FileExistsError(f"Sequence file '{filename}' already exists in {folder_path.name}")
        target.write_text(body, encoding="utf-8")
        return target

    def iter_sequence_files(self) -> Iterator[SequenceFile]:
        for folder in self.folders:
            yield from folder.iter_files()

    def find_file(self, folder_name: str, filename: str) -> Optional[SequenceFile]:
        folder_name = folder_name.lower()
        filename = filename.lower()
        for folder in self.folders:
            if folder.name.lower() != folder_name:
                continue
            for seq_file in folder.files:
                if seq_file.filename.lower() == filename:
                    return seq_file
        return None

    def folder_map(self) -> Dict[str, SequenceFolder]:
        return {folder.name: folder for folder in self.folders}

    def reload(self) -> None:
        refreshed = self.__class__.load(self.root)
        self.folders = refreshed.folders


@dataclass
class RenameAction:
    """Undo information for file or folder rename operations."""

    old_path: Path
    new_path: Path

    def undo(self) -> None:
        if self.old_path.exists():
            raise FileExistsError(f"Cannot undo rename: '{self.old_path}' already exists")
        if not self.new_path.exists():
            raise FileNotFoundError(f"Cannot undo rename: '{self.new_path}' is missing")
        self.new_path.rename(self.old_path)


class RenameHistory:
    """Bounded stack of rename actions supporting undo."""

    def __init__(self, *, capacity: int = 32) -> None:
        self._capacity = max(1, capacity)
        self._stack: List[RenameAction] = []

    def push(self, action: RenameAction) -> None:
        self._stack.append(action)
        if len(self._stack) > self._capacity:
            self._stack.pop(0)

    def can_undo(self) -> bool:
        return bool(self._stack)

    def undo(self) -> Optional[RenameAction]:
        if not self._stack:
            return None
        action = self._stack.pop()
        action.undo()
        return action
