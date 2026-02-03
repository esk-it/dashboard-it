from __future__ import annotations

from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt, Signal, QPropertyAnimation
from PySide6.QtGui import QColor, QEnterEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QSpinBox, QFrame, QMessageBox,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)

from core.db import TaskRepository, Task


# ---------- Dialog ----------
class AddTaskDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter une tâche")
        self.resize(460, 240)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.title = QLineEdit()
        self.title.setPlaceholderText("Ex: Vérifier les agents WithSecure")

        self.category = QLineEdit()
        self.category.setPlaceholderText("admin / réseau / pédago")

        self.priority = QSpinBox()
        self.priority.setRange(1, 3)
        self.priority.setValue(2)

        self.due = QLineEdit()
        self.due.setPlaceholderText("YYYY-MM-DD (optionnel)")

        form.addRow("Titre", self.title)
        form.addRow("Catégorie", self.category)
        form.addRow("Priorité", self.priority)
        form.addRow("Échéance", self.due)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self):
        return (
            self.title.text().strip(),
            self.category.text().strip(),
            self.priority.value(),
            self.due.text().strip() or None
        )


# ---------- UI Widgets ----------
class Chip(QLabel):
    def __init__(self, text: str, variant: str = ""):
        super().__init__(text)
        self.setObjectName("Chip")
        self.setProperty("variant", variant)


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

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        # Check
        self.check = QPushButton()
        self.check.setObjectName("CheckBtn")
        self.check.setCheckable(True)
        self.check.setChecked(task.done)
        self.check.setFixedSize(26, 26)
        self.check.clicked.connect(self._toggle)
        self._refresh_icon()

        # Text
        left = QVBoxLayout()
        self.lbl_title = QLabel(task.title)
        self.lbl_title.setObjectName("TaskTitle")

        meta = []
        if task.category:
            meta.append(task.category)
        if task.due_date:
            meta.append(f"échéance {task.due_date}")

        self.lbl_meta = QLabel(" • ".join(meta))
        self.lbl_meta.setObjectName("TaskMeta")

        left.addWidget(self.lbl_title)
        left.addWidget(self.lbl_meta)

        # Right
        right = QHBoxLayout()
        if task.priority == 3:
            right.addWidget(Chip("priorité 3", "high"))
        elif task.priority == 1:
            right.addWidget(Chip("priorité 1", "low"))
        else:
            right.addWidget(Chip("priorité 2"))

        if task.due_date:
            right.addWidget(Chip(task.due_date))

        self.btn_del = QPushButton()
        self.btn_del.setObjectName("DelBtn")
        self.btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#AAB3C5"))
        self.btn_del.setIconSize(self.btn_del.sizeHint() * 0.75)
        self.btn_del.clicked.connect(lambda: self.deleted.emit(task.id))
        right.addWidget(self.btn_del)

        root.addWidget(self.check)
        root.addLayout(left, 1)
        root.addLayout(right)

        self._apply_done_style()

    def _refresh_icon(self):
        if self.check.isChecked():
            # fait : icône claire et pleine
            self.check.setIcon(qta.icon("fa5s.check-circle", color="#E6EAF2"))
            self.check.setProperty("checked", True)
        else:
            # pas fait : cercle vide (outline) bien lisible
            self.check.setIcon(qta.icon("fa5s.circle", color="#AAB3C5"))
            self.check.setProperty("checked", False)

        self.check.setIconSize(self.check.size() * 0.70)
        self.check.style().unpolish(self.check)
        self.check.style().polish(self.check)


    def _toggle(self):
        self._refresh_icon()
        self.task = self.task.__class__(**{**self.task.__dict__, "done": self.check.isChecked()})
        self._apply_done_style()
        self.toggled.emit(self.task.id, self.task.done)

    def _apply_done_style(self):
        f = self.lbl_title.font()
        f.setStrikeOut(self.task.done)
        self.lbl_title.setFont(f)

    def enterEvent(self, event: QEnterEvent):
        self.setProperty("hover", True)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().polish(self)
        super().leaveEvent(event)


# ---------- Page ----------
class TasksPage(QWidget):
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
            search=self.search.text()
        )

        for t in tasks:
            item = QListWidgetItem()
            row = TaskRow(t)

            row.toggled.connect(lambda i, d, tid=t.id: self.repo.set_done(tid, d))
            row.deleted.connect(self._delete_task)

            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)

            self._fade_in(row)

    def _fade_in(self, row: QWidget):
        eff = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", row)
        anim.setDuration(180)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        row._anim = anim

    def _delete_task(self, task_id: int):
        if QMessageBox.question(self, "Suppression", "Supprimer cette tâche ?") == QMessageBox.Yes:
            self.repo.delete_task(task_id)
            self.reload()

    def _sync_active(self, current, previous):
        for it, active in ((previous, False), (current, True)):
            if not it:
                continue
            w = self.list.itemWidget(it)
            if w:
                w.setProperty("active", active)
                w.style().polish(w)

    def add_task(self):
        dlg = AddTaskDialog(self)
        if dlg.exec() == QDialog.Accepted:
            t, c, p, d = dlg.values()
            if t:
                self.repo.add_task(t, c, p, d)
                self.reload()
