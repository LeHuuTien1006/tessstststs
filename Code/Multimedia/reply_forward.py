from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QMenu, QAbstractItemView, QListWidget
from PySide6.QtCore import Qt

class ReplyHandler:
    def __init__(self, main_window):
        self.main = main_window
        self._setup_reply_bar()
        self.original_mouse_press = self.main.chat_list.mousePressEvent
        self.main.chat_list.mousePressEvent = self._chat_list_mouse_press

    def _setup_reply_bar(self):
        """Tạo thanh preview reply phía trên ô nhập tin nhắn (ẩn mặc định)."""
        self.reply_bar = QFrame()
        self.reply_bar.setFixedHeight(44)
        self.reply_bar.setStyleSheet("""
            QFrame {
                background-color: #1E242C;
                border-top: 2px solid #3498db;
            }
        """)

        bar_layout = QHBoxLayout(self.reply_bar)
        bar_layout.setContentsMargins(10, 4, 6, 4)
        bar_layout.setSpacing(6)

        icon_lbl = QLabel("↩")
        icon_lbl.setStyleSheet("color: #3498db; font-size: 16px; background: transparent;")
        icon_lbl.setFixedWidth(20)

        self.reply_preview_lbl = QLabel("Đang trả lời...")
        self.reply_preview_lbl.setStyleSheet(
            "color: #B0B8C1; font-size: 12px; background: transparent;"
        )

        cancel_btn = QPushButton("✕")
        cancel_btn.setFixedSize(24, 24)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #8A8D91;
                font-size: 14px; border: none; border-radius: 12px;
            }
            QPushButton:hover { color: #fff; background: rgba(255,255,255,0.1); }
        """)
        cancel_btn.clicked.connect(self._cancel_reply)

        bar_layout.addWidget(icon_lbl)
        bar_layout.addWidget(self.reply_preview_lbl, 1)
        bar_layout.addWidget(cancel_btn)

        # Chèn vào layout của col3, phía trên widget cuối (input area)
        col3_layout = self.main.ui.col3_mainchat.layout()
        col3_layout.insertWidget(col3_layout.count() - 1, self.reply_bar)
        self.reply_bar.hide()

    def _show_chat_context_menu(self, pos):
        """Hiển thị menu chuột phải trên danh sách tin nhắn."""
        item = self.main.chat_list.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.UserRole)
        if not data or data.get("type") not in ("text", "image"):
            return
        menu = QMenu(self.main)
        menu.setStyleSheet("""
            QMenu { background:#2C323A; color:white; border:1px solid #444;
                    border-radius:6px; padding:4px; }
            QMenu::item { padding:6px 20px; border-radius:4px; }
            QMenu::item:selected { background:#3498db; }
        """)
        reply_action = menu.addAction("↩  Trả lời tin nhắn này")
        action = menu.exec(self.main.chat_list.viewport().mapToGlobal(pos))
        if action == reply_action:
            self._start_reply(data)

    def _start_reply(self, msg_data):
        """Lưu tin nhắn cần reply và hiện thanh preview."""
        self.main.reply_to_data = {
            "sender": msg_data["sender"],
            "content": msg_data.get("content", "[Ảnh]")
        }
        preview = self.main.reply_to_data["content"]
        if len(preview) > 55:
            preview = preview[:52] + "..."
        self.reply_preview_lbl.setText(
            f"<b style='color:#3498db'>{self.main.reply_to_data['sender']}</b>: {preview}"
        )
        self.reply_bar.show()
        self.main.ui.txt_input_message.setFocus()

    def _cancel_reply(self):
        """Hủy trả lời — ẩn thanh preview và xóa state."""
        self.main.reply_to_data = None
        self.reply_bar.hide()

    def _chat_list_mouse_press(self, event):
        """Xử lý click vào tin nhắn — nếu click trúng quote reply thì nhảy về tin gốc."""
        # Gọi xử lý mặc định trước
        self.original_mouse_press(event)

        item = self.main.chat_list.itemAt(event.position().toPoint())
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data or not isinstance(data, dict) or not data.get("reply_to"):
            return

        # Tính vùng quote block trong item
        y_offset = 0
        if data.get("show_time_tag"):
            y_offset += 40
        if data.get("show_name"):
            y_offset += 25

        item_rect = self.main.chat_list.visualItemRect(item)
        click_y = event.position().y() - item_rect.y()

        # Quote block cao 38px, bắt đầu tại y_offset+6
        if y_offset + 6 <= click_y <= y_offset + 44:
            reply_to = data["reply_to"]
            target_sender = reply_to.get("sender", "")
            target_content = reply_to.get("content", "")

            # Tìm tin gốc từ dưới lên
            for i in range(self.main.chat_list.count() - 1, -1, -1):
                other = self.main.chat_list.item(i)
                od = other.data(Qt.UserRole)
                if not od or not isinstance(od, dict) or od.get("type") != "text":
                    continue
                s = od.get("sender", "")
                # So sánh sender ("Tôi" ⟷ nickname)
                match_sender = (
                    s == target_sender
                    or (s == "Tôi" and target_sender == self.main.nickname)
                    or (s == self.main.nickname and target_sender == "Tôi")
                )
                if match_sender and od.get("content") == target_content:
                    self.main.chat_list.scrollToItem(other, QAbstractItemView.PositionAtCenter)
                    self.main.chat_list.setCurrentItem(other)
                    break
