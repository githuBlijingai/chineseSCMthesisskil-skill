#!/usr/bin/env python3
"""
硬件证据自动构建脚本
在构建项目证据时自动检测并解析硬件设计文件

用法：
    python scripts/evidence/build_hardware_evidence.py [--project-path <路径>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 导入硬件解析器
from parse_hardware_files import parse_hardware_project, save_evidence


# 支持的硬件文件扩展名
HARDWARE_EXTENSIONS = {
    '.pcbdoc', '.prjpcb', '.brd', '.kicad_pcb',
    '.schdoc', '.sch', '.dsn', '.kicad_sch',
    '.csv', '.xlsx', '.xls', '.txt',
    '.gtl', '.gbl', '.gbs', '.gbo', '.drl'
}

# BOM文件关键词
BOM_KEYWORDS = ['bom', '物料', '器件', '元器件', 'parts', 'partslist']


def has_hardware_files(project_path: Path) -> bool:
    """检测项目目录是否包含硬件设计文件"""
    for f in project_path.rglob('*'):
        if not f.is_file():
            continue

        name_lower = f.name.lower()
        ext = f.suffix.lower()

        # 检查扩展名
        if ext in HARDWARE_EXTENSIONS:
            return True

        # 检查BOM关键词
        if any(kw in name_lower for kw in BOM_KEYWORDS):
            return True

    return False


def find_hardware_project_paths(project_path: Path) -> list[Path]:
    """查找可能的硬件设计项目子目录"""
    candidates = []

    # 常见硬件项目目录名
    hw_dirs = ['hardware', 'pcb', 'schematic', 'altium', 'kicad', 'hardware_design']

    # 检查当前目录
    if has_hardware_files(project_path):
        candidates.append(project_path)

    # 检查子目录
    for subdir in project_path.iterdir():
        if subdir.is_dir():
            subdir_name = subdir.name.lower()
            # 匹配常见目录名
            if any(hw_dir in subdir_name for hw_dir in hw_dirs):
                if has_hardware_files(subdir):
                    candidates.append(subdir)

    return candidates


def main():
    parser = argparse.ArgumentParser(
        description='自动检测并解析硬件设计项目证据'
    )
    parser.add_argument(
        '--project-path', '-p',
        default='.',
        help='项目根目录（默认: 当前目录）'
    )
    parser.add_argument(
        '--out', '-o',
        default='paper-context/evidence',
        help='输出目录（默认: paper-context/evidence）'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制解析，即使没有检测到硬件文件'
    )

    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    output_path = Path(args.out)

    print("=" * 60)
    print("硬件证据自动构建")
    print("=" * 60)
    print(f"项目路径: {project_path}")
    print(f"输出路径: {output_path}")

    # 检查项目是否存在
    if not project_path.exists():
        print(f"[ERROR] 项目目录不存在: {project_path}")
        sys.exit(1)

    # 查找硬件项目
    hw_paths = find_hardware_project_paths(project_path)

    if not hw_paths and not args.force:
        print("\n[INFO] 未检测到硬件设计文件")
        print("支持的格式:")
        print("  - PCB: .pcbdoc, .prjpcb, .kicad_pcb, .brd")
        print("  - 原理图: .schdoc, .sch, .dsn")
        print("  - BOM: .csv, .xlsx, .txt")
        print("  - Gerber: .gtl, .gbl, .drl")
        print("\n使用 --force 强制解析")
        return

    # 解析每个硬件项目
    for hw_path in hw_paths:
        print(f"\n[INFO] 发现硬件项目: {hw_path.relative_to(project_path.parent)}")

        evidence = parse_hardware_project(hw_path, output_path)

        # 保存证据
        # 输出到项目根目录下的 paper-context/evidence
        project_output = hw_path.parent / output_path
        save_evidence(evidence, project_output)

    print("\n" + "=" * 60)
    print("硬件证据构建完成!")
    print("=" * 60)
    print(f"\n查看证据:")
    print(f"  JSON: {output_path}/hardware-evidence.json")
    print(f"  Markdown: {output_path}/hardware-evidence.md")


if __name__ == "__main__":
    main()
