#!/bin/bash
# 一键打包 MMY-SymLink for macOS
# 用法：双击或在终端运行 ./build_mac.sh [版本号]

set -e

VERSION="1.0.0"
if [ -n "$1" ]; then
    VERSION="$1"
fi

cd "$(dirname "$0")"

echo "[build] 开始打包 MMY-SymLink v${VERSION} ..."
python3 scripts/build.py --platform mac --version "${VERSION}"

echo "[build] 打包完成，产物在 dist/v${VERSION}/macOS/ 目录。"
