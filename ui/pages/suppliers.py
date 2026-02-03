# ui/pages/suppliers.py
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QEnterEvent, QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QFrame, QMessageBox, QTextEdit, QApplication, QFileDialog,
    QColorDialog, QSpinBox, QScrollArea, QGridLayout
)

import qtawesome as qta
from core.db import SupplierRepository, Supplier, SupplierDomain


DEFAULT_DOMAIN_STYLE = ("#AAB3C5", "fa5s.address-book")

DOMAIN_KEYWORDS = {
    "réseau": ("#2D6CDF", "fa5s.network-wired"),
    "reseau": ("#2D6CDF", "fa5s.network-wired"),
    "wifi": ("#2D6CDF", "fa5s.wifi"),
    "fibre": ("#7C3AED", "fa5s.globe-europe"),
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


# Catalogue d'icônes "pratiques" (tu peux en ajouter facilement)
# Format: (icon_key, label)
ICON_CATALOG = [
    ("fa5s.address-book", "Contacts"),
    ("fa5s.network-wired", "Réseau"),
    ("fa5s.wifi", "Wi-Fi"),
    ("fa5s.globe-europe", "Internet"),
    ("fa5s.project-diagram", "Fibre"),
    ("fa5s.phone", "Téléphonie"),
    ("fa5s.print", "Impression"),
    ("fa5s.shield-alt", "Sécurité"),
    ("fa5s.lock", "Verrou"),
    ("fa5s.key", "Clé"),
    ("fa5s.user-shield", "Admin"),
    ("fa5s.server", "Serveur"),
    ("fa5s.database", "Base"),
    ("fa5s.cloud", "Cloud"),
    ("fa5s.hdd", "Stockage"),
    ("fa5s.tools", "Outils"),
    ("fa5s.toolbox", "Matériel"),
    ("fa5s.desktop", "PC"),
    ("fa5s.laptop", "Laptop"),
    ("fa5s.mobile-alt", "Mobile"),
    ("fa5s.tablet-alt", "Tablette"),
    ("fa5s.tv", "Écran"),
    ("fa5s.video", "Vidéo"),
    ("fa5s.camera", "Caméra"),
    ("fa5s.eye", "Surveillance"),
    ("fa5s.bolt", "Énergie"),
    ("fa5s.plug", "Prise"),
    ("fa5s.cogs", "Paramètres"),
    ("fa5s.wrench", "Maintenance"),
    ("fa5s.puzzle-piece", "Logiciels"),
    ("fa5s.code", "Dev"),
    ("fa5s.file-alt", "Docs"),
    ("fa5s.envelope", "Mail"),
    ("fa5s.exclamation-triangle", "Alerte"),
    ("fa5s.check-circle", "OK"),
    ("fa5s.times-circle", "KO"),
    ("fa5s.sync", "Sync"),
    ("fa5s.clock", "Temps"),
    ("fa5s.map-marker-alt", "Site"),
]


def _initials(name: str) -> str:
    parts = [p for p in (name or "").strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[1][:1]).upper()


def import_logo_to_project(file_path: str, project_dir: Path) -> str:
    src = Path(file_path)
    if not src.exists():
        return ""

    logos_dir = project_dir / "logos"
    logos_dir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        ext = src.suffix or ".png"

    dst_name = f"{uuid.uuid4().hex}{ext}"
    dst = logos_dir / dst_name
    shutil.copy2(src, dst)

    return str(Path("logos") / dst_name)


class DomainStyleResolver:
    def __init__(self, repo: SupplierRepository):
        self.repo = repo
        self._map: dict[str, tuple[str, str]] = {}
        self.reload()

    def reload(self):
        self._map.clear()
        for d in self.repo.list_domain_records():
            self._map[d.name.strip().lower()] = (d.color_hex, d.icon_key)

    def style_for(self, domain: str) -> tuple[str, str]:
        d = (domain or "").strip()
        if not d:
            return DEFAULT_DOMAIN_STYLE

        key = d.lower()
        if key in self._map:
            return self._map[key]

        for k, v in DOMAIN_KEYWORDS.items():
            if k in key:
                return v

        return DEFAULT_DOMAIN_STYLE


class LogoPicker(QWidget):
    def __init__(self, project_dir: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.project_dir = project_dir
        self._rel_path = ""

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.path = QLineEdit()
        self.path.setReadOnly(True)
        self.path.setPlaceholderText("Aucun logo")

        self.btn_pick = QPushButton("Choisir…")
        self.btn_pick.setProperty("class", "GhostButton")
        self.btn_clear = QPushButton("Effacer")
        self.btn_clear.setProperty("class", "GhostButton")

        self.btn_pick.clicked.connect(self.pick)
        self.btn_clear.clicked.connect(self.clear)

        lay.addWidget(self.path, 1)
        lay.addWidget(self.btn_pick)
        lay.addWidget(self.btn_clear)

    def set_value(self, rel_path: str):
        self._rel_path = (rel_path or "").strip()
        self.path.setText(self._rel_path)

    def value(self) -> str:
        return (self._rel_path or "").strip()

    def pick(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un logo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not file_path:
            return
        rel = import_logo_to_project(file_path, self.project_dir)
        self.set_value(rel)

    def clear(self):
        self.set_value("")


class SupplierLogo(QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(44, 44)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "border: 1px solid #1B263A; border-radius: 12px; background-color: #0B1322; color: #E6EAF2; font-weight: 800;"
        )

    def set_logo(self, project_dir: Path, rel_path: str, fallback_text: str):
        rel_path = (rel_path or "").strip()
        if rel_path:
            full = project_dir / rel_path
            if full.exists():
                px = QPixmap(str(full))
                if not px.isNull():
                    px = px.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.setPixmap(px)
                    self.setText("")
                    self.setStyleSheet(
                        "border: 1px solid #1B263A; border-radius: 12px; background-color: #0F1625;"
                    )
                    return

        self.setPixmap(QPixmap())
        self.setText(fallback_text)
        self.setStyleSheet(
            "border: 1px solid #1B263A; border-radius: 12px; background-color: #0B1322; color: #E6EAF2; font-weight: 900;"
        )


# -----------------------------
# Icon Picker Dialog
# -----------------------------
class IconPickerDialog(QDialog):
    """
    Fenêtre de sélection d'icône :
    - recherche
    - grille d'icônes (catalogue)
    Retour: icon_key choisi (string) ou "" si cancel.
    """
    def __init__(self, parent: QWidget, color_hex: str, current_key: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Choisir une icône")
        self.resize(760, 520)

        self._color = (color_hex or "#AAB3C5").strip()
        self._current = (current_key or "").strip()
        self.selected_key: str = ""

        root = QVBoxLayout(self)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)

        lbl = QLabel("Recherche")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Ex: réseau, wifi, sécurité, mail…")
        self.search.textChanged.connect(self._rebuild_grid)

        top.addWidget(lbl)
        top.addWidget(self.search, 1)
        root.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)

        self.scroll.setWidget(container)
        root.addWidget(self.scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._rebuild_grid()

    def _clear_grid(self):
        while self.grid.count():
            it = self.grid.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _match(self, q: str, key: str, label: str) -> bool:
        if not q:
            return True
        q = q.lower().strip()
        return (q in key.lower()) or (q in label.lower())

    def _rebuild_grid(self):
        q = self.search.text()
        self._clear_grid()

        # Filtre sur le catalogue
        items = [(k, lbl) for (k, lbl) in ICON_CATALOG if self._match(q, k, lbl)]
        if not items:
            # fallback: afficher tout si la recherche est trop stricte
            items = ICON_CATALOG[:]

        cols = 8
        row = 0
        col = 0

        for (key, label) in items:
            btn = QPushButton()
            btn.setToolTip(f"{label}\n{key}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(54, 54)
            btn.setObjectName("DelBtn")  # réutilise ton style “bouton” dark

            # icon preview
            try:
                btn.setIcon(qta.icon(key, color=self._color))
            except Exception:
                btn.setIcon(qta.icon("fa5s.exclamation-triangle", color="#EF4444"))
            btn.setIconSize(btn.sizeHint() * 0.70)

            # surlignage si icône courante
            if self._current and key == self._current:
                btn.setStyleSheet(
                    "border: 1px solid #2D6CDF; background-color: #0F1A33; border-radius: 10px;"
                )

            btn.clicked.connect(lambda _=False, k=key: self._choose(k))
            self.grid.addWidget(btn, row, col)

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _choose(self, key: str):
        self.selected_key = key
        self.accept()


class IconField(QWidget):
    """
    Champ icône non-éditable + bouton “picker”.
    Stocke la valeur icon_key en interne.
    """
    valueChanged = Signal(str)

    def __init__(self, color_hex: str, icon_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = (color_hex or "#AAB3C5").strip()
        self._key = (icon_key or "fa5s.address-book").strip()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.txt = QLineEdit(self._key)
        self.txt.setReadOnly(True)

        self.btn_pick = QPushButton()
        self.btn_pick.setObjectName("DelBtn")
        self.btn_pick.setToolTip("Choisir une icône")
        self.btn_pick.setFixedSize(40, 40)
        self.btn_pick.clicked.connect(self.pick)

        self.preview = QLabel()
        self.preview.setFixedWidth(30)
        self.preview.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.txt, 1)
        lay.addWidget(self.btn_pick, 0)
        lay.addWidget(self.preview, 0)

        self._refresh()

    def set_color(self, color_hex: str):
        self._color = (color_hex or "#AAB3C5").strip()
        self._refresh()

    def set_value(self, icon_key: str):
        self._key = (icon_key or "fa5s.address-book").strip()
        self.txt.setText(self._key)
        self._refresh()
        self.valueChanged.emit(self._key)

    def value(self) -> str:
        return (self._key or "").strip()

    def _refresh(self):
        key = self._key or "fa5s.address-book"
        try:
            ico = qta.icon(key, color=self._color)
            self.btn_pick.setIcon(ico)
            self.btn_pick.setIconSize(self.btn_pick.sizeHint() * 0.70)
            self.preview.setPixmap(ico.pixmap(20, 20))
        except Exception:
            ico = qta.icon("fa5s.exclamation-triangle", color="#EF4444")
            self.btn_pick.setIcon(ico)
            self.preview.setPixmap(ico.pixmap(20, 20))

    def pick(self):
        dlg = IconPickerDialog(self, color_hex=self._color, current_key=self._key)
        if dlg.exec() == QDialog.Accepted and dlg.selected_key:
            self.set_value(dlg.selected_key)


# -----------------------------
# Domain manager
# -----------------------------
class DomainRow(QFrame):
    changed = Signal()
    deleted = Signal(str)

    def __init__(self, repo: SupplierRepository, dom: SupplierDomain):
        super().__init__()
        self.repo = repo
        self.original_name = dom.name

        self.setObjectName("TaskRow")
        self.setProperty("hover", False)
        self.setFrameShape(QFrame.NoFrame)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        self.name = QLineEdit(dom.name)
        self.name.setPlaceholderText("Nom du domaine")

        self.color_btn = QPushButton()
        self.color_btn.setObjectName("DelBtn")
        self.color_btn.setToolTip("Choisir couleur")
        self.color_hex = (dom.color_hex or "#AAB3C5").strip()
        self._apply_color_btn()
        self.color_btn.clicked.connect(self._pick_color)

        # Nouveau: icon picker (plus de saisie manuelle)
        self.icon_field = IconField(self.color_hex, dom.icon_key)

        self.sort = QSpinBox()
        self.sort.setRange(0, 999)
        self.sort.setValue(int(dom.sort_order))

        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.setProperty("class", "PrimaryButton")
        self.btn_save.clicked.connect(self._save)

        self.btn_del = QPushButton()
        self.btn_del.setObjectName("DelBtn")
        self.btn_del.setToolTip("Supprimer")
        self.btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#AAB3C5"))
        self.btn_del.clicked.connect(self._delete)

        root.addWidget(QLabel("Nom"))
        root.addWidget(self.name, 2)
        root.addSpacing(6)

        root.addWidget(QLabel("Couleur"))
        root.addWidget(self.color_btn, 0)
        root.addSpacing(6)

        root.addWidget(QLabel("Icône"))
        root.addWidget(self.icon_field, 2)
        root.addSpacing(6)

        root.addWidget(QLabel("Ordre"))
        root.addWidget(self.sort, 0)
        root.addSpacing(6)

        root.addWidget(self.btn_save, 0)
        root.addWidget(self.btn_del, 0)

    def _apply_color_btn(self):
        self.color_btn.setFixedSize(34, 34)
        self.color_btn.setStyleSheet(
            f"background-color: {self.color_hex}; border: 1px solid #1B263A; border-radius: 10px;"
        )

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color_hex), self, "Choisir une couleur")
        if not c.isValid():
            return
        self.color_hex = c.name().upper()
        self._apply_color_btn()
        self.icon_field.set_color(self.color_hex)

    def _save(self):
        try:
            self.repo.update_domain(
                old_name=self.original_name,
                new_name=self.name.text(),
                color_hex=self.color_hex,
                icon_key=self.icon_field.value(),
                sort_order=self.sort.value(),
            )
            self.original_name = self.name.text().strip()
            self.changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _delete(self):
        name = self.original_name.strip()
        if not name:
            return
        if QMessageBox.question(self, "Suppression", f"Supprimer le domaine '{name}' ?") != QMessageBox.Yes:
            return
        try:
            self.repo.delete_domain(name)
            self.deleted.emit(name)
        except Exception as e:
            QMessageBox.warning(self, "Suppression impossible", str(e))

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


class DomainManagerDialog(QDialog):
    def __init__(self, parent: QWidget, repo: SupplierRepository):
        super().__init__(parent)
        self.repo = repo
        self.setWindowTitle("Gérer les domaines")
        self.resize(980, 520)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Domaines")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        root.addLayout(header)

        add_bar = QHBoxLayout()
        add_bar.setSpacing(10)

        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("Nouveau domaine (ex: Vidéosurveillance)")

        self.new_color = "#AAB3C5"

        self.btn_new_color = QPushButton()
        self.btn_new_color.setObjectName("DelBtn")
        self.btn_new_color.setFixedSize(34, 34)
        self.btn_new_color.clicked.connect(self._pick_new_color)

        # IMPORTANT: créer l'IconField AVANT d'appeler _apply_new_color()
        self.new_icon = IconField(self.new_color, "fa5s.address-book")

        # Maintenant seulement on applique le style couleur (qui appelle new_icon.set_color)
        self._apply_new_color()

        self.new_order = QSpinBox()
        self.new_order.setRange(0, 999)
        self.new_order.setValue(100)

        self.btn_add = QPushButton("Ajouter")
        self.btn_add.setProperty("class", "PrimaryButton")
        self.btn_add.clicked.connect(self._add_domain)

        add_bar.addWidget(QLabel("Nom"))
        add_bar.addWidget(self.new_name, 2)
        add_bar.addWidget(QLabel("Couleur"))
        add_bar.addWidget(self.btn_new_color, 0)
        add_bar.addWidget(QLabel("Icône"))
        add_bar.addWidget(self.new_icon, 2)
        add_bar.addWidget(QLabel("Ordre"))
        add_bar.addWidget(self.new_order, 0)
        add_bar.addWidget(self.btn_add, 0)

        root.addLayout(add_bar)

        self.list = QListWidget()
        self.list.setSpacing(10)
        root.addWidget(self.list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

        self.reload()

    def _apply_new_color(self):
        self.btn_new_color.setStyleSheet(
            f"background-color: {self.new_color}; border: 1px solid #1B263A; border-radius: 10px;"
        )
        self.new_icon.set_color(self.new_color)

    def _pick_new_color(self):
        c = QColorDialog.getColor(QColor(self.new_color), self, "Choisir une couleur")
        if not c.isValid():
            return
        self.new_color = c.name().upper()
        self._apply_new_color()

    def reload(self):
        self.list.clear()
        for d in self.repo.list_domain_records():
            item = QListWidgetItem()
            row = DomainRow(self.repo, d)
            row.changed.connect(self.reload)
            row.deleted.connect(lambda _name: self.reload())
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)

    def _add_domain(self):
        try:
            self.repo.add_domain(
                name=self.new_name.text(),
                color_hex=self.new_color,
                icon_key=self.new_icon.value(),
                sort_order=self.new_order.value(),
            )
            self.new_name.setText("")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))


