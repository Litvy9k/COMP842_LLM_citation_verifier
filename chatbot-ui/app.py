import sys
from datetime import datetime
from PySide6 import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt
MAX_BUBBLE_RATIO = 0.68


class SendTextEdit(QtWidgets.QTextEdit):
    sendTriggered = QtCore.Signal()
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            event.accept()
            self.sendTriggered.emit()
            return
        super().keyPressEvent(event)


class AutoHeightTextBrowser(QtWidgets.QTextBrowser):
    heightChanged = QtCore.Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setOpenExternalLinks(True)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet("QTextBrowser { background: transparent; color: #222; }")
        pal = self.viewport().palette()
        pal.setColor(QtGui.QPalette.Base, QtCore.Qt.transparent)
        self.viewport().setPalette(pal)

        self.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)
        opt = self.document().defaultTextOption()
        opt.setWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(opt)

        self.document().contentsChanged.connect(self._relayout_to_contents)
        self.setMinimumHeight(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)

    def setMaximumTextWidth(self, max_width: int):
        self.setMaximumWidth(max(50, max_width - 24))  # leave padding room
        self.document().setTextWidth(self.maximumWidth())
        self._relayout_to_contents()

    def _relayout_to_contents(self):
        doc = self.document()
        doc.adjustSize()
        doc_size = doc.size().toSize()
        margins = self.contentsMargins()
        h = doc_size.height() + margins.top() + margins.bottom()
        self.setFixedHeight(h)
        self.heightChanged.emit()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        self._relayout_to_contents()


class MessageBubble(QtWidgets.QFrame):
    def __init__(self, text: str, role: str = "chatbot", parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName(f"bubble-{role}")
        self._last_max_w = 360

        self.text_edit = AutoHeightTextBrowser()
        self.text_edit.setText(text)
        self.text_edit.document().contentsChanged.connect(self._recalc_width)

        self.time_label = QtWidgets.QLabel(datetime.now().strftime("%H:%M"))
        self.time_label.setObjectName("timestamp")
        self.time_label.setAlignment(Qt.AlignRight)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)
        lay.addWidget(self.text_edit)
        lay.addWidget(self.time_label)

        self.setStyleSheet("""
        QFrame#bubble-user {
            background: #a0c4ff;
            border: 1px solid #6699ff;
            border-radius: 12px;
        }
        QFrame#bubble-chatbot {
            background: #d9d9d9;
            border: 1px solid #bfbfbf;
            border-radius: 12px;
        }
        QFrame#bubble-system {
            background: #e6ccb2;
            border: 1px solid #d4a373;
            border-radius: 12px;
        }
        QLabel#timestamp { color:#666; font-size:11px; }
        """)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def set_max_width(self, w: int):
        """Compute final bubble width by content; wrap long lines under max width."""
        self._last_max_w = max(160, w)
        pad = 24
        min_text_w = 80

        max_text_w = max(50, self._last_max_w - pad)
        doc = self.text_edit.document()
        doc.setTextWidth(max_text_w)
        doc.adjustSize()

        ideal = int(doc.idealWidth())
        used_text_w = max(min_text_w, min(max_text_w, ideal))

        self.text_edit.setFixedWidth(used_text_w)
        self.setFixedWidth(used_text_w + pad)

        self.layout().activate()
        self.updateGeometry()

    def _recalc_width(self):
        self.set_max_width(self._last_max_w)


class VerticalTabButton(QtWidgets.QAbstractButton):
    def __init__(self, text="CiVi", parent=None):
        super().__init__(parent)
        self.setText(text)
        self._hover = False
        self._pressed = False
        self._w = 36
        self._h = 120 
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))

    def sizeHint(self):
        return QtCore.QSize(self._w, self._h)

    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True; self.update()
    def mouseReleaseEvent(self, e):
        if self._pressed and self.rect().contains(e.pos()):
            self.clicked.emit()
        self._pressed = False; self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        if self._pressed:
            bg = QtGui.QColor("#e0e0e0")
        elif self._hover:
            bg = QtGui.QColor("#f7f7f7")
        else:
            bg = QtGui.QColor("#ffffff")

        path = QtGui.QPainterPath()
        path.addRoundedRect(rect.adjusted(0, 0, -1, -1), 16, 16)
        p.fillPath(path, bg)
        pen = QtGui.QPen(QtGui.QColor("#cfcfcf")); pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)

        p.save()
        p.translate(rect.center())
        p.rotate(-90)
        text_rect = QtCore.QRectF(-rect.height()/2, -rect.width()/2, rect.height(), rect.width())
        pen.setColor(QtGui.QColor("#333"))
        p.setPen(pen)
        font = self.font(); font.setWeight(QtGui.QFont.DemiBold)
        p.setFont(font)
        p.drawText(text_rect, Qt.AlignCenter, self.text())
        p.restore()


