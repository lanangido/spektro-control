"""
main_window.py - GUI utama Spektro-Control.

Layout (gaya software analytical instrument profesional):
- Menu bar atas: File, Instrument, Tools + language toggle + theme toggle
- Panel kontrol KIRI (~240px, scrollable): cards dengan judul dan spacing
- Area grafik KANAN: pyqtgraph plot + angka besar wavelength & hasil ukur
- Export bar: Export Grafik / Export CSV
- Tabel data / log komunikasi BAWAH

Fitur:
- Light / Dark Mode (token-based, persistent via QSettings)
- Bahasa Indonesia / English (centralized strings, persistent via QSettings)
- Export CSV (save tabel data ke file)
- Export Grafik (save plot pyqtgraph ke PNG)
"""

import csv
import traceback
import logging
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QStatusBar, QSplitter, QFrame, QProgressBar,
    QHeaderView, QScrollArea, QFileDialog, QMessageBox, QStyle,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, Slot, QRunnable, QObject, QThreadPool, QSettings, QUrl, QTimer
from PySide6.QtGui import QFont, QAction, QDesktopServices, QTextDocument, QPainter
from PySide6.QtPrintSupport import QPrinterInfo, QPrinter
import pyqtgraph as pg

from protocol.uv_protocol import UVProtocol
from ui.strings import STRINGS


# ══════════════════════════════════════════════════════════════════════════════
# Worker untuk operasi serial di background thread
# ══════════════════════════════════════════════════════════════════════════════

class WorkerSignals(QObject):
    """Sinyal dari worker thread ke main thread."""
    finished = Signal(object)  # result data
    error = Signal(str)        # error message


class Worker(QRunnable):
    """
    Worker generik: jalankan fungsi apapun di thread pool.
    Hasil dikirim lewat signal finished/error.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())


# ══════════════════════════════════════════════════════════════════════════════
# Design Tokens — Light / Dark
# ══════════════════════════════════════════════════════════════════════════════

LIGHT_THEME = {
    'name': 'light',
    'bg_app': '#F5F6F8',
    'bg_panel': '#FFFFFF',
    'bg_panel_header': '#EEF1F5',
    'border': '#D8DCE3',
    'text_primary': '#1C1E21',
    'text_secondary': '#6B7280',
    'accent': '#1565C0',
    'accent_hover': '#0D47A1',
    'accent_text': '#FFFFFF',
    'success': '#2E7D32',
    'danger': '#C62828',
    'graph_bg': '#FFFFFF',
    'graph_line': '#1565C0',
    'graph_grid': '#E3E6EA',
    'graph_fg': '#6B7280',
    'log_bg': '#F8F9FA',
    'log_text': '#2E3134',
    'table_alt': '#F5F6F8',
    'scrollbar_handle': '#C4C7CC',
    'scrollbar_handle_hover': '#A0A4AB',
    'input_bg': '#FFFFFF',
    'toolbar_bg': '#EBEDF0',
    'toolbar_border': '#D8DCE3',
    'statusbar_bg': '#EBEDF0',
    'tab_selected_border': '#1565C0',
    'warning': '#F9A825',
}

DARK_THEME = {
    'name': 'dark',
    'bg_app': '#1A1C1E',
    'bg_panel': '#242628',
    'bg_panel_header': '#2E3134',
    'border': '#3A3D42',
    'text_primary': '#E8E9EB',
    'text_secondary': '#9AA0A6',
    'accent': '#4C9AFF',
    'accent_hover': '#6BA9FF',
    'accent_text': '#1A1C1E',
    'success': '#4CAF50',
    'danger': '#EF5350',
    'graph_bg': '#242628',
    'graph_line': '#4C9AFF',
    'graph_grid': '#34373B',
    'graph_fg': '#9AA0A6',
    'log_bg': '#1A1C1E',
    'log_text': '#A8E6A0',
    'table_alt': '#2A2C2E',
    'scrollbar_handle': '#4A4D52',
    'scrollbar_handle_hover': '#5A5D62',
    'input_bg': '#2E3134',
    'toolbar_bg': '#242628',
    'toolbar_border': '#3A3D42',
    'statusbar_bg': '#1E2022',
    'tab_selected_border': '#4C9AFF',
    'warning': '#FFD54F',
}


# ══════════════════════════════════════════════════════════════════════════════
# Mode pengukuran: index combo → kode command v
# ══════════════════════════════════════════════════════════════════════════════

MODE_LABELS = ["Abs", "T%", "Energy"]
MODE_Y_LABELS = ["Absorbance", "Transmittance (%)", "Energy"]



from PySide6.QtWidgets import QToolButton, QSizePolicy
from PySide6.QtCore import QPropertyAnimation, QParallelAnimationGroup, QAbstractAnimation

class CollapsibleSection(QWidget):
    def __init__(self, settings, section_id: str, title: str = "", parent=None):
        super().__init__(parent)
        self._settings = settings
        self._section_id = f"panel_{section_id}_expanded"
        
        self.toggle_button = QToolButton(self)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; text-align: left; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.content_area = QWidget()
        
        # Load state
        is_expanded = self._settings.value(self._section_id, True, type=bool)
        if is_expanded:
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.toggle_button.setChecked(True)
            self.content_area.setVisible(True)
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.toggle_button.setChecked(False)
            self.content_area.setVisible(False)

        main_vbox = QVBoxLayout(self)
        main_vbox.setSpacing(0)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.addWidget(self.toggle_button)
        main_vbox.addWidget(self.content_area)

    def on_pressed(self):
        checked = not self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content_area.setVisible(checked)
        self._settings.setValue(self._section_id, checked)

    def setContentLayout(self, layout):
        self.content_area.setLayout(layout)

    def setTitle(self, title):
        self.toggle_button.setText(title)


# ══════════════════════════════════════════════════════════════════════════════
# Dialog Pembuka — Cek Status PC Control
# ══════════════════════════════════════════════════════════════════════════════

class StartupDialog(QDialog):
    """
    Dialog modal yang muncul saat pertama kali aplikasi dibuka.
    Membantu operator lab awam mengecek apakah alat sudah di mode PC Control
    sebelum masuk ke aplikasi utama.

    State:
        'question'   - Pertanyaan awal Ya/Tidak
        'instruction'- Instruksi pasang kabel (setelah klik Tidak)
        'connecting' - Sedang mencoba auto-connect
    """

    # Signal: minta parent untuk connect ke port tertentu
    request_connect = Signal(str)  # port name
    # Signal: dialog ditutup (skipped)
    skipped = Signal()

    def __init__(self, parent=None, theme=None, lang="id"):
        super().__init__(parent)
        self._theme = theme or LIGHT_THEME
        self._lang = lang
        self._state = "question"

        # Frameless untuk tampil modern, tapi tetap ada tombol X
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setFixedSize(440, 370)

        self._build_ui()
        self._apply_dialog_theme()
        self._apply_dialog_language()

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        """Buat semua widget dialog."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container dengan border radius
        self._container = QFrame(self)
        self._container.setObjectName("startupDialogContainer")
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(28, 20, 28, 20)
        container_layout.setSpacing(0)

        # ── Header: title + close button ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("startupTitle")
        self._lbl_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header.addWidget(self._lbl_title)
        header.addStretch(1)

        self._btn_close = QPushButton("✕")
        self._btn_close.setObjectName("startupCloseBtn")
        self._btn_close.setFixedSize(28, 28)
        self._btn_close.setCursor(Qt.PointingHandCursor)
        self._btn_close.clicked.connect(self._on_skip)
        header.addWidget(self._btn_close)

        container_layout.addLayout(header)
        container_layout.addSpacing(12)

        # ── Icon ──
        self._lbl_icon = QLabel("🔬")
        self._lbl_icon.setAlignment(Qt.AlignCenter)
        self._lbl_icon.setFont(QFont("Segoe UI Emoji", 36))
        self._lbl_icon.setObjectName("startupIcon")
        container_layout.addWidget(self._lbl_icon)
        container_layout.addSpacing(12)

        # ── Question text / Instruction text (stacked) ──
        self._lbl_question = QLabel()
        self._lbl_question.setObjectName("startupQuestion")
        self._lbl_question.setAlignment(Qt.AlignCenter)
        self._lbl_question.setWordWrap(True)
        self._lbl_question.setFont(QFont("Segoe UI", 12))
        container_layout.addWidget(self._lbl_question)

        self._lbl_instruction = QLabel()
        self._lbl_instruction.setObjectName("startupInstruction")
        self._lbl_instruction.setAlignment(Qt.AlignCenter)
        self._lbl_instruction.setWordWrap(True)
        self._lbl_instruction.setFont(QFont("Segoe UI", 10))
        self._lbl_instruction.setVisible(False)
        container_layout.addWidget(self._lbl_instruction)

        # ── Connecting label ──
        self._lbl_connecting = QLabel()
        self._lbl_connecting.setObjectName("startupConnecting")
        self._lbl_connecting.setAlignment(Qt.AlignCenter)
        self._lbl_connecting.setFont(QFont("Segoe UI", 11))
        self._lbl_connecting.setVisible(False)
        container_layout.addWidget(self._lbl_connecting)

        # ── Progress bar (connecting state) ──
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        container_layout.addWidget(self._progress)

        container_layout.addSpacing(18)

        # ── Buttons: Ya / Tidak (question state) ──
        self._btn_row_question = QWidget()
        btn_q_layout = QHBoxLayout(self._btn_row_question)
        btn_q_layout.setContentsMargins(0, 0, 0, 0)
        btn_q_layout.setSpacing(12)

        self._btn_yes = QPushButton()
        self._btn_yes.setObjectName("btnPrimary")
        self._btn_yes.setFixedHeight(38)
        self._btn_yes.setCursor(Qt.PointingHandCursor)
        self._btn_yes.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._btn_yes.clicked.connect(self._on_yes)
        btn_q_layout.addWidget(self._btn_yes, 1)

        self._btn_no = QPushButton()
        self._btn_no.setObjectName("btnSecondary")
        self._btn_no.setFixedHeight(38)
        self._btn_no.setCursor(Qt.PointingHandCursor)
        self._btn_no.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._btn_no.clicked.connect(self._on_no)
        btn_q_layout.addWidget(self._btn_no, 1)

        container_layout.addWidget(self._btn_row_question)

        # ── Button: Sudah, Coba Lagi (instruction state) ──
        self._btn_retry = QPushButton()
        self._btn_retry.setObjectName("btnPrimary")
        self._btn_retry.setFixedHeight(38)
        self._btn_retry.setCursor(Qt.PointingHandCursor)
        self._btn_retry.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._btn_retry.clicked.connect(self._on_yes)  # same as Yes
        self._btn_retry.setVisible(False)
        container_layout.addWidget(self._btn_retry)

        container_layout.addSpacing(10)

        # ── Skip link ──
        self._btn_skip = QPushButton()
        self._btn_skip.setObjectName("startupSkipBtn")
        self._btn_skip.setCursor(Qt.PointingHandCursor)
        self._btn_skip.setFont(QFont("Segoe UI", 9))
        self._btn_skip.clicked.connect(self._on_skip)
        container_layout.addWidget(self._btn_skip, alignment=Qt.AlignCenter)

        container_layout.addStretch(1)
        main_layout.addWidget(self._container)

    # ── State transitions ─────────────────────────────────────────────────

    def _set_state(self, state: str):
        """Switch tampilan dialog sesuai state."""
        self._state = state

        is_question = state == "question"
        is_instruction = state == "instruction"
        is_connecting = state == "connecting"

        self._lbl_icon.setVisible(not is_connecting)
        self._lbl_question.setVisible(is_question)
        self._lbl_instruction.setVisible(is_instruction)
        self._lbl_connecting.setVisible(is_connecting)
        self._progress.setVisible(is_connecting)
        self._btn_row_question.setVisible(is_question)
        self._btn_retry.setVisible(is_instruction)
        self._btn_skip.setVisible(not is_connecting)

    def _on_yes(self):
        """User klik Ya atau Sudah Coba Lagi — coba auto-connect."""
        self._set_state("connecting")
        # Emit signal ke MainWindow untuk lakukan connect
        self.request_connect.emit("")

    def _on_no(self):
        """User klik Tidak — tampilkan instruksi."""
        self._set_state("instruction")

    def _on_skip(self):
        """User klik Lewati / X — tutup dialog, masuk ke app utama."""
        self.skipped.emit()
        self.accept()

    def on_connect_success(self):
        """Dipanggil oleh MainWindow saat connect berhasil."""
        self.accept()

    def on_connect_failed(self):
        """Dipanggil oleh MainWindow saat connect gagal. Kembali ke pertanyaan."""
        self._set_state("question")

    # ── Theming ────────────────────────────────────────────────────────────

    def update_theme(self, theme):
        """Update tema dialog (dipanggil saat user toggle tema)."""
        self._theme = theme
        self._apply_dialog_theme()

    def _apply_dialog_theme(self):
        """Terapkan stylesheet sesuai tema aktif."""
        t = self._theme
        self.setStyleSheet(f"""
            QFrame#startupDialogContainer {{
                background-color: {t['bg_panel']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QLabel#startupTitle {{
                color: {t['text_primary']};
                background: transparent;
                font-size: 14px;
            }}
            QLabel#startupIcon {{
                background: transparent;
                padding: 4px;
            }}
            QLabel#startupQuestion {{
                color: {t['text_primary']};
                background: transparent;
                font-size: 14px;
                padding: 6px 0;
            }}
            QLabel#startupInstruction {{
                color: {t['text_secondary']};
                background-color: {t['bg_panel_header']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                font-size: 12px;
                padding: 14px;
            }}
            QLabel#startupConnecting {{
                color: {t['accent']};
                background: transparent;
                font-size: 13px;
                padding: 8px;
            }}
            QPushButton#btnPrimary {{
                background-color: {t['accent']};
                color: {t['accent_text']};
                border: none;
                border-radius: 6px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton#btnPrimary:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton#btnPrimary:disabled {{
                background-color: {t['bg_panel_header']};
                color: {t['text_secondary']};
            }}
            QPushButton#btnSecondary {{
                background-color: transparent;
                color: {t['accent']};
                border: 1px solid {t['accent']};
                border-radius: 6px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton#btnSecondary:hover {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}
            QPushButton#startupCloseBtn {{
                background: transparent;
                color: {t['text_secondary']};
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton#startupCloseBtn:hover {{
                background-color: {t['danger']};
                color: white;
            }}
            QPushButton#startupSkipBtn {{
                background: transparent;
                color: {t['text_secondary']};
                border: none;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton#startupSkipBtn:hover {{
                color: {t['accent']};
                text-decoration: underline;
            }}
            QProgressBar {{
                background-color: {t['bg_panel_header']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 2px;
            }}
        """)

    # ── Language ───────────────────────────────────────────────────────────

    def update_language(self, lang: str):
        """Update bahasa dialog (dipanggil saat user toggle bahasa)."""
        self._lang = lang
        self._apply_dialog_language()

    def _tr(self, key):
        """Helper i18n lokal."""
        return STRINGS.get(self._lang, STRINGS['id']).get(key, key)

    def _apply_dialog_language(self):
        """Set semua teks dialog sesuai bahasa aktif."""
        self._lbl_title.setText(self._tr("dlg_startup_title"))
        self._lbl_question.setText(self._tr("dlg_startup_question"))
        self._btn_yes.setText(self._tr("dlg_startup_btn_yes"))
        self._btn_no.setText(self._tr("dlg_startup_btn_no"))
        self._lbl_instruction.setText(self._tr("dlg_startup_instruction"))
        self._btn_retry.setText(self._tr("dlg_startup_btn_retry"))
        self._btn_skip.setText(self._tr("dlg_startup_btn_skip"))
        self._lbl_connecting.setText(self._tr("dlg_startup_connecting"))


