from __future__ import annotations

from dataclasses import replace
from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QDate
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QSpinBox, QFrame, QMessageBox, QTextEdit,
    QGraphicsOpacityEffect, QDateEdit, QCheckBox
)

from core.db import TaskRepository, Task


# -----------------------------
# Category styling
# -----------------------------
CATEGORY_STYLES = {
    "réseau": ("#2D6CDF", "fa5s.network-wired"),
    "reseau": ("#2D6CDF", "fa5s.network-wired"),
    "wifi": ("#2D6CDF", "fa5s.wifi"),
    "admin": ("#A855F7", "fa5s.user-shield"),
    "pédago": ("#22C55E", "fa5s.graduation-cap"),
    "pedago": ("#22C55E", "fa5s.graduation-cap"),
    "sécurité": ("#EF4444", "fa5s.shield-alt"),
    "securite": ("#EF4444", "fa5s.shield-alt"),
    "imprim": ("#F59E0B", "fa5s.print"),
    "copieur": ("#F59E0B", "fa5s.print"),
    "serveur": ("#38BDF8", "fa5s.server"),
    "backup": ("#38BDF8", "fa5s.hdd"),
    "sauveg": ("#38BDF8", "fa5s.hdd"),
    "mail": ("#AAB3C5", "fa5s.envelope"),
    "support": ("#AAB3C5", "fa5s.headset"),
    "logiciel": ("#22C55E", "fa5s.puzzle-piece"),
}
DEFAULT_CATEGORY_STYLE = ("#AAB3C5", "fa5s.tag")


def style_for_category(category: str) -> tuple[str, str]:
    c = (category or "").strip().lower()
    if not c:
        return DEFAULT_CATEGORY_STYLE
    for key, val in CATEGORY_STYLES.items():
        if key in c:
            return val
    return DEFAULT_CATEGORY_STYLE


# -----------------------------
# Priority styling
# -----------------------------
PRIORITY_STYLES = {
    1: ("#22C55E", "Basse", "fa5s.arrow-down"),
    2: ("#2D6CDF", "Normale", "fa5s.equals"),
    3: ("#EF4444", "Urgente", "fa5s.exclamation-triangle"),
}


def style_for_priority(p: int) -> tuple[str, str, str]:
    return PRIORITY_STYLES.get(int(p or 2), PRIORITY_STYLES[2])


# -----------------------------
# Date helpers
# -----------------------------
def qdate_from_iso(iso: str) -> QDate:
    try:
        y, m, d = iso.split("-")
        return QDate(int(y), int(m), int(d))
    except Exception:
        return QDate.currentDate()


def iso_from_qdate(d: QDate) -> str:
    return d.toString("yyyy-MM-dd")


# -----------------------------
# Dialogs
# -----------------------------
class TaskDialogBase(QDialog):
    def __init__(self, repo: TaskRepository, parent: QWidget | None = None, window_title: str = "Tâche"):
        super().__init__(parent)
        self.repo = repo
        self.setWindowTitle(window_title)
        self.resize(580, 420)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.title = QLineEdit()
        self.title.setPlaceholderText("Ex: Vérifier les agents WithSecure")

        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.category.setPlaceholderText("Choisir ou taper une catégorie…")

        cats = self.repo.list_categories()
        defaults = ["Réseau", "Admin", "Pédago", "Sécurité", "Imprimantes", "Serveur", "Support"]
        for d in reversed(defaults):
            if d not in cats:
                cats.insert(0, d)
        self.category.addItems(cats)

        self.priority = QSpinBox()
        self.priority.setRange(1, 3)
        self.priority.setValue(2)

        self.no_due = QCheckBox("Sans échéance")
        self.no_due.setChecked(False)

        self.due = QDateEdit()
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat("dd/MM/yyyy")
        self.due.setDate(QDate.currentDate())

        self.no_due.toggled.connect(self._sync_due_enabled)
        self._sync_due_enabled(self.no_due.isChecked())

        due_row = QHBoxLayout()
        due_row.setSpacing(10)
        due_row.addWidget(self.due, 0)
        due_row.addWidget(self.no_due, 0)
        due_wrap = QWidget()
        due_wrap.setLayout(due_row)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Commentaires / détails (optionnel)…")
        self.notes.setMinimumHeight(110)

        form.addRow("Titre", self.title)
        form.addRow("Catégorie", self.category)
        form.addRow("Priorité", self.priority)
        form.addRow("Échéance", due_wrap)
        form.addRow("Commentaires", self.notes)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _sync_due_enabled(self, no_due: bool):
        self.due.setEnabled(not no_due)

    def set_values(self, title: str, category: str, priority: int, due_iso: Optional[str], notes: str):
        self.title.setText(title or "")

        i = self.category.findText(category or "")
        if i >= 0:
            self.category.setCurrentIndex(i)
        else:
            self.category.setCurrentText(category or "")

        self.priority.setValue(int(priority or 2))

        if due_iso:
            self.no_due.setChecked(False)
            self.due.setDate(qdate_from_iso(due_iso))
        else:
            self.no_due.setChecked(True)

        self.notes.setPlainText(notes or "")

    def values(self) -> tuple[str, str, int, Optional[str], str]:
        t = self.title.text().strip()
        c = self.category.currentText().strip()
        p = int(self.priority.value())
        d = None if self.no_due.isChecked() else iso_from_qdate(self.due.date())
        n = self.notes.toPlainText().strip()
        return t, c, p, d, n

    def _on_accept(self):
        t, *_ = self.values()
        if not t:
            QMessageBox.warning(self, "Validation", "Le titre est obligatoire.")
            return
        self.accept()