class OverlayPanel(QtWidgets.QFrame):
    toggled = QtCore.Signal(bool)

    def __init__(self, parent: QtWidgets.QWidget, target_rect_getter, width_expanded: int = 320):
        super().__init__(parent)
        self._get_target_rect = target_rect_getter
        self._expanded_width = width_expanded
        self._is_open = False

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("OverlayPanel{background: transparent;}")

        self.panel = QtWidgets.QFrame(self)
        self.panel.setObjectName("civi-panel")
        self.panel.setStyleSheet("""
            QFrame#civi-panel {
                background: #f2f2f2;
                border-left: 1px solid #cfcfcf;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }
        """)
        self.panel.setFixedWidth(0)
        self.panel.setMinimumWidth(0)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("CiVi")
        title.setStyleSheet("font-weight:700; font-size:15px; color:#222;")
        header.addWidget(title)
        header.addStretch()
        close_btn = QtWidgets.QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; font-size:16px; color:#555; }
            QPushButton:hover { background:#e5e5e5; border-radius:12px; }
        """)
        header.addWidget(close_btn)

        body = QtWidgets.QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setStyleSheet("QTextBrowser{border:1px solid #ccc; border-radius:8px; background:#fff; color:#222; padding:8px;}")
        body.setPlainText("Placeholder for citation verifier info. Put the verification result here.")

        p_lay = QtWidgets.QVBoxLayout(self.panel)
        p_lay.setContentsMargins(10, 10, 10, 10)
        p_lay.setSpacing(10)
        p_lay.addLayout(header)
        p_lay.addWidget(body, 1)

        self.anim = QtCore.QVariantAnimation(self)
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        self.anim.valueChanged.connect(self._on_anim_step)
        self.anim.finished.connect(lambda: self.toggled.emit(self._is_open))

        self.tab_btn = VerticalTabButton("CiVi", self)
        self.tab_btn.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.tab_btn.raise_()

        self.tab_btn.clicked.connect(self.toggle)
        close_btn.clicked.connect(self.collapse)

    def _on_anim_step(self, value):
        w = int(value)
        self.panel.setFixedWidth(w)
        self.layout_to_target()

    def _anim_start(self, start, end):
        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()

    def layout_to_target(self):
        rect = self._get_target_rect()
        self.setGeometry(rect)
        cur_w = self.panel.width()
        self.panel.setGeometry(rect.width() - cur_w, 0, cur_w, rect.height())

        tab_margin = 8
        tx = rect.width() - self.tab_btn.width() - (cur_w if cur_w > 0 else 0) - tab_margin
        ty = (rect.height() - self.tab_btn.height()) // 2
        self.tab_btn.move(max(0, tx), max(0, ty))
        self.raise_()

    def expand(self):
        if self._is_open: return
        self._is_open = True
        self._anim_start(self.panel.width(), self._expanded_width)

    def collapse(self):
        if not self._is_open: return
        self._is_open = False
        self._anim_start(self.panel.width(), 0)

    def toggle(self):
        self.expand() if not self._is_open else self.collapse()

    def isOpen(self) -> bool:
        return self._is_open


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CiVi Chatbot")
        self.resize(600, 680)
        self._build_ui()
        self._build_menu()

        self.history = []
        self._bubble_items = []

        self.add_message(
            "How can I help you today?",
            role="chatbot"
        )

        def get_list_rect_in_central():
            vp = self.list_view.viewport()
            top_left = vp.mapTo(self.centralWidget(), QtCore.QPoint(0, 0))
            return QtCore.QRect(top_left, vp.size())

        self.overlay = OverlayPanel(self.centralWidget(), get_list_rect_in_central, width_expanded=320)
        QtCore.QTimer.singleShot(0, self.overlay.layout_to_target)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title_bar = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Chat")
        title.setStyleSheet("font-weight:600; font-size:16px; color:#222;")
        title_bar.addWidget(title)
        title_bar.addStretch()
        self.status_hint = QtWidgets.QLabel("")
        self.status_hint.setStyleSheet("color:#555;")
        title_bar.addWidget(self.status_hint)
        root.addLayout(title_bar)

        self.list_view = QtWidgets.QListWidget()
        self.list_view.setAlternatingRowColors(False)
        self.list_view.setUniformItemSizes(False)
        self.list_view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.list_view.setFocusPolicy(Qt.NoFocus)
        self.list_view.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setStyleSheet("QListWidget{border:1px solid #bbb; border-radius:8px; background:#e0e0e0;}")
        root.addWidget(self.list_view, 1)

        input_row = QtWidgets.QHBoxLayout()
        input_row.setSpacing(8)

        self.input = SendTextEdit()
        self.input.setPlaceholderText("Type a message… (Enter to send, Shift+Enter for newline)")
        self.input.setFixedHeight(90)
        self.input.sendTriggered.connect(self.on_send_clicked)
        self.input.setStyleSheet("QTextEdit{border:1px solid #aaa; border-radius:8px; padding:8px; background:#f5f5f5; color:#222;}")
        input_row.addWidget(self.input, 1)

        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.setDefault(True)
        self.send_btn.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        self.send_btn.clicked.connect(self.on_send_clicked)
        self.send_btn.setFixedWidth(96)
        self.send_btn.setStyleSheet("""
            QPushButton{
                background:#1677ff; color:white; border:none; border-radius:8px; padding:10px 14px;
                font-weight:600;
            }
            QPushButton:hover{ background:#3c89ff; }
            QPushButton:pressed{ background:#0f5ed7; }
        """)
        input_row.addWidget(self.send_btn, 0)
        root.addLayout(input_row)

        font = self.font()
        if font.pointSize() < 11:
            font.setPointSize(11)
            self.setFont(font)

    def _build_menu(self):
        bar = self.menuBar()
        file_menu = bar.addMenu("File")
        act_save = QtGui.QAction("Save chat as text…", self)
        act_save.triggered.connect(self.save_history_as_txt)
        file_menu.addAction(act_save)

        act_clear = QtGui.QAction("Clear chat", self)
        act_clear.triggered.connect(self.clear_history)
        file_menu.addAction(act_clear)

        file_menu.addSeparator()
        act_exit = QtGui.QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        help_menu = bar.addMenu("Help")
        act_about = QtGui.QAction("About", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

    def on_send_clicked(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self.add_message(text, role="user")
        QtCore.QTimer.singleShot(200, lambda: self.bot_reply(f"You said: {text}"))

    def bot_reply(self, text: str):
        self.add_message(text, role="chatbot")

    def get_bubble_max_width(self) -> int:
        vp_w = self.list_view.viewport().width()
        return max(160, int(vp_w * MAX_BUBBLE_RATIO))

    def add_message(self, text: str, role: str = "chatbot"):
        container = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(container)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(8)

        bubble = MessageBubble(text, role=role)
        bubble.set_max_width(self.get_bubble_max_width())

        if role == "user":
            h.addStretch(1)
            h.addWidget(bubble, 0, Qt.AlignRight)
        else:
            h.addWidget(bubble, 0, Qt.AlignLeft)
            h.addStretch(1)

        item = QtWidgets.QListWidgetItem()
        self.list_view.addItem(item)
        self.list_view.setItemWidget(item, container)

        def _sync_item_height():
            container.layout().activate()
            item.setSizeHint(container.sizeHint())
        bubble.text_edit.heightChanged.connect(_sync_item_height)
        _sync_item_height()

        self.list_view.scrollToBottom()
        self._bubble_items.append((item, container, bubble))
        self.history.append((role, text))

    def refresh_bubble_widths(self):
        max_w = self.get_bubble_max_width()
        for item, container, bubble in self._bubble_items:
            bubble.set_max_width(max_w)
            container.layout().activate()
            item.setSizeHint(container.sizeHint())
        self.list_view.updateGeometries()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "overlay"):
            self.overlay.layout_to_target()
        QtCore.QTimer.singleShot(0, self.refresh_bubble_widths)

    def clear_history(self):
        self.list_view.clear()
        self.history.clear()
        self._bubble_items.clear()
        self.status_hint.setText("Chat cleared")

    def save_history_as_txt(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As…", "chat.txt", "Text Files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for role, text in self.history:
                f.write(f"[{role}] {text}\n")
        self.status_hint.setText(f"Saved: {path}")

    def show_about(self):
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("About")
        box.setText(
            "Idk what to put here.\n"
        )
        box.setIcon(QtWidgets.QMessageBox.Information)
        box.setStyleSheet(
            "QMessageBox{background:#f0f0f0;color:#222;}"
            "QMessageBox QLabel{color:#222;font-size:13px;}"
            "QMessageBox QPushButton{background:#1677ff;color:#fff;border:none;border-radius:6px;padding:6px 12px;min-width:72px;}"
            "QMessageBox QPushButton:hover{background:#3c89ff;}"
            "QMessageBox QPushButton:pressed{background:#0f5ed7;}"
        )
        box.exec()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = app.palette()
    pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#f0f0f0"))
    pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#e0e0e0"))
    pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#222"))
    app.setPalette(pal)

    app.setStyleSheet("""
        QMenuBar {
            background-color: #f0f0f0;
            color: #222;
        }
        QMenuBar::item {
            background: transparent;
            padding: 4px 12px;
        }
        QMenuBar::item:selected {
            background: #dcdcdc;
        }
        QMenu {
            background-color: #f0f0f0;
            color: #222;
            border: 1px solid #aaa;
        }
        QMenu::item {
            padding: 5px 24px 5px 24px;
        }
        QMenu::item:selected {
            background-color: #dcdcdc;
            color: #000;
        }
    """)

    w = ChatWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()