# -----------------------------
# Suppliers dialogs
# -----------------------------
class AddSupplierDialog(QDialog):
    def __init__(self, domains: list[str], project_dir: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un prestataire")
        self.resize(560, 420)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit()
        self.name.setPlaceholderText("Ex: ACME Réseaux")

        self.domain = QComboBox()
        self.domain.setEditable(True)
        self.domain.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.domain.setPlaceholderText("Choisir ou taper un domaine…")
        self.domain.addItems(domains)

        self.logo = LogoPicker(project_dir)

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
        form.addRow("Logo", self.logo)
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
            self.domain.currentText().strip(),
            self.phone.text().strip(),
            self.email.text().strip(),
            self.contact.text().strip(),
            self.notes.toPlainText().strip(),
            self.logo.value(),
        )


class SupplierDetailDialog(QDialog):
    def __init__(self, parent: QWidget, repo: SupplierRepository, supplier_id: int, project_dir: Path):
        super().__init__(parent)
        self.repo = repo
        self.supplier_id = supplier_id
        self.project_dir = project_dir
        self.setWindowTitle("Fiche prestataire")
        self.resize(600, 460)

        self._edit_mode = False

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit()
        self.domain = QComboBox()
        self.domain.setEditable(True)
        self.domain.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.logo = LogoPicker(project_dir)

        self.contact = QLineEdit()
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.notes = QTextEdit()

        form.addRow("Société / Nom", self.name)
        form.addRow("Domaine", self.domain)
        form.addRow("Logo", self.logo)
        form.addRow("Contact", self.contact)
        form.addRow("Téléphone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("Notes", self.notes)

        root.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)

        self.btn_edit = QPushButton("Modifier")
        self.btn_save = QPushButton("Enregistrer")
        self.btn_delete = QPushButton("Supprimer")
        self.btn_close = QPushButton("Fermer")

        self.btn_edit.setProperty("class", "GhostButton")
        self.btn_close.setProperty("class", "GhostButton")
        self.btn_delete.setProperty("class", "GhostButton")
        self.btn_save.setProperty("class", "PrimaryButton")

        for b in (self.btn_edit, self.btn_save, self.btn_delete, self.btn_close):
            b.setMinimumWidth(120)

        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_save)
        btns.addStretch(1)
        btns.addWidget(self.btn_delete)
        btns.addWidget(self.btn_close)
        root.addLayout(btns)

        self.btn_close.clicked.connect(self.reject)
        self.btn_edit.clicked.connect(self._toggle_edit)
        self.btn_save.clicked.connect(self._save)
        self.btn_delete.clicked.connect(self._delete)

        self._reload_domains()
        self._load()
        self._set_editable(False)

    def _reload_domains(self):
        self.domain.blockSignals(True)
        self.domain.clear()
        self.domain.addItems(self.repo.list_domains())
        self.domain.blockSignals(False)

    def _load(self):
        s = self.repo.get_supplier(self.supplier_id)
        if not s:
            QMessageBox.warning(self, "Erreur", "Prestataire introuvable.")
            self.reject()
            return

        self.name.setText(s.name)
        i = self.domain.findText(s.domain)
        if i >= 0:
            self.domain.setCurrentIndex(i)
        else:
            self.domain.setCurrentText(s.domain)

        self.logo.set_value(s.logo_path)
        self.contact.setText(s.contact)
        self.phone.setText(s.phone)
        self.email.setText(s.email)
        self.notes.setPlainText(s.notes)

    def _set_editable(self, editable: bool):
        for w in (self.name, self.contact, self.phone, self.email):
            w.setReadOnly(not editable)
        self.domain.setEnabled(editable)
        self.notes.setReadOnly(not editable)
        self.logo.setEnabled(editable)
        self.btn_save.setEnabled(editable)

    def _toggle_edit(self):
        self._edit_mode = not self._edit_mode
        self._set_editable(self._edit_mode)
        self.btn_edit.setText("Annuler" if self._edit_mode else "Modifier")
        if not self._edit_mode:
            self._reload_domains()
            self._load()

    def _save(self):
        try:
            self.repo.update_supplier(
                supplier_id=self.supplier_id,
                name=self.name.text(),
                domain=self.domain.currentText(),
                phone=self.phone.text(),
                email=self.email.text(),
                contact=self.contact.text(),
                notes=self.notes.toPlainText(),
                logo_path=self.logo.value(),
            )
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return

        self._edit_mode = False
        self._set_editable(False)
        self.btn_edit.setText("Modifier")
        QMessageBox.information(self, "OK", "Modifications enregistrées.")
        self._reload_domains()

    def _delete(self):
        res = QMessageBox.question(self, "Suppression", "Supprimer ce prestataire ?")
        if res != QMessageBox.Yes:
            return
        self.repo.delete_supplier(self.supplier_id)
        self.accept()


