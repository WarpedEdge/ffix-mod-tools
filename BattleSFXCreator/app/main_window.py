from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from functools import partial

from PySide6.QtCore import Qt, QPoint, QUrl, QSettings, QByteArray
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QTextBrowser,
    QComboBox,
    QInputDialog,
    QDialog,
    QDialogButtonBox,
    QSizePolicy,
    QRadioButton,
)

from . import sequence_data
from .models import (
    SequenceDocument,
    SequenceFile,
    RenameHistory,
    RenameAction,
)


HELP_LINKS = [
    ("Sequence File", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence"),
    ("Format", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#format"),
    ("Threads", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#threads"),
    (
        "Synchronous vs Asynchronous",
        "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#synchronous-and-asynchronous-threads",
    ),
    ("Target Swap", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#target-swap"),
    ("Looping Threads", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#looping-threads"),
    ("Instruction List", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#list-of-instructions"),
    ("Argument Types", "https://github.com/Albeoris/Memoria/wiki/Battle-SFX-Sequence#argument-types"),
]

DEFAULT_SEQUENCE_BODY = "// New sequence\n"

HELP_STYLESHEET = """
body { font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 11pt; color: #e8e8f2; background: #1f1f26; }
h2 { font-size: 18pt; margin: 0 0 12px 0; }
h3 { font-size: 13pt; margin: 18px 0 6px 0; }
ul { margin: 4px 0 12px 22px; }
li { margin-bottom: 4px; }
code { background: #2b2b35; padding: 2px 6px; border-radius: 3px; color: #f3f3ff; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._base_title = "Battle SFX Sequence Builder"
        self._document: Optional[SequenceDocument] = None
        self._document_root: Optional[Path] = None
        self._current_file: Optional[SequenceFile] = None
        self._current_original_text: str = ""
        self._dirty_entries: Dict[str, str] = {}
        self._rename_history = RenameHistory()
        self.template_sets: Dict[str, Dict[str, List[sequence_data.SequenceTemplate]]] = {}
        self.current_template_set: str = ""
        self._template_set_paths: Dict[str, Path] = {}
        self._templates_dir = Path(__file__).resolve().parent / "templates"
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._tree_items: Dict[str, QTreeWidgetItem] = {}
        self._is_closing = False
        self._saved_history: Dict[str, List[str]] = {}
        self.template_search_box: Optional[QLineEdit] = None
        self.template_tree: Optional[QTreeWidget] = None
        self._preview_editor_splitter: Optional[QSplitter] = None
        self._preview_orientation: Qt.Orientation = Qt.Horizontal
        self._main_splitter: Optional[QSplitter] = None
        self._preview_box: Optional[QGroupBox] = None
        self._editor_box: Optional[QGroupBox] = None
        self._pending_geometry: Optional[QByteArray] = None
        self._pending_main_splitter_state: Optional[QByteArray] = None
        self._preview_splitter_states: Dict[Qt.Orientation, Optional[QByteArray]] = {
            Qt.Horizontal: None,
            Qt.Vertical: None,
        }

        self._load_settings()
        self._build_templates()
        self._build_menu()
        self._build_ui()
        self._refresh_template_set_box()
        self._update_actions()

    def _load_settings(self) -> None:
        settings = QSettings("BattleSFXCreator", "BattleSFXCreator")
        mode = settings.value("preview_mode", "horizontal")
        if isinstance(mode, str) and mode.lower() == "vertical":
            self._preview_orientation = Qt.Vertical
        else:
            self._preview_orientation = Qt.Horizontal

        geometry = settings.value("window_geometry", QByteArray())
        if isinstance(geometry, QByteArray) and not geometry.isEmpty():
            self._pending_geometry = QByteArray(geometry)
        else:
            self._pending_geometry = None

        main_state = settings.value("main_splitter_state", QByteArray())
        if isinstance(main_state, QByteArray) and not main_state.isEmpty():
            self._pending_main_splitter_state = QByteArray(main_state)
        else:
            self._pending_main_splitter_state = None

        horiz_state = settings.value("preview_splitter_state_horizontal", QByteArray())
        vert_state = settings.value("preview_splitter_state_vertical", QByteArray())
        self._preview_splitter_states[Qt.Horizontal] = (
            QByteArray(horiz_state) if isinstance(horiz_state, QByteArray) and not horiz_state.isEmpty() else None
        )
        self._preview_splitter_states[Qt.Vertical] = (
            QByteArray(vert_state) if isinstance(vert_state, QByteArray) and not vert_state.isEmpty() else None
        )

    def _save_settings(self) -> None:
        settings = QSettings("BattleSFXCreator", "BattleSFXCreator")
        mode = "vertical" if self._preview_orientation == Qt.Vertical else "horizontal"
        settings.setValue("preview_mode", mode)
        settings.setValue("window_geometry", self.saveGeometry())

        if self._main_splitter is not None:
            state = self._main_splitter.saveState()
            settings.setValue("main_splitter_state", state)
            self._pending_main_splitter_state = QByteArray(state)

        if self._preview_editor_splitter is not None:
            state = self._preview_editor_splitter.saveState()
            self._preview_splitter_states[self._preview_orientation] = QByteArray(state)

        horiz_state = self._preview_splitter_states.get(Qt.Horizontal)
        if horiz_state:
            settings.setValue("preview_splitter_state_horizontal", horiz_state)
        else:
            settings.remove("preview_splitter_state_horizontal")

        vert_state = self._preview_splitter_states.get(Qt.Vertical)
        if vert_state:
            settings.setValue("preview_splitter_state_vertical", vert_state)
        else:
            settings.remove("preview_splitter_state_vertical")

    # ------------------------------------------------------------------ setup
    def _set_preview_orientation(self, orientation: Qt.Orientation) -> None:
        if orientation == self._preview_orientation:
            return
        if self._preview_editor_splitter is not None:
            state = self._preview_editor_splitter.saveState()
            self._preview_splitter_states[self._preview_orientation] = QByteArray(state)
        self._preview_orientation = orientation
        self._recreate_preview_splitter()
        self._apply_layout_settings()
        self._save_settings()

    def _recreate_preview_splitter(self) -> None:
        if not hasattr(self, '_main_splitter') or self._main_splitter is None:
            return
        if self._preview_box is None or self._editor_box is None:
            return
        if self._preview_editor_splitter is not None:
            self._preview_box.setParent(None)
            self._editor_box.setParent(None)
            index = self._main_splitter.indexOf(self._preview_editor_splitter)
            if index != -1:
                old = self._main_splitter.widget(index)
                old.setParent(None)
                old.deleteLater()
        splitter = QSplitter(self._preview_orientation)
        splitter.addWidget(self._preview_box)
        splitter.addWidget(self._editor_box)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._preview_editor_splitter = splitter
        if self._main_splitter.count() == 1:
            self._main_splitter.addWidget(splitter)
        else:
            self._main_splitter.insertWidget(1, splitter)
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)

    def _apply_layout_settings(self) -> None:
        if self._main_splitter and self._pending_main_splitter_state:
            self._main_splitter.restoreState(self._pending_main_splitter_state)
            self._pending_main_splitter_state = None

        state = self._preview_splitter_states.get(self._preview_orientation)
        if self._preview_editor_splitter and state:
            self._preview_editor_splitter.restoreState(state)

        if self._pending_geometry:
            self.restoreGeometry(self._pending_geometry)
            self._pending_geometry = None

    def _build_templates(self) -> None:
        self._load_built_in_templates()
        self._load_saved_template_sets()

    def _load_built_in_templates(self) -> None:
        built_ins = sequence_data.built_in_template_sets()
        built_in_paths = sequence_data.built_in_template_paths()
        for name, mapping in built_ins.items():
            if not mapping:
                continue
            self.template_sets[name] = mapping
            self._template_set_paths[name] = built_in_paths.get(name)
        if "Individuals" in self.template_sets:
            self.current_template_set = "Individuals"
        elif self.template_sets:
            self.current_template_set = next(iter(self.template_sets))

    def _load_saved_template_sets(self) -> None:
        existing_paths = {p for p in self._template_set_paths.values() if p}
        for path in sorted(self._templates_dir.glob("*.json")):
            if path in existing_paths:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Failed to load template set from {path}: {exc}")
                continue
            name = str(data.get("name") or path.stem)
            if name in self.template_sets:
                # Avoid clobbering a built-in set; append suffix.
                suffix = 2
                new_name = f"{name}_{suffix}"
                while new_name in self.template_sets:
                    suffix += 1
                    new_name = f"{name}_{suffix}"
                name = new_name
            templates = sequence_data.templates_from_dict(data)
            if not templates:
                continue
            self.template_sets[name] = templates
            self._template_set_paths[name] = path
        if self.current_template_set not in self.template_sets and self.template_sets:
            self.current_template_set = next(iter(self.template_sets))

    def _template_file_for(self, name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()) or "templates"
        return self._templates_dir / f"{safe}.json"

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open sequence directory…", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_directory)
        file_menu.addAction(open_action)

        self.reload_action = QAction("Reload from disk", self)
        self.reload_action.setShortcut(QKeySequence.Refresh)
        self.reload_action.triggered.connect(self._reload_directory)
        file_menu.addAction(self.reload_action)

        file_menu.addSeparator()

        self.save_current_action = QAction("Save current sequence", self)
        self.save_current_action.setShortcut(QKeySequence.Save)
        self.save_current_action.triggered.connect(self._save_current_sequence)
        file_menu.addAction(self.save_current_action)

        self.save_all_action = QAction("Save all sequences", self)
        self.save_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_all_action.triggered.connect(self._save_all_sequences)
        file_menu.addAction(self.save_all_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("Edit")
        self.undo_rename_action = QAction("Undo rename", self)
        self.undo_rename_action.setShortcut(QKeySequence.Undo)
        self.undo_rename_action.triggered.connect(self._undo_last_rename)
        edit_menu.addAction(self.undo_rename_action)

        edit_menu.addSeparator()

        copy_path_action = QAction("Copy sequence path", self)
        copy_path_action.triggered.connect(self._copy_sequence_path)
        edit_menu.addAction(copy_path_action)

        preferences_action = QAction("Preferences…", self)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self._show_preferences_dialog)
        edit_menu.addAction(preferences_action)

        templates_menu = menubar.addMenu("Templates")
        import_action = QAction("Import template set…", self)
        import_action.triggered.connect(self._import_template_set)
        templates_menu.addAction(import_action)

        export_action = QAction("Export current template set…", self)
        export_action.triggered.connect(self._export_template_set)
        templates_menu.addAction(export_action)

        help_menu = menubar.addMenu("Help")
        instructions_action = QAction("List of Instructions", self)
        instructions_action.triggered.connect(
            partial(self._show_help_dialog, "List of Instructions", sequence_data.INSTRUCTION_HELP_HTML)
        )
        help_menu.addAction(instructions_action)

        arguments_action = QAction("Argument Types", self)
        arguments_action.triggered.connect(
            partial(self._show_help_dialog, "Argument Types", sequence_data.ARGUMENT_HELP_HTML)
        )
        help_menu.addAction(arguments_action)

        help_menu.addSeparator()

        battle_menu = help_menu.addMenu("Battle SFX Sequence")
        for label, url in HELP_LINKS:
            action = QAction(label, self)
            action.triggered.connect(partial(QDesktopServices.openUrl, QUrl(url)))
            battle_menu.addAction(action)

    # ------------------------------------------------------------------ UI layout
    def _build_ui(self) -> None:
        splitter = QSplitter(orientation=Qt.Horizontal)
        splitter.setHandleWidth(6)

        # Left side: directory and sequence browser
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Loaded sequences"))

        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Filter by folder or sequence name…")
        self.filter_box.textChanged.connect(self._apply_filter)
        left_layout.addWidget(self.filter_box)

        self.sequence_tree = QTreeWidget()
        self.sequence_tree.setHeaderHidden(True)
        self.sequence_tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.sequence_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.sequence_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sequence_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        left_layout.addWidget(self.sequence_tree, stretch=1)

        tree_tools_row = QHBoxLayout()
        self.new_folder_btn = QPushButton("New folder…")
        self.new_folder_btn.clicked.connect(self._create_folder_prompt)
        tree_tools_row.addWidget(self.new_folder_btn)

        self.generate_folder_btn = QPushButton("Generate ef####")
        self.generate_folder_btn.clicked.connect(self._generate_effect_folder)
        tree_tools_row.addWidget(self.generate_folder_btn)

        self.expand_all_btn = QPushButton("Expand all")
        self.expand_all_btn.clicked.connect(lambda _checked=False: self.sequence_tree.expandAll())
        tree_tools_row.addWidget(self.expand_all_btn)

        self.collapse_all_btn = QPushButton("Collapse all")
        self.collapse_all_btn.clicked.connect(lambda _checked=False: self.sequence_tree.collapseAll())
        tree_tools_row.addWidget(self.collapse_all_btn)

        tree_tools_row.addStretch(1)
        left_layout.addLayout(tree_tools_row)

        template_group = QGroupBox("Template catalog")
        template_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        template_layout = QVBoxLayout(template_group)

        template_header = QHBoxLayout()
        template_header.addWidget(QLabel("Template set:"))
        self.template_set_box = QComboBox()
        self.template_set_box.setMaxVisibleItems(20)
        self.template_set_box.currentTextChanged.connect(self._on_template_set_changed)
        template_header.addWidget(self.template_set_box, stretch=1)
        template_layout.addLayout(template_header)

        self.template_search_box = QLineEdit()
        self.template_search_box.setPlaceholderText("Search templates…")
        self.template_search_box.textChanged.connect(self._apply_template_filter)
        template_layout.addWidget(self.template_search_box)

        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderHidden(True)
        self.template_tree.itemSelectionChanged.connect(self._on_template_tree_selection)
        self.template_tree.itemDoubleClicked.connect(self._on_template_double_clicked)
        template_layout.addWidget(self.template_tree)

        template_insert_btn = QPushButton("Insert template into editor")
        template_insert_btn.clicked.connect(self._insert_selected_template)
        template_layout.addWidget(template_insert_btn)

        left_layout.addWidget(template_group, stretch=1)

        button_row = QHBoxLayout()
        self.open_dir_btn = QPushButton("Open directory…")
        self.open_dir_btn.clicked.connect(self._open_directory)
        button_row.addWidget(self.open_dir_btn)

        self.reload_dir_btn = QPushButton("Reload")
        self.reload_dir_btn.clicked.connect(self._reload_directory)
        self.reload_dir_btn.setEnabled(False)
        button_row.addWidget(self.reload_dir_btn)
        left_layout.addLayout(button_row)

        splitter.addWidget(left_panel)

        preview_box = QGroupBox("Template preview")
        preview_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        preview_layout = QVBoxLayout(preview_box)
        self.template_preview = QPlainTextEdit()
        self.template_preview.setReadOnly(True)
        preview_layout.addWidget(self.template_preview)

        editor_box = QGroupBox("Sequence editor")
        editor_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor_layout = QVBoxLayout(editor_box)

        self.sequence_path_label = QLabel("No sequence loaded")
        self.sequence_path_label.setWordWrap(True)
        editor_layout.addWidget(self.sequence_path_label)

        self.sequence_editor = QPlainTextEdit()
        self.sequence_editor.setPlaceholderText("Open a sequence to edit or insert a template…")
        self.sequence_editor.textChanged.connect(self._on_editor_changed)
        self.sequence_editor.setEnabled(False)
        editor_layout.addWidget(self.sequence_editor, stretch=1)

        editor_button_row = QHBoxLayout()
        self.save_sequence_btn = QPushButton("Save sequence")
        self.save_sequence_btn.clicked.connect(self._save_current_sequence)
        self.save_sequence_btn.setEnabled(False)
        editor_button_row.addWidget(self.save_sequence_btn)

        self.revert_sequence_btn = QPushButton("Revert changes")
        self.revert_sequence_btn.clicked.connect(self._revert_current_sequence)
        self.revert_sequence_btn.setEnabled(False)
        editor_button_row.addWidget(self.revert_sequence_btn)

        editor_layout.addLayout(editor_button_row)

        self._preview_box = preview_box
        self._editor_box = editor_box
        self._main_splitter = splitter
        self._recreate_preview_splitter()

        self.setCentralWidget(splitter)
        self._apply_layout_settings()
        self.statusBar().showMessage("Open a battle SFX directory to begin.")

    # ---------------------------------------------------------------- actions / state
    def _update_actions(self) -> None:
        has_document = self._document is not None
        has_selection = self._current_file is not None
        has_dirty_any = bool(self._dirty_entries)
        is_current_dirty = self._is_current_dirty()

        self.reload_action.setEnabled(has_document)
        self.reload_dir_btn.setEnabled(has_document)
        self.save_current_action.setEnabled(has_selection and is_current_dirty)
        self.save_sequence_btn.setEnabled(has_selection and is_current_dirty)
        has_history = bool(self._current_file and self._saved_history.get(self._current_file.identifier))
        self.revert_sequence_btn.setEnabled(has_selection and (is_current_dirty or has_history))
        self.save_all_action.setEnabled(has_dirty_any)
        self.undo_rename_action.setEnabled(self._rename_history.can_undo())
        for button in (
            getattr(self, "new_folder_btn", None),
            getattr(self, "generate_folder_btn", None),
            getattr(self, "expand_all_btn", None),
            getattr(self, "collapse_all_btn", None),
        ):
            if button is not None:
                button.setEnabled(has_document)

        marker = "*" if has_dirty_any else ""
        if self._document_root:
            self.setWindowTitle(f"{marker}{self._base_title} — {self._document_root}")
        else:
            self.setWindowTitle(f"{marker}{self._base_title}")

    def _apply_filter(self, text: str) -> None:
        text = text.strip().lower()
        root_item = self.sequence_tree.invisibleRootItem()
        for i in range(root_item.childCount()):
            folder_item = root_item.child(i)
            folder_match = text in folder_item.text(0).lower() if text else True
            child_visible = False
            for j in range(folder_item.childCount()):
                child_item = folder_item.child(j)
                visible = text in child_item.text(0).lower() or folder_match
                child_item.setHidden(not visible)
                if visible:
                    child_visible = True
            folder_item.setHidden(not (folder_match or child_visible))

    def _rebuild_tree(self, target_identifier: Optional[str] = None) -> None:
        expanded_state: Dict[str, bool] = {}
        root = self.sequence_tree.invisibleRootItem()
        for i in range(root.childCount()):
            folder_item = root.child(i)
            payload = folder_item.data(0, Qt.UserRole) or {}
            if payload.get("type") == "folder":
                key = payload.get("path") or folder_item.text(0)
                expanded_state[key] = folder_item.isExpanded()

        if target_identifier is None and self._current_file:
            target_identifier = self._current_file.identifier

        self.sequence_tree.clear()
        self._tree_items.clear()

        if not self._document:
            return

        selected_item: Optional[QTreeWidgetItem] = None
        for folder in self._document.folders:
            folder_item = QTreeWidgetItem()
            folder_payload = {"type": "folder", "path": str(folder.path)}
            folder_item.setData(0, Qt.UserRole, folder_payload)
            folder_item.setData(0, Qt.UserRole + 1, folder.name)
            folder_item.setText(0, folder.name)
            for seq_file in folder.iter_files():
                item = QTreeWidgetItem()
                payload = {
                    "type": "file",
                    "folder": folder.name,
                    "filename": seq_file.filename,
                    "path": str(seq_file.path),
                }
                item.setData(0, Qt.UserRole, payload)
                item.setData(0, Qt.UserRole + 1, seq_file.filename)
                item.setText(0, seq_file.filename)
                identifier = seq_file.identifier
                self._tree_items[identifier] = item
                if target_identifier and identifier == target_identifier:
                    selected_item = item
                folder_item.addChild(item)
            key = folder_payload.get("path")
            if key in expanded_state:
                folder_item.setExpanded(expanded_state[key])
            else:
                folder_item.setExpanded(True)
            self.sequence_tree.addTopLevelItem(folder_item)

        if selected_item is not None:
            self.sequence_tree.setCurrentItem(selected_item)

        for identifier in list(self._dirty_entries.keys()):
            self._set_tree_item_dirty(identifier, True)

        self._refresh_folder_dirty_flags()

        self.sequence_tree.resizeColumnToContents(0)
        self._apply_filter(self.filter_box.text())

    def _open_directory(self) -> None:
        start_dir = str(self._document_root or Path.cwd())
        chosen = QFileDialog.getExistingDirectory(self, "Select Battle SFX directory", start_dir)
        if not chosen:
            return
        self._load_directory(Path(chosen))

    def _push_history(self, identifier: str, snapshot: str, *, limit: int = 5) -> None:
        if not snapshot:
            return
        stack = self._saved_history.setdefault(identifier, [])
        if stack and stack[-1] == snapshot:
            return
        stack.append(snapshot)
        if len(stack) > limit:
            stack.pop(0)

    def _select_folder(self, folder_name: str) -> None:
        target = folder_name.lower()
        root = self.sequence_tree.invisibleRootItem()
        for i in range(root.childCount()):
            folder_item = root.child(i)
            base = folder_item.data(0, Qt.UserRole + 1) or folder_item.text(0)
            if base.lower().rstrip(" *") == target:
                folder_item.setExpanded(True)
                self.sequence_tree.setCurrentItem(folder_item)
                self.sequence_tree.scrollToItem(folder_item)
                break

    def _create_folder_prompt(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No directory loaded", "Open a battle SFX directory first.")
            return
        default_name = self._document.suggest_new_folder_name()
        name, ok = QInputDialog.getText(self, "Create folder", "Folder name:", text=default_name)
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if any(ch in name for ch in ("/", "\\")):
            QMessageBox.warning(self, "Invalid name", "Folder name cannot contain path separators.")
            return
        try:
            self._document.create_folder(name)
        except FileExistsError:
            QMessageBox.warning(self, "Already exists", f"A folder named '{name}' already exists.")
            return
        except Exception as exc:
            QMessageBox.warning(self, "Failed to create folder", str(exc))
            return
        try:
            self._document.reload()
        except Exception as exc:
            QMessageBox.warning(self, "Failed to refresh", str(exc))
            return
        self._rebuild_tree()
        self._select_folder(name)
        self.statusBar().showMessage(f"Created folder {name}", 4000)
        self._update_actions()

    def _generate_effect_folder(self) -> None:
        if not self._document:
            QMessageBox.information(self, "No directory loaded", "Open a battle SFX directory first.")
            return
        folder_name = self._document.suggest_new_folder_name()
        try:
            folder_path = self._document.create_folder(folder_name)
        except FileExistsError:
            QMessageBox.warning(self, "Already exists", f"Folder '{folder_name}' already exists.")
            return
        except Exception as exc:
            QMessageBox.warning(self, "Failed to create folder", str(exc))
            return
        try:
            self._document.create_sequence_file(folder_path, "PlayerSequence.seq", body=DEFAULT_SEQUENCE_BODY)
        except FileExistsError:
            pass
        except Exception as exc:
            QMessageBox.warning(self, "Failed to create PlayerSequence", str(exc))
        try:
            self._document.reload()
        except Exception as exc:
            QMessageBox.warning(self, "Failed to refresh", str(exc))
            return
        identifier = f"{folder_path.name}/PlayerSequence.seq"
        self._rebuild_tree(target_identifier=identifier)
        sequence = self._document.find_file(folder_path.name, "PlayerSequence.seq")
        if sequence:
            self._set_current_file(sequence)
        self.statusBar().showMessage(f"Generated {folder_path.name} with PlayerSequence.seq", 4000)
        self._update_actions()

    def _create_sequence_file_for_folder(self, folder_path: Path, filename: str) -> Optional[SequenceFile]:
        if not self._document:
            QMessageBox.information(self, "No directory loaded", "Open a battle SFX directory first.")
            return None
        filename = filename.strip() or "Sequence.seq"
        try:
            self._document.create_sequence_file(folder_path, filename, body=DEFAULT_SEQUENCE_BODY)
        except FileExistsError:
            QMessageBox.warning(self, "Already exists", f"{filename} already exists in {folder_path.name}.")
            return None
        except Exception as exc:
            QMessageBox.warning(self, "Failed to create sequence", str(exc))
            return None
        try:
            self._document.reload()
        except Exception as exc:
            QMessageBox.warning(self, "Failed to refresh", str(exc))
            return None
        identifier = f"{folder_path.name}/{filename}"
        self._rebuild_tree(target_identifier=identifier)
        sequence = self._document.find_file(folder_path.name, filename)
        if sequence:
            self._set_current_file(sequence)
        self.statusBar().showMessage(f"Created {filename} in {folder_path.name}", 4000)
        self._update_actions()
        return sequence

    def _set_tree_item_dirty(self, identifier: str, dirty: bool) -> None:
        item = self._tree_items.get(identifier)
        if not item:
            return
        base = item.data(0, Qt.UserRole + 1) or item.text(0).rstrip(" *")
        item.setText(0, f"{base}{' *' if dirty else ''}")
        parent = item.parent()
        if parent is not None:
            self._update_folder_dirty_flag(parent)

    def _refresh_folder_dirty_flags(self) -> None:
        root = self.sequence_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._update_folder_dirty_flag(root.child(i))

    def _update_folder_dirty_flag(self, folder_item: QTreeWidgetItem) -> None:
        base = folder_item.data(0, Qt.UserRole + 1) or folder_item.text(0).rstrip(" *")
        dirty = any(folder_item.child(i).text(0).endswith("*") for i in range(folder_item.childCount()))
        folder_item.setText(0, f"{base}{' *' if dirty else ''}")

    def _load_directory(self, path: Path) -> None:
        try:
            document = SequenceDocument.load(path)
        except Exception as exc:
            QMessageBox.warning(self, "Failed to load", str(exc))
            return
        self._document = document
        self._document_root = path
        self.sequence_path_label.setText("No sequence loaded")
        self.sequence_editor.clear()
        self.sequence_editor.setEnabled(False)
        self._current_file = None
        self._current_original_text = ""
        self._dirty_entries.clear()
        self._saved_history.clear()
        self._rebuild_tree()
        self.statusBar().showMessage(f"Loaded {len(document.folders)} folders from {path}", 5000)
        self._update_actions()

    def _reload_directory(self) -> None:
        if not self._document:
            return
        try:
            self._document.reload()
        except Exception as exc:
            QMessageBox.warning(self, "Failed to reload", str(exc))
            return
        self._dirty_entries.clear()
        self._saved_history.clear()
        self._current_file = None
        self.sequence_editor.clear()
        self.sequence_editor.setEnabled(False)
        self.sequence_path_label.setText("No sequence loaded")
        self._rebuild_tree()
        self.statusBar().showMessage("Reloaded from disk", 4000)
        self._update_actions()

    def _on_selection_changed(self) -> None:
        items = self.sequence_tree.selectedItems()
        if not items:
            self._set_current_file(None)
            return
        item = items[0]
        payload = item.data(0, Qt.UserRole) or {}
        if payload.get("type") != "file":
            self._set_current_file(None)
            return
        folder_name = payload.get("folder")
        filename = payload.get("filename")
        if not (self._document and folder_name and filename):
            self._set_current_file(None)
            return
        sequence = self._document.find_file(folder_name, filename)
        if not sequence:
            self._set_current_file(None)
            return
        self._set_current_file(sequence)

    def _set_current_file(self, sequence: Optional[SequenceFile]) -> None:
        self._current_file = sequence
        if not sequence:
            self.sequence_path_label.setText("No sequence loaded")
            self.sequence_editor.blockSignals(True)
            self.sequence_editor.clear()
            self.sequence_editor.blockSignals(False)
            self.sequence_editor.setEnabled(False)
            self._current_original_text = ""
            self._update_actions()
            return
        try:
            text = sequence.read_text()
        except Exception as exc:
            QMessageBox.warning(self, "Failed to read sequence", str(exc))
            return
        self.sequence_path_label.setText(sequence.path.as_posix())
        self.sequence_editor.blockSignals(True)
        display_text = self._dirty_entries.get(sequence.identifier, text)
        self.sequence_editor.setPlainText(display_text)
        self.sequence_editor.blockSignals(False)
        self.sequence_editor.setEnabled(True)
        self._current_original_text = text
        self._update_actions()

    def _on_editor_changed(self) -> None:
        if self._is_closing or not self._current_file:
            return
        identifier = self._current_file.identifier
        current_text = self.sequence_editor.toPlainText()
        if current_text == self._current_original_text:
            self._dirty_entries.pop(identifier, None)
            self._set_tree_item_dirty(identifier, False)
        else:
            self._dirty_entries[identifier] = current_text
            self._set_tree_item_dirty(identifier, True)
        self._refresh_folder_dirty_flags()
        self._update_actions()

    def _is_current_dirty(self) -> bool:
        if not self._current_file:
            return False
        return self._current_file.identifier in self._dirty_entries

    def _save_current_sequence(self) -> None:
        if not self._current_file or not self._is_current_dirty():
            return
        text = self.sequence_editor.toPlainText()
        self._push_history(self._current_file.identifier, self._current_original_text)
        try:
            self._current_file.write_text(text)
        except Exception as exc:
            QMessageBox.warning(self, "Failed to save sequence", str(exc))
            return
        self._current_original_text = text
        self._dirty_entries.pop(self._current_file.identifier, None)
        self._set_tree_item_dirty(self._current_file.identifier, False)
        self._refresh_folder_dirty_flags()
        self.statusBar().showMessage(f"Saved {self._current_file.path.name}", 4000)
        self._update_actions()

    def _revert_current_sequence(self) -> None:
        if not self._current_file:
            return
        identifier = self._current_file.identifier
        if identifier in self._dirty_entries:
            try:
                text = self._current_file.read_text(use_cache=False)
            except Exception as exc:
                QMessageBox.warning(self, "Failed to reload sequence", str(exc))
                return
            self.sequence_editor.blockSignals(True)
            self.sequence_editor.setPlainText(text)
            self.sequence_editor.blockSignals(False)
            self._current_original_text = text
            self._dirty_entries.pop(identifier, None)
            self._set_tree_item_dirty(identifier, False)
            self._refresh_folder_dirty_flags()
            self.statusBar().showMessage("Reverted to disk version", 4000)
            self._update_actions()
            return

        history = self._saved_history.get(identifier)
        if not history:
            self.statusBar().showMessage("Nothing to revert.", 3000)
            return
        previous = history.pop()
        if not history:
            self._saved_history.pop(identifier, None)
        try:
            self._current_file.write_text(previous)
        except Exception as exc:
            QMessageBox.warning(self, "Failed to restore previous save", str(exc))
            history.append(previous)
            self._saved_history[identifier] = history
            return
        self.sequence_editor.blockSignals(True)
        self.sequence_editor.setPlainText(previous)
        self.sequence_editor.blockSignals(False)
        self._current_original_text = previous
        self._set_tree_item_dirty(identifier, False)
        self._refresh_folder_dirty_flags()
        self.statusBar().showMessage("Restored previous save", 4000)
        self._update_actions()

    def _save_all_sequences(self) -> None:
        if not self._dirty_entries or not self._document:
            return
        failures: List[str] = []
        for sequence in list(self._document.iter_sequence_files()):
            identifier = sequence.identifier
            if identifier not in self._dirty_entries:
                continue
            text = self._dirty_entries[identifier]
            if self._current_file and identifier == self._current_file.identifier:
                previous_text = self._current_original_text
            else:
                try:
                    previous_text = sequence.read_text()
                except Exception as exc:
                    failures.append(f"{identifier}: failed to read current file ({exc})")
                    continue
            self._push_history(identifier, previous_text)
            try:
                sequence.write_text(text)
            except Exception as exc:
                failures.append(f"{identifier}: {exc}")
                continue
            if self._current_file and identifier == self._current_file.identifier:
                self._current_original_text = text
            self._dirty_entries.pop(identifier, None)
            self._set_tree_item_dirty(identifier, False)
        if failures:
            QMessageBox.warning(self, "Some sequences failed", "\n".join(failures))
        else:
            self.statusBar().showMessage("All dirty sequences saved", 5000)
        self._refresh_folder_dirty_flags()
        self._update_actions()

    def _copy_sequence_path(self) -> None:
        if not self._current_file:
            return
        QApplication.clipboard().setText(str(self._current_file.path))
        self.statusBar().showMessage("Sequence path copied", 3000)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:  # noqa: ARG002
        payload = item.data(0, Qt.UserRole) or {}
        if payload.get("type") != "file":
            return
        self._open_containing_folder(payload.get("path"))

    def _open_containing_folder(self, path_str: Optional[str]) -> None:
        if not path_str:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path_str).parent)))

    def _open_folder_path(self, path_str: Optional[str]) -> None:
        if not path_str:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path_str))))

    # ---------------------------- context menu / rename operations
    def _show_tree_context_menu(self, pos: QPoint) -> None:
        item = self.sequence_tree.itemAt(pos)
        menu = QMenu(self)

        if item is None:
            if self._document:
                new_folder_action = menu.addAction("New folder…")
                new_folder_action.triggered.connect(self._create_folder_prompt)
                generate_action = menu.addAction("Generate ef####")
                generate_action.triggered.connect(self._generate_effect_folder)
                menu.addSeparator()
            expand_action = menu.addAction("Expand all")
            expand_action.triggered.connect(lambda _checked=False: self.sequence_tree.expandAll())
            collapse_action = menu.addAction("Collapse all")
            collapse_action.triggered.connect(lambda _checked=False: self.sequence_tree.collapseAll())
            if menu.actions():
                menu.exec(QCursor.pos())
            return

        payload = item.data(0, Qt.UserRole) or {}
        if payload.get("type") == "folder":
            path_str = payload.get("path")
            folder_path = Path(path_str) if path_str else None
            if folder_path:
                player_action = menu.addAction("Create PlayerSequence.seq")
                player_action.triggered.connect(
                    lambda _checked=False, p=folder_path: self._create_sequence_file_for_folder(p, "PlayerSequence.seq")
                )
                sequence_action = menu.addAction("Create Sequence.seq")
                sequence_action.triggered.connect(
                    lambda _checked=False, p=folder_path: self._create_sequence_file_for_folder(p, "Sequence.seq")
                )
            menu.addSeparator()
            rename_action = menu.addAction("Rename folder…")
            rename_action.triggered.connect(partial(self._rename_folder, payload))
            menu.addSeparator()
            expand_action = menu.addAction("Expand all")
            expand_action.triggered.connect(lambda _checked=False: self.sequence_tree.expandAll())
            collapse_action = menu.addAction("Collapse all")
            collapse_action.triggered.connect(lambda _checked=False: self.sequence_tree.collapseAll())
            if path_str:
                menu.addSeparator()
                open_action = menu.addAction("Open folder")
                open_action.triggered.connect(lambda _checked=False, p=path_str: self._open_folder_path(p))
        elif payload.get("type") == "file":
            rename_action = menu.addAction("Rename sequence…")
            rename_action.triggered.connect(partial(self._rename_sequence, payload))
            save_action = menu.addAction("Save sequence")
            save_action.triggered.connect(self._save_current_sequence)
            revert_action = menu.addAction("Revert sequence")
            revert_action.triggered.connect(self._revert_current_sequence)
            menu.addSeparator()
            open_action = menu.addAction("Open containing folder")
            open_action.triggered.connect(
                lambda _checked=False, p=payload.get("path"): self._open_containing_folder(p)
            )

        if menu.actions():
            menu.exec(QCursor.pos())

    def _rename_folder(self, payload: Dict[str, str]) -> None:
        path_str = payload.get("path")
        if not path_str:
            return
        old_path = Path(path_str)
        old_name = old_path.name
        new_name, ok = QInputDialog.getText(self, "Rename folder", "New folder name:", text=old_name)
        if not ok or not new_name:
            return
        new_path = old_path.parent / new_name
        if new_path.exists():
            QMessageBox.warning(self, "Cannot rename", "A folder with that name already exists.")
            return
        was_current = bool(self._current_file and self._current_file.folder_path == old_path)
        current_filename = self._current_file.filename if was_current and self._current_file else None
        try:
            old_path.rename(new_path)
        except Exception as exc:
            QMessageBox.warning(self, "Failed to rename", str(exc))
            return
        self._rename_history.push(RenameAction(old_path=old_path, new_path=new_path))

        updated_dirty: Dict[str, str] = {}
        prefix = f"{old_name}/"
        for identifier, text_value in self._dirty_entries.items():
            if identifier.startswith(prefix):
                suffix = identifier[len(prefix):]
                updated_dirty[f"{new_name}/{suffix}"] = text_value
            else:
                updated_dirty[identifier] = text_value
        self._dirty_entries = updated_dirty

        updated_history: Dict[str, List[str]] = {}
        for identifier, stack in self._saved_history.items():
            if identifier.startswith(prefix):
                suffix = identifier[len(prefix):]
                updated_history[f"{new_name}/{suffix}"] = stack
            else:
                updated_history[identifier] = stack
        self._saved_history = updated_history

        new_sequence = None
        if self._document:
            try:
                self._document.reload()
            except Exception as exc:  # pragma: no cover - defensive
                QMessageBox.warning(self, "Failed to refresh", str(exc))
            else:
                if was_current and current_filename:
                    new_sequence = self._document.find_file(new_name, current_filename)
                    if new_sequence:
                        self._set_current_file(new_sequence)
                        if new_sequence.identifier in self._dirty_entries:
                            dirty_text = self._dirty_entries[new_sequence.identifier]
                            self.sequence_editor.blockSignals(True)
                            self.sequence_editor.setPlainText(dirty_text)
                            self.sequence_editor.blockSignals(False)
                    else:
                        self._set_current_file(None)
        else:
            if was_current:
                self._set_current_file(None)

        target_id = new_sequence.identifier if new_sequence else None
        self._rebuild_tree(target_identifier=target_id)
        self.statusBar().showMessage(f"Renamed folder to {new_name}", 4000)
        self._update_actions()

    def _rename_sequence(self, payload: Dict[str, str]) -> None:
        folder_name = payload.get("folder")
        filename = payload.get("filename")
        if not (self._document and folder_name and filename):
            return
        sequence = self._document.find_file(folder_name, filename)
        if not sequence:
            return
        current_name = sequence.filename
        new_name, ok = QInputDialog.getText(self, "Rename sequence", "New file name:", text=current_name)
        if not ok or not new_name:
            return
        old_identifier = sequence.identifier
        was_current = bool(self._current_file and self._current_file.identifier == old_identifier)
        dirty_backup = self._dirty_entries.pop(old_identifier, None)
        history_backup = self._saved_history.pop(old_identifier, None)
        old_path = sequence.path
        try:
            new_path = sequence.rename(new_name)
        except FileExistsError as exc:
            QMessageBox.warning(self, "Cannot rename", str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.warning(self, "Cannot rename", str(exc))
            return
        self._rename_history.push(RenameAction(old_path=old_path, new_path=new_path))

        new_sequence = None
        new_identifier = None
        if self._document:
            try:
                self._document.reload()
            except Exception as exc:  # pragma: no cover - defensive
                QMessageBox.warning(self, "Failed to refresh", str(exc))
            else:
                new_folder_name = Path(new_path).parent.name
                new_sequence = self._document.find_file(new_folder_name, new_path.name)
                if new_sequence:
                    new_identifier = new_sequence.identifier
                    if dirty_backup is not None:
                        self._dirty_entries[new_identifier] = dirty_backup
                    if was_current:
                        self._set_current_file(new_sequence)
                        if dirty_backup is not None:
                            self.sequence_editor.blockSignals(True)
                            self.sequence_editor.setPlainText(dirty_backup)
                            self.sequence_editor.blockSignals(False)
                    if history_backup is not None:
                        self._saved_history[new_identifier] = history_backup
                elif was_current:
                    self._set_current_file(None)
        elif was_current:
            self._set_current_file(None)
        if new_identifier is None and history_backup is not None:
            # rename failed to yield new identifier; restore original key
            self._saved_history[old_identifier] = history_backup

        target_identifier = new_identifier or (new_sequence.identifier if new_sequence else None)
        self._rebuild_tree(target_identifier=target_identifier)
        self.statusBar().showMessage(f"Renamed sequence to {new_path.name}", 4000)
        self._update_actions()

    def _undo_last_rename(self) -> None:
        try:
            action = self._rename_history.undo()
        except Exception as exc:
            QMessageBox.warning(self, "Failed to undo", str(exc))
            return
        if not action:
            return
        if self._document:
            try:
                self._document.reload()
            except Exception as exc:
                QMessageBox.warning(self, "Failed to refresh", str(exc))
        self._dirty_entries.clear()
        self._saved_history.clear()
        self._rebuild_tree()
        self.statusBar().showMessage("Rename undone", 4000)
        self._update_actions()

    # ----------------------------------------------------------------- templates
    def _refresh_template_set_box(self, target: Optional[str] = None) -> None:
        names = sorted(self.template_sets.keys())
        target_name = target or self.current_template_set
        self.template_set_box.blockSignals(True)
        self.template_set_box.clear()
        for name in names:
            self.template_set_box.addItem(name)
        if target_name in names:
            self.template_set_box.setCurrentText(target_name)
            self.current_template_set = target_name
        elif names:
            self.template_set_box.setCurrentIndex(0)
            self.current_template_set = self.template_set_box.currentText()
        self.template_set_box.blockSignals(False)
        self._populate_template_tree()

    def _on_template_set_changed(self, name: str) -> None:
        if not name or name == self.current_template_set or name not in self.template_sets:
            return
        self.current_template_set = name
        self._populate_template_tree()

    def _template_map(self) -> Dict[str, List[sequence_data.SequenceTemplate]]:
        return self.template_sets.get(self.current_template_set, {})

    def _populate_template_tree(self) -> None:
        if not hasattr(self, "template_tree"):
            return
        self.template_tree.blockSignals(True)
        self.template_tree.clear()
        mapping = self._template_map()
        for category in sorted(mapping.keys(), key=str.lower):
            category_item = QTreeWidgetItem([category])
            category_item.setData(0, Qt.UserRole, None)
            for tpl in mapping.get(category, []):
                child = QTreeWidgetItem([tpl.label])
                child.setData(0, Qt.UserRole, tpl)
                category_item.addChild(child)
            category_item.setExpanded(False)
            self.template_tree.addTopLevelItem(category_item)
        self.template_tree.blockSignals(False)
        if self.template_search_box:
            self.template_search_box.blockSignals(True)
            self.template_search_box.clear()
            self.template_search_box.blockSignals(False)
        self._apply_template_filter(initial=True)

    def _display_template(self, template: sequence_data.SequenceTemplate) -> None:
        lines = [template.description]
        if template.example:
            lines.append("")
            lines.append(template.example)
        if template.placeholders:
            lines.append("")
            lines.append("Placeholders:")
            for key, description in template.placeholders.items():
                lines.append(f"  {{{key}}}: {description}")
        if template.notes:
            lines.append("")
            lines.append(f"Notes: {template.notes}")
        self.template_preview.setPlainText("\n".join(lines))

    def _on_template_tree_selection(self) -> None:
        item = self.template_tree.currentItem()
        if not item:
            self.template_preview.clear()
            return
        template = item.data(0, Qt.UserRole)
        if isinstance(template, sequence_data.SequenceTemplate):
            self._display_template(template)
        else:
            self.template_preview.clear()

    def _on_template_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:  # noqa: ARG002
        template = item.data(0, Qt.UserRole)
        if isinstance(template, sequence_data.SequenceTemplate):
            self._insert_selected_template()

    def _insert_selected_template(self) -> None:
        item = self.template_tree.currentItem()
        if not item:
            return
        if not self.sequence_editor.isEnabled():
            QMessageBox.information(self, "No sequence loaded", "Open a sequence before inserting a template.")
            return
        template = item.data(0, Qt.UserRole)
        if not isinstance(template, sequence_data.SequenceTemplate):
            return
        cursor = self.sequence_editor.textCursor()
        cursor.insertText(template.body)
        self.sequence_editor.setTextCursor(cursor)
        self.sequence_editor.setFocus()

    def _apply_template_filter(self, _text: str = "", *, initial: bool = False) -> None:
        if not hasattr(self, "template_tree"):
            return
        pattern = ""
        if self.template_search_box:
            pattern = self.template_search_box.text().strip().lower()
        pattern = pattern.lower()
        first_child: Optional[QTreeWidgetItem] = None
        for idx in range(self.template_tree.topLevelItemCount()):
            category_item = self.template_tree.topLevelItem(idx)
            category_text = category_item.text(0).lower()
            category_match = bool(pattern) and pattern in category_text
            any_child_visible = False
            for child_idx in range(category_item.childCount()):
                child = category_item.child(child_idx)
                child_text = child.text(0).lower()
                child_match = pattern in child_text if pattern else True
                visible = child_match or category_match or not pattern
                child.setHidden(not visible)
                if visible:
                    any_child_visible = True
                    if (pattern and child_match) or (not pattern and first_child is None):
                        first_child = child if first_child is None else first_child
            category_visible = category_match or any_child_visible
            category_item.setHidden(not category_visible)
            category_item.setExpanded(bool(pattern) and category_visible)
            if first_child is None and category_visible and category_item.childCount():
                first_child = category_item.child(0)

        current = self.template_tree.currentItem()
        if current and current.isHidden():
            current = None

        if first_child is None:
            self.template_tree.setCurrentItem(None)
            if not initial:
                self.template_preview.clear()
            return

        if current is None or current.isHidden():
            self.template_tree.setCurrentItem(first_child)
            template = first_child.data(0, Qt.UserRole)
            if isinstance(template, sequence_data.SequenceTemplate):
                self._display_template(template)

    def _import_template_set(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import template set",
            str(self._templates_dir),
            "Template sets (*.json)",
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.warning(self, "Failed to import", str(exc))
            return
        name = str(data.get("name") or Path(path).stem)
        template_map = sequence_data.templates_from_dict(data)
        if not template_map:
            QMessageBox.warning(self, "Invalid template set", "No templates were found in the file.")
            return
        self.template_sets[name] = template_map
        self._template_set_paths[name] = Path(path)
        self._refresh_template_set_box(target=name)
        self.statusBar().showMessage(f"Imported template set '{name}'", 4000)

    def _export_template_set(self) -> None:
        if self.current_template_set not in self.template_sets:
            QMessageBox.warning(self, "Nothing to export", "No template set is selected.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export template set",
            str(self._template_file_for(self.current_template_set)),
            "Template sets (*.json)",
        )
        if not path:
            return
        template_map = self.template_sets[self.current_template_set]
        payload = sequence_data.templates_to_dict(self.current_template_set, template_map)
        try:
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Failed to export", str(exc))
            return
        self.statusBar().showMessage(f"Exported template set to {path}", 4000)

    def _show_preferences_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Preferences")
        layout = QVBoxLayout(dialog)

        layout_group = QGroupBox("Template preview layout")
        layout_group_layout = QVBoxLayout(layout_group)
        horizontal_radio = QRadioButton("Preview beside editor")
        vertical_radio = QRadioButton("Preview above editor")
        if self._preview_orientation == Qt.Horizontal:
            horizontal_radio.setChecked(True)
        else:
            vertical_radio.setChecked(True)
        layout_group_layout.addWidget(horizontal_radio)
        layout_group_layout.addWidget(vertical_radio)
        layout.addWidget(layout_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec() == QDialog.Accepted:
            new_orientation = Qt.Horizontal if horizontal_radio.isChecked() else Qt.Vertical
            self._set_preview_orientation(new_orientation)

    # ----------------------------------------------------------------- help
    def _show_help_dialog(self, title: str, content: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setUndoRedoEnabled(False)
        view.document().setDefaultStyleSheet(HELP_STYLESHEET)
        view.setHtml(f"<html><body>{content}</body></html>")
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.resize(760, 860)
        dialog.exec()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._is_closing = True
        self._save_settings()
        super().closeEvent(event)
