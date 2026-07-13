#!/usr/bin/env python3
"""从源 PNG 生成 Windows ICO 和 macOS ICNS 图标资源。

Windows ICO 使用 PNG-in-ICO 格式（Vista+ 支持），手动嵌入每个尺寸的完整 PNG，
避免 Pillow Image.save(ICO, append_images=...) 实际只嵌入首图的坑。
"""
from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PNG = PROJECT_ROOT / "图标" / "MMY-SymLink-icon.png"
ASSETS_DIR = PROJECT_ROOT / "assets"

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def _load_source() -> Image.Image:
    if not SRC_PNG.exists():
        raise FileNotFoundError(f"找不到源图标：{SRC_PNG}")
    img = Image.open(SRC_PNG).convert("RGBA")
    w, h = img.size
    if w != h:
        # 非正方形则居中裁剪
        size = min(w, h)
        left = (w - size) // 2
        top = (h - size) // 2
        img = img.crop((left, top, left + size, top + size))
    return img


def _resize_for_size(img: Image.Image, size: int) -> Image.Image:
    """高质量缩放 + 轻量锐化，小尺寸图标更清晰。"""
    resized = img.resize((size, size), Image.LANCZOS)
    if size <= 64:
        # 小尺寸适度锐化，避免发糊
        resized = resized.filter(
            ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3)
        )
    return resized


def make_ico() -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out = ASSETS_DIR / "MMY-SymLink.ico"
    img = _load_source()

    png_datas: list[bytes] = []
    for size in ICO_SIZES:
        frame = _resize_for_size(img, size)
        buf = io.BytesIO()
        frame.save(buf, format="PNG", optimize=True)
        png_datas.append(buf.getvalue())

    count = len(ICO_SIZES)
    header = struct.pack("<HHH", 0, 1, count)
    dir_entries: list[bytes] = []
    data_offset = 6 + 16 * count

    for size, data in zip(ICO_SIZES, png_datas):
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        entry = struct.pack(
            "<BBBBHHII",
            width,       # 宽度；256 写 0
            height,      # 高度；256 写 0
            0,           # 颜色数
            0,           # 保留
            1,           # 颜色平面
            32,          # 每像素位数
            len(data),   # 图像数据大小
            data_offset, # 图像数据偏移
        )
        dir_entries.append(entry)
        data_offset += len(data)

    with open(out, "wb") as f:
        f.write(header)
        for entry in dir_entries:
            f.write(entry)
        for data in png_datas:
            f.write(data)

    print(f"[ico] 已生成 {out} ({count} sizes: {ICO_SIZES})")
    return out


def make_icns() -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out = ASSETS_DIR / "MMY-SymLink.icns"
    img = _load_source()

    frames: list[Image.Image] = []
    for size in ICNS_SIZES:
        frames.append(_resize_for_size(img, size))

    # Pillow 原生支持 ICNS 写入多帧
    frames[0].save(
        out,
        format="ICNS",
        append_images=frames[1:],
    )
    print(f"[icns] 已生成 {out} ({len(ICNS_SIZES)} sizes: {ICNS_SIZES})")
    return out


def main():
    make_ico()
    if sys.platform == "darwin":
        # ICNS 在 Windows 上保存可能失败，仅在 macOS 生成
        make_icns()
    else:
        print("[icns] 当前非 macOS，跳过 ICNS 生成（Mac 打包时在此平台运行即可）")


if __name__ == "__main__":
    main()
