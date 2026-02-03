import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QLineEdit, QFrame, QGridLayout
)

from core.db import TaskRepository, SupplierRepository
from ui.pages.tasks import TasksPage
from ui.pages.suppliers import SuppliersPage


QSS = """
QWidget {
    background-color: #0B0F17;
    color: #E6EAF2;
    font-family: "Segoe UI", "Inter", "Arial";
    font-size: 12pt;
}
QLineEdit {
    background-color: #0F1625;
    border: 1px solid #1B263A;
    border-radius: 10px;
    padding: 10px 12px;
}
QLineEdit:focus { border: 1px solid #2D6CDF; }

QComboBox {
    background-color: #0F1625;
    border: 1px solid #1B263A;
    border-radius: 10px;
    padding: 8px 10px;
}
QComboBox:hover { border: 1px solid #22324D; }
QComboBox:focus { border: 1px solid #2D6CDF; }

/* ---- List container ---- */
QListWidget {
    background-color: transparent;
    border: none;
    padding: 0px;
    outline: 0;
}
QListWidget::item {
    background: transparent;
    border: none;
    padding: 0px;
}
QListWidget::item:selected {
    background: transparent;
    border: none;
}
QListWidget::item:focus {
    outline: 0;
}

/* ---- TaskRow ---- */
#TaskRow {
    background-color: #0F1625;
    border: 1px solid #1B263A;
    border-radius: 14px;
}
#TaskRow[hover="true"] {
    border: 1px solid #22324D;
    background-color: #0E172A;
}

/* ---- Task text ---- */
#TaskTitle { font-weight: 800; font-size: 12pt; }
#TaskMeta  { color: #AAB3C5; font-size: 10pt; }

/* ---- Chips ---- */
#Chip {
    background-color: #0B1322;
    border: 1px solid #1B263A;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 10pt;
    color: #AAB3C5;
}
#Chip[variant="high"] { border: 1px solid #2D6CDF; color: #E6EAF2; }
#Chip[variant="low"]  { color: #AAB3C5; }

/* ---- Round checkbox button ---- */
#CheckBtn {
    background-color: transparent;
    border: 1px solid #1B263A;
    border-radius: 12px;
    min-width: 24px;
    min-height: 24px;
    font-weight: 900;
}
#CheckBtn[checked="true"] {
    background-color: #2D6CDF;
    border: 1px solid #2D6CDF;
}
#DelBtn {
    background-color: transparent;
    border: 1px solid #1B263A;
    border-radius: 10px;
    padding: 6px 10px;
}
#DelBtn:hover { background-color: #0B1322; }

/* Sidebar */
#Sidebar {
    background-color: #0A0E15;
    border-right: 1px solid #121A2A;
}
#Brand { font-size: 14pt; font-weight: 800; }
.NavButton {
    text-align: left;
    padding: 10px 12px;
    border-radius: 10px;
    background-color: transparent;
    border: 1px solid transparent;
}
.NavButton:hover {
    background-color: #0F1625;
    border: 1px solid #1B263A;
}
.NavButton[active="true"] {
    background-color: #0F1A33;
    border: 1px solid #2D6CDF;
}

#PageTitle { font-size: 18pt; font-weight: 900; }
.Muted { color: #AAB3C5; }

.Card {
    background-color: #0F1625;
    border: 1px solid #1B263A;
    border-radius: 16px;
}
.CardTitle { font-size: 13pt; font-weight: 800; }

.PrimaryButton {
    background-color: #2D6CDF;
    border: 1px solid #2D6CDF;
    padding: 8px 12px;
    border-radius: 10px;
    font-weight: 700;
}
.PrimaryButton:hover {
    background-color: #2A60C9;
    border: 1px solid #2A60C9;
}
.GhostButton {
    background-color: transparent;
    border: 1px solid #1B263A;
    padding: 8px 12px;
    border-radius: 10px;
    font-weight: 700;
}
.GhostButton:hover { background-color: #0B1322; }

/* ---- Chips / Tags ---- */
.Chip {
    background-color: #0B1322;
    border: 1px solid #1B263A;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 10pt;
    color: #AAB3C5;
}
.ChipHigh { border: 1px solid #2D6CDF; color: #E6EAF2; }
.ChipLow  { color: #AAB3C5; }

/* ---- Task row ---- */
.TaskRow {
    background-color: #0F1625;
    border: 1px solid #1B263A;
    border-radius: 14px;
}
.TaskRow:hover {
    border: 1px solid #22324D;
    background-color: #0E172A;
}
.TaskTitle { font-weight: 800; font-size: 12pt; }
.TaskMeta { color: #AAB3C5; font-size: 10pt; }

#TaskRow[active="true"] {
    border: 1px solid #2D6CDF;
    background-color: #0F1A33;
}

#DelBtn:hover {
    background-color: #0B1322;
    border: 1px solid #2D6CDF;
}
#CardTitle { font-size: 13pt; font-weight: 800; }

/* ---- FIX: remove dark "textbox" behind text inside rows ---- */
#TaskRow QLabel {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}

#TaskTitle, #TaskMeta {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}


"""


