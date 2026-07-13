<div align="center">

<img src="图标/MMY-SymLink-icon.png" width="128" alt="MMY-SymLink Logo">

# MMY-SymLink

**跨平台软链接（符号链接）图形化管理工具**

用拖拽的方式在 Windows 和 macOS 上创建、检测、删除软链接，无需记命令行。

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)]()
[![Python](https://img.shields.io/badge/python-3.9%2B-green)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6-orange)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

</div>

---

## 这是什么

很多工具（Blender 插件、`.claude` / `.codex` 规则文件、各类配置目录）要求文件放在**固定位置**才会被读取，但你真正的开发目录却在别处。软链接（symlink / junction）能把「被读取的位置」指向「实际文件所在」，让两边保持同步。

**MMY-SymLink** 把这件事变成一次拖拽：

```
[ 目标位置 TARGET ]  ──link points to──▶  [ 源目录 SOURCE ]
  软链接创建在这里                            真正的文件在这里
```

删除左侧的链接**只会删掉链接入口，不会动右侧的源文件**——数据安全是第一优先级。

## 功能特性

- 🖱 **拖拽创建** — 把文件夹/文件拖到两个框里，点一下就建好链接
- 🔍 **实时检测** — 拖入目标后自动显示：路径是否已是链接、指向哪里、最终链接会落在哪个路径
- 🛡 **数据保护** — 目标已存在真实文件夹时，可自动重命名为 `.bak`（带时间戳）再建链接，原数据保留
- 🔀 **智能类型** — 文件夹优先用 Junction（Windows 免管理员权限），文件用 symlink
- 📌 **预设快捷** — 内置 Blender addons、`.claude`、`.codex` 等常用目标位置 chip
- 🕐 **历史记录** — 最近 50 条操作可一键复用
- 🚀 **无黑窗启动** — Windows 下双击 `run_silent.vbs` 静默启动，不弹 cmd 窗口
- 📦 **单文件打包** — 一键打包成独立 exe / app，分发给无 Python 环境的用户

## 快速开始

### 方式一：下载打包好的可执行文件（推荐普通用户）

前往 [Releases](https://github.com/yuyeming0115/MMY-SymLink/releases) 下载对应平台的文件：

- **Windows**：下载 `MMY-SymLink.exe`，双击运行
- **macOS**：下载 `MMY-SymLink.app`，拖到「应用程序」后运行

### 方式二：从源码运行（推荐开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/yuyeming0115/MMY-SymLink.git
cd MMY-SymLink

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

**Windows 用户**也可以直接双击：

- `run_silent.vbs` — 无黑窗静默启动（推荐）
- `run.bat` — 带控制台启动，方便看日志

> 两个启动脚本都会自动清理被污染的 `PYTHONHOME`/`PYTHONPATH`、探测可用的 Python 解释器、缺少 PySide6 时自动安装。

## 使用说明

1. **拖入目标位置（左）** — 软链接将创建在这里，通常是被程序读取的固定位置
2. **拖入源目录（右）** — 你实际的开发目录/文件
3. **确认链接名称与类型** — 留空则用源同名，会自动识别文件夹/单文件
4. **点「创建软链接」** — 完成

删除链接：把链接路径拖入左侧，点「删除目标链接」。工具会校验它确实是链接才允许删除，避免误删真实文件。

## 权限说明（重要）

| 链接类型 | Windows 权限要求 | 说明 |
|---|---|---|
| 文件夹 Junction | ✅ 免管理员 | 默认优先使用，最省心 |
| 文件夹 symlink | ⚠ 需开发者模式或管理员 | Junction 失败时回退 |
| 文件 symlink | ⚠ 需开发者模式或管理员 | 文件无法用 Junction |

**创建文件软链接报 `WinError 1314`？** 这是权限不足。两种解决方式：

- **开启开发者模式**（推荐，一劳永逸）：`Win + I` → 隐私和安全性 → 开发者模式 → 打开
- **以管理员身份运行**本工具

> macOS / Linux 上 symlink 无需特殊权限，直接可用。

## 打包成可执行文件

项目内置跨平台一键打包脚本，产物按版本号隔离在 `dist/v{版本}/{平台}/`。

### Windows

```bat
:: 双击 build_win.bat，或命令行指定版本号
build_win.bat 1.0.0
```
输出：`dist/v1.0.0/Windows/MMY-SymLink.exe`

### macOS

```bash
chmod +x build_mac.sh
./build_mac.sh 1.0.0
```
输出：`dist/v1.0.0/macOS/MMY-SymLink.app`

> 打包脚本使用 PyInstaller，图标由 `scripts/build_assets.py` 从 `图标/MMY-SymLink-icon.png` 生成（Windows 手写 PNG-in-ICO 多尺寸，避免只嵌单一尺寸的问题）。

## 项目结构

```
MMY-SymLink/
├── main.py               # GUI 主程序（PySide6）
├── linker.py             # 跨平台软链接核心逻辑（创建/删除/检测/历史）
├── requirements.txt      # 依赖：PySide6
├── run_silent.vbs        # Windows 无黑窗启动器
├── run_silent.pyw        # 静默安装依赖 + 启动 GUI
├── run.bat               # 带控制台启动器
├── build_win.bat         # Windows 一键打包
├── build_mac.sh          # macOS 一键打包
├── build_mac.command     # macOS 双击打包
├── scripts/
│   ├── build.py          # 跨平台构建脚本
│   └── build_assets.py   # 图标 ICO/ICNS 生成
└── 图标/
    └── MMY-SymLink-icon.png
```

## 技术栈

- **Python 3.9+**
- **PySide6** — Qt for Python GUI 框架
- **PyInstaller** — 单文件打包

## License

[MIT](LICENSE) © yuyeming0115
