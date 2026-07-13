"""MMY-SymLink GUI 主程序。

布局（与原型一致）：
    顶部  ─ 标题 + 权限徽章
    提示  ─ 一句话说明左右关系
    主区  ─ [目标 TARGET 拖拽框]  ─link points to→  [源 SOURCE 拖拽框]
    行2   ─ 链接名称 + 类型(文件夹/单文件)
    行3   ─ [交换] [创建软链接] [删除已有链接]
    检测  ─ 拖入目标后自动显示该位置是否已是链接、指向哪里
    历史  ─ 最近 50 条
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QRadioButton, QButtonGroup, QFrame,
    QFileDialog, QScrollArea, QMessageBox, QSizePolicy, QToolButton,
)

import linker


# --------------------------------------------------------------------------- #
# DropZone：可拖拽的区域，含内置预设 chip
# --------------------------------------------------------------------------- #
class DropZone(QFrame):
    """一个拖拽区域。

    role: "target" | "source"
    color_brand: 品牌色 hex（左紫右青）
    """
    pathChanged = Signal(str)

    def __init__(self, role: str, title: str, subtitle: str, role_tag: str,
                 brand_color: str, soft_bg: str, text_color: str, parent=None):
        super().__init__(parent)
        self.role = role
        self.brand_color = brand_color
        self.setAcceptDrops(True)
        self.setObjectName(f"zone-{role}")
        self.setStyleSheet(self._stylesheet(brand_color, soft_bg))

        self._path: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        # 标题行
        head = QHBoxLayout()
        head.setSpacing(8)
        name = QLabel(title)
        name.setObjectName("zoneName")
        name.setStyleSheet(f"color: {text_color}; font-weight: 600; font-size: 15px;")
        head.addWidget(name)
        head.addStretch()
        tag = QLabel(role_tag)
        tag.setObjectName("zoneTag")
        tag.setStyleSheet(
            f"color: #6b7280; border: 1px solid rgba(0,0,0,0.12); "
            f"background: #fff; padding: 2px 10px; border-radius: 999px; font-size: 11px;"
        )
        head.addWidget(tag)
        root.addLayout(head)

        # 副标题
        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #6b7280; font-size: 12px;")
        root.addWidget(sub)

        # 预设 chip 行（内置在拖拽框内）
        self.chip_row = QHBoxLayout()
        self.chip_row.setSpacing(6)
        self.chip_row.addWidget(QLabel("快速填入:"))
        self.chip_row.addStretch()
        root.addLayout(self.chip_row)

        # 路径显示
        self.path_label = QLabel("（未选择）")
        self.path_label.setObjectName("pathLabel")
        self.path_label.setWordWrap(False)
        self.path_label.setStyleSheet(
            f"font-family: Consolas, 'JetBrains Mono', monospace; font-size: 12px; "
            f"color: #171717; background: #fff; border: 1px solid rgba(0,0,0,0.12); "
            f"border-radius: 6px; padding: 8px 10px;"
        )
        self.path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.path_label.setMinimumHeight(32)
        root.addWidget(self.path_label)

        # 拖拽提示
        self.drop_hint = QLabel("📂 拖拽文件夹 / 文件至此")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet(
            f"color: #6b7280; font-size: 13px; "
            f"border: 1.5px dashed rgba(0,0,0,0.18); border-radius: 8px; "
            f"padding: 14px; background: rgba(255,255,255,0.6);"
        )
        self.drop_hint.setMinimumHeight(60)
        root.addWidget(self.drop_hint)

        # 浏览按钮
        bot = QHBoxLayout()
        bot.addStretch()
        self.btn_browse = QPushButton("浏览…")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setStyleSheet(
            f"color: #6b7280; border: 1px solid rgba(0,0,0,0.12); "
            f"background: #fff; padding: 4px 12px; border-radius: 6px; font-size: 12px;"
        )
        self.btn_browse.clicked.connect(self._on_browse)
        bot.addWidget(self.btn_browse)
        root.addLayout(bot)

        root.addStretch()

    @staticmethod
    def _stylesheet(brand: str, soft_bg: str) -> str:
        return f"""
        #zone-target, #zone-source {{
            border: 1.5px solid {brand};
            background: {soft_bg};
            border-radius: 12px;
        }}
        """

    # ---- 拖拽 ----
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.drop_hint.setStyleSheet(
                "color: #fff; font-size: 13px; "
                "border: 1.5px dashed #4B3FE3; border-radius: 8px; "
                "padding: 14px; background: #4B3FE3;"
            )
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._reset_hint()

    def dropEvent(self, e: QDropEvent):
        self._reset_hint()
        urls = e.mimeData().urls()
        if not urls:
            return
        local = urls[0].toLocalFile()
        if local:
            self.set_path(local)

    def _reset_hint(self):
        self.drop_hint.setStyleSheet(
            "color: #6b7280; font-size: 13px; "
            "border: 1.5px dashed rgba(0,0,0,0.18); border-radius: 8px; "
            "padding: 14px; background: rgba(255,255,255,0.6);"
        )

    # ---- 路径 ----
    def set_path(self, p: str):
        self._path = p
        # 路径太长用省略号前缀
        display = p if len(p) <= 72 else "…" + p[-71:]
        self.path_label.setText(display)
        self.path_label.setToolTip(p)
        self.pathChanged.emit(p)

    def path(self) -> str:
        return self._path

    def _on_browse(self):
        caption = "选择文件夹" if self.role == "target" else "选择源文件夹"
        # 同时支持文件夹与单文件（AGENTS.md 等场景）
        # 优先选目录；提供 "选文件" 备用按钮在主窗口里
        chosen = QFileDialog.getExistingDirectory(self, caption, str(Path.home()))
        if chosen:
            self.set_path(chosen)

    def add_preset_chip(self, name: str, path: str):
        btn = QToolButton()
        btn.setText(f"+ {name}")
        btn.setToolTip(path)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"color: #1A1759; background: #E5EAFF; border: 1px solid #A9AEFF; "
            f"padding: 3px 10px; border-radius: 999px; font-size: 12px;"
        )
        btn.clicked.connect(lambda: self.set_path(path))
        # 插在 "快速填入:" 之后、stretch 之前
        self.chip_row.insertWidget(self.chip_row.count() - 1, btn)


# --------------------------------------------------------------------------- #
# Arrow：中间的链接指向箭头
# --------------------------------------------------------------------------- #
class ArrowWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        # 用 QLabel + SVG 画箭头
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 40' "
            "preserveAspectRatio='none'>"
            "<defs><marker id='a' viewBox='0 0 8 8' refX='7' refY='4' "
            "markerWidth='8' markerHeight='8' markerUnits='userSpaceOnUse' orient='auto'>"
            "<path d='M1 1 L7 4 L1 7 Z' fill='#4B3FE3'/></marker></defs>"
            "<path d='M6 20 L72 20' stroke='#4B3FE3' stroke-width='2' "
            "stroke-linecap='round' fill='none' marker-end='url(#a)'/></svg>"
        )
        img = QLabel()
        img.setText(svg)
        img.setTextFormat(Qt.RichText)
        img.setFixedHeight(40)
        lay.addWidget(img, alignment=Qt.AlignCenter)
        lbl = QLabel("link\npoints to")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #4B3FE3; font-size: 11px; font-weight: 500;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        lay.addStretch()


# --------------------------------------------------------------------------- #
# 主窗口
# --------------------------------------------------------------------------- #
BRAND = "#4B3FE3"
BRAND_SOFT = "#F2F7FF"
ACCENT = "#27D2BF"
ACCENT_SOFT = "#EAFBF8"
ACCENT_TEXT = "#0F766E"
BRAND_TEXT = "#1A1759"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MMY-SymLink · 软链接管理工具")
        self.resize(980, 720)
        self.setMinimumSize(860, 640)

        self._build_ui()
        self._refresh_history()
        self._refresh_permission_badge()

    # ----------------- UI -----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # 顶栏
        top = QHBoxLayout()
        title = QLabel("🔗 MMY-SymLink · 软链接管理工具")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #171717;")
        top.addWidget(title)
        top.addStretch()
        self.lbl_perm = QLabel("权限检测中…")
        self.lbl_perm.setStyleSheet(
            "color: #EFAA17; border: 1px solid #EFAA17; background: #fff; "
            "padding: 2px 10px; border-radius: 999px; font-size: 12px;"
        )
        top.addWidget(self.lbl_perm)
        root.addLayout(top)

        # 一句话提示
        hint = QLabel(
            "把文件夹拖到下面两个框里。<b style='color:#4B3FE3'>左侧</b>是「软链接创建的位置」，"
            "<b style='color:#0F766E'>右侧</b>是「实际文件所在」。箭头表示 <b>链接指向</b>。"
            "删除左侧只会删链接，不会动右侧源文件。"
        )
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.RichText)
        hint.setStyleSheet("color: #52525B; font-size: 12px; background: #F7F7F8; "
                           "border: 1px solid rgba(0,0,0,0.08); border-radius: 8px; padding: 10px 12px;")
        root.addWidget(hint)

        # 拖拽框 + 箭头
        pair = QHBoxLayout()
        pair.setSpacing(8)

        self.zone_target = DropZone(
            role="target",
            title="目标位置 TARGET",
            subtitle="软链接将在此生成 · 一般是被读取的位置（Blender addons / .claude 等）",
            role_tag="左 · 创建于此",
            brand_color=BRAND,
            soft_bg=BRAND_SOFT,
            text_color=BRAND_TEXT,
        )
        self.zone_target.pathChanged.connect(self._on_target_changed)
        pair.addWidget(self.zone_target, stretch=1)

        pair.addWidget(ArrowWidget())

        self.zone_source = DropZone(
            role="source",
            title="源目录 SOURCE",
            subtitle="真正的文件存放处 · 你的开发目录 / 被 sync 的规则文件",
            role_tag="右 · 实际文件",
            brand_color=ACCENT,
            soft_bg=ACCENT_SOFT,
            text_color=ACCENT_TEXT,
        )
        self.zone_source.pathChanged.connect(self._on_source_changed)
        pair.addWidget(self.zone_source, stretch=1)
        root.addLayout(pair)

        # 检测区
        self.inspect_box = QLabel("拖入「目标位置」后将自动检测该路径当前是否已是软链接…")
        self.inspect_box.setWordWrap(True)
        self.inspect_box.setTextFormat(Qt.RichText)
        self.inspect_box.setStyleSheet(
            "color: #52525B; font-size: 12px; background: #F7F7F8; "
            "border: 1px solid rgba(0,0,0,0.08); border-left: 3px solid #4B3FE3; "
            "border-radius: 6px; padding: 10px 12px;"
        )
        root.addWidget(self.inspect_box)

        # 链接名称 + 类型
        row_link = QHBoxLayout()
        row_link.setSpacing(10)
        row_link.addWidget(QLabel("链接名称:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("留空则使用源文件夹同名")
        self.edit_name.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 13px; padding: 5px 8px; "
            "border: 1px solid rgba(0,0,0,0.15); border-radius: 6px; background: #fff;"
        )
        self.edit_name.setMinimumWidth(220)
        self.edit_name.textChanged.connect(self._on_name_changed)
        row_link.addWidget(self.edit_name, stretch=1)
        row_link.addSpacing(16)
        row_link.addWidget(QLabel("类型:"))
        self.rb_folder = QRadioButton("文件夹")
        self.rb_file = QRadioButton("单文件")
        self.rb_folder.setChecked(True)
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.rb_folder)
        self.type_group.addButton(self.rb_file)
        row_link.addWidget(self.rb_folder)
        row_link.addWidget(self.rb_file)
        row_link.addStretch()
        root.addLayout(row_link)

        # 操作按钮
        acts = QHBoxLayout()
        acts.setSpacing(10)
        self.btn_swap = QPushButton("🔄 交换左右")
        self.btn_swap.setCursor(Qt.PointingHandCursor)
        self.btn_swap.clicked.connect(self._on_swap)
        self.btn_create = QPushButton("✓ 创建软链接")
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setStyleSheet(
            f"background: {BRAND}; color: #fff; border: none; "
            f"padding: 8px 22px; border-radius: 8px; font-size: 14px; font-weight: 500;"
        )
        self.btn_create.clicked.connect(self._on_create)
        self.btn_delete = QPushButton("🗑 删除目标链接")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._on_delete)
        for b in (self.btn_swap, self.btn_delete):
            b.setStyleSheet(
                "color: #52525B; border: 1px solid rgba(0,0,0,0.15); background: #fff; "
                "padding: 8px 18px; border-radius: 8px; font-size: 13px;"
            )
        acts.addStretch()
        acts.addWidget(self.btn_swap)
        acts.addWidget(self.btn_create)
        acts.addWidget(self.btn_delete)
        acts.addStretch()
        root.addLayout(acts)

        # 源文件选择（备用，用于 AGENTS.md 这种单文件场景）
        file_row = QHBoxLayout()
        self.btn_pick_file = QPushButton("📁 改为选取单文件（源）")
        self.btn_pick_file.setCursor(Qt.PointingHandCursor)
        self.btn_pick_file.setStyleSheet(
            "color: #6b7280; border: 1px dashed rgba(0,0,0,0.2); background: transparent; "
            "padding: 4px 10px; border-radius: 6px; font-size: 12px;"
        )
        self.btn_pick_file.clicked.connect(self._on_pick_source_file)
        file_row.addWidget(self.btn_pick_file)
        file_row.addStretch()
        root.addLayout(file_row)

        # 历史
        hist_label = QLabel("历史记录")
        hist_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #171717;")
        root.addWidget(hist_label)

        self.hist_container = QWidget()
        self.hist_layout = QVBoxLayout(self.hist_container)
        self.hist_layout.setContentsMargins(0, 0, 0, 0)
        self.hist_layout.setSpacing(4)
        self.hist_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self.hist_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(180)
        root.addWidget(scroll)

        # 加载预设到拖拽框内
        self._load_presets_into_zones()

    def _load_presets_into_zones(self):
        presets = linker.load_presets()
        for name, path in presets:
            # chip 加到「目标」框（这些预设通常作为被读取的目标位置）
            self.zone_target.add_preset_chip(name, path)

    # ----------------- 事件 -----------------
    def _on_target_changed(self, p: str):
        self._inspect_target(p)

    def _on_source_changed(self, p: str):
        # 若用户拖入的是文件，自动切到「单文件」
        if p and Path(p).is_file():
            self.rb_file.setChecked(True)
        elif p and Path(p).is_dir():
            self.rb_folder.setChecked(True)
        # 源变化后，最终链接路径可能改变，刷新检测
        self._inspect_target(self.zone_target.path())

    def _on_name_changed(self, _=None):
        self._inspect_target(self.zone_target.path())

    def _compute_final_target(self) -> Path | None:
        """根据当前 target / source / name 计算最终链接创建位置。"""
        src = self.zone_source.path()
        tgt = self.zone_target.path()
        if not src or not tgt:
            return None
        try:
            return self._resolve_final_target(Path(tgt), Path(src), self.edit_name.text().strip())
        except Exception:
            return None

    def _inspect_target(self, p: str):
        final = self._compute_final_target()
        final_html = (
            f"<br><b>最终链接路径</b>：<code>{final}</code>"
            if final else ""
        )

        if not p:
            self.inspect_box.setText(
                f"拖入「目标位置」后将自动检测该路径当前是否已是软链接…{final_html}"
            )
            self.inspect_box.setStyleSheet(
                "color: #52525B; font-size: 12px; background: #F7F7F8; "
                "border: 1px solid rgba(0,0,0,0.08); border-left: 3px solid #4B3FE3; "
                "border-radius: 6px; padding: 10px 12px;"
            )
            return

        # 检测以最终链接路径为准；若 final 还没算出来，退回到当前 target
        inspect_path = final if final else Path(p)
        info = linker.inspect_link(inspect_path)

        text = f"<b>当前目标</b>：<code>{p}</code>{final_html}"
        if final and str(final) != p:
            text += f"<br><b>将检测</b>：<code>{inspect_path}</code>"

        if not info.exists:
            text += f"<br>状态：路径不存在 → 可直接创建链接。"
            color = "#4B3FE3"
        elif info.is_link:
            text += (f"<br>⚠ 已是 <b>{info.kind}</b>，指向 <code>{info.target}</code><br>"
                     f"如要重建请先点「删除目标链接」。")
            color = "#EFAA17"
        else:
            if inspect_path.is_dir():
                text += (f"<br>⚠ 路径已存在为<b>真实文件夹</b>。<br>"
                         f"点击「创建软链接」时可选择重命名为 <code>.bak</code> 并创建链接，原数据会被保留。")
            else:
                text += (f"<br>⚠ 路径已存在为<b>真实文件</b>。"
                         f"为保护数据，请手动删除或重命名后再创建。")
            color = "#E8463A"
        self.inspect_box.setText(text)
        self.inspect_box.setStyleSheet(
            f"color: #52525B; font-size: 12px; background: #F7F7F8; "
            f"border: 1px solid rgba(0,0,0,0.08); border-left: 3px solid {color}; "
            f"border-radius: 6px; padding: 10px 12px;"
        )

    def _on_swap(self):
        t = self.zone_target.path()
        s = self.zone_source.path()
        self.zone_target.set_path(s)
        self.zone_source.set_path(t)

    def _on_pick_source_file(self):
        chosen, _ = QFileDialog.getOpenFileName(self, "选取源文件（单文件链接）", str(Path.home()))
        if chosen:
            self.zone_source.set_path(chosen)
            self.rb_file.setChecked(True)

    def _on_create(self):
        src = self.zone_source.path()
        tgt = self.zone_target.path()
        if not src or not tgt:
            QMessageBox.warning(self, "缺少路径", "请把两侧文件夹/文件都填上（可拖拽或点 chip）。")
            return

        src_p = Path(src)
        tgt_p = Path(tgt)

        if not src_p.exists():
            QMessageBox.warning(self, "源不存在", f"源路径不存在：\n{src_p}")
            return

        # 自动修正单文件/文件夹模式
        is_file_mode = self.rb_file.isChecked() or src_p.is_file()
        if is_file_mode and src_p.is_dir():
            QMessageBox.warning(self, "类型不匹配", "选了「单文件」但源是文件夹，请改选「文件夹」。")
            return

        name = self.edit_name.text().strip()
        final = self._resolve_final_target(tgt_p, src_p, name)

        if final.resolve() == src_p.resolve():
            QMessageBox.warning(self, "路径冲突", "源路径和目标链接路径不能是同一个位置。")
            return

        info = linker.inspect_link(final)
        if info.is_link:
            QMessageBox.warning(
                self, "目标已是链接",
                f"目标路径已经是 {info.kind}，指向：\n{info.target}\n\n"
                f"如需重建，请先点「删除目标链接」。"
            )
            return

        if info.exists:
            if final.is_dir():
                backup_name = linker._find_backup_name(final).name
                reply = QMessageBox.question(
                    self, "目标已存在",
                    f"目标位置已存在真实文件夹：\n{final}\n\n"
                    f"是否将其重命名为「{backup_name}」并创建软链接？\n"
                    f"（原文件夹数据会被保留，不会丢失）",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply != QMessageBox.Yes:
                    return
                r = linker.create_link_with_backup(final, src_p, prefer="symlink" if is_file_mode else "auto")
            else:
                QMessageBox.warning(
                    self, "目标已存在",
                    f"目标位置已存在文件：\n{final}\n"
                    f"为保护数据，拒绝覆盖。请手动删除或重命名后重试。"
                )
                return
        else:
            prefer = "symlink" if is_file_mode else "auto"
            r = linker.create_link(final, src_p, prefer=prefer)

        # 写历史
        linker.append_history(linker.HistoryItem(
            source=str(src_p),
            target=str(final),
            kind=r.method or ("symlink" if is_file_mode else "auto"),
            link_type="file" if is_file_mode else "folder",
            created_at=linker.now_str(),
            ok=r.ok,
            note=r.msg,
        ))
        self._refresh_history()

        if r.ok:
            QMessageBox.information(self, "成功", r.msg)
            self._inspect_target(str(final))
        else:
            QMessageBox.critical(self, "失败", r.msg)

    def _resolve_final_target(self, tgt_p: Path, src_p: Path, name: str) -> Path:
        """根据用户填写的 target、源文件名和 link name，推断最终链接应创建在哪里。"""
        if tgt_p.is_dir():
            if name:
                return tgt_p / name
            # 目标是一个真实文件夹，且名字和源相同：把它当成“最终链接路径”
            # 这样用户可以直接拖拽 Blender addons 里已有的同名文件夹到「目标」
            if tgt_p.name == src_p.name:
                return tgt_p
            return tgt_p / src_p.name

        # target 是非存在的完整路径或文件路径
        if name:
            return tgt_p.parent / name
        return tgt_p

    def _on_delete(self):
        tgt = self.zone_target.path()
        if not tgt:
            QMessageBox.warning(self, "缺少路径", "请先在「目标位置」填入或拖入要删除的链接路径。")
            return
        tgt_p = Path(tgt)
        info = linker.inspect_link(tgt_p)
        if not info.is_link:
            QMessageBox.warning(self, "无法删除",
                                f"该路径不是软链接（类型：{info.kind}），为保护源文件已拒绝删除。")
            return
        confirm = QMessageBox.question(
            self, "确认删除",
            f"将删除此链接（不会动源文件）：\n  {tgt_p}\n指向：{info.target}\n\n确认继续？",
        )
        if confirm != QMessageBox.Yes:
            return
        r = linker.delete_link(tgt_p)
        if r.ok:
            QMessageBox.information(self, "已删除", r.msg)
            self._inspect_target(str(tgt_p))
        else:
            QMessageBox.critical(self, "删除失败", r.msg)

    # ----------------- 历史 / 权限 -----------------
    def _refresh_history(self):
        # 清空
        while self.hist_layout.count() > 1:
            item = self.hist_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        items = linker.load_history()
        if not items:
            empty = QLabel("（暂无历史）")
            empty.setStyleSheet("color: #9ca3af; font-size: 12px;")
            self.hist_layout.insertWidget(0, empty)
            return
        for it in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            icon = QLabel("✓" if it.ok else "✗")
            icon.setStyleSheet(f"color: {'#1DC981' if it.ok else '#E8463A'}; font-size: 13px;")
            row.addWidget(icon)
            txt = QLabel(
                f"<code style='color:#171717;'>{it.source}</code>"
                f" <span style='color:#4B3FE3;'>→</span> "
                f"<code style='color:#171717;'>{it.target}</code>"
                f"  <span style='color:#6b7280;'>[{it.kind}/{it.link_type}]</span>"
                f"  <span style='color:#9ca3af;'>{it.created_at}</span>"
            )
            txt.setTextFormat(Qt.RichText)
            txt.setWordWrap(False)
            txt.setToolTip(it.note)
            row.addWidget(txt, stretch=1)
            # 复用按钮
            reuse = QPushButton("复用")
            reuse.setCursor(Qt.PointingHandCursor)
            reuse.setStyleSheet(
                "color: #4B3FE3; border: 1px solid #A9AEFF; background: #fff; "
                "padding: 2px 8px; border-radius: 6px; font-size: 11px;"
            )
            reuse.clicked.connect(lambda _=False, s=it.source, t=it.target:
                                  (self.zone_source.set_path(s), self.zone_target.set_path(t)))
            row.addWidget(reuse)

            wrap = QWidget()
            wrap.setLayout(row)
            wrap.setStyleSheet(
                "border-bottom: 1px solid rgba(0,0,0,0.06); padding: 2px 0;"
            )
            self.hist_layout.insertWidget(self.hist_layout.count() - 1, wrap)

    def _refresh_permission_badge(self):
        if sys.platform != "win32":
            self.lbl_perm.setText("✓ Unix: symlink 可直接用")
            self.lbl_perm.setStyleSheet(
                "color: #1DC981; border: 1px solid #1DC981; background: #fff; "
                "padding: 2px 10px; border-radius: 999px; font-size: 12px;"
            )
            return
        if linker.can_create_symlink_without_admin():
            self.lbl_perm.setText("✓ 可建 symlink（开发者模式或管理员）")
            self.lbl_perm.setStyleSheet(
                "color: #1DC981; border: 1px solid #1DC981; background: #fff; "
                "padding: 2px 10px; border-radius: 999px; font-size: 12px;"
            )
        else:
            self.lbl_perm.setText(
                "⚠ symlink 需管理员/开发者模式；文件夹将优先用 Junction（免权限）"
            )
            self.lbl_perm.setStyleSheet(
                "color: #EFAA17; border: 1px solid #EFAA17; background: #fff; "
                "padding: 2px 10px; border-radius: 999px; font-size: 12px;"
            )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MMY-SymLink")
    # 全局字体
    f = app.font()
    f.setFamily("Microsoft YaHei UI")
    f.setPointSize(9)
    app.setFont(f)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