class AddTaskDialog(TaskDialogBase):
    def __init__(self, repo: TaskRepository, parent: QWidget | None = None):
        super().__init__(repo, parent, "Ajouter une tâche")


class EditTaskDialog(TaskDialogBase):
    def __init__(self, repo: TaskRepository, parent: QWidget | None = None):
        super().__init__(repo, parent, "Modifier la tâche")


# -----------------------------
# UI Widgets
# -----------------------------
class Chip(QLabel):
    def __init__(self, text: str, border_color: Optional[str] = None):
        super().__init__(text)
        self.setObjectName("Chip")
        if border_color:
            self.setStyleSheet(f"border: 1px solid {border_color}; color: #E6EAF2; background: transparent;")


class CategoryChip(QWidget):
    def __init__(self, category: str):
        super().__init__()
        self.setStyleSheet("background: transparent;")

        color, icon_key = style_for_category(category)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 11pt; background: transparent;")

        ico = QLabel()
        ico.setFixedWidth(18)
        ico.setAlignment(Qt.AlignCenter)
        ico.setPixmap(qta.icon(icon_key, color=color).pixmap(14, 14))

        chip = QLabel(category)
        chip.setObjectName("Chip")
        chip.setStyleSheet(f"border: 1px solid {color}; color: #E6EAF2; background: transparent;")

        lay.addWidget(dot)
        lay.addWidget(ico)
        lay.addWidget(chip)


class TaskRow(QFrame):
    toggled = Signal(int, bool)
    deleted = Signal(int)

    def __init__(self, task: Task):
        super().__init__()
        self.task = task

        self.setObjectName("TaskRow")
        self.setProperty("hover", False)
        self.setProperty("active", False)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        pr_color, pr_label, pr_icon = style_for_priority(task.priority)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background-color: {pr_color}; border-radius: 2px;")

        # Check
        self.check = QPushButton()
        self.check.setObjectName("CheckBtn")
        self.check.setCheckable(True)
        self.check.setChecked(task.done)
        self.check.setFixedSize(26, 26)
        self.check.clicked.connect(self._toggle)
        self._refresh_icon()

        # Left
        left = QVBoxLayout()
        left.setSpacing(6)

        self.lbl_title = QLabel(task.title)
        self.lbl_title.setObjectName("TaskTitle")
        left.addWidget(self.lbl_title)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(10)

        if task.category:
            meta_row.addWidget(CategoryChip(task.category), 0)

        if task.due_date:
            cal = QLabel()
            cal.setPixmap(qta.icon("fa5s.calendar-alt", color="#AAB3C5").pixmap(14, 14))
            meta_row.addWidget(cal, 0)

            due = QLabel(task.due_date)
            due.setObjectName("TaskMeta")
            due.setStyleSheet("background: transparent;")
            meta_row.addWidget(due, 0)

        meta_row.addStretch(1)
        left.addLayout(meta_row)

        # Details (comments) - hidden by default; shown when active
        self.details = QLabel(task.notes or "")
        self.details.setWordWrap(True)
        self.details.setProperty("class", "Muted")
        self.details.setStyleSheet("background: transparent; padding-top: 2px;")
        self.details.setVisible(False)
        left.addWidget(self.details)

        # Right
        right = QHBoxLayout()
        right.setSpacing(8)

        pr_ico = QLabel()
        pr_ico.setPixmap(qta.icon(pr_icon, color=pr_color).pixmap(14, 14))
        right.addWidget(pr_ico, 0)

        right.addWidget(Chip(pr_label, border_color=pr_color), 0)

        self.btn_del = QPushButton()
        self.btn_del.setObjectName("DelBtn")
        self.btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#AAB3C5"))
        self.btn_del.clicked.connect(lambda: self.deleted.emit(task.id))
        right.addWidget(self.btn_del)

        root.addWidget(accent, 0, Qt.AlignVCenter)
        root.addWidget(self.check, 0, Qt.AlignTop)
        root.addLayout(left, 1)
        root.addLayout(right, 0)

        self._apply_done_style()

    def set_active(self, active: bool):
        self.setProperty("active", active)
        self.details.setVisible(active and bool((self.task.notes or "").strip()))
        self.style().unpolish(self)
        self.style().polish(self)

    def set_notes(self, notes: str):
        self.task = replace(self.task, notes=notes or "")
        self.details.setText(self.task.notes or "")

    def _refresh_icon(self):
        if self.check.isChecked():
            self.check.setIcon(qta.icon("fa5s.check-circle", color="#E6EAF2"))
            self.check.setProperty("checked", True)
        else:
            self.check.setIcon(qta.icon("fa5s.circle", color="#AAB3C5"))
            self.check.setProperty("checked", False)

        self.check.setIconSize(self.check.size() * 0.70)
        self.check.style().unpolish(self.check)
        self.check.style().polish(self.check)

    def _toggle(self):
        self._refresh_icon()
        self.task = replace(self.task, done=self.check.isChecked())
        self._apply_done_style()
        self.toggled.emit(self.task.id, self.task.done)

    def _apply_done_style(self):
        f = self.lbl_title.font()
        f.setStrikeOut(self.task.done)
        self.lbl_title.setFont(f)

    def enterEvent(self, event: QEnterEvent):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)