class Chip(QLabel):
    def __init__(self, text: str, variant: str = ""):
        super().__init__(text)
        self.setObjectName("Chip")
        self.setProperty("variant", variant)


class SupplierRow(QFrame):
    deleted = Signal(int)

    def __init__(self, s: Supplier, style_resolver: DomainStyleResolver, project_dir: Path):
        super().__init__()
        self.s = s
        self._resolver = style_resolver
        self._project_dir = project_dir

        self.setObjectName("TaskRow")
        self.setProperty("hover", False)
        self.setFrameShape(QFrame.NoFrame)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        color, icon_name = self._resolver.style_for(s.domain)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        logo = SupplierLogo()
        logo.set_logo(self._project_dir, s.logo_path, _initials(s.name))

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

        right = QHBoxLayout()
        right.setSpacing(8)

        if s.domain:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 11pt;")
            right.addWidget(dot)

            chip = Chip(s.domain, "domain")
            chip.setStyleSheet(f"border: 1px solid {color}; color: #E6EAF2; background: transparent;")
            right.addWidget(chip)

        domain_icon = QLabel()
        domain_icon.setFixedWidth(28)
        domain_icon.setAlignment(Qt.AlignCenter)
        domain_icon.setToolTip("Domaine")
        domain_icon.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))
        right.addWidget(domain_icon)

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
        root.addWidget(logo, 0, Qt.AlignVCenter)
        root.addLayout(left, 1)
        root.addLayout(right, 0)

        if s.notes:
            self.setToolTip(s.notes)

    def _copy_email(self):
        if self.s.email:
            QApplication.clipboard().setText(self.s.email)

    def _copy_phone(self):
        if self.s.phone:
            QApplication.clipboard().setText(self.s.phone)

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
        self.style_resolver = DomainStyleResolver(repo)
        self.project_dir = Path(self.repo.db_path).parent

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Prestataires")
        title.setObjectName("PageTitle")

        self.btn_manage_domains = QPushButton("⚙️ Domaines")
        self.btn_manage_domains.setProperty("class", "GhostButton")

        self.btn_add = QPushButton("+ Ajouter")
        self.btn_add.setProperty("class", "PrimaryButton")

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.btn_manage_domains)
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
        self.list.itemDoubleClicked.connect(self._open_details)

        root.addLayout(header)
        root.addLayout(filters)
        root.addWidget(self.list, 1)

        self.btn_add.clicked.connect(self.add_supplier)
        self.btn_refresh.clicked.connect(self.reload)
        self.domain.currentIndexChanged.connect(self.reload)
        self.search.textChanged.connect(self.reload)
        self.btn_manage_domains.clicked.connect(self.manage_domains)

        self.reload()

    def manage_domains(self):
        dlg = DomainManagerDialog(self, self.repo)
        dlg.exec()
        self.reload()

    def _reload_domains(self):
        current = self.domain.currentText()
        self.domain.blockSignals(True)
        self.domain.clear()
        self.domain.addItem("Tous")
        for d in self.repo.list_domains():
            self.domain.addItem(d)
        i = self.domain.findText(current)
        if i >= 0:
            self.domain.setCurrentIndex(i)
        self.domain.blockSignals(False)

        self.style_resolver.reload()

    def reload(self):
        self._reload_domains()
        self.list.clear()

        suppliers = self.repo.list_suppliers(
            search=self.search.text(),
            domain=self.domain.currentText(),
        )

        for s in suppliers:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, s.id)
            row = SupplierRow(s, self.style_resolver, self.project_dir)
            row.deleted.connect(self._delete_supplier)

            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)

    def add_supplier(self):
        domains = self.repo.list_domains()
        dlg = AddSupplierDialog(domains, self.project_dir, self)

        if dlg.exec() != QDialog.Accepted:
            return

        name, domain, phone, email, contact, notes, logo_path = dlg.values()
        if not name:
            return

        self.repo.add_supplier(
            name=name,
            domain=domain,
            phone=phone,
            email=email,
            contact=contact,
            notes=notes,
            logo_path=logo_path,
        )
        self.reload()

    def _delete_supplier(self, supplier_id: int):
        res = QMessageBox.question(self, "Suppression", "Supprimer ce prestataire ?")
        if res != QMessageBox.Yes:
            return
        self.repo.delete_supplier(supplier_id)
        self.reload()

    def _open_details(self, item: QListWidgetItem):
        supplier_id = int(item.data(Qt.UserRole))
        dlg = SupplierDetailDialog(self, self.repo, supplier_id, self.project_dir)
        dlg.exec()
        self.reload()
