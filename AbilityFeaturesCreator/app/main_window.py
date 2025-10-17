from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from functools import partial

from PySide6.QtCore import Qt, QModelIndex, QUrl
from PySide6.QtGui import (
    QAction,
    QCursor,
    QTextCursor,
    QDesktopServices,
    QTextDocument,
    QTextOption,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QLineEdit,
    QComboBox,
    QTextBrowser,
    QToolButton,
    QInputDialog,
    QFormLayout,
)

from . import ability_data
from .models import AbilityDocument, AbilityEntry


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._base_title = "Ability Features Builder"
        self._dirty = False
        self.setWindowTitle(self._base_title)
        self.resize(1300, 900)

        self._document: Optional[AbilityDocument] = None
        self._document_path: Optional[Path] = None
        self._preview_window: Optional[QMainWindow] = None
        self._preview_editor: Optional[QPlainTextEdit] = None
        self.require_confirmations = True
        self._selected_template_item: Optional[QListWidgetItem] = None
        self._template_selection_recent = False
        self.template_sets: Dict[str, Dict[str, List[ability_data.AbilityTemplate]]] = {}
        self.current_template_set: str = ""
        self._last_preview_find: str = ""
        self._preview_find_bar: Optional[QWidget] = None
        self._preview_find_input: Optional[QLineEdit] = None
        self._preview_find_status: Optional[QLabel] = None
        self._preview_shortcuts: List[QShortcut] = []
        self._templates_dir = Path(__file__).resolve().parent / "templates"
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._template_set_paths: Dict[str, Path] = {}

        self._load_default_templates()
        self._load_saved_template_sets()

        self._build_menu()
        self._build_ui()
        self._populate_type_picker()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        splitter = QSplitter(orientation=Qt.Horizontal)
        splitter.setHandleWidth(6)

        # Left panel: current document entries
        self.entry_filter = QLineEdit()
        self.entry_filter.setPlaceholderText("Filter entries…")
        self.entry_filter.textChanged.connect(self._on_entry_filter_changed)
        self.entry_list = QListWidget()
        self.entry_list.currentItemChanged.connect(self._on_entry_selected)
        self.entry_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.entry_list.customContextMenuRequested.connect(self._show_entry_context_menu)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Loaded Entries"))
        left_layout.addWidget(self.entry_filter)
        left_layout.addWidget(self.entry_list)
        delete_row = QHBoxLayout()
        self.delete_entry_btn = QPushButton("Delete entry")
        self.delete_entry_btn.clicked.connect(self._delete_entry)
        self.delete_entry_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        delete_row.addWidget(self.delete_entry_btn)
        self.duplicate_entry_btn = QPushButton("Duplicate entry")
        self.duplicate_entry_btn.clicked.connect(self._duplicate_entry)
        self.duplicate_entry_btn.setEnabled(False)
        self.duplicate_entry_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        delete_row.addWidget(self.duplicate_entry_btn)
        delete_row.setSpacing(6)
        left_layout.addLayout(delete_row)



        move_buttons = QHBoxLayout()
        self.move_up_btn = QPushButton("Move up")
        self.move_up_btn.clicked.connect(self._move_entry_up)
        self.move_up_btn.setEnabled(False)
        move_buttons.addWidget(self.move_up_btn)
        self.move_down_btn = QPushButton("Move down")
        self.move_down_btn.clicked.connect(self._move_entry_down)
        self.move_down_btn.setEnabled(False)
        move_buttons.addWidget(self.move_down_btn)
        left_layout.addLayout(move_buttons)

        load_btn = QPushButton("Open AbilityFeatures.txt…")
        load_btn.clicked.connect(self._open_file)
        left_layout.addWidget(load_btn)

        self.reload_button = QPushButton("Reload from disk")
        self.reload_button.clicked.connect(self._reload_file)
        self.reload_button.setEnabled(False)
        left_layout.addWidget(self.reload_button)

        self.preview_doc_btn = QPushButton("Preview full document")
        self.preview_doc_btn.clicked.connect(self._show_document_preview)
        self.preview_doc_btn.setEnabled(False)
        left_layout.addWidget(self.preview_doc_btn)

        clear_selection_btn = QPushButton("New blank entry")
        clear_selection_btn.clicked.connect(self._start_blank_entry)
        left_layout.addWidget(clear_selection_btn)

        splitter.addWidget(left_panel)

        # Right panel: editors, templates, and options
        right_panel = QWidget()
        right_layout = QHBoxLayout(right_panel)

        type_box = QGroupBox("Ability type")
        type_box.setToolTip("Choose whether you are editing a Support Ability or Active Ability block.")
        type_layout = QVBoxLayout(type_box)
        self.type_list = QListWidget()
        self.type_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.type_list.currentItemChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_list)
        type_layout.setStretchFactor(self.type_list, 1)
        self.type_description = QLabel()
        self.type_description.setWordWrap(True)
        type_layout.addWidget(self.type_description)

        template_box = QGroupBox("Templates for this type")
        template_box.setToolTip("Pre-built examples you can insert and customise.")
        template_layout = QVBoxLayout(template_box)
        selector_row = QHBoxLayout()
        selector_label = QLabel("Template set:")
        selector_row.addWidget(selector_label)
        self.template_set_box = QComboBox()
        self.template_set_box.currentTextChanged.connect(self._on_template_set_changed)
        selector_row.addWidget(self.template_set_box, stretch=1)
        template_layout.addLayout(selector_row)
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        self.template_list.itemClicked.connect(self._on_template_clicked)
        template_layout.addWidget(self.template_list)
        template_buttons = QHBoxLayout()
        template_buttons.addStretch(1)
        self.delete_template_btn = QPushButton("Delete template")
        self.delete_template_btn.clicked.connect(self._delete_selected_template)
        self.delete_template_btn.setEnabled(False)
        template_buttons.addWidget(self.delete_template_btn)
        template_layout.addLayout(template_buttons)

        preview_box = QGroupBox("Template preview / editing")
        preview_layout = QVBoxLayout(preview_box)
        self.template_preview = QPlainTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout.addWidget(self.template_preview)

        apply_btn = QPushButton("Insert template into editor")
        apply_btn.clicked.connect(self._insert_template)
        preview_layout.addWidget(apply_btn)

        editor_box = QGroupBox("Entry editor")
        editor_layout = QVBoxLayout(editor_box)
        self.entry_editor = QPlainTextEdit()
        self.entry_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor_layout.addWidget(self.entry_editor)

        button_row = QHBoxLayout()
        self.save_entry_btn = QPushButton("Replace selected entry")
        self.save_entry_btn.clicked.connect(self._replace_entry)
        button_row.addWidget(self.save_entry_btn)

        self.append_entry_btn = QPushButton("Append as new entry")
        self.append_entry_btn.clicked.connect(self._append_entry)
        button_row.addWidget(self.append_entry_btn)

        self.validate_entry_btn = QPushButton("Validate entry")
        self.validate_entry_btn.clicked.connect(self._validate_entry)
        button_row.addWidget(self.validate_entry_btn)

        self.save_template_btn = QPushButton("Save as template…")
        self.save_template_btn.clicked.connect(self._save_entry_as_template)
        button_row.addWidget(self.save_template_btn)

        editor_layout.addLayout(button_row)

        preview_editor_splitter = QSplitter(orientation=Qt.Vertical)
        preview_editor_splitter.addWidget(preview_box)
        preview_editor_splitter.addWidget(editor_box)
        preview_editor_splitter.setStretchFactor(0, 1)
        preview_editor_splitter.setStretchFactor(1, 1)

        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(8)
        options_layout.addWidget(type_box)
        options_layout.addWidget(template_box)
        options_layout.addStretch(1)
        options_widget.setMinimumWidth(300)
        options_widget.setMaximumWidth(440)

        right_splitter = QSplitter(orientation=Qt.Horizontal)
        right_splitter.addWidget(options_widget)
        right_splitter.addWidget(preview_editor_splitter)
        right_splitter.setStretchFactor(0, 0)
        right_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(right_splitter)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Pick an ability type to begin.")

        self._refresh_template_set_box()

        # Populate defaults
        if self.type_list.count():
            self.type_list.setCurrentRow(0)

    def _load_default_templates(self) -> None:
        self.template_sets["Default"] = ability_data.default_templates_by_type()
        self.current_template_set = "Default"
        default_path = self._template_file_for("Default")
        self._template_set_paths["Default"] = default_path
        if default_path.exists():
            try:
                data = json.loads(default_path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Failed to load custom Default templates: {exc}")
            else:
                templates = ability_data.templates_from_dict(data)
                if templates:
                    self.template_sets["Default"] = templates

    def _load_saved_template_sets(self) -> None:
        if not self._templates_dir.exists():
            return
        default_path = self._template_set_paths.get("Default")
        for path in sorted(self._templates_dir.glob("*.json")):
            if default_path and path == default_path:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Failed to load template set from {path}: {exc}")
                continue
            name = str(data.get("name") or path.stem)
            templates = ability_data.templates_from_dict(data)
            if not templates:
                continue
            self.template_sets[name] = templates
            self._template_set_paths[name] = path
        if self.current_template_set not in self.template_sets and self.template_sets:
            self.current_template_set = next(iter(self.template_sets))

    def _template_map(self) -> Dict[str, List[ability_data.AbilityTemplate]]:
        return self.template_sets.get(self.current_template_set, {})

    def _template_file_for(self, name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()) or "templates"
        return self._templates_dir / f"{safe}.json"

    def _refresh_template_set_box(self, target: Optional[str] = None) -> None:
        if not hasattr(self, "template_set_box"):
            return
        names = sorted(self.template_sets.keys())
        target_name = target or self.current_template_set
        self.template_set_box.blockSignals(True)
        self.template_set_box.clear()
        for name in names:
            self.template_set_box.addItem(name)
        index = names.index(target_name) if target_name in names else (0 if names else -1)
        if index >= 0:
            self.template_set_box.setCurrentIndex(index)
            self.current_template_set = names[index]
        self.template_set_box.blockSignals(False)
        self._update_template_actions()

    def _on_template_set_changed(self, name: str) -> None:
        if not name or name == self.current_template_set or name not in self.template_sets:
            return
        self.current_template_set = name
        type_key = self._current_type_key()
        if type_key:
            self._populate_templates(type_key)
        else:
            self.template_list.clear()
        self.template_preview.clear()
        self._update_template_actions()

    def _current_type_key(self) -> Optional[str]:
        item = self.type_list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _update_template_actions(self) -> None:
        has_selection = self.template_list.currentItem() is not None
        if hasattr(self, "delete_template_btn"):
            self.delete_template_btn.setEnabled(has_selection)

    def _update_entry_actions(self) -> None:
        row = self.entry_list.currentRow()
        has_selection = row >= 0
        max_index = self.entry_list.count() - 1
        if hasattr(self, "move_up_btn"):
            self.move_up_btn.setEnabled(has_selection and row > 0)
        if hasattr(self, "move_down_btn"):
            self.move_down_btn.setEnabled(has_selection and row < max_index and max_index >= 0)
        if hasattr(self, "duplicate_entry_btn"):
            self.duplicate_entry_btn.setEnabled(has_selection)

    def _entry_text_for_editing(self, entry: AbilityEntry) -> str:
        lines = [entry.header]
        lines.extend(entry.body_lines)
        return "\n".join(lines)

    def _parse_entry_text(
        self, raw: str, *, require_type: bool = False
    ) -> Optional[Tuple[AbilityEntry, Optional[str]]]:
        raw = raw.strip()
        if not raw:
            QMessageBox.information(self, "Empty entry", "Write or paste an entry first.")
            return None
        try:
            entry = AbilityEntry.from_text(raw)
        except ValueError as exc:
            QMessageBox.information(self, "Invalid entry", str(exc))
            return None
        type_key = self._detect_entry_type(entry.header)
        if require_type and not type_key:
            QMessageBox.information(
                self,
                "Missing ability type",
                "No ability header (e.g. >SA or >AA) was detected.",
            )
            return None
        return entry, type_key

    def _validate_entry(self) -> None:
        result = self._parse_entry_text(self.entry_editor.toPlainText(), require_type=True)
        if not result:
            return
        _, type_key = result
        type_label = ability_data.ABILITY_TYPES.get(type_key or "", {}).get("label", type_key or "unknown")
        QMessageBox.information(self, "Entry valid", f"Detected ability type: {type_label}.")
        self.statusBar().showMessage("Entry validation succeeded.", 5000)

    def _save_template_set(
        self,
        name: str,
        mapping: Optional[Dict[str, List[ability_data.AbilityTemplate]]] = None,
        *,
        show_message: bool = False,
    ) -> bool:
        if name not in self.template_sets and mapping is None:
            return False
        set_mapping = mapping if mapping is not None else self.template_sets.get(name)
        if set_mapping is None:
            return False
        path = self._template_set_paths.get(name)
        if path is None:
            path = self._template_file_for(name)
            self._template_set_paths[name] = path
        data = ability_data.templates_to_dict(name, set_mapping)
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Failed to save templates", f"{exc}")
            return False
        if show_message:
            self.statusBar().showMessage(f"Saved template set '{name}'.", 5000)
        return True

    def _import_template_set(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import template file",
            str(self._templates_dir),
            "Template files (*.json);;All files (*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", f"Could not read template file:\n{exc}")
            return
        name = str(data.get("name") or path.stem)
        templates = ability_data.templates_from_dict(data)
        if not templates:
            QMessageBox.information(self, "No templates", "The selected file did not contain any templates.")
            return
        if name in self.template_sets:
            confirm = QMessageBox.question(
                self,
                "Template set exists",
                f"Replace the existing template set '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        self.template_sets[name] = templates
        if self._save_template_set(name, templates, show_message=False):
            self._refresh_template_set_box(name)
            type_key = self._current_type_key()
            if type_key:
                self._populate_templates(type_key)
            self.statusBar().showMessage(f"Imported template set '{name}'.", 5000)

    def _export_current_template_set(self) -> None:
        if not self.current_template_set:
            QMessageBox.information(self, "No template set", "No template set is currently selected.")
            return
        mapping = self.template_sets.get(self.current_template_set)
        if mapping is None:
            QMessageBox.information(self, "No templates", "The current template set does not exist.")
            return
        if not any(mapping.values()):
            QMessageBox.information(self, "Empty set", "The current template set is empty.")
            return
        suggested = self._template_file_for(self.current_template_set).name
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export template file",
            str(self._templates_dir / suggested),
            "Template files (*.json);;All files (*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        if not path.suffix:
            path = path.with_suffix(".json")
        data = ability_data.templates_to_dict(self.current_template_set, mapping)
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", f"Could not write template file:\n{exc}")
            return
        self.statusBar().showMessage(
            f"Exported template set '{self.current_template_set}' to {path.name}.",
            5000,
        )

    def _create_template_set(self) -> None:
        name, ok = QInputDialog.getText(self, "Create template set", "Template set name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.information(self, "Invalid name", "Enter a name for the template set.")
            return
        if name in self.template_sets:
            QMessageBox.information(self, "Exists", "A template set with that name already exists.")
            return
        self.template_sets[name] = {}
        if self._save_template_set(name, show_message=False):
            self._refresh_template_set_box(name)
            type_key = self._current_type_key()
            if type_key:
                self._populate_templates(type_key)
            self.statusBar().showMessage(f"Created template set '{name}'.", 5000)

    def _delete_template_set(self) -> None:
        if not self.current_template_set:
            QMessageBox.information(self, "No template set", "No template set is currently selected.")
            return
        if self.current_template_set == "Default":
            QMessageBox.information(self, "Protected set", "The Default template set cannot be deleted.")
            return
        name = self.current_template_set
        path = self._template_set_paths.get(name)
        filename = f" ({path.name})" if path else ""
        confirm = QMessageBox.question(
            self,
            "Delete template set",
            f"Delete the template set '{name}'{filename}? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        if path and path.exists():
            try:
                path.unlink()
            except Exception as exc:
                QMessageBox.critical(self, "Delete failed", f"Could not remove {path.name}:\n{exc}")
                return
        self.template_sets.pop(name, None)
        self._template_set_paths.pop(name, None)
        new_name = "Default" if "Default" in self.template_sets else next(iter(self.template_sets), "")
        self.current_template_set = new_name
        self._refresh_template_set_box(new_name)
        type_key = self._current_type_key()
        if type_key:
            self._populate_templates(type_key)
        else:
            self.template_list.clear()
            self.template_preview.clear()
        self.statusBar().showMessage(f"Deleted template set '{name}'.", 5000)

    def _templates_for_type(self, type_key: str) -> List[ability_data.AbilityTemplate]:
        mapping = self._template_map()
        return mapping.get(type_key, [])

    def _populate_type_picker(self) -> None:
        self.type_list.clear()
        for key, info in ability_data.ABILITY_TYPES.items():
            item = QListWidgetItem(info["label"])
            item.setData(Qt.UserRole, key)
            item.setToolTip(info["tooltip"])
            self.type_list.addItem(item)
        type_count = max(1, len(ability_data.ABILITY_TYPES))
        self.type_list.setMinimumHeight(type_count * 32)
        self.type_list.setMaximumHeight(type_count * 32)
        if self.type_list.count():
            self.type_list.setCurrentRow(0)

    def _resize_list(self, widget: QListWidget, min_rows: int = 1, max_rows: int = 6) -> None:
        count = widget.count()
        if count == 0:
            base = self.fontMetrics().height() * max(min_rows, 1) + 12
            widget.setMinimumHeight(base)
            widget.setMaximumHeight(base)
            return
        row_height = widget.sizeHintForRow(0)
        visible = max(min_rows, min(max_rows, count))
        height = row_height * visible + widget.frameWidth() * 2 + 6
        widget.setMinimumHeight(height)
        widget.setMaximumHeight(height)

    # ---------------------------------------------------------------- Document IO
    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open AbilityFeatures file",
            str(self._document_path or Path.cwd()),
            "AbilityFeatures (*.txt);;All files (*)",
        )
        if not path:
            return
        file_path = Path(path)
        try:
            document = AbilityDocument.load(file_path)
        except Exception as exc:  # pragma: no cover - GUI path
            QMessageBox.critical(self, "Failed to load", f"{exc}")
            return
        self._document = document
        self._document_path = file_path
        self.entry_filter.blockSignals(True)
        self.entry_filter.clear()
        self.entry_filter.blockSignals(False)
        self._update_entry_list()
        self._mark_dirty(False)
        self._update_file_actions()
        self._refresh_preview()
        self.statusBar().showMessage(f"Loaded {len(document.entries)} entries from {path}")

    def _update_entry_list(
        self,
        *,
        select_entry: Optional[AbilityEntry] = None,
        select_row: Optional[int] = None,
    ) -> None:
        self.entry_list.blockSignals(True)
        target_entry = select_entry
        target_header: Optional[str] = None
        if target_entry is None and select_row is None:
            current_item = self.entry_list.currentItem()
            if current_item:
                current_entry: Optional[AbilityEntry] = current_item.data(Qt.UserRole)
                if current_entry:
                    target_entry = current_entry
                    target_header = current_entry.header
                else:
                    target_header = current_item.text()
        elif target_entry is not None:
            target_header = target_entry.header

        self.entry_list.clear()
        chosen_row: Optional[int] = None
        if not self._document:
            self.entry_list.blockSignals(False)
            self._update_entry_actions()
            return

        filter_text = self.entry_filter.text().lower()
        for entry in self._document.entries:
            haystack = " ".join([entry.header, *entry.body_lines]).lower()
            if filter_text and filter_text not in haystack:
                continue
            item = QListWidgetItem(entry.header)
            item.setData(Qt.UserRole, entry)
            self.entry_list.addItem(item)
            if target_entry is entry:
                chosen_row = self.entry_list.count() - 1
            elif chosen_row is None and target_entry is None and target_header and entry.header == target_header:
                chosen_row = self.entry_list.count() - 1

        self.entry_list.blockSignals(False)

        if select_row is not None and 0 <= select_row < self.entry_list.count():
            self.entry_list.setCurrentRow(select_row)
        elif chosen_row is not None and 0 <= chosen_row < self.entry_list.count():
            self.entry_list.setCurrentRow(chosen_row)
        elif self.entry_list.count():
            self.entry_list.setCurrentRow(0)

        self._update_entry_actions()

    # ---------------------------------------------------------------- Menu actions
    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        self.open_action = QAction("Open…", self)
        self.open_action.triggered.connect(self._open_file)
        file_menu.addAction(self.open_action)

        self.reload_action = QAction("Reload", self)
        self.reload_action.triggered.connect(self._reload_file)
        self.reload_action.setEnabled(False)
        file_menu.addAction(self.reload_action)

        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self._save_file)
        self.save_action.setEnabled(False)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Save As…", self)
        self.save_as_action.triggered.connect(self._save_file_as)
        self.save_as_action.setEnabled(False)
        file_menu.addAction(self.save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        preferences_action = QAction("Preferences…", self)
        preferences_action.triggered.connect(self._open_preferences)
        edit_menu.addAction(preferences_action)

        self.tools_menu = self.menuBar().addMenu("Tools")
        templates_menu = self.tools_menu.addMenu("Templates")

        import_templates_action = QAction("Import template file…", self)
        import_templates_action.triggered.connect(self._import_template_set)
        templates_menu.addAction(import_templates_action)

        export_templates_action = QAction("Export current template file…", self)
        export_templates_action.triggered.connect(self._export_current_template_set)
        templates_menu.addAction(export_templates_action)

        templates_menu.addSeparator()

        new_set_action = QAction("Create new template set…", self)
        new_set_action.triggered.connect(self._create_template_set)
        templates_menu.addAction(new_set_action)

        delete_set_action = QAction("Delete current template set…", self)
        delete_set_action.triggered.connect(self._delete_template_set)
        templates_menu.addAction(delete_set_action)

        self.help_menu = self.menuBar().addMenu("Help")

        feature_types_action = QAction("Feature types…", self)
        feature_types_action.triggered.connect(self._show_feature_types_help)
        self.help_menu.addAction(feature_types_action)

        self.ncalc_menu = self.help_menu.addMenu("NCalc formulas")
        self._populate_ncalc_menu()

    def _save_file(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open or create a document first.")
            return
        if not self._document_path:
            self._save_file_as()
            return
        self._perform_save(self._document_path)

    def _save_file_as(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open or create a document first.")
            return
        default_dir = str(self._document_path.parent) if self._document_path else str(Path.cwd())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save AbilityFeatures file",
            default_dir,
            "AbilityFeatures (*.txt);;All files (*)",
        )
        if not path:
            return
        self._document_path = Path(path)
        self._perform_save(self._document_path)

    def _reload_file(self, checked: bool = False) -> None:
        if not self._document_path:
            QMessageBox.information(self, "No file", "Open a document before reloading.")
            return
        if self._dirty:
            confirm = QMessageBox.question(
                self,
                "Discard changes",
                "Reloading will discard unsaved changes. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        try:
            document = AbilityDocument.load(self._document_path)
        except Exception as exc:
            QMessageBox.critical(self, "Failed to reload", f"{exc}")
            return
        self._document = document
        self.entry_filter.blockSignals(True)
        self.entry_filter.clear()
        self.entry_filter.blockSignals(False)
        self._update_entry_list()
        self._mark_dirty(False)
        self._refresh_preview()
        self.statusBar().showMessage(f"Reloaded {self._document_path}")

    def _perform_save(self, path: Path) -> None:
        assert self._document is not None
        text = self._document.to_text().rstrip() + "\n"
        path.write_text(text, encoding="utf-8")
        self._mark_dirty(False)
        self._refresh_preview()
        self.statusBar().showMessage(f"Saved {path}")

    def _update_file_actions(self) -> None:
        has_document = self._document is not None
        self.save_as_action.setEnabled(has_document)
        self.save_action.setEnabled(has_document and self._document_path is not None)
        can_reload = has_document and self._document_path is not None
        self.reload_action.setEnabled(can_reload)
        if hasattr(self, "reload_button"):
            self.reload_button.setEnabled(can_reload)
        if hasattr(self, "preview_doc_btn"):
            self.preview_doc_btn.setEnabled(has_document)

    def _open_preferences(self) -> None:
        dialog = PreferencesDialog(self, self.require_confirmations)
        if dialog.exec() == QDialog.Accepted:
            self.require_confirmations = dialog.ask_confirmations
            state = "enabled" if self.require_confirmations else "disabled"
            self.statusBar().showMessage(f"Delete confirmations {state}.")

    def _show_feature_types_help(self) -> None:
        dialog = FeatureTypesDialog(self)
        dialog.exec()

    def _populate_ncalc_menu(self) -> None:
        if not hasattr(self, "ncalc_menu"):
            return
        self.ncalc_menu.clear()
        for link in ability_data.ncalc_links():
            action = self.ncalc_menu.addAction(link["label"])
            action.triggered.connect(partial(self._open_url, link["url"]))

    def _open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def _update_window_title(self) -> None:
        if not self._document:
            self.setWindowTitle(self._base_title)
            return
        name = self._document_path.name if self._document_path else "Untitled"
        suffix = "*" if self._dirty else ""
        self.setWindowTitle(f"{self._base_title} - {name}{suffix}")

    def _mark_dirty(self, dirty: bool = True) -> None:
        if self._document is None:
            return
        self._dirty = dirty
        self._update_window_title()
        self._update_file_actions()


    # ---------------------------------------------------------------- Callbacks
    def _on_type_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if not current:
            return
        key = current.data(Qt.UserRole)
        info = ability_data.ABILITY_TYPES.get(key)
        if not info:
            return
        self.type_description.setText(info["tooltip"])
        self._populate_templates(key)
        self.template_preview.clear()

    def _populate_templates(self, type_key: str) -> None:
        self.template_list.clear()
        for template in self._templates_for_type(type_key):
            item = QListWidgetItem(template.label)
            item.setData(Qt.UserRole, template)
            item.setToolTip(template.description)
            self.template_list.addItem(item)
        self._resize_list(self.template_list, min_rows=1, max_rows=8)
        if self.template_list.count() and not self.template_list.currentItem():
            self.template_list.setCurrentRow(0)
        if not self.template_list.count():
            self.template_preview.clear()
        self._update_template_actions()

    def _on_template_selected(self, current: QListWidgetItem, previous: Optional[QListWidgetItem]) -> None:  # noqa: D401
        self._update_template_actions()
        if not current:
            self._selected_template_item = None
            self.template_preview.clear()
            return
        template = current.data(Qt.UserRole)
        if not template:
            return
        self._selected_template_item = current
        self._template_selection_recent = True
        blocks = ability_data.blocks_for(template.block_sequence)
        block_summary = "\n".join(f"• {blk.label}: {blk.description}" for blk in blocks)

        placeholder_summary = "\n".join(
            f"• {{{name}}}: {desc}" for name, desc in template.placeholders.items()
        )

        parts = [
            f"# Target type: {template.target_type}",
            f"# Scope: {template.scope_key}",
            "# Blocks:",
            block_summary,
        ]

        if placeholder_summary:
            parts.extend(["", "# Placeholders:", placeholder_summary])

        if template.notes:
            parts.extend(["", f"# Notes: {template.notes}"])

        if template.example:
            parts.extend(["", template.example.strip()])

        parts.extend(["", template.body])

        self.template_preview.setPlainText("\n".join(parts))

    def _on_entry_selected(self, current: QListWidgetItem, previous: Optional[QListWidgetItem]) -> None:
        self._update_entry_actions()
        if not current:
            self.entry_editor.clear()
            return
        entry: AbilityEntry = current.data(Qt.UserRole)
        self.entry_editor.setPlainText(self._entry_text_for_editing(entry))

    # ---------------------------------------------------------------- Editing helpers
    def _insert_template(self) -> None:
        template_item = self.template_list.currentItem()
        if not template_item:
            QMessageBox.information(self, "No template", "Select a template first.")
            return
        template = template_item.data(Qt.UserRole)
        if not template:
            return
        self.entry_editor.insertPlainText(template.body)
        self.statusBar().showMessage("Template inserted. Fill in the placeholders before saving.")

    def _save_entry_as_template(self) -> None:
        raw = self.entry_editor.toPlainText()
        result = self._parse_entry_text(raw, require_type=True)
        if not result:
            return
        parsed_entry, type_key = result
        type_key = type_key or ""

        current_item = self.entry_list.currentItem()
        current_entry: Optional[AbilityEntry] = current_item.data(Qt.UserRole) if current_item else None

        header_line = parsed_entry.header
        suggested_label = self._suggest_template_label(header_line)
        suggested_description = self._suggest_template_description(header_line)

        comment_source = self._extract_leading_comments(parsed_entry.body_lines)
        if not comment_source and current_entry:
            comment_source = self._extract_leading_comments(current_entry.body_lines)
        default_notes_lines = [line.strip() for line in comment_source]
        default_notes = "\n".join(default_notes_lines).strip()

        placeholder_names = sorted(set(re.findall(r"{([A-Za-z0-9_]+)}", raw)))
        detected_blocks = self._detect_block_sequence(raw)

        dialog = TemplateDetailsDialog(
            self,
            target_type=type_key or "",
            default_label=suggested_label,
            default_description=suggested_description,
            default_notes=default_notes,
            placeholder_names=placeholder_names,
            selected_blocks=detected_blocks,
        )
        if dialog.exec() != QDialog.Accepted or not dialog.result:
            return

        name = dialog.result["label"]
        template_set = self.template_sets.setdefault(self.current_template_set, {})
        templates_for_type = template_set.setdefault(type_key or "", [])

        existing = next((tpl for tpl in templates_for_type if tpl.label == name), None)
        if existing:
            confirm = QMessageBox.question(
                self,
                "Replace template",
                f"A template named '{name}' already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
            templates_for_type.remove(existing)

        template_id = existing.template_id if existing else self._generate_template_id(name)
        new_template = ability_data.AbilityTemplate(
            template_id=template_id,
            target_type=type_key or "",
            label=name,
            description=dialog.result["description"],
            scope_key=dialog.result["scope_key"],
            block_sequence=dialog.result["block_sequence"],
            body=raw.strip(),
            placeholders=dialog.result["placeholders"],
            example=dialog.result["example"],
            notes=dialog.result["notes"],
        )
        templates_for_type.append(new_template)

        if self._save_template_set(self.current_template_set, show_message=False):
            if self._current_type_key() == type_key:
                self._populate_templates(type_key)
                matches = self.template_list.findItems(name, Qt.MatchExactly)
                if matches:
                    self.template_list.setCurrentItem(matches[-1])
            self.statusBar().showMessage(
                f"Saved template '{name}' to set '{self.current_template_set}'.",
                5000,
            )


    def _move_entry_up(self) -> None:
        self._move_entry(-1)

    def _move_entry_down(self) -> None:
        self._move_entry(1)

    def _move_entry(self, delta: int) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open a file before reordering entries.")
            return
        row = self.entry_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "No entry selected", "Choose an entry to move.")
            return
        new_row = row + delta
        if new_row < 0 or new_row >= len(self._document.entries):
            return
        if not self._document.move(row, new_row):
            return
        self._update_entry_list(select_row=new_row)
        self._mark_dirty()
        self._refresh_preview()
        direction = "up" if delta < 0 else "down"
        self.statusBar().showMessage(f"Moved entry {direction}.", 5000)

    def _delete_selected_template(self) -> None:
        item = self.template_list.currentItem()
        if not item:
            QMessageBox.information(self, "No template", "Select a template to delete.")
            return
        template: ability_data.AbilityTemplate = item.data(Qt.UserRole)
        if not template:
            return
        confirm = QMessageBox.question(
            self,
            "Delete template",
            f"Remove template '{template.label}' from the current set?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        mapping = self._template_map()
        templates = mapping.get(template.target_type)
        if not templates:
            return
        try:
            templates.remove(template)
        except ValueError:
            return
        if self._save_template_set(self.current_template_set, show_message=False):
            self._populate_templates(template.target_type)
            self.template_preview.clear()
            self.statusBar().showMessage(f"Deleted template '{template.label}'.", 5000)

    def _detect_entry_type(self, text: str) -> Optional[str]:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break
        else:
            return None
        if not first_line.startswith(">"):
            return None
        header = re.sub(r"\s+", " ", first_line[1:].strip())
        patterns = [
            (r"^SA\s+GLOBALENEMY\+", "SA_GLOBAL_ENEMY"),
            (r"^SA\s+GLOBALLAST\+", "SA_GLOBAL_LAST"),
            (r"^SA\s+GLOBAL\+", "SA_GLOBAL"),
            (r"^SA\b", "SA"),
            (r"^AA\s+GLOBAL\+", "AA_GLOBAL"),
            (r"^AA\b", "AA"),
        ]
        for pattern, type_key in patterns:
            if re.match(pattern, header, flags=re.IGNORECASE):
                return type_key
        return None

    def _suggest_template_label(self, header_line: str) -> str:
        header = header_line[1:].strip() if header_line.startswith(">") else header_line.strip()
        if "~~" in header:
            return header.split("~~", 1)[1].strip()
        return header

    def _suggest_template_description(self, header_line: str) -> str:
        match = re.search(r"~~\s*(.+)", header_line)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_leading_comments(self, body_lines: List[str]) -> List[str]:
        comments: List[str] = []
        collecting = False
        for line in body_lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                comments.append(line.rstrip())
                collecting = True
            elif stripped == "" and collecting:
                comments.append("")
            elif collecting:
                break
        return comments

    def _detect_block_sequence(self, text: str) -> List[str]:
        ordered: List[str] = []
        for line in text.splitlines():
            match = re.search(r"\[code=([A-Za-z0-9_]+)", line)
            if not match:
                continue
            key = match.group(1)
            if key in ability_data.FEATURE_BLOCKS and key not in ordered:
                ordered.append(key)
        return ordered

    def _generate_template_id(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "custom"
        existing_ids = {
            tpl.template_id
            for templates in self.template_sets.get(self.current_template_set, {}).values()
            for tpl in templates
        }
        if base not in existing_ids:
            return base
        for number in range(2, 10000):
            candidate = f"{base}_{number}"
            if candidate not in existing_ids:
                return candidate
        return f"{base}_{uuid4().hex[:6]}"

    def _replace_entry(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open a file first.")
            return
        item = self.entry_list.currentItem()
        if not item:
            QMessageBox.information(self, "No entry selected", "Choose an entry to replace.")
            return
        raw = self.entry_editor.toPlainText().strip()
        if not raw:
            QMessageBox.information(self, "Empty entry", "Editor is empty.")
            return
        parsed = self._parse_entry_text(raw, require_type=True)
        if not parsed:
            return
        new_entry, _ = parsed
        replaced = self._document.replace(item.text(), new_entry)
        if not replaced:
            QMessageBox.warning(self, "Header mismatch", "Could not find matching entry in document.")
            return
        item.setText(new_entry.header)
        item.setData(Qt.UserRole, new_entry)
        self._mark_dirty()
        self._refresh_preview()
        self.statusBar().showMessage("Entry replaced.")

    def _append_entry(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open a file first.")
            return
        raw = self.entry_editor.toPlainText().strip()
        if not raw:
            QMessageBox.information(self, "Empty entry", "Editor is empty.")
            return
        parsed = self._parse_entry_text(raw, require_type=True)
        if not parsed:
            return
        new_entry, _ = parsed
        insert_index = len(self._document.entries)
        current_row = self.entry_list.currentRow()
        if current_row >= 0:
            insert_index = current_row + 1
        self._document.insert(insert_index, new_entry)
        self._update_entry_list(select_entry=new_entry)
        self._mark_dirty()
        self._refresh_preview()
        self.statusBar().showMessage("Entry added to document.")


    def _duplicate_entry(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open a file first.")
            return
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._document.entries):
            QMessageBox.information(self, "No entry selected", "Choose an entry to duplicate.")
            return
        source = self._document.entries[row]
        try:
            duplicate = AbilityEntry.from_text(source.to_text())
        except ValueError as exc:
            QMessageBox.information(self, "Could not duplicate", str(exc))
            return

        base_header = duplicate.header
        headers = {entry.header for entry in self._document.entries}
        if base_header in headers:
            suffix = " (Copy)"
            candidate = f"{base_header}{suffix}"
            counter = 2
            while candidate in headers:
                candidate = f"{base_header} (Copy {counter})"
                counter += 1
            duplicate.header = candidate
        self._document.insert(row + 1, duplicate)
        self._update_entry_list(select_entry=duplicate)
        self._mark_dirty()
        self._refresh_preview()
        self.statusBar().showMessage(f"Duplicated entry as {duplicate.header}.", 5000)

    def _delete_entry(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open a file first.")
            return
        item = self.entry_list.currentItem()
        if not item:
            QMessageBox.information(self, "No entry selected", "Choose an entry to delete.")
            return
        row = self.entry_list.currentRow()
        if self.require_confirmations:
            confirm = QMessageBox.question(
                self,
                "Delete entry",
                "Remove the selected entry from the document?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        try:
            self._document.entries.pop(row)
        except IndexError:
            pass
        self.entry_editor.clear()
        self._mark_dirty()
        self._refresh_preview()
        self.statusBar().showMessage("Entry deleted.")
        if self._document and self._document.entries:
            next_row = min(row, len(self._document.entries) - 1)
            self._update_entry_list(select_row=next_row)
        else:
            self._update_entry_list()

    def _start_blank_entry(self) -> None:
        self.entry_editor.clear()
        placeholder = (
            ">TYPE ID Comment\n"
            "# Fill in the ability header and add [code=...] lines below."
        )
        self.entry_editor.setPlainText(placeholder)
        cursor = self.entry_editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.entry_editor.setTextCursor(cursor)
        self.statusBar().showMessage("Editing blank entry. Use Append to add it to the document.")

    def _on_entry_filter_changed(self, text: str) -> None:
        self._update_entry_list()

    def _show_entry_context_menu(self, point) -> None:
        menu = QMenu(self)
        clear_action = menu.addAction("Clear selection")
        delete_action = menu.addAction("Delete entry")
        copy_action = menu.addAction("Copy entry to editor")
        action = menu.exec(QCursor.pos())
        if action == clear_action:
            self.entry_list.clearSelection()
            self.entry_editor.clear()
        elif action == delete_action:
            self._delete_entry()
        elif action == copy_action:
            current = self.entry_list.currentItem()
            if current:
                entry: AbilityEntry = current.data(Qt.UserRole)
                self.entry_editor.setPlainText(self._entry_text_for_editing(entry))

    def _on_template_clicked(self, item: QListWidgetItem) -> None:
        if self._selected_template_item is item:
            if self._template_selection_recent:
                # First click after selection change; keep selection
                self._template_selection_recent = False
                return
            self._clear_template_selection()

    def _clear_template_selection(self) -> None:
        self.template_list.blockSignals(True)
        self.template_list.selectionModel().clearSelection()
        self.template_list.setCurrentIndex(QModelIndex())
        self.template_list.blockSignals(False)
        self._selected_template_item = None
        self._template_selection_recent = False
        self.template_preview.clear()
        self._update_template_actions()

    def _show_document_preview(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No document", "Open a file first.")
            return
        if self._preview_window and self._preview_window.isVisible():
            self._preview_window.raise_()
            self._preview_window.activateWindow()
            self._refresh_preview()
            return

        window = QMainWindow(self)
        window.setWindowTitle("Document preview")
        preview = QPlainTextEdit()
        preview.setReadOnly(True)

        self._preview_window = window
        self._preview_editor = preview

        container = QWidget(window)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        find_bar = self._ensure_preview_find_bar(preview)
        layout.addWidget(find_bar)
        layout.addWidget(preview)
        window.setCentralWidget(container)
        window.resize(900, 700)

        self._setup_preview_shortcuts(preview)
        window.destroyed.connect(self._clear_preview_window)

        self._refresh_preview()
        window.show()

    def _refresh_preview(self) -> None:
        if not self._preview_editor:
            return
        text = self._document.to_text() if self._document else ""
        self._preview_editor.setPlainText(text)

    def _clear_preview_window(self, obj: Optional[object] = None) -> None:
        self._preview_window = None
        self._preview_editor = None
        self._preview_find_bar = None
        self._preview_find_input = None
        self._preview_find_status = None
        self._preview_shortcuts = []

    def _ensure_preview_find_bar(self, editor: QPlainTextEdit) -> QWidget:
        if self._preview_find_bar:
            return self._preview_find_bar

        bar = QWidget()
        bar.setVisible(False)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Find:"))

        input_field = QLineEdit()
        input_field.setPlaceholderText("Search in document…")
        layout.addWidget(input_field, 1)

        prev_button = QToolButton()
        prev_button.setText("Previous")
        prev_button.clicked.connect(self._find_prev_in_preview)
        prev_button.setToolTip("Find previous (Shift+F3)")
        layout.addWidget(prev_button)

        next_button = QToolButton()
        next_button.setText("Next")
        next_button.clicked.connect(self._find_next_in_preview)
        next_button.setToolTip("Find next (F3)")
        layout.addWidget(next_button)

        status_label = QLabel()
        status_label.setObjectName("previewFindStatus")
        status_label.setMinimumWidth(90)
        layout.addWidget(status_label)

        layout.addStretch(1)

        close_button = QToolButton()
        close_button.setText("Close")
        close_button.clicked.connect(self._hide_preview_find)
        close_button.setToolTip("Hide find bar (Esc)")
        layout.addWidget(close_button)

        input_field.textChanged.connect(self._on_preview_find_text_changed)
        input_field.returnPressed.connect(self._find_next_in_preview)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), bar)
        esc_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        esc_shortcut.activated.connect(self._hide_preview_find)
        bar._esc_shortcut = esc_shortcut  # type: ignore[attr-defined]

        self._preview_find_bar = bar
        self._preview_find_input = input_field
        self._preview_find_status = status_label

        return bar

    def _setup_preview_shortcuts(self, editor: QPlainTextEdit) -> None:
        for shortcut in self._preview_shortcuts:
            shortcut.setParent(None)
        self._preview_shortcuts = []

        for sequence, handler in (
            (QKeySequence.Find, self._show_preview_find),
            (QKeySequence.FindNext, self._find_next_in_preview),
            (QKeySequence.FindPrevious, self._find_prev_in_preview),
        ):
            shortcut = QShortcut(sequence, editor)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)
            self._preview_shortcuts.append(shortcut)

        escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), editor)
        escape_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        escape_shortcut.activated.connect(self._handle_preview_escape)
        self._preview_shortcuts.append(escape_shortcut)

    def _show_preview_find(self, editor: Optional[QPlainTextEdit] = None) -> None:
        editor = editor or self._preview_editor
        if not editor:
            return
        bar = self._ensure_preview_find_bar(editor)
        bar.setVisible(True)

        if not self._preview_find_input:
            return

        selected_text = editor.textCursor().selectedText().replace("\u2029", "\n")
        if selected_text:
            self._preview_find_input.setText(selected_text)
        elif not self._preview_find_input.text() and self._last_preview_find:
            self._preview_find_input.setText(self._last_preview_find)

        self._preview_find_input.selectAll()
        self._preview_find_input.setFocus(Qt.ShortcutFocusReason)

    def _hide_preview_find(self) -> None:
        if self._preview_find_bar and self._preview_find_bar.isVisible():
            self._preview_find_bar.setVisible(False)
            self._set_preview_find_status("")
        if self._preview_editor:
            self._preview_editor.setFocus(Qt.ShortcutFocusReason)

    def _handle_preview_escape(self) -> None:
        if self._preview_find_bar and self._preview_find_bar.isVisible():
            self._hide_preview_find()

    def _on_preview_find_text_changed(self, text: str) -> None:
        if not text:
            self._set_preview_find_status("")
            return
        self._last_preview_find = text
        self._find_next_in_preview(from_start=True, wrap=False)

    def _find_next_in_preview(self, from_start: bool = False, wrap: bool = True) -> bool:
        editor = self._preview_editor
        field = self._preview_find_input
        if not editor or not field:
            return False
        text = field.text()
        if not text:
            self._set_preview_find_status("")
            return False

        self._last_preview_find = text
        cursor = editor.textCursor()
        original_position = cursor.position()

        if from_start:
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)

        if editor.find(text):
            self._set_preview_find_status("")
            return True

        if wrap and not from_start:
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)
            if editor.find(text):
                self._set_preview_find_status("Wrapped")
                return True

        cursor = editor.textCursor()
        cursor.setPosition(original_position)
        editor.setTextCursor(cursor)
        self._set_preview_find_status("No matches")
        return False

    def _find_prev_in_preview(self) -> bool:
        editor = self._preview_editor
        field = self._preview_find_input
        if not editor or not field:
            return False
        text = field.text()
        if not text:
            self._set_preview_find_status("")
            return False

        self._last_preview_find = text
        cursor = editor.textCursor()
        original_position = cursor.position()

        if editor.find(text, QTextDocument.FindBackward):
            self._set_preview_find_status("")
            return True

        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        if editor.find(text, QTextDocument.FindBackward):
            self._set_preview_find_status("Wrapped")
            return True

        cursor = editor.textCursor()
        cursor.setPosition(original_position)
        editor.setTextCursor(cursor)
        self._set_preview_find_status("No matches")
        return False

    def _set_preview_find_status(self, message: str) -> None:
        if not self._preview_find_status:
            return
        self._preview_find_status.setText(message)


class TemplateDetailsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        target_type: str,
        *,
        default_label: str = "",
        default_description: str = "",
        default_notes: str = "",
        placeholder_names: Optional[List[str]] = None,
        selected_blocks: Optional[List[str]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save as template")
        self.resize(520, 640)
        self.result: Optional[Dict[str, object]] = None

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit(default_label)
        form.addRow("Name", self.name_edit)

        self.description_edit = QLineEdit(default_description)
        form.addRow("Description", self.description_edit)

        target_label = ability_data.ABILITY_TYPES.get(target_type, {}).get("label", target_type)
        target_display = QLabel(target_label)
        form.addRow("Target type", target_display)

        self.scope_combo = QComboBox()
        scopes = ability_data.scopes_for(target_type)
        if scopes:
            for scope in scopes:
                self.scope_combo.addItem(scope.label, scope.key)
        else:
            self.scope_combo.addItem("Custom", "Custom")
        form.addRow("Scope", self.scope_combo)

        layout.addLayout(form)

        block_label = QLabel("Blocks (optional, check any that apply):")
        block_label.setWordWrap(True)
        layout.addWidget(block_label)

        self.block_list = QListWidget()
        self.block_list.setMinimumHeight(140)
        selected_blocks = selected_blocks or []
        for key, block in ability_data.FEATURE_BLOCKS.items():
            item = QListWidgetItem(f"{block.label} [{key}]", self.block_list)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if key in selected_blocks else Qt.Unchecked)
            item.setData(Qt.UserRole, key)
        layout.addWidget(self.block_list)

        placeholder_label = QLabel("Placeholders (one per line as name: description)")
        placeholder_label.setWordWrap(True)
        layout.addWidget(placeholder_label)

        self.placeholder_edit = QPlainTextEdit()
        if placeholder_names:
            self.placeholder_edit.setPlainText("\n".join(f"{name}: " for name in placeholder_names))
        layout.addWidget(self.placeholder_edit)

        example_label = QLabel("Example text (optional)")
        layout.addWidget(example_label)
        self.example_edit = QPlainTextEdit()
        self.example_edit.setPlaceholderText("Include example usage or snippets shown in the preview.")
        layout.addWidget(self.example_edit)

        notes_label = QLabel("Notes (optional)")
        layout.addWidget(notes_label)
        self.notes_edit = QPlainTextEdit(default_notes)
        self.notes_edit.setPlaceholderText("Additional guidance shown in the preview.")
        layout.addWidget(self.notes_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_accept(self) -> None:
        label = self.name_edit.text().strip()
        if not label:
            QMessageBox.information(self, "Missing name", "Enter a name for the template.")
            self.name_edit.setFocus()
            return
        description = self.description_edit.text().strip() or label
        scope_key = self.scope_combo.currentData() or "Custom"

        block_sequence: List[str] = []
        for idx in range(self.block_list.count()):
            item = self.block_list.item(idx)
            if item.checkState() == Qt.Checked:
                key = item.data(Qt.UserRole)
                if key:
                    block_sequence.append(str(key))

        placeholders: Dict[str, str] = {}
        for line in self.placeholder_edit.toPlainText().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if ":" in stripped:
                name, desc = stripped.split(":", 1)
            elif "-" in stripped:
                name, desc = stripped.split("-", 1)
            else:
                name, desc = stripped, ""
            name = name.strip()
            if not name:
                continue
            placeholders[name] = desc.strip()

        example_text = self.example_edit.toPlainText().strip()
        notes_text = self.notes_edit.toPlainText().strip()

        self.result = {
            "label": label,
            "description": description,
            "scope_key": scope_key,
            "block_sequence": block_sequence,
            "placeholders": placeholders,
            "example": example_text or None,
            "notes": notes_text or None,
        }
        self.accept()


class PreferencesDialog(QDialog):
    def __init__(self, parent: MainWindow, require_confirmations: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        layout = QVBoxLayout(self)

        self.confirm_checkbox = QCheckBox("Ask before deleting entries")
        self.confirm_checkbox.setChecked(require_confirmations)
        layout.addWidget(self.confirm_checkbox)

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def ask_confirmations(self) -> bool:
        return self.confirm_checkbox.isChecked()


class FeatureTypesDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Feature types reference")
        self.resize(720, 600)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setLineWrapMode(QTextBrowser.WidgetWidth)

        sections = ["<h2>Feature types</h2>"]
        for detail in ability_data.feature_type_details():
            sections.append(f"<h3>{detail['name']}</h3>")
            sections.append(f"<p>{detail['description']}</p>")
            arguments = detail.get("arguments", [])
            if arguments:
                sections.append("<p><b>Arguments</b></p>")
                sections.append("<div class='arguments'>" + "<br/>".join(arguments) + "</div>")
            properties = detail.get("properties", [])
            if properties:
                sections.append("<p><b>Modifiable properties</b></p>")
                sections.append("<div class='properties'>" + ", ".join(properties) + "</div>")
        browser.setHtml("\n".join(sections))

        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