# -----------------------------
# Page
# -----------------------------
class TasksPage(QWidget):
    changed = Signal()

    def __init__(self, repo: TaskRepository):
        super().__init__()
        self.repo = repo

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Tâches")
        title.setObjectName("PageTitle")

        self.btn_add = QPushButton("+ Ajouter")
        self.btn_add.setProperty("class", "PrimaryButton")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.btn_add)

        filters = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItems(["Tout", "À faire", "Fait"])

        self.search = QLineEdit()
        self.search.setPlaceholderText("Recherche")

        filters.addWidget(self.status)
        filters.addWidget(self.search)

        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._sync_active)
        self.list.itemDoubleClicked.connect(self._edit_task_from_item)

        root.addLayout(header)
        root.addLayout(filters)
        root.addWidget(self.list)

        self.btn_add.clicked.connect(self.add_task)
        self.status.currentIndexChanged.connect(self.reload)
        self.search.textChanged.connect(self.reload)

        self.reload()

    def reload(self):
        self.list.clear()
        tasks = self.repo.list_tasks(
            status=["all", "open", "done"][self.status.currentIndex()],
            search=self.search.text(),
        )

        for t in tasks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, t.id)

            row = TaskRow(t)
            row.toggled.connect(self._on_toggle_done)
            row.deleted.connect(self._delete_task)

            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)

            self._fade_in(row)

    def _fade_in(self, row: QWidget):
        eff = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", row)
        anim.setDuration(160)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        row._anim = anim

    def _on_toggle_done(self, task_id: int, done: bool):
        self.repo.set_done(task_id, done)
        self.changed.emit()

    def _delete_task(self, task_id: int):
        if QMessageBox.question(self, "Suppression", "Supprimer cette tâche ?") == QMessageBox.Yes:
            self.repo.delete_task(task_id)
            self.reload()
            self.changed.emit()

    def _sync_active(self, current, previous):
        for it, active in ((previous, False), (current, True)):
            if not it:
                continue
            w = self.list.itemWidget(it)
            if isinstance(w, TaskRow):
                w.set_active(active)
                it.setSizeHint(w.sizeHint())  # important: resize item for details area

    def add_task(self):
        dlg = AddTaskDialog(self.repo, self)
        if dlg.exec() != QDialog.Accepted:
            return
        t, c, p, d, n = dlg.values()
        self.repo.add_task(t, c, p, d, n)
        self.reload()
        self.changed.emit()

    def _edit_task_from_item(self, item: QListWidgetItem):
        task_id = int(item.data(Qt.UserRole))
        self.edit_task(task_id)

    def edit_task(self, task_id: int):
        task = self.repo.get_task(task_id)
        if not task:
            QMessageBox.warning(self, "Erreur", "Tâche introuvable.")
            return

        dlg = EditTaskDialog(self.repo, self)
        dlg.set_values(task.title, task.category, task.priority, task.due_date, task.notes)

        if dlg.exec() != QDialog.Accepted:
            return

        title, category, priority, due_iso, notes = dlg.values()
        self.repo.update_task(task_id, title, category, priority, due_iso, notes)
        self.reload()
        self.changed.emit()