class Card(QFrame):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setProperty("class", "Card")
        self.setObjectName("Card")
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "CardTitle")
        title_lbl.setObjectName("CardTitle")

        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setProperty("class", "Muted")
        subtitle_lbl.setWordWrap(True)

        layout.addWidget(title_lbl)
        layout.addWidget(subtitle_lbl)
        layout.addStretch(1)


class StatCard(QFrame):
    def __init__(self, title: str, value: str):
        super().__init__()
        self.setProperty("class", "Card")
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        t = QLabel(title)
        t.setProperty("class", "Muted")

        v = QLabel(value)
        v.setObjectName("PageTitle")  # grosse typo
        v.setStyleSheet("font-size: 16pt; font-weight: 900;")  # petite custom

        layout.addWidget(t)
        layout.addWidget(v)


class TaskPreviewRow(QFrame):
    def __init__(self, text_left: str, text_right: str = ""):
        super().__init__()
        self.setObjectName("TaskRow")
        self.setProperty("hover", False)
        self.setFrameShape(QFrame.NoFrame)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        left = QLabel(text_left)
        left.setObjectName("TaskTitle")
        left.setStyleSheet("font-size: 11pt;")  # un poil plus compact
        left.setWordWrap(True)

        right = QLabel(text_right)
        right.setProperty("class", "Muted")
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        root.addWidget(left, 1)
        root.addWidget(right, 0)

    def enterEvent(self, event):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)


class StatCard(QFrame):
    def __init__(self, title: str, value: str):
        super().__init__()
        self.setProperty("class", "Card")
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        t = QLabel(title)
        t.setProperty("class", "Muted")

        v = QLabel(value)
        v.setObjectName("PageTitle")  # grosse typo
        v.setStyleSheet("font-size: 16pt; font-weight: 900;")  # petite custom

        layout.addWidget(t)
        layout.addWidget(v)


class TaskPreviewRow(QFrame):
    def __init__(self, text_left: str, text_right: str = ""):
        super().__init__()
        self.setObjectName("TaskRow")
        self.setProperty("hover", False)
        self.setFrameShape(QFrame.NoFrame)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        left = QLabel(text_left)
        left.setObjectName("TaskTitle")
        left.setStyleSheet("font-size: 11pt;")  # un poil plus compact
        left.setWordWrap(True)

        right = QLabel(text_right)
        right.setProperty("class", "Muted")
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        root.addWidget(left, 1)
        root.addWidget(right, 0)

    def enterEvent(self, event):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)


