"""Lightweight data models for the Ability Features document."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class AbilityEntry:
    """Single entry in the AbilityFeatures file."""

    header: str
    body_lines: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        return "\n".join([self.header, *self.body_lines])

    @classmethod
    def from_text(cls, text: str) -> "AbilityEntry":
        lines = text.splitlines()
        if not lines:
            raise ValueError("Entry text is empty")
        header = lines[0].strip()
        if not header.startswith(">"):
            raise ValueError("Entry header must start with '>' (e.g. >SA ...)")
        return cls(header=lines[0], body_lines=lines[1:])


@dataclass
class AbilityDocument:
    entries: List[AbilityEntry] = field(default_factory=list)
    preamble: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "AbilityDocument":
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        preamble: List[str] = []
        entries: List[AbilityEntry] = []
        current: Optional[AbilityEntry] = None

        for line in lines:
            if line.startswith(">"):
                if current:
                    entries.append(current)
                current = AbilityEntry(header=line, body_lines=[])
            else:
                if current is None:
                    preamble.append(line)
                else:
                    current.body_lines.append(line)
        if current:
            entries.append(current)
        return cls(entries=entries, preamble=preamble)

    def to_text(self) -> str:
        sections: List[str] = []
        if self.preamble:
            sections.append("\n".join(self.preamble).rstrip())
        for entry in self.entries:
            sections.append(entry.to_text().rstrip())
        return "\n\n".join(sections)

    def append(self, entry: AbilityEntry) -> None:
        self.entries.append(entry)

    def insert(self, index: int, entry: AbilityEntry) -> None:
        index = max(0, min(index, len(self.entries)))
        self.entries.insert(index, entry)

    def move(self, old_index: int, new_index: int) -> bool:
        if not self.entries:
            return False
        if old_index < 0 or old_index >= len(self.entries):
            return False
        new_index = max(0, min(new_index, len(self.entries) - 1))
        if old_index == new_index:
            return False
        entry = self.entries.pop(old_index)
        self.entries.insert(new_index, entry)
        return True

    def replace(self, header: str, new_entry: AbilityEntry) -> bool:
        for idx, existing in enumerate(self.entries):
            if existing.header == header:
                self.entries[idx] = new_entry
                return True
        return False

    def iter_by_prefix(self, prefix: str) -> Iterable[AbilityEntry]:
        for entry in self.entries:
            if entry.header.startswith(prefix):
                yield entry
