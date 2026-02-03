from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QEnterEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QFrame, QMessageBox, QTextEdit
)

import qtawesome as qta
from core.db import SupplierRepository, Supplier

DOMAIN_STYLES = {
    # clé = mot-clé détecté (lowercase)
    "réseau": ("#2D6CDF", "fa5s.network-wired"),
    "reseau": ("#2D6CDF", "fa5s.network-wired"),
    "wifi": ("#2D6CDF", "fa5s.wifi"),
    "fibre": ("#7C3AED", "fa5s.project-diagram"),
    "internet": ("#7C3AED", "fa5s.globe-europe"),
    "téléphonie": ("#10B981", "fa5s.phone"),
    "telephonie": ("#10B981", "fa5s.phone"),
    "imprim": ("#F59E0B", "fa5s.print"),
    "copieur": ("#F59E0B", "fa5s.print"),
    "sécurité": ("#EF4444", "fa5s.shield-alt"),
    "securite": ("#EF4444", "fa5s.shield-alt"),
    "antivirus": ("#EF4444", "fa5s.shield-alt"),
    "logiciel": ("#22C55E", "fa5s.puzzle-piece"),
    "matériel": ("#AAB3C5", "fa5s.toolbox"),
    "materiel": ("#AAB3C5", "fa5s.toolbox"),
}

DEFAULT_DOMAIN_STYLE = ("#AAB3C5", "fa5s.address-book")


def style_for_domain(domain: str):
    d = (domain or "").strip().lower()
    if not d:
        return DEFAULT_DOMAIN_STYLE
    for key, (color, icon_name) in DOMAIN_STYLES.items():
        if key in d:
            return color, icon_name
    return DEFAULT_DOMAIN_STYLE


class AddSupplierDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un prestataire")
        self.resize(520, 360)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit()
        self.name.setPlaceholderText("Ex: ACME Réseaux")

        self.domain = QLineEdit()
        self.domain.setPlaceholderText("Ex: réseau / fibre / imprimantes / téléphonie")

        self.contact = QLineEdit()
        self.contact.setPlaceholderText("Nom du contact (optionnel)")

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Téléphone (optionnel)")

        self.email = QLineEdit()
        self.email.setPlaceholderText("Email (optionnel)")

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Notes (contrat, horaires, infos intervention…)")

        form.addRow("Société / Nom", self.name)
        form.addRow("Domaine", self.domain)
        form.addRow("Contact", self.contact)
        form.addRow("Téléphone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("Notes", self.notes)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self):
        return (
            self.name.text().strip(),
            self.domain.text().strip(),
            self.phone.text().strip(),
            self.email.text().strip(),
            self.contact.text().strip(),
            self.notes.toPlainText().strip(),
        )


class Chip(QLabel):
    def __init__(self, text: str, variant: str = ""):
        super().__init__(text)
        self.setObjectName("Chip")
        self.setProperty("variant", variant)


class SupplierRow(QFrame):
    deleted = Signal(int)

    def __init__(self, s: Supplier):
        super().__init__()
        self.s = s
        self.setObjectName("TaskRow")           # on réutilise le style “row”
        self.setProperty("hover", False)
        self.setFrameShape(QFrame.NoFrame)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        # Icône domaine (simple, neutre)
        color, icon_name = style_for_domain(s.domain)

        # petite barre verticale de couleur (accent discret)
        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        icon = QLabel()
        icon.setFixedWidth(26)
        icon.setAlignment(Qt.AlignCenter)
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))


        # Bloc principal
        left = QVBoxLayout()
        left.setSpacing(2)

        title = QLabel(s.name)
        title.setObjectName("TaskTitle")
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)

        meta_parts = []
        if s.contact:
            meta_parts.append(s.contact)
        if s.phone:
            meta_parts.append(s.phone)
        if s.email:
            meta_parts.append(s.email)

        meta = QLabel(" • ".join(meta_parts))
        meta.setObjectName("TaskMeta")
        meta.setTextInteractionFlags(Qt.TextSelectableByMouse)

        left.addWidget(title)
        if meta_parts:
            left.addWidget(meta)

        # droite : chips + delete
        right = QHBoxLayout()
        right.setSpacing(8)

        if s.domain:
            chip = Chip(s.domain, "domain")
            chip.setStyleSheet(
                f"border: 1px solid {color}; color: #E6EAF2; background-color: rgba(45,108,223,0.0);"
            )
            right.addWidget(chip)


        btn_copy_mail = QPushButton()
        btn_copy_mail.setObjectName("DelBtn")
        btn_copy_mail.setToolTip("Copier email")
        btn_copy_mail.setIcon(qta.icon("fa5s.copy", color="#AAB3C5"))
        btn_copy_mail.clicked.connect(self._copy_email)
        right.addWidget(btn_copy_mail)

        btn_copy_phone = QPushButton()
        btn_copy_phone.setObjectName("DelBtn")
        btn_copy_phone.setToolTip("Copier téléphone")
        btn_copy_phone.setIcon(qta.icon("fa5s.phone", color="#AAB3C5"))
        btn_copy_phone.clicked.connect(self._copy_phone)
        right.addWidget(btn_copy_phone)

        btn_del = QPushButton()
        btn_del.setObjectName("DelBtn")
        btn_del.setToolTip("Supprimer")
        btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#AAB3C5"))
        btn_del.clicked.connect(lambda: self.deleted.emit(self.s.id))
        right.addWidget(btn_del)

        root.addWidget(accent, 0, Qt.AlignVCenter)
        root.addWidget(icon, 0, Qt.AlignVCenter)
        root.addLayout(left, 1)
        root.addLayout(right, 0)

        # Notes en tooltip si présent
        if s.notes:
            self.setToolTip(s.notes)

    def _copy_email(self):
        if not self.s.email:
            return
        QApplication = self.window().windowHandle()  # not used, keep simple
        cb = self._clipboard()
        cb.setText(self.s.email)

    def _copy_phone(self):
        if not self.s.phone:
            return
        cb = self._clipboard()
        cb.setText(self.s.phone)

    def _clipboard(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.clipboard()

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


class SuppliersPage(QWidget):
    def __init__(self, repo: SupplierRepository):
        super().__init__()
        self.repo = repo

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Prestataires")
        title.setObjectName("PageTitle")

        self.btn_add = QPushButton("+ Ajouter")
        self.btn_add.setProperty("class", "PrimaryButton")

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.btn_add)

        filters = QHBoxLayout()
        self.domain = QComboBox()
        self.domain.addItem("Tous")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher (nom, domaine, tel, email, notes...)")

        self.btn_refresh = QPushButton("Actualiser")
        self.btn_refresh.setProperty("class", "GhostButton")

        filters.addWidget(QLabel("Domaine"))
        filters.addWidget(self.domain)
        filters.addSpacing(10)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.btn_refresh)

        self.list = QListWidget()
        self.list.setSpacing(10)

        root.addLayout(header)
        root.addLayout(filters)
        root.addWidget(self.list, 1)

        self.btn_add.clicked.connect(self.add_supplier)
        self.btn_refresh.clicked.connect(self.reload)
        self.domain.currentIndexChanged.connect(self.reload)
        self.search.textChanged.connect(self.reload)

        self.reload()

    def _reload_domains(self):
        current = self.domain.currentText()
        self.domain.blockSignals(True)
        self.domain.clear()
        self.domain.addItem("Tous")
        for d in self.repo.list_domains():
            self.domain.addItem(d)
        # Restore selection if exists
        i = self.domain.findText(current)
        if i >= 0:
            self.domain.setCurrentIndex(i)
        self.domain.blockSignals(False)

    def reload(self):
        self._reload_domains()
        self.list.clear()

        suppliers = self.repo.list_suppliers(
            search=self.search.text(),
            domain=self.domain.currentText(),
        )

        for s in suppliers:
            item = QListWidgetItem()
            row = SupplierRow(s)
            row.deleted.connect(self._delete_supplier)

            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)

    def add_supplier(self):
        dlg = AddSupplierDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        name, domain, phone, email, contact, notes = dlg.values()
        if not name:
            return

        self.repo.add_supplier(
            name=name,
            domain=domain,
            phone=phone,
            email=email,
            contact=contact,
            notes=notes,
        )
        self.reload()

    def _delete_supplier(self, supplier_id: int):
        res = QMessageBox.question(self, "Suppression", "Supprimer ce prestataire ?")
        if res != QMessageBox.Yes:
            return
        self.repo.delete_supplier(supplier_id)
        self.reload()
