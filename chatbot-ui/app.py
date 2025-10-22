import sys
import requests
from datetime import datetime
from PySide6 import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt
MAX_BUBBLE_RATIO = 0.68
API_URL = "http://localhost:8000/rag"


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
        self.document().setDocumentMargin(2)

    def setMaximumTextWidth(self, max_width: int):
        self.setMaximumWidth(max(50, max_width - 24))
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
        self._last_max_w = max(160, w)
        bubble_side_padding = 24
        doc_margin = int(self.text_edit.document().documentMargin())
        safety = 6

        max_text_w = max(50, self._last_max_w - bubble_side_padding - 2*doc_margin - safety)

        doc = self.text_edit.document()
        doc.setTextWidth(max_text_w)
        doc.adjustSize()
        ideal = int(doc.idealWidth())

        used_text_w = max(80, min(max_text_w, ideal)) + 2*doc_margin + safety

        self.text_edit.setFixedWidth(used_text_w)
        self.setFixedWidth(used_text_w + bubble_side_padding)

        self.layout().activate()
        self.updateGeometry()

    def _recalc_width(self):
        self.set_max_width(self._last_max_w)


class VerticalTabButton(QtWidgets.QAbstractButton):
    highlightedChanged = QtCore.Signal(bool)

    def __init__(self, text="CiVi", parent=None):
        super().__init__(parent)
        self.setText(text)
        self._hover = False
        self._pressed = False
        self._highlight = False
        self._pulse = QtCore.QVariantAnimation(self)
        self._pulse.setStartValue(0.0)
        self._pulse.setEndValue(1.0)
        self._pulse.setDuration(1000)
        self._pulse.setLoopCount(-1)
        self._pulse.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        self._w = 36
        self._h = 120
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        self._pulse.valueChanged.connect(self.update)

    def setHighlighted(self, on: bool):
        if self._highlight == on:
            return
        self._highlight = on
        if on:
            self._pulse.start()
        else:
            self._pulse.stop()
        self.update()
        self.highlightedChanged.emit(on)

    def sizeHint(self):
        return QtCore.QSize(self._w, self._h)

    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True; self.update()
    def mouseReleaseEvent(self, e):
        if self._pressed and self.rect().contains(e.pos()):
            self.setHighlighted(False)
            self.clicked.emit()
        self._pressed = False; self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()
        radius = 18

        if self._pressed:
            base_bg = QtGui.QColor("#e9eefc")
        elif self._hover:
            base_bg = QtGui.QColor("#f7f7f7")
        else:
            base_bg = QtGui.QColor("#ffffff")

        if self._highlight:
            k = float(self._pulse.currentValue() or 0.0)
            mix = 0.25 + 0.50 * (0.5 - abs(k - 0.5)) * 2.0
            blue = QtGui.QColor(22, 119, 255)
            r = int((1 - mix) * base_bg.red()   + mix * blue.red())
            g = int((1 - mix) * base_bg.green() + mix * blue.green())
            b = int((1 - mix) * base_bg.blue()  + mix * blue.blue())
            fill_bg = QtGui.QColor(r, g, b)
        else:
            fill_bg = base_bg

        path = QtGui.QPainterPath()
        path.addRoundedRect(rect.adjusted(0, 0, -1, -1), radius, radius)

        p.fillPath(path, fill_bg)

        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 35))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)

        p.save()
        p.translate(rect.center())
        p.rotate(-90)
        text_rect = QtCore.QRectF(-rect.height()/2, -rect.width()/2, rect.height(), rect.width())
        text_pen = QtGui.QPen(QtGui.QColor("#333"))
        p.setPen(text_pen)
        font = self.font()
        font.setWeight(QtGui.QFont.DemiBold)
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
        self._civi_items = []

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

        self.list = QtWidgets.QListWidget(self.panel)
        self.list.setAlternatingRowColors(False)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.list.setStyleSheet("QListWidget { border: none; background: transparent; }")
        self.list.setObjectName("civiList")
        self.list.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.list.viewport().setAutoFillBackground(False)
        self.list.setStyleSheet("""
            #civiList { border: none; background: transparent; }
            #civiList::item { margin: 0; padding: 0; border: none; background: transparent; }
            #civiList::item:selected { background: transparent; }
        """)

        p_lay = QtWidgets.QVBoxLayout(self.panel)
        p_lay.setContentsMargins(10, 10, 10, 10)
        p_lay.setSpacing(10)
        p_lay.addLayout(header)
        p_lay.addWidget(self.list, 1)

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
        
        self.parentWidget().installEventFilter(self)
        try:
            self._target_vp = self._get_target_rect.__self__.list_view.viewport()
            self._target_vp.installEventFilter(self)
            self._target_list = self._get_target_rect.__self__.list_view
            self._target_list.installEventFilter(self)
            self._target_list.verticalScrollBar().rangeChanged.connect(
                lambda *_: QtCore.QTimer.singleShot(0, self.layout_to_target)
            )
        except Exception:
            self._target_vp = None
        
        self.list.installEventFilter(self)
        self.list.viewport().installEventFilter(self)
        
    def eventFilter(self, obj, ev):
        if ev.type() in (
            QtCore.QEvent.Resize,
            QtCore.QEvent.Move,
            QtCore.QEvent.LayoutRequest,
            QtCore.QEvent.Show,
            QtCore.QEvent.Hide
        ):
            QtCore.QTimer.singleShot(0, self.layout_to_target)
            QtCore.QTimer.singleShot(0, self.refresh_bubble_widths)
        return super().eventFilter(obj, ev)
            
    def _on_anim_step(self, value):
        w = int(value)
        self.panel.setFixedWidth(w)
        self.layout_to_target()
        self.refresh_bubble_widths()

    def _anim_start(self, start, end):
        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()

    def layout_to_target(self):
        rect = self._get_target_rect()

        panel_w = self.panel.width()
        tab_w   = self.tab_btn.width()
        margin  = 8
        strip_w = panel_w + tab_w + margin

        x = rect.x() + rect.width() - strip_w
        if x < rect.x():
            x = rect.x()
        self.setGeometry(x, rect.y(), strip_w, rect.height())
        self.panel.setGeometry(self.width() - panel_w, 0, panel_w, self.height())

        tx = self.width() - panel_w - tab_w - margin//2
        ty = (self.height() - self.tab_btn.height()) // 2
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
        self.tab_btn.setHighlighted(False)
        self.expand() if not self._is_open else self.collapse()

    def isOpen(self) -> bool:
        return self._is_open

    def _bubble_max_width(self) -> int:
        w = self.panel.width() if self.panel.width() > 0 else self._expanded_width
        return max(160, int(w * 0.92))

    def add_civi_message(self, text: str):
        row = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(6, 6, 6, 6)
        h.setSpacing(6)

        bubble = QtWidgets.QFrame()
        bubble.setObjectName("civiBubble")
        bubble.setAttribute(Qt.WA_StyledBackground, True)
        bubble.setStyleSheet("""
            #civiBubble { background:#fff; border:1px solid #ccc; border-radius:10px; }
            #civiBubble > * { background:transparent; }
            QLabel#timestamp { color:#666; font-size:11px; }
        """)
        bubble.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        v = QtWidgets.QVBoxLayout(bubble)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(6)

        txt = AutoHeightTextBrowser()
        txt.setText(text)
        v.addWidget(txt)

        ts = QtWidgets.QLabel(datetime.now().strftime("%H:%M"))
        ts.setObjectName("timestamp")
        v.addWidget(ts, 0, Qt.AlignRight)

        h.addWidget(bubble, 1)
        
        item = QtWidgets.QListWidgetItem()
        self.list.addItem(item)
        self.list.setItemWidget(item, row)

        def sync_item_size():
            txt.setFixedWidth(self._civi_viewport_width())
            row.layout().activate()
            item.setSizeHint(row.sizeHint())

        QtCore.QTimer.singleShot(0, sync_item_size)
        txt.heightChanged.connect(sync_item_size)

        self.list.scrollToBottom()

        if not self._is_open:
            self.tab_btn.setHighlighted(True)
            
    def _civi_viewport_width(self) -> int:
        vp_w = self.list.viewport().width()
        row_margins = 6 * 2
        bubble_margins = 10 * 2
        safety = 6
        return max(80, vp_w - row_margins - bubble_margins - safety)

    def _update_civi_row_width(self, row_widget: QtWidgets.QWidget):
        txt = row_widget.findChild(AutoHeightTextBrowser)
        if txt:
            txt.setFixedWidth(self._civi_viewport_width())
            row_widget.layout().activate()
            item = self.list.item(self.list.indexAt(row_widget.pos()).row())
            if item:
                item.setSizeHint(row_widget.sizeHint())

    def refresh_bubble_widths(self):
        for i in range(self.list.count()):
            item = self.list.item(i)
            row = self.list.itemWidget(item)
            if not row:
                continue
            txt = row.findChild(AutoHeightTextBrowser)
            if txt:
                txt.setFixedWidth(self._civi_viewport_width())
            row.layout().activate()
            item.setSizeHint(row.sizeHint())
        self.list.updateGeometries()