class HomePage(QWidget):
    def __init__(self, repo: TaskRepository, on_add_task):
        super().__init__()
        self.repo = repo
        self.on_add_task = on_add_task

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # --- Row: KPI cards + action
        top = QHBoxLayout()
        top.setSpacing(12)

        self.card_open = StatCard("À faire", "0")
        self.card_done = StatCard("Fait", "0")
        self.card_total = StatCard("Total", "0")

        top.addWidget(self.card_open, 1)
        top.addWidget(self.card_done, 1)
        top.addWidget(self.card_total, 1)

        actions = QVBoxLayout()
        actions.setSpacing(10)
        btn_add = QPushButton("+ Nouvelle tâche")
        btn_add.setProperty("class", "PrimaryButton")
        btn_add.clicked.connect(self.on_add_task)

        hint = QLabel("Raccourci : ajoute une tâche\nsans quitter l’accueil.")
        hint.setProperty("class", "Muted")
        hint.setWordWrap(True)

        actions.addWidget(btn_add)
        actions.addWidget(hint)
        actions.addStretch(1)

        top.addLayout(actions, 1)

        # --- Card: Top tasks
        self.top_card = QFrame()
        self.top_card.setProperty("class", "Card")
        self.top_card.setObjectName("Card")
        card_layout = QVBoxLayout(self.top_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel("Top 5 à faire")
        title.setObjectName("CardTitle")
        subtitle = QLabel("Trié par échéance puis priorité.")
        subtitle.setProperty("class", "Muted")

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(subtitle)

        self.top_list = QVBoxLayout()
        self.top_list.setSpacing(10)

        card_layout.addLayout(header)
        card_layout.addLayout(self.top_list)

        root.addLayout(top)
        root.addWidget(self.top_card, 1)

        self.refresh()

    def _set_stat(self, card: QFrame, value: int):
        # 2e widget dans la card = value label
        lbl = card.layout().itemAt(1).widget()
        lbl.setText(str(value))

    def refresh(self):
        open_count, done_count = self.repo.count_tasks()
        total = open_count + done_count
        self._set_stat(self.card_open, open_count)
        self._set_stat(self.card_done, done_count)
        self._set_stat(self.card_total, total)

        # Clear top list
        while self.top_list.count():
            item = self.top_list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        top = self.repo.top_open_tasks(5)
        if not top:
            self.top_list.addWidget(QLabel("Rien à faire 🎉"))
            return

        for t in top:
            left = t.title
            if t.category:
                left = f"[{t.category}] {left}"

            right = ""
            if t.due_date:
                right = t.due_date
            else:
                right = "sans échéance"

            row = TaskPreviewRow(left, right)
            self.top_list.addWidget(row)

        self.top_list.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard IT — Dark Pro")
        self.resize(1180, 720)

        app = QApplication.instance()
        if app:
            app.setStyleSheet(QSS)

        # DB (fichier dans le dossier du projet)
        db_path = Path(__file__).parent / "dashboard.db"
        self.repo = TaskRepository(db_path)
        self.sup_repo = SupplierRepository(db_path)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(16, 16, 16, 16)
        sb.setSpacing(10)

        brand = QLabel("Dashboard IT")
        brand.setObjectName("Brand")
        hint = QLabel("Console perso • v1")
        hint.setProperty("class", "Muted")

        sb.addWidget(brand)
        sb.addWidget(hint)
        sb.addSpacing(14)

        self.btn_home = QPushButton("🏠  Accueil")
        self.btn_home.setProperty("class", "NavButton")
        self.btn_home.setProperty("active", True)

        self.btn_tasks = QPushButton("✅  Tâches")
        self.btn_tasks.setProperty("class", "NavButton")
        self.btn_tasks.setProperty("active", False)

        self.btn_tools = QPushButton("🧰  Outils")
        self.btn_tools.setProperty("class", "NavButton")
        self.btn_tools.setProperty("active", False)

        self.btn_suppliers = QPushButton("📇  Prestataires")
        self.btn_suppliers.setProperty("class", "NavButton")
        self.btn_suppliers.setProperty("active", False)

        for b in (self.btn_home, self.btn_tasks, self.btn_suppliers, self.btn_tools):
            b.setCursor(Qt.PointingHandCursor)
            sb.addWidget(b)


        sb.addStretch(1)

        # Main area
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(22, 18, 22, 18)
        main_layout.setSpacing(14)

        top = QHBoxLayout()
        self.page_title = QLabel("Accueil")
        self.page_title.setObjectName("PageTitle")

        search = QLineEdit()
        search.setPlaceholderText("Recherche globale (V2)")

        top.addWidget(self.page_title)
        top.addStretch(1)
        top.addWidget(search, 0)

        self.pages = QStackedWidget()
        self.page_suppliers = SuppliersPage(self.sup_repo)
        self.page_home = HomePage(self.repo, on_add_task=self._add_task_from_home)
        self.page_tasks = TasksPage(self.repo)
        placeholder_tools = Card("Outils", "Page à venir : ping/dns/ports + boutons scripts.")

        container_tools = QWidget()
        lo = QVBoxLayout(container_tools)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(placeholder_tools)

        self.pages.addWidget(self.page_home)      # 0
        self.pages.addWidget(self.page_tasks)     # 1
        self.pages.addWidget(self.page_suppliers) # 2
        self.pages.addWidget(container_tools)     # 3

        main_layout.addLayout(top)
        main_layout.addWidget(self.pages, 1)

        root.addWidget(sidebar)
        root.addWidget(main, 1)

        self.btn_home.clicked.connect(lambda: self.go(0, "Accueil", self.btn_home))
        self.btn_tasks.clicked.connect(lambda: self.go(1, "Tâches", self.btn_tasks))
        self.btn_suppliers.clicked.connect(lambda: self.go(2, "Prestataires", self.btn_suppliers))
        self.btn_tools.clicked.connect(lambda: self.go(3, "Outils", self.btn_tools))
        

        self._nav_buttons = [self.btn_home, self.btn_tasks, self.btn_suppliers, self.btn_tools]

    def go(self, index: int, title: str, active_btn: QPushButton):
        self.pages.setCurrentIndex(index)
        self.page_title.setText(title)
        for b in self._nav_buttons:
            b.setProperty("active", b is active_btn)
            b.style().unpolish(b)
            b.style().polish(b)

        if index == 0:  # accueil
            self.page_home.refresh()

    def _add_task_from_home(self):
        # On affiche la page tâches, et on déclenche l’ajout via la page
        self.go(1, "Tâches", self.btn_tasks)
        # ouvre la fenêtre "Ajouter"
        self.page_tasks.add_task()
        # refresh de l'accueil (au cas où)
        self.page_home.refresh()
        


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dashboard IT")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