class MainWindow(QMainWindow):
    """Jendela utama Spektro-Control."""

    # Signal untuk marshal log dari worker thread ke GUI thread
    _log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(1100, 700)
        
        self.logger = logging.getLogger("spektro.ui")

        # -- Preferences --
        self._settings = QSettings("SpektroControl", "SpektroControl")
        saved_theme = self._settings.value("theme", "light")
        self._current_theme = DARK_THEME if saved_theme == "dark" else LIGHT_THEME
        self._current_lang = self._settings.value("lang", "id")

        # pyqtgraph global config
        pg.setConfigOptions(antialias=True)

        self._active_workers = set()
        self._serial_pool = QThreadPool()

        # -- Central widget --
        central = QWidget()
        self.setCentralWidget(central)

        # -- Menu bar (moved to end of init) --

        # -- Main layout --
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(0)

        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # ═══════════════════════════════════════════════════════════════════════
        # PANEL KIRI — Kontrol (scrollable)
        # ═══════════════════════════════════════════════════════════════════════
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # left_scroll.setMaximumWidth(270) removed
        left_scroll.setMinimumWidth(320)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setObjectName("leftScroll")

        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 6, 4, 6)
        left_layout.setSpacing(10)

        # ── 1. Status Koneksi (Auto) ─────────────────────────────────────────
        status_container = QWidget()
        status_container.setObjectName("statusContainer")
        status_container.setStyleSheet("background: transparent; margin-bottom: 8px;")
        status_h = QHBoxLayout(status_container)
        status_h.setContentsMargins(0, 0, 0, 0)
        status_h.setSpacing(6)

        self.lbl_conn_dot = QLabel("●")
        self.lbl_conn_dot.setObjectName("connDot")
        self.lbl_conn_dot.setFixedWidth(14)
        status_h.addWidget(self.lbl_conn_dot)

        self.lbl_conn_status = QLabel()
        self.lbl_conn_status.setWordWrap(True)
        self.lbl_conn_status.setObjectName("lblConnStatus")
        status_h.addWidget(self.lbl_conn_status)
        status_h.addStretch(1)

        left_layout.addWidget(status_container)

        # Setup Advanced Connection Dialog (Hidden)
        self.dlg_adv_conn = QDialog(self)
        self.dlg_adv_conn.setWindowTitle(self._tr("title_adv_conn"))
        self.dlg_adv_conn.setMinimumWidth(300)
        dlg_layout = QGridLayout(self.dlg_adv_conn)
        
        self.lbl_com_port = QLabel()
        dlg_layout.addWidget(self.lbl_com_port, 0, 0)
        
        self.combo_port = QComboBox()
        self.combo_port.setMinimumWidth(100)
        # Not Editable anymore to prevent typing invalid ports
        dlg_layout.addWidget(self.combo_port, 0, 1)
        
        self.btn_connect = QPushButton()
        self.btn_connect.setObjectName("btnPrimary")
        dlg_layout.addWidget(self.btn_connect, 1, 0, 1, 2)

        # ── 8. Status Printer ────────────────────────────────────────────────
        self.grp_printer = CollapsibleSection(self._settings, "printer")
        printer_layout = QGridLayout(); self.grp_printer.setContentLayout(printer_layout)
        printer_layout.setSpacing(6)

        self.lbl_printer_name = QLabel()
        self.lbl_printer_name.setWordWrap(True)
        printer_layout.addWidget(self.lbl_printer_name, 0, 0, 1, 2)

        self.combo_printer = QComboBox()
        printer_layout.addWidget(self.combo_printer, 1, 0)

        self.btn_refresh_printer = QPushButton()
        self.btn_refresh_printer.setObjectName("btnSecondary")
        self.btn_refresh_printer.setToolTip(self._tr("tt_refresh_printer"))
        self.btn_refresh_printer.setText("\u21BB")
        self.btn_refresh_printer.setFixedWidth(32)
        self.btn_refresh_printer.clicked.connect(self._refresh_printers)
        printer_layout.addWidget(self.btn_refresh_printer, 1, 1)

        p_status_container = QWidget()
        p_status_container.setObjectName("statusContainer")
        p_status_h = QHBoxLayout(p_status_container)
        p_status_h.setContentsMargins(2, 0, 0, 0)
        p_status_h.setSpacing(4)

        self.lbl_printer_dot = QLabel("\u25cf")
        self.lbl_printer_dot.setObjectName("connDot")
        self.lbl_printer_dot.setFixedWidth(14)
        p_status_h.addWidget(self.lbl_printer_dot)

        self.lbl_printer_status = QLabel()
        self.lbl_printer_status.setWordWrap(True)
        self.lbl_printer_status.setObjectName("lblConnStatus")
        p_status_h.addWidget(self.lbl_printer_status)
        p_status_h.addStretch(1)

        printer_layout.addWidget(p_status_container, 2, 0, 1, 2)
        left_layout.addWidget(self.grp_printer)

        # ── 2. Mode Pengukuran ───────────────────────────────────────────────
        self.grp_mode = CollapsibleSection(self._settings, "mode")
        mode_layout = QHBoxLayout(); self.grp_mode.setContentLayout(mode_layout)
        mode_layout.setSpacing(6)

        self.lbl_mode = QLabel()
        self.lbl_mode.setWordWrap(True)
        mode_layout.addWidget(self.lbl_mode)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Abs", "T%", "Energy"])
        mode_layout.addWidget(self.combo_mode, 1)

        left_layout.addWidget(self.grp_mode)

        # ── 3. GOTO Wavelength ───────────────────────────────────────────────
        self.grp_wl = CollapsibleSection(self._settings, "wl")
        wl_layout = QGridLayout(); self.grp_wl.setContentLayout(wl_layout)
        wl_layout.setSpacing(6)

        self.lbl_wavelength = QLabel()
        self.lbl_wavelength.setWordWrap(True)
        wl_layout.addWidget(self.lbl_wavelength, 0, 0)

        self.spin_wavelength = QDoubleSpinBox()
        self.spin_wavelength.setRange(190.0, 1100.0)
        self.spin_wavelength.setDecimals(1)
        self.spin_wavelength.setSingleStep(0.5)
        self.spin_wavelength.setValue(500.0)
        self.spin_wavelength.setSuffix(" nm")
        wl_layout.addWidget(self.spin_wavelength, 0, 1)

        self.btn_goto_wl = QPushButton()
        self.btn_goto_wl.setObjectName("btnPrimary")
        wl_layout.addWidget(self.btn_goto_wl, 1, 0, 1, 2)

        left_layout.addWidget(self.grp_wl)

        # ── 4. Kalibrasi ────────────────────────────────────────────────────
        self.grp_calib = CollapsibleSection(self._settings, "calib")
        calib_layout = QGridLayout()
        self.grp_calib.setContentLayout(calib_layout)
        calib_layout.setSpacing(6)

        self.btn_auto_zero = QPushButton()
        self.btn_auto_zero.setObjectName("btnPrimary")
        calib_layout.addWidget(self.btn_auto_zero, 0, 0, 1, 2)

        self.lbl_bl_start = QLabel()
        self.lbl_bl_start.setWordWrap(True)
        calib_layout.addWidget(self.lbl_bl_start, 1, 0)

        self.spin_bl_start = QDoubleSpinBox()
        self.spin_bl_start.setRange(190.0, 1100.0)
        self.spin_bl_start.setDecimals(1)
        self.spin_bl_start.setValue(190.0)
        self.spin_bl_start.setSuffix(" nm")
        calib_layout.addWidget(self.spin_bl_start, 1, 1)

        self.lbl_bl_end = QLabel()
        self.lbl_bl_end.setWordWrap(True)
        calib_layout.addWidget(self.lbl_bl_end, 2, 0)

        self.spin_bl_end = QDoubleSpinBox()
        self.spin_bl_end.setRange(190.0, 1100.0)
        self.spin_bl_end.setDecimals(1)
        self.spin_bl_end.setValue(1100.0)
        self.spin_bl_end.setSuffix(" nm")
        calib_layout.addWidget(self.spin_bl_end, 2, 1)

        self.btn_baseline = QPushButton()
        self.btn_baseline.setObjectName("btnPrimary")
        calib_layout.addWidget(self.btn_baseline, 3, 0, 1, 2)

        left_layout.addWidget(self.grp_calib)

        # ── 5. Baca Data ────────────────────────────────────────────────────
        self.grp_read = CollapsibleSection(self._settings, "read")
        read_layout = QHBoxLayout(self.grp_read)

        self.btn_read_data = QPushButton()
        self.btn_read_data.setObjectName("btnPrimary")
        read_layout.addWidget(self.btn_read_data)

        left_layout.addWidget(self.grp_read)

        # ── 6. Wavelength Scan ───────────────────────────────────────────────
        self.grp_wscan = CollapsibleSection(self._settings, "wscan")
        wscan_layout = QGridLayout(); self.grp_wscan.setContentLayout(wscan_layout)
        wscan_layout.setSpacing(6)

        self.lbl_scan_start = QLabel()
        self.lbl_scan_start.setWordWrap(True)
        wscan_layout.addWidget(self.lbl_scan_start, 0, 0)

        self.spin_scan_start = QDoubleSpinBox()
        self.spin_scan_start.setRange(190.0, 1100.0)
        self.spin_scan_start.setDecimals(1)
        self.spin_scan_start.setValue(190.0)
        self.spin_scan_start.setSuffix(" nm")
        wscan_layout.addWidget(self.spin_scan_start, 0, 1)

        self.lbl_scan_end = QLabel()
        self.lbl_scan_end.setWordWrap(True)
        wscan_layout.addWidget(self.lbl_scan_end, 1, 0)

        self.spin_scan_end = QDoubleSpinBox()
        self.spin_scan_end.setRange(190.0, 1100.0)
        self.spin_scan_end.setDecimals(1)
        self.spin_scan_end.setValue(800.0)
        self.spin_scan_end.setSuffix(" nm")
        wscan_layout.addWidget(self.spin_scan_end, 1, 1)

        self.lbl_speed = QLabel()
        self.lbl_speed.setWordWrap(True)
        wscan_layout.addWidget(self.lbl_speed, 2, 0)

        self.combo_scan_speed = QComboBox()
        self.combo_scan_speed.addItems([
            "1 - Very Fast", "2 - Fast", "3 - Medium",
            "4 - Slow", "5 - Very Slow"
        ])
        self.combo_scan_speed.setCurrentIndex(2)
        wscan_layout.addWidget(self.combo_scan_speed, 2, 1)

        self.btn_start_wscan = QPushButton()
        self.btn_start_wscan.setObjectName("btnPrimary")
        wscan_layout.addWidget(self.btn_start_wscan, 3, 0, 1, 2)

        self.progress_wscan = QProgressBar()
        self.progress_wscan.setRange(0, 0)
        self.progress_wscan.setVisible(False)
        self.progress_wscan.setTextVisible(True)
        wscan_layout.addWidget(self.progress_wscan, 4, 0, 1, 2)

        left_layout.addWidget(self.grp_wscan)

        # ── 7. Time Scan ────────────────────────────────────────────────────
        self.grp_tscan = CollapsibleSection(self._settings, "tscan")
        tscan_layout = QGridLayout(); self.grp_tscan.setContentLayout(tscan_layout)
        tscan_layout.setSpacing(6)

        self.lbl_duration = QLabel()
        self.lbl_duration.setWordWrap(True)
        tscan_layout.addWidget(self.lbl_duration, 0, 0)

        self.spin_tscan_duration = QSpinBox()
        self.spin_tscan_duration.setRange(1, 6500)
        self.spin_tscan_duration.setValue(60)
        tscan_layout.addWidget(self.spin_tscan_duration, 0, 1)

        self.lbl_unit = QLabel()
        self.lbl_unit.setWordWrap(True)
        tscan_layout.addWidget(self.lbl_unit, 1, 0)

        self.combo_tscan_unit = QComboBox()
        tscan_layout.addWidget(self.combo_tscan_unit, 1, 1)

        self.btn_start_tscan = QPushButton()
        self.btn_start_tscan.setObjectName("btnPrimary")
        tscan_layout.addWidget(self.btn_start_tscan, 2, 0, 1, 2)

        self.progress_tscan = QProgressBar()
        self.progress_tscan.setRange(0, 0)
        self.progress_tscan.setVisible(False)
        self.progress_tscan.setTextVisible(True)
        tscan_layout.addWidget(self.progress_tscan, 3, 0, 1, 2)

        left_layout.addWidget(self.grp_tscan)


        # Spacer
        left_layout.addStretch(1)

        left_scroll.setWidget(left_panel)
        main_splitter.addWidget(left_scroll)

        # ═══════════════════════════════════════════════════════════════════════
        # PANEL KANAN — Grafik + Data
        # ═══════════════════════════════════════════════════════════════════════
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # ── Header: angka besar wavelength & hasil ukur ──────────────────────
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 12, 20, 12)

        self.lbl_current_wl = QLabel("--- nm")
        self.lbl_current_wl.setObjectName("lblBigValue")
        self.lbl_current_wl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header_layout.addWidget(self.lbl_current_wl)

        header_layout.addStretch(1)

        self.lbl_current_value = QLabel("---")
        self.lbl_current_value.setObjectName("lblBigValue")
        self.lbl_current_value.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header_layout.addWidget(self.lbl_current_value)

        self.lbl_current_unit = QLabel("Abs")
        self.lbl_current_unit.setObjectName("lblUnit")
        self.lbl_current_unit.setFont(QFont("Segoe UI", 14))
        header_layout.addWidget(self.lbl_current_unit)

        right_layout.addWidget(header_frame)

        # ── Grafik pyqtgraph ─────────────────────────────────────────────────
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Absorbance')
        self.plot_widget.setLabel('bottom', 'Wavelength', units='nm')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMinimumHeight(300)

        self.plot_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=self._current_theme['graph_line'], width=2)
        )

        right_layout.addWidget(self.plot_widget, stretch=3)

        # ── Export bar (antara grafik dan tab) ────────────────────────────────
        export_bar = QWidget()
        export_bar.setObjectName("exportBar")
        export_h = QHBoxLayout(export_bar)
        export_h.setContentsMargins(0, 2, 0, 2)
        export_h.setSpacing(8)

        self.btn_export_graph = QPushButton()
        self.btn_export_graph.setObjectName("btnSecondary")
        export_h.addWidget(self.btn_export_graph)

        self.btn_export_csv = QPushButton()
        self.btn_export_csv.setObjectName("btnSecondary")
        export_h.addWidget(self.btn_export_csv)

        export_h.addStretch(1)

        right_layout.addWidget(export_bar)

        # ── Tab bawah: Tabel Data / Log Komunikasi ───────────────────────────
        self.tab_bottom = QTabWidget()
        self.tab_bottom.setMaximumHeight(220)

        self.table_data = QTableWidget()
        self.table_data.setColumnCount(2)
        self.table_data.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_data.setAlternatingRowColors(True)
        self.tab_bottom.addTab(self.table_data, "")

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 9))
        self.tab_bottom.addTab(self.txt_log, "")

        right_layout.addWidget(self.tab_bottom, stretch=1)

        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([320, 830])

        # ═══════════════════════════════════════════════════════════════════════
        # Status bar
        # ═══════════════════════════════════════════════════════════════════════
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # ═══════════════════════════════════════════════════════════════════════
        # Logic setup
        # ═══════════════════════════════════════════════════════════════════════
        self.protocol = UVProtocol()
        self.protocol.on_raw_data = self._on_raw_data

        self._serial_pool = QThreadPool()
        self._serial_pool.setMaxThreadCount(1)

        self._current_mode_index = 0
        self._scan_result = None

        self._log_signal.connect(self._append_log_text)
        self._startup_dialog = None  # Init sebelum _apply_theme yang cek atribut ini
        self._setup_menu_bar()
        self._setup_connections()
        self._set_controls_enabled(False)

        # Apply theme + language (sets all text and colors)
        self._apply_theme()
        self._apply_language()

        # Auto-detect COM ports & Printers
        self._refresh_ports()
        self._refresh_printers()

        # -- Dialog Pembuka --
        # Tampilkan setelah window sudah di-render
        QTimer.singleShot(300, self._show_startup_dialog)

    # ══════════════════════════════════════════════════════════════════════════
    # i18n helper
    # ══════════════════════════════════════════════════════════════════════════

    def _tr(self, key, **kwargs):
        """Ambil string terjemahan. Pakai kwargs untuk format placeholder."""
        text = STRINGS.get(self._current_lang, STRINGS['id']).get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    # ══════════════════════════════════════════════════════════════════════════
    # Dialog Pembuka
    # ══════════════════════════════════════════════════════════════════════════

    def _show_startup_dialog(self):
        """Tampilkan dialog pembuka untuk cek status PC Control."""
        self._startup_dialog = StartupDialog(
            parent=self,
            theme=self._current_theme,
            lang=self._current_lang,
        )
        self._startup_dialog.request_connect.connect(self._on_startup_connect_request)

        def on_dialog_closed():
            # Setelah dialog ditutup (baik skip maupun connect berhasil),
            # mulai auto-connect timer
            if not self.protocol.is_connected:
                self.timer_auto_connect.start(3000)
            self._startup_dialog = None

        self._startup_dialog.finished.connect(on_dialog_closed)
        self._startup_dialog.show()

    def _on_startup_connect_request(self, _port_hint: str):
        """
        Dipanggil saat user klik Ya / Sudah Coba Lagi di startup dialog.
        Tentukan port, set ke combo_port, lalu trigger _on_connect_clicked.
        """
        # 1. Coba port terakhir yang berhasil
        last_port = self._settings.value("last_port", "")

        # 2. Refresh daftar port
        self._refresh_ports()
        ports = UVProtocol.list_ports()

        # 3. Tentukan port yang akan dicoba
        target_port = ""
        if last_port and last_port in ports:
            target_port = last_port
        elif ports:
            target_port = ports[0]

        if not target_port:
            # Tidak ada port tersedia — langsung gagal
            self._show_alert(
                self._tr("title_error"),
                self._tr("msg_error_no_port"),
            )
            if self._startup_dialog and self._startup_dialog.isVisible():
                self._startup_dialog.on_connect_failed()
            return

        # 4. Set port di combo dan trigger connect
        self.combo_port.setCurrentText(target_port)
        self._on_connect_clicked()

    # ══════════════════════════════════════════════════════════════════════════
    # Menu bar
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_menu_bar(self):
        """Setup menu bar: File, Instrument, Tools + language & theme toggle."""
        mbar = self.menuBar()

        # -- File --
        self.menu_file = mbar.addMenu("")
        self.act_export_csv_menu = QAction("", self)
        self.act_export_csv_menu.setEnabled(False)
        self.menu_file.addAction(self.act_export_csv_menu)
        self.menu_file.addSeparator()
        self.act_exit = QAction("", self)
        self.act_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.act_exit)

        # -- Instrument --
        self.menu_instrument = mbar.addMenu("")
        self.act_conn_info = QAction("", self)
        self.act_conn_info.setEnabled(False)
        self.menu_instrument.addAction(self.act_conn_info)
        self.act_adv_conn = QAction("", self)
        self.act_adv_conn.triggered.connect(self.dlg_adv_conn.exec)
        self.menu_instrument.addAction(self.act_adv_conn)

        # -- Tools --
        self.menu_tools = mbar.addMenu("")
        self.act_settings = QAction("", self)
        self.act_settings.setEnabled(False)
        self.menu_tools.addAction(self.act_settings)
        
        self.menu_tools.addSeparator()
        self.act_open_log = QAction("", self)
        self.act_open_log.triggered.connect(self._open_log_folder)
        self.menu_tools.addAction(self.act_open_log)

        # -- Corner: language toggle + theme toggle --
        self.corner = QWidget()
        corner_layout = QHBoxLayout(self.corner)
        corner_layout.setContentsMargins(0, 0, 4, 0)
        corner_layout.setSpacing(4)

        self.btn_lang_toggle = QPushButton()
        self.btn_lang_toggle.setObjectName("btnThemeToggle")
        self.btn_lang_toggle.setFixedHeight(24)
        self.btn_lang_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_lang_toggle.clicked.connect(self._toggle_language)
        corner_layout.addWidget(self.btn_lang_toggle)

        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setObjectName("btnThemeToggle")
        self.btn_theme_toggle.setFixedHeight(24)
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        corner_layout.addWidget(self.btn_theme_toggle)

        mbar.setCornerWidget(self.corner)

    # ══════════════════════════════════════════════════════════════════════════
    # Theme system
    # ══════════════════════════════════════════════════════════════════════════

    def _toggle_theme(self):
        """Toggle antara light dan dark, simpan preferensi."""
        if self._current_theme['name'] == 'light':
            self._current_theme = DARK_THEME
        else:
            self._current_theme = LIGHT_THEME
        self._settings.setValue("theme", self._current_theme['name'])
        self._apply_theme()

    def _apply_theme(self):
        """Terapkan tema saat ini ke seluruh UI."""
        t = self._current_theme

        # Update toggle button text
        if t['name'] == 'light':
            self.btn_theme_toggle.setText(self._tr("theme_to_dark"))
        else:
            self.btn_theme_toggle.setText(self._tr("theme_to_light"))

        self.setStyleSheet(self._build_stylesheet(t))

        # pyqtgraph colors
        self.plot_widget.setBackground(t['graph_bg'])
        for axis_name in ('left', 'bottom'):
            ax = self.plot_widget.getAxis(axis_name)
            ax.setPen(pg.mkPen(color=t['graph_fg']))
            ax.setTextPen(pg.mkPen(color=t['graph_fg']))
        self.plot_curve.setPen(pg.mkPen(color=t['graph_line'], width=2))

        self._refresh_conn_dot()

        # Forward theme ke startup dialog jika masih terbuka
        if self._startup_dialog and self._startup_dialog.isVisible():
            self._startup_dialog.update_theme(t)

    def _refresh_conn_dot(self):
        """Update warna dot koneksi sesuai tema dan status."""
        t = self._current_theme
        if self.protocol.is_connected:
            self.lbl_conn_dot.setStyleSheet(
                f"color: {t['success']}; font-size: 14px; background: transparent;"
            )
        else:
            self.lbl_conn_dot.setStyleSheet(
                f"color: {t['danger']}; font-size: 14px; background: transparent;"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # Language system
    # ══════════════════════════════════════════════════════════════════════════

    def _toggle_language(self):
        """Toggle bahasa ID ↔ EN, simpan preferensi."""
        self._current_lang = "en" if self._current_lang == "id" else "id"
        self._settings.setValue("lang", self._current_lang)
        self._apply_language()
        # Theme toggle text juga tergantung bahasa
        self._apply_theme()

    def _apply_language(self):
        """Set semua teks UI dari dict bahasa aktif."""
        # Window title
        self.setWindowTitle(self._tr("window_title"))

        # -- Menu bar --
        self.menu_file.setTitle(self._tr("menu_file"))
        self.menu_instrument.setTitle(self._tr("menu_instrument"))
        self.menu_tools.setTitle(self._tr("menu_tools"))
        self.act_export_csv_menu.setText(self._tr("menu_export_csv"))
        self.act_exit.setText(self._tr("menu_exit"))
        self.act_conn_info.setText(self._tr("menu_conn_info"))
        self.act_adv_conn.setText(self._tr("action_adv_conn"))
        self.act_settings.setText(self._tr("menu_settings"))
        self.act_open_log.setText(self._tr("menu_open_log_folder"))

        # -- Language toggle --
        if self._current_lang == "id":
            self.btn_lang_toggle.setText(self._tr("lang_to_en"))
        else:
            self.btn_lang_toggle.setText(self._tr("lang_to_id"))

        # -- GroupBox titles --
        # self.grp_conn.setTitle(self._tr("grp_connection"))
        self.grp_mode.setTitle(self._tr("grp_mode"))
        self.grp_wl.setTitle(self._tr("grp_goto_wl"))
        self.grp_calib.setTitle(self._tr("grp_calibration"))
        self.grp_read.setTitle(self._tr("grp_read_data"))
        self.grp_wscan.setTitle(self._tr("grp_wscan"))
        self.grp_tscan.setTitle(self._tr("grp_tscan"))
        self.grp_printer.setTitle(self._tr("grp_printer"))

        # -- Labels --
        self.lbl_com_port.setText(self._tr("lbl_com_port"))
        self.lbl_mode.setText(self._tr("lbl_mode"))
        self.lbl_wavelength.setText(self._tr("lbl_wavelength"))
        self.lbl_bl_start.setText(self._tr("lbl_bl_start"))
        self.lbl_bl_end.setText(self._tr("lbl_bl_end"))
        self.lbl_scan_start.setText(self._tr("lbl_scan_start"))
        self.lbl_scan_end.setText(self._tr("lbl_scan_end"))
        self.lbl_speed.setText(self._tr("lbl_speed"))
        self.lbl_duration.setText(self._tr("lbl_duration"))
        self.lbl_unit.setText(self._tr("lbl_unit"))
        self.lbl_printer_name.setText(self._tr("lbl_printer_name"))
        # self.btn_refresh_printer.setText(self._tr("btn_refresh_printer"))

        # -- Buttons --
        # Connect button: depends on connection state
        if self.protocol.is_connected:
            self.btn_connect.setText(self._tr("btn_disconnect"))
            self.lbl_conn_status.setText(self._tr("status_connected"))
        else:
            self.btn_connect.setText(self._tr("btn_connect"))
            self.lbl_conn_status.setText(self._tr("status_disconnected"))

        self.btn_goto_wl.setText(self._tr("btn_goto_wl"))
        self.btn_auto_zero.setText(self._tr("btn_auto_zero"))
        self.btn_baseline.setText(self._tr("btn_baseline"))
        self.btn_read_data.setText(self._tr("btn_read_data"))
        self.btn_start_wscan.setText(self._tr("btn_start_wscan"))
        self.btn_start_tscan.setText(self._tr("btn_start_tscan"))
        self.btn_export_csv.setText(self._tr("btn_export_csv"))
        # self.btn_refresh_printer.setText(self._tr("btn_refresh"))
        self.btn_export_graph.setText(self._tr("btn_export_graph"))

        # -- Combo: time scan unit (save/restore index) --
        idx = self.combo_tscan_unit.currentIndex()
        if idx < 0:
            idx = 0
        self.combo_tscan_unit.clear()
        self.combo_tscan_unit.addItems([
            self._tr("unit_seconds"),
            self._tr("unit_minutes"),
        ])
        self.combo_tscan_unit.setCurrentIndex(idx)

        # -- Progress bar formats --
        self.progress_wscan.setFormat(self._tr("progress_scanning"))
        self.progress_tscan.setFormat(self._tr("progress_measuring"))

        # -- Tab titles --
        self.tab_bottom.setTabText(0, self._tr("tab_data"))
        self.tab_bottom.setTabText(1, self._tr("tab_log"))

        # -- Table headers --
        self.table_data.setHorizontalHeaderLabels([
            self._tr("header_wavelength"),
            self._tr("header_value"),
        ])

        # -- Log placeholder --
        self.txt_log.setPlaceholderText(self._tr("log_placeholder"))

        # -- Status bar --
        self.status_bar.showMessage(self._tr("msg_ready"))

        # Forward language ke startup dialog jika masih terbuka
        if self._startup_dialog and self._startup_dialog.isVisible():
            self._startup_dialog.update_language(self._current_lang)

    # ══════════════════════════════════════════════════════════════════════════
    # Signal / Slot wiring
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_connections(self):
        """Hubungkan semua tombol ke slot handler."""
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.combo_mode.currentIndexChanged.connect(self._on_set_mode)
        self.btn_goto_wl.clicked.connect(self._on_goto_wl)
        self.btn_auto_zero.clicked.connect(self._on_auto_zero)
        self.btn_baseline.clicked.connect(self._on_baseline)
        self.btn_read_data.clicked.connect(self._on_read_data)
        self.btn_start_wscan.clicked.connect(self._on_start_wscan)
        self.btn_start_tscan.clicked.connect(self._on_start_tscan)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_export_graph.clicked.connect(self._export_graph)

        # -- Auto Connect --
        self._is_auto_connecting = False
        self.timer_auto_connect = QTimer(self)
        self.timer_auto_connect.timeout.connect(self._auto_connect_tick)
        # Timer TIDAK di-start di sini — akan di-start setelah startup dialog ditutup

    def _auto_connect_tick(self):
        if self.protocol.is_connected or self._is_auto_connecting or self.dlg_adv_conn.isVisible():
            return
        # Jangan auto-connect saat startup dialog masih terbuka
        if self._startup_dialog and self._startup_dialog.isVisible():
            return
        
        ports = UVProtocol.list_ports()
        if not ports:
            self.lbl_conn_status.setText(self._tr("status_searching_no_ports"))
            self.lbl_conn_dot.setStyleSheet(f"color: {self._current_theme['warning']}; font-size: 14px; background: transparent;")
            return
            
        self.lbl_conn_status.setText(self._tr("status_searching"))
        self.lbl_conn_dot.setStyleSheet(f"color: {self._current_theme['warning']}; font-size: 14px; background: transparent;")
        self._is_auto_connecting = True
        
        def auto_connect_worker():
            for p in ports:
                try:
                    self.protocol.connect(p, timeout=1.0)
                    if self.protocol.test_connection():
                        return p
                    self.protocol.disconnect()
                except Exception:
                    self.protocol.disconnect()
            return None
            
        def on_success(port_found):
            self._is_auto_connecting = False
            if port_found:
                self.combo_port.clear()
                self.combo_port.addItem(port_found)
                self.combo_port.setCurrentText(port_found)
                self._update_connection_status(True)
                self.status_bar.showMessage(self._tr("msg_connected", port=port_found))
                self._log(self._tr("msg_connect_ok", port=port_found))
            else:
                self.lbl_conn_status.setText(self._tr("status_searching_failed"))
                
        def on_error(err):
            self._is_auto_connecting = False
            self.lbl_conn_status.setText(self._tr("status_searching_failed"))
            
        self._run_in_thread(auto_connect_worker, on_success, on_error)

    # ══════════════════════════════════════════════════════════════════════════
    # Thread helper
    # ══════════════════════════════════════════════════════════════════════════

    def _run_in_thread(self, fn, on_success=None, on_error=None):
        """Jalankan fn di thread pool. Hubungkan callback jika ada."""
        worker = Worker(fn)
        self._active_workers.add(worker)
        
        def _cleanup(*args, **kwargs):
            self._active_workers.discard(worker)
            
        worker.signals.finished.connect(_cleanup)
        worker.signals.error.connect(_cleanup)

        if on_success:
            worker.signals.finished.connect(on_success)
        worker.signals.error.connect(on_error or self._default_error_handler)
        self._serial_pool.start(worker)

    
    def _show_alert(self, title, message):
        def _do_show():
            QMessageBox.warning(self, title, message)
        QTimer.singleShot(0, self, _do_show)

    def _default_error_handler(self, error_msg):
        """Handler error default: tampilkan di status bar dan log."""
        short = error_msg.strip().split('\n')[-1]
        self.status_bar.showMessage(f"Error: {short}")
        self._log(f"ERROR: {short}")
        self.logger.error(f"Worker Error: {error_msg}")
        self._set_controls_enabled(True)
        self.progress_wscan.setVisible(False)
        self.progress_tscan.setVisible(False)
        self._show_alert(self._tr("title_error"), short)

    # ══════════════════════════════════════════════════════════════════════════
    # Koneksi (Tahap 3)
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_ports(self):
        """Refresh daftar COM port di dropdown."""
        current = self.combo_port.currentText()
        self.combo_port.clear()
        ports = UVProtocol.list_ports()
        self.combo_port.addItems(ports)
        if current and current in ports:
            self.combo_port.setCurrentText(current)
        display = ports if ports else self._tr("log_no_ports")
        self._log(self._tr("log_ports_found", ports=display))

    def _on_connect_clicked(self):
        """Toggle connect / disconnect."""
        if self.protocol.is_connected:
            self.protocol.disconnect()
            self._update_connection_status(False)
            self.status_bar.showMessage(self._tr("msg_disconnected"))
            self._log(self._tr("msg_disconnected"))
            return

        port = self.combo_port.currentText().strip()
        if not port:
            self.status_bar.showMessage(self._tr("msg_error_no_port"))
            return

        self.btn_connect.setEnabled(False)
        self.status_bar.showMessage(self._tr("msg_connecting", port=port))
        self._log(self._tr("msg_connecting", port=port))

        def connect_workflow():
            self.protocol.connect(port)
            ok = self.protocol.test_connection()
            if not ok:
                self.protocol.disconnect()
                raise RuntimeError("NO_RESPONSE")
            return True

        def on_success(_result):
            self._update_connection_status(True)
            self.status_bar.showMessage(self._tr("msg_connected", port=port))
            self._log(self._tr("msg_connect_ok", port=port))
            # Simpan port terakhir yang berhasil connect
            self._settings.setValue("last_port", port)
            # Notify startup dialog jika masih terbuka
            if self._startup_dialog and self._startup_dialog.isVisible():
                self._startup_dialog.on_connect_success()

        def on_error(err):
            self._update_connection_status(False)
            self.btn_connect.setEnabled(True)
            if "FileNotFoundError" in err or "could not open port" in err:
                msg = self._tr("msg_err_conn_fail", port=port)
            elif "NO_RESPONSE" in err:
                msg = self._tr("msg_err_no_response")
            else:
                msg = err.strip().split('\n')[-1]
            self.status_bar.showMessage(f"Error: {msg}")
            self._log(self._tr("msg_connect_error", err=msg))
            self.logger.error(f"Connection Error: {err}")
            self._show_alert(self._tr("title_error"), msg)
            # Notify startup dialog jika masih terbuka
            if self._startup_dialog and self._startup_dialog.isVisible():
                self._startup_dialog.on_connect_failed()

        self._run_in_thread(connect_workflow, on_success, on_error)

    def _update_connection_status(self, connected: bool):
        """Update UI berdasarkan status koneksi."""
        t = self._current_theme
        if connected:
            self.btn_connect.setText(self._tr("btn_disconnect"))
            self.btn_connect.setObjectName("btnSecondary")
            self.lbl_conn_status.setText(self._tr("status_connected"))
            self.lbl_conn_dot.setStyleSheet(
                f"color: {t['success']}; font-size: 14px; background: transparent;"
            )
        else:
            self.btn_connect.setText(self._tr("btn_connect"))
            self.btn_connect.setObjectName("btnPrimary")
            self.lbl_conn_status.setText(self._tr("status_disconnected"))
            self.lbl_conn_dot.setStyleSheet(
                f"color: {t['danger']}; font-size: 14px; background: transparent;"
            )

        # Force style refresh setelah objectName berubah
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.btn_connect.update()

        self.btn_connect.setEnabled(True)
        self._set_controls_enabled(connected)

    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable semua kontrol kecuali koneksi."""
        for widget in [
            self.btn_goto_wl,
            self.btn_auto_zero, self.btn_baseline,
            self.btn_read_data, self.btn_start_wscan,
            self.btn_start_tscan, self.combo_mode,
            self.spin_wavelength, self.spin_bl_start, self.spin_bl_end,
            self.spin_scan_start, self.spin_scan_end, self.combo_scan_speed,
            self.spin_tscan_duration, self.combo_tscan_unit,
        ]:
            widget.setEnabled(enabled)

    # ══════════════════════════════════════════════════════════════════════════
    # GOTO WL — Set Wavelength (Tahap 3)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_goto_wl(self):
        """Kirim command w untuk pindah wavelength."""


        if not self.protocol.is_connected:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_not_connected"))
            return
        wl = self.spin_wavelength.value()
        wl_param = int(wl * 10)
        cmd = f"w{wl_param}"

        self._set_controls_enabled(False)
        self.status_bar.showMessage(self._tr("msg_goto_wl_progress", wl=f"{wl:.1f}"))
        self._log(f"GOTO WL: sending '{cmd}'")

        def workflow():
            ok = self.protocol.send_command(cmd)
            if not ok:
                raise RuntimeError(f"GOTO WL gagal: command '{cmd}' tidak di-ACK")
            return wl

        def on_success(result_wl):
            self.lbl_current_wl.setText(f"{result_wl:.1f} nm")
            self.status_bar.showMessage(
                self._tr("msg_goto_wl_ok", wl=f"{result_wl:.1f}")
            )
            self._log(f"GOTO WL OK: {result_wl:.1f} nm")
            self._set_controls_enabled(True)

        self._run_in_thread(workflow, on_success)

    # ══════════════════════════════════════════════════════════════════════════
    # Mode Pengukuran (Tahap 4) — auto-apply via combo change
    # ══════════════════════════════════════════════════════════════════════════

    def _on_set_mode(self, _idx=None):
        """Kirim command v untuk set mode Abs/T%/Energy."""
        if not self.protocol.is_connected:
            return

        idx = self.combo_mode.currentIndex()
        cmd = f"v{idx}"
        label = MODE_LABELS[idx]

        self._set_controls_enabled(False)
        self.status_bar.showMessage(self._tr("msg_set_mode_progress", label=label))
        self._log(f"Set mode: sending '{cmd}' ({label})")

        def workflow():
            ok = self.protocol.send_command(cmd)
            if not ok:
                raise RuntimeError(f"Set mode gagal: command '{cmd}' tidak di-ACK")
            return idx

        def on_success(result_idx):
            self._current_mode_index = result_idx
            mode_label = MODE_LABELS[result_idx]
            y_label = MODE_Y_LABELS[result_idx]
            self.lbl_current_unit.setText(mode_label)
            self.plot_widget.setLabel('left', y_label)
            self.status_bar.showMessage(
                self._tr("msg_set_mode_ok", label=mode_label)
            )
            self._log(f"Set mode OK: {mode_label}")
            self._set_controls_enabled(True)

        self._run_in_thread(workflow, on_success)

    # ══════════════════════════════════════════════════════════════════════════
    # Auto Zero (Tahap 4)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_auto_zero(self):
        """Kirim command x untuk auto zero."""


        if not self.protocol.is_connected:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_not_connected"))
            return
        self._set_controls_enabled(False)
        self.status_bar.showMessage(self._tr("msg_auto_zero_progress"))
        self._log("A-Z: sending 'x'")

        def workflow():
            ok = self.protocol.send_command("x")
            if not ok:
                raise RuntimeError("Auto Zero gagal: command 'x' tidak di-ACK")
            return True

        def on_success(_):
            self.status_bar.showMessage(self._tr("msg_auto_zero_ok"))
            self._log("A-Z OK")
            self._set_controls_enabled(True)

        self._run_in_thread(workflow, on_success)

    # ══════════════════════════════════════════════════════════════════════════
    # Baseline Correction (Tahap 4)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_baseline(self):
        """Kirim command c untuk baseline correction."""


        if not self.protocol.is_connected:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_not_connected"))
            return
        start = self.spin_bl_start.value()
        end = self.spin_bl_end.value()
        start_param = int(start * 10)
        end_param = int(end * 10)
        cmd = f"c{start_param},{end_param}"

        self._set_controls_enabled(False)
        self.status_bar.showMessage(
            self._tr("msg_baseline_progress", start=f"{start:.1f}", end=f"{end:.1f}")
        )
        self._log(f"B-L: sending '{cmd}'")

        def workflow():
            ok = self.protocol.send_command(cmd)
            if not ok:
                raise RuntimeError(f"Baseline gagal: command '{cmd}' tidak di-ACK")
            return True

        def on_success(_):
            self.status_bar.showMessage(
                self._tr("msg_baseline_ok", start=f"{start:.1f}", end=f"{end:.1f}")
            )
            self._log(f"B-L OK: {start:.1f}-{end:.1f} nm")
            self._set_controls_enabled(True)

        self._run_in_thread(workflow, on_success)

    # ══════════════════════════════════════════════════════════════════════════
    # Baca Data (Tahap 3)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_read_data(self):
        """Kirim command d untuk baca nilai saat ini."""


        if not self.protocol.is_connected:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_not_connected"))
            return
        self._set_controls_enabled(False)
        self.status_bar.showMessage(self._tr("msg_read_progress"))
        self._log("Read data: sending 'd'")

        def workflow():
            result = self.protocol.read_data("d")
            if result is None:
                raise RuntimeError("Baca data gagal: tidak ada respons dari alat")
            return result

        def on_success(raw_value):
            self._log(f"Read data OK: '{raw_value}'")
            try:
                numeric = float(raw_value.strip())
                self.lbl_current_value.setText(f"{numeric:.4f}")
            except ValueError:
                self.lbl_current_value.setText(raw_value.strip())
            self.status_bar.showMessage(
                self._tr("msg_read_value", val=raw_value.strip())
            )
            self._set_controls_enabled(True)

        self._run_in_thread(workflow, on_success)

    # ══════════════════════════════════════════════════════════════════════════
    # Wavelength Scan (Tahap 5)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_start_wscan(self):
        """
        Wavelength Scan — alur:
        1. Kirim a{start},{end},{speed} (Protocol A)
        2. Tunggu EOT (alat melakukan pengukuran)
        3. Tarik data via f0 (Protocol B')
        4. Render grafik penuh
        """


        if not self.protocol.is_connected:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_not_connected"))
            return
        start = self.spin_scan_start.value()
        end = self.spin_scan_end.value()
        speed = self.combo_scan_speed.currentIndex() + 1

        if start >= end:
            self.status_bar.showMessage(self._tr("msg_error_start_gt_end"))
            return

        start_param = int(start * 10)
        end_param = int(end * 10)
        cmd_scan = f"a{start_param},{end_param},{speed}"

        self._set_controls_enabled(False)
        self.progress_wscan.setVisible(True)
        self.progress_wscan.setFormat(self._tr("progress_scanning"))
        self.status_bar.showMessage(
            self._tr("msg_wscan_progress",
                     start=f"{start:.1f}", end=f"{end:.1f}", speed=speed)
        )
        self._log(f"W-Scan: sending '{cmd_scan}'")

        def workflow():
            ok = self.protocol.send_command(cmd_scan)
            if not ok:
                raise RuntimeError(f"Scan gagal: command '{cmd_scan}' tidak di-ACK")

            self._log_signal.emit(self._tr("msg_wscan_waiting"))
            eot = self.protocol.wait_for_eot(timeout=600)
            if not eot:
                raise RuntimeError("Scan timeout: alat tidak mengirim EOT")

            self._log_signal.emit(self._tr("msg_wscan_pulling"))
            data = self.protocol.read_bulk_data("f0")
            if data is None:
                raise RuntimeError("Gagal membaca data scan (Protocol B')")

            return data

        def on_success(data):
            self.progress_wscan.setVisible(False)
            self._log(f"W-Scan OK: {len(data)} data points")

            self._render_scan_result(
                data=data, scan_type='wavelength',
                x_start=start, x_end=end,
            )
            self.status_bar.showMessage(self._tr("msg_wscan_ok", n=len(data)))
            self._set_controls_enabled(True)

        def on_error(err):
            self.progress_wscan.setVisible(False)
            self._default_error_handler(err)

        self._run_in_thread(workflow, on_success, on_error)

    # ══════════════════════════════════════════════════════════════════════════
    # Time Scan (Tahap 6)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_start_tscan(self):
        """
        Time Scan — alur:
        1. Kirim b{durasi},{satuan} (Protocol A)  satuan: 0=detik, 1=menit
        2. Tunggu EOT (alat melakukan pengukuran)
        3. Tarik data via f0 (Protocol B')
        4. Render grafik penuh (nilai vs waktu)
        """


        if not self.protocol.is_connected:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_not_connected"))
            return
        duration = self.spin_tscan_duration.value()
        unit_idx = self.combo_tscan_unit.currentIndex()
        unit_label = self._tr("unit_seconds") if unit_idx == 0 \
            else self._tr("unit_minutes")
        cmd_scan = f"b{duration},{unit_idx}"

        timeout_seconds = duration * (60 if unit_idx == 1 else 1) + 60

        self._set_controls_enabled(False)
        self.progress_tscan.setVisible(True)
        self.progress_tscan.setFormat(self._tr("progress_measuring"))
        self.status_bar.showMessage(
            self._tr("msg_tscan_progress", duration=duration, unit=unit_label)
        )
        self._log(f"T-Scan: sending '{cmd_scan}' ({duration} {unit_label})")

        def workflow():
            ok = self.protocol.send_command(cmd_scan)
            if not ok:
                raise RuntimeError(f"Time scan gagal: command '{cmd_scan}' tidak di-ACK")

            self._log_signal.emit(
                self._tr("msg_tscan_waiting", duration=duration, unit=unit_label)
            )
            eot = self.protocol.wait_for_eot(timeout=timeout_seconds)
            if not eot:
                raise RuntimeError("Time scan timeout: alat tidak mengirim EOT")

            self._log_signal.emit(self._tr("msg_tscan_pulling"))
            data = self.protocol.read_bulk_data("f0")
            if data is None:
                raise RuntimeError("Gagal membaca data time scan (Protocol B')")

            return data

        total_seconds = duration * (60 if unit_idx == 1 else 1)

        def on_success(data):
            self.progress_tscan.setVisible(False)
            self._log(f"T-Scan OK: {len(data)} data points")

            self._render_scan_result(
                data=data, scan_type='time',
                x_start=0, x_end=total_seconds,
            )
            self.status_bar.showMessage(self._tr("msg_tscan_ok", n=len(data)))
            self._set_controls_enabled(True)

        def on_error(err):
            self.progress_tscan.setVisible(False)
            self._default_error_handler(err)

        self._run_in_thread(workflow, on_success, on_error)

    # ══════════════════════════════════════════════════════════════════════════
    # Render hasil scan ke grafik + tabel
    # ══════════════════════════════════════════════════════════════════════════

    def _render_scan_result(self, data, scan_type, x_start, x_end):
        """
        Parse data string, hitung sumbu X, plot grafik, isi tabel.

        Args:
            data: list of strings dari Protocol B'
            scan_type: 'wavelength' atau 'time'
            x_start: nilai awal sumbu X
            x_end: nilai akhir sumbu X
        """
        y_values = []
        for raw in data:
            try:
                y_values.append(float(raw.strip()))
            except ValueError:
                parts = raw.strip().split(',')
                try:
                    y_values.append(float(parts[-1]))
                except (ValueError, IndexError):
                    y_values.append(0.0)
                    self._log(f"WARNING: tidak bisa parse '{raw}', pakai 0.0")

        n = len(y_values)
        if n == 0:
            self._log("WARNING: tidak ada data untuk diplot")
            return

        if n > 1:
            step = (x_end - x_start) / (n - 1)
            x_values = [x_start + i * step for i in range(n)]
        else:
            x_values = [x_start]

        if scan_type == 'wavelength':
            x_label = self._tr("header_wavelength")
            x_unit = "nm"
        else:
            x_label = self._tr("header_time")
            x_unit = "s"

        y_label = MODE_LABELS[self._current_mode_index]

        self._scan_result = {
            'type': scan_type,
            'x_label': x_label,
            'y_label': y_label,
            'x': x_values,
            'y': y_values,
            'timestamp': datetime.now().isoformat(),
        }

        self.plot_curve.setData(x_values, y_values)
        self.plot_widget.setLabel('bottom', x_label.split(' (')[0], units=x_unit)
        self.plot_widget.setLabel('left', MODE_Y_LABELS[self._current_mode_index])

        self.table_data.setRowCount(n)
        self.table_data.setHorizontalHeaderLabels([x_label, y_label])
        for i in range(n):
            self.table_data.setItem(i, 0, QTableWidgetItem(f"{x_values[i]:.1f}"))
            self.table_data.setItem(i, 1, QTableWidgetItem(f"{y_values[i]:.4f}"))

        self.tab_bottom.setCurrentIndex(0)

    # ══════════════════════════════════════════════════════════════════════════
    # Export CSV
    # ══════════════════════════════════════════════════════════════════════════

    def _export_csv(self):
        """Export isi tabel Data ke file CSV."""
        rows = self.table_data.rowCount()
        if rows == 0:
            self.status_bar.showMessage(self._tr("msg_csv_no_data"))
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"hasil_ukur_{ts}.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("dlg_csv_title"),
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )
        if not filepath:
            return

        try:
            cols = self.table_data.columnCount()
            headers = []
            for c in range(cols):
                item = self.table_data.horizontalHeaderItem(c)
                headers.append(item.text() if item else f"Col{c}")

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                rows_data = []
                for r in range(rows):
                    row = []
                    for c in range(cols):
                        item = self.table_data.item(r, c)
                        row.append(item.text() if item else "")
                    writer.writerow(row)
                    rows_data.append(row)

            short_path = Path(filepath).name
            self.status_bar.showMessage(self._tr("msg_csv_saved", path=short_path))
            self._log(f"CSV saved: {filepath}")
            
            # Print logic
            self._prompt_print_csv(headers, rows_data)
            
        except Exception as e:
            self.status_bar.showMessage(self._tr("msg_csv_error", err=str(e)))
            self._show_alert(self._tr("title_error"), self._tr("msg_csv_error", err=str(e)))
            self._log(f"CSV error: {e}")
            self.logger.exception(f"Error during CSV export: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # Export Grafik (PNG)
    # ══════════════════════════════════════════════════════════════════════════

    def _export_graph(self):
        """Export tampilan grafik saat ini ke file PNG."""
        try:
            from pyqtgraph.exporters import ImageExporter
        except ImportError:
            self.status_bar.showMessage(
                self._tr("msg_graph_error", err="ImageExporter not available")
            )
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"grafik_{ts}.png"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("dlg_graph_title"),
            default_name,
            "PNG Image (*.png);;All Files (*)",
        )
        if not filepath:
            return

        try:
            exporter = ImageExporter(self.plot_widget.plotItem)
            # Export at 2x widget width for crisp output
            exporter.parameters()['width'] = int(self.plot_widget.width() * 2)
            exporter.export(filepath)

            short_path = Path(filepath).name
            self.status_bar.showMessage(
                self._tr("msg_graph_saved", path=short_path)
            )
            self._log(f"Graph saved: {filepath}")
            
            # Print logic
            self._prompt_print_graph(filepath)
            
        except Exception as e:
            self.status_bar.showMessage(self._tr("msg_graph_error", err=str(e)))
            self._show_alert(self._tr("title_error"), self._tr("msg_graph_error", err=str(e)))
            self._log(f"Graph export error: {e}")
            self.logger.exception(f"Error during graph export: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # Print Helper Functions
    # ══════════════════════════════════════════════════════════════════════════

    def _get_active_printer(self):
        printer_name = self.combo_printer.currentText()
        if not printer_name:
            return None
            
        printers = QPrinterInfo.availablePrinters()
        for p in printers:
            if p.printerName() == printer_name:
                return p
        return None

    def _prompt_print_csv(self, headers, rows_data):
        p_info = self._get_active_printer()
        if not p_info:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_no_printer"))
            return
            
        printer_name = p_info.printerName()
        ans = QMessageBox.question(
            self,
            "Print",
            self._tr("msg_print_confirm", printer=printer_name),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if ans == QMessageBox.No:
            self._log(self._tr("msg_print_skip"))
            return
            
        try:
            printer = QPrinter(p_info)
            doc = QTextDocument()
            
            html = "<h2>Data Export</h2>"
            html += "<table border='1' cellspacing='0' cellpadding='4'>"
            html += "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
            for row in rows_data:
                html += "<tr>" + "".join(f"<td>{r}</td>" for r in row) + "</tr>"
            html += "</table>"
            
            doc.setHtml(html)
            doc.print_(printer)
            
            self._log(self._tr("msg_print_ok"))
            self.status_bar.showMessage(self._tr("msg_print_ok"))
        except Exception as e:
            err_msg = str(e)
            self._log(self._tr("msg_print_error", err=err_msg))
            self.status_bar.showMessage(self._tr("msg_print_error", err=err_msg))
            self._show_alert(self._tr("title_error"), self._tr("msg_print_error", err=err_msg))
            self.logger.exception("Error printing CSV")

    def _prompt_print_graph(self, filepath):
        p_info = self._get_active_printer()
        if not p_info:
            self._show_alert(self._tr("title_error"), self._tr("msg_err_no_printer"))
            return
            
        printer_name = p_info.printerName()
        ans = QMessageBox.question(
            self,
            "Print",
            self._tr("msg_print_confirm", printer=printer_name),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if ans == QMessageBox.No:
            self._log(self._tr("msg_print_skip"))
            return
            
        try:
            from PySide6.QtGui import QImage
            
            printer = QPrinter(p_info)
            
            # Create a painter to draw the image onto the printer
            painter = QPainter()
            painter.begin(printer)
            
            img = QImage(filepath)
            
            # Scale image to fit the page horizontally if needed, keeping aspect ratio
            rect = painter.viewport()
            size = img.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(img.rect())
            painter.drawImage(0, 0, img)
            
            painter.end()
            
            self._log(self._tr("msg_print_ok"))
            self.status_bar.showMessage(self._tr("msg_print_ok"))
        except Exception as e:
            err_msg = str(e)
            self._log(self._tr("msg_print_error", err=err_msg))
            self.status_bar.showMessage(self._tr("msg_print_error", err=err_msg))
            self._show_alert(self._tr("title_error"), self._tr("msg_print_error", err=err_msg))
            self.logger.exception("Error printing graph")

    # ══════════════════════════════════════════════════════════════════════════
    # Logging & Printer Status
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_printers(self):
        """Refresh daftar printer di sistem."""
        current = self.combo_printer.currentText()
        self.combo_printer.clear()
        
        printers = QPrinterInfo.availablePrinters()
        printer_names = [p.printerName() for p in printers]
        self.combo_printer.addItems(printer_names)
        
        default_p = QPrinterInfo.defaultPrinter()
        if current and current in printer_names:
            self.combo_printer.setCurrentText(current)
        elif not default_p.isNull() and default_p.printerName() in printer_names:
            self.combo_printer.setCurrentText(default_p.printerName())
            
        self._update_printer_status()

    def _update_printer_status(self):
        """Update indikator warna status printer."""
        t = self._current_theme
        if self.combo_printer.count() > 0:
            self.lbl_printer_status.setText(self._tr("status_printer_ready"))
            self.lbl_printer_dot.setStyleSheet(
                f"color: {t['success']}; font-size: 14px; background: transparent;"
            )
        else:
            self.lbl_printer_status.setText(self._tr("status_printer_none"))
            self.lbl_printer_dot.setStyleSheet(
                f"color: {t['danger']}; font-size: 14px; background: transparent;"
            )

    def _open_log_folder(self):
        """Buka folder logs/ di file explorer."""
        log_dir = Path("logs").absolute()
        if log_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

    def _log(self, message: str):
        """Tambah pesan ke panel log dan file log (dari main thread)."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.txt_log.append(f"[{timestamp}] {message}")
        if not message.startswith("ERROR:"):
            self.logger.info(message)

    def _on_raw_data(self, direction: str, data: bytes):
        """
        Callback dari UVProtocol — dipanggil dari WORKER THREAD.
        Gunakan signal untuk marshal ke main thread.
        """
        formatted = UVProtocol.format_bytes_display(data)
        self._log_signal.emit(f"  {direction}: {formatted}")

    @Slot(str)
    def _append_log_text(self, text: str):
        """Slot: terima log dari worker thread, tulis ke panel log & file."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.txt_log.append(f"[{timestamp}] {text}")
        self.logger.info(text)

    # ══════════════════════════════════════════════════════════════════════════
    # Stylesheet (token-based)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _build_stylesheet(t: dict) -> str:
        """Build stylesheet lengkap dari design tokens."""
        return f"""
            /* ── Base ─────────────────────────────────────────────── */
            QMainWindow, QWidget {{
                background-color: {t['bg_app']};
                color: {t['text_primary']};
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 13px;
            }}

            /* ── Menu bar ─────────────────────────────────────────── */
            QMenuBar {{
                background-color: {t['toolbar_bg']};
                color: {t['text_primary']};
                border-bottom: 1px solid {t['toolbar_border']};
                padding: 1px 0;
                font-size: 13px;
                spacing: 0px;
            }}
            QMenuBar::item {{
                padding: 5px 14px;
                background: transparent;
                border-radius: 0;
            }}
            QMenuBar::item:selected {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}
            QMenu {{
                background-color: {t['bg_panel']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                padding: 4px 0;
            }}
            QMenu::item {{
                padding: 6px 28px 6px 16px;
            }}
            QMenu::item:selected {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}
            QMenu::item:disabled {{
                color: {t['text_secondary']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {t['border']};
                margin: 4px 8px;
            }}

            /* ── Corner toggle buttons ────────────────────────────── */
            QPushButton#btnThemeToggle {{
                background-color: {t['bg_panel']};
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
                margin: 2px 0px;
            }}
            QPushButton#btnThemeToggle:hover {{
                background-color: {t['bg_panel_header']};
                border-color: {t['accent']};
                color: {t['accent']};
            }}

            /* ── GroupBox (Cards) ─────────────────────────────────── */
            QGroupBox {{
                background-color: {t['bg_panel']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                margin-top: 16px;
                padding: 16px 10px 10px 10px;
                color: {t['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px 4px 10px;
                background-color: {t['bg_panel_header']};
                border: 1px solid {t['border']};
                border-top-left-radius: 6px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                border-bottom-left-radius: 0px;
                color: {t['text_primary']};
                font-weight: bold;
                font-size: 10px;
                letter-spacing: 0.8px;
            }}

            /* ── Default buttons ──────────────────────────────────── */
            QPushButton {{
                background-color: transparent;
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {t['accent']};
                color: {t['accent']};
            }}
            QPushButton:pressed {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}
            QPushButton:disabled {{
                background-color: {t['bg_app']};
                color: {t['text_secondary']};
                border-color: {t['border']};
            }}

            /* ── Primary button ──────────────────────────────────── */
            QPushButton#btnPrimary {{
                background-color: {t['accent']};
                color: {t['accent_text']};
                border: none;
                font-weight: 600;
            }}
            QPushButton#btnPrimary:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton#btnPrimary:pressed {{
                background-color: {t['accent_hover']};
            }}
            QPushButton#btnPrimary:disabled {{
                background-color: {t['bg_panel_header']};
                color: {t['text_secondary']};
            }}

            /* ── Secondary / outline button ──────────────────────── */
            QPushButton#btnSecondary {{
                background-color: transparent;
                color: {t['accent']};
                border: 1px solid {t['accent']};
            }}
            QPushButton#btnSecondary:hover {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}
            QPushButton#btnSecondary:disabled {{
                background-color: transparent;
                color: {t['text_secondary']};
                border-color: {t['border']};
            }}

            /* ── Inputs ──────────────────────────────────────────── */
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                selection-background-color: {t['accent']};
                selection-color: {t['accent_text']};
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
            QComboBox:focus {{
                border-color: {t['accent']};
            }}
            QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
            QComboBox:disabled {{
                color: {t['text_secondary']};
                background-color: {t['bg_app']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['bg_panel']};
                color: {t['text_primary']};
                selection-background-color: {t['accent']};
                selection-color: {t['accent_text']};
                border: 1px solid {t['border']};
                outline: none;
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {t['bg_panel_header']};
                border: none;
                border-left: 1px solid {t['border']};
                width: 18px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {t['accent']};
            }}

            /* ── Labels ──────────────────────────────────────────── */
            QLabel {{
                color: {t['text_secondary']};
                background: transparent;
                font-size: 12px;
            }}
            QLabel#lblBigValue {{
                color: {t['text_primary']};
            }}
            QLabel#lblUnit {{
                color: {t['text_secondary']};
            }}
            QLabel#lblConnStatus {{
                color: {t['text_secondary']};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#connDot {{
                background: transparent;
            }}

            /* ── Header frame ────────────────────────────────────── */
            QFrame#headerFrame {{
                background-color: {t['bg_panel']};
                border: 1px solid {t['border']};
                border-radius: 6px;
            }}

            /* ── Export bar ───────────────────────────────────────── */
            QWidget#exportBar {{
                background: transparent;
            }}

            /* ── Table ───────────────────────────────────────────── */
            QTableWidget {{
                background-color: {t['bg_panel']};
                alternate-background-color: {t['table_alt']};
                color: {t['text_primary']};
                gridline-color: {t['border']};
                border: none;
                selection-background-color: {t['accent']};
                selection-color: {t['accent_text']};
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {t['bg_panel_header']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                padding: 5px;
                font-weight: bold;
                font-size: 11px;
            }}

            /* ── Tab widget ──────────────────────────────────────── */
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                background-color: {t['bg_panel']};
            }}
            QTabBar::tab {{
                background-color: {t['bg_panel_header']};
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 5px 16px;
                margin-right: 2px;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background-color: {t['bg_panel']};
                color: {t['accent']};
                border-bottom: 2px solid {t['tab_selected_border']};
                font-weight: bold;
            }}

            /* ── TextEdit (log) ──────────────────────────────────── */
            QTextEdit {{
                background-color: {t['log_bg']};
                color: {t['log_text']};
                border: none;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
            }}

            /* ── Progress bar ────────────────────────────────────── */
            QProgressBar {{
                background-color: {t['bg_panel_header']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                text-align: center;
                color: {t['text_primary']};
                height: 18px;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 3px;
            }}

            /* ── Status bar ──────────────────────────────────────── */
            QStatusBar {{
                background-color: {t['statusbar_bg']};
                color: {t['text_secondary']};
                border-top: 1px solid {t['border']};
                font-size: 12px;
                padding: 2px 8px;
            }}

            /* ── Scroll area ─────────────────────────────────────── */
            QScrollArea, QScrollArea > QWidget > QWidget {{
                background-color: {t['bg_app']};
                border: none;
            }}

            /* ── Scrollbar ───────────────────────────────────────── */
            QScrollBar:vertical {{
                background-color: {t['bg_app']};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {t['scrollbar_handle']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {t['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background-color: {t['bg_app']};
                height: 8px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {t['scrollbar_handle']};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {t['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}

            /* ── Splitter ────────────────────────────────────────── */
            QSplitter::handle {{
                background-color: {t['border']};
                width: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {t['accent']};
            }}
        """