class TypingIndicator(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bubble-system")
        self.setStyleSheet("""
            QFrame#bubble-system {
                background: #e6ccb2;
                border: 1px solid #d4a373;
                border-radius: 12px;
            }
            QLabel { color:#553; }
        """)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)
        self.label = QtWidgets.QLabel("Assistant is typing")
        lay.addWidget(self.label)
        self._dots = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self.label.setText("Assistant is typing" + "." * self._dots)


class ApiWorker(QtCore.QObject):
    finished = QtCore.Signal(str, dict)
    failed = QtCore.Signal(str)

    def __init__(self, prompt: str, parent=None):
        super().__init__(parent)
        self.prompt = prompt

    @QtCore.Slot()
    def run(self):
        try:
            payload = {"prompt": self.prompt, "max_tokens": 200}
            resp = requests.post(API_URL, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("response", "")
                metadata = data.get("paper_metadata", {})
                if "\n\n" in text:
                    text = text.split("\n\n", 1)[1]
                if self.prompt in text:
                    text = text.replace(self.prompt, "").strip()
                self.finished.emit(text.strip(), metadata)
            else:
                self.failed.emit(f"Error {resp.status_code}: server returned an error.")
        except Exception as e:
            self.failed.emit(f"Request failed: {e}")


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CiVi Chatbot")
        self.resize(600, 680)
        self._build_ui()
        self._build_menu()

        self.history = []
        self._bubble_items = []
        self._typing_item = None
        self._thread = None

        self.add_message("How can I help you today?", role="chatbot")

        def get_list_rect_in_central():
            vp = self.list_view.viewport()
            top_left = vp.mapTo(self.centralWidget(), QtCore.QPoint(0, 0))
            return QtCore.QRect(top_left, vp.size())

        self.overlay = OverlayPanel(self.centralWidget(), get_list_rect_in_central, width_expanded=320)
        QtCore.QTimer.singleShot(0, self.overlay.layout_to_target)
        
    def civi_add_info(self, text: str):
        self.overlay.add_civi_message(text)

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
        self.show_typing_indicator()
        self.start_api_call(text)
        # self.add_message("You said:{}".format(text), role="chatbot")
        # self.civi_add_info("He said:{}".format(text))

    def start_api_call(self, prompt: str):
        if self._thread is not None:
            try:
                self._thread.quit()
                self._thread.wait(50)
            except Exception:
                pass
        self._thread = QtCore.QThread(self)
        self._worker = ApiWorker(prompt)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self.on_api_success)
        self._worker.failed.connect(self.on_api_fail)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def on_api_success(self, text: str, metadata: dict):
        self.hide_typing_indicator()
        self.bot_reply(text)
        if metadata:
            self.civi_add_info(self.debug_metadata(metadata))
    
    def debug_metadata(self, metadata: dict):
        msg = "Cited paper:\nTitle: {}\nauthor: {}\nDOI: {}\nDate: {}\nJournal: {}".format(
            metadata.get("title"),
            metadata.get("author"),
            metadata.get("doi"),
            metadata.get("date"),
            metadata.get("journal"),
        )
        return msg
        
    def on_api_fail(self, msg: str):
        self.hide_typing_indicator()
        self.add_message(msg, role="system")

    def show_typing_indicator(self):
        if self._typing_item is not None:
            return
        container = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(container)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(8)

        bubble = TypingIndicator()
        max_w = self.get_bubble_max_width()
        bubble.setFixedWidth(min(max_w, 260))

        h.addWidget(bubble, 0, Qt.AlignLeft)
        h.addStretch(1)

        item = QtWidgets.QListWidgetItem()
        self.list_view.addItem(item)
        self.list_view.setItemWidget(item, container)

        def _sync_item_height():
            container.layout().activate()
            item.setSizeHint(container.sizeHint())
        _sync_item_height()

        self.list_view.scrollToBottom()
        self._typing_item = (item, container, bubble)

    def hide_typing_indicator(self):
        if self._typing_item is None:
            return
        item, container, bubble = self._typing_item
        row = self.list_view.row(item)
        if row >= 0:
            self.list_view.takeItem(row)
        self._typing_item = None

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
        super().resizeEventot(0, self.refresh_bubble_widths)(event)
        if hasattr(self, "overlay"):
            self.overlay.layout_to_target()
            self.overlay.refresh_bubble_widths()
        QtCore.QTimer.singleShot(0, self.refresh_bubble_widths)

    def clear_history(self):
        self.list_view.clear()
        self.history.clear()
        self._bubble_items.clear()
        self._typing_item = None
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
        box.setText("Idk what to put here.\n")
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