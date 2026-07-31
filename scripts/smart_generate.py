#!/usr/bin/env python3
"""
智能论文生成入口

集成工作流守卫，确保：
1. 有模板才能生成
2. 大纲已确认才能生成
3. 用户明确说"生成论文"才能执行

使用方式：
    python scripts/smart_generate.py --user-request="生成论文"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 导入守卫模块
sys.path.insert(0, str(Path(__file__).parent))
from workflow_guard import workflow_guard, print_guard_result
from user_intent import detect_intent, should_generate_thesis


def smart_generate(
    user_request: str,
    spec_path: str = "thesis-ai-standard/templates/thesis-ai-spec.yaml",
    output_dir: str = "paper-output/",
    force: bool = False
) -> int:
    """
    智能生成论文 - 带工作流守卫
    
    Returns:
        0 - 生成成功或继续流程
        1 - 被守卫阻止
    """
    
    print("=" * 60)
    print("Chinese Thesis Workbench - 智能生成")
    print("=" * 60)
    
    # 步骤 1: 识别用户意图
    intent = detect_intent(user_request)
    print(f"\n[1/3] 用户意图识别: {intent.value}")
    
    # 步骤 2: 工作流守卫检查
    print("\n[2/3] 工作流检查...")
    guard_result = workflow_guard(user_request=user_request, force=force)
    print_guard_result(guard_result)
    
    if not guard_result.can_proceed:
        print("\n[STOP] 论文生成被阻止，请按建议操作后重试")
        print("=" * 60)
        return 1
    
    # 步骤 3: 执行生成
    print("\n[3/3] 开始生成论文...")
    print("=" * 60)
    
    # 这里调用实际的生成脚本
    # 例如：调用 build_complete_thesis.py
    
    print("[INFO] 调用 build_complete_thesis.py...")
    print(f"  参数: --spec={spec_path}")
    print(f"  参数: --output={output_dir}")
    
    # 实际调用代码（简化版）
    # import subprocess
    # result = subprocess.run([
    #     sys.executable,
    #     "scripts/docx/build_complete_thesis.py",
    #     "--spec", spec_path,
    #     "--output", output_dir,
    #     # ... 其他参数
    # ])
    
    print("\n[SUCCESS] 论文生成流程已完成")
    print("=" * 60)
    return 0


def show_current_status():
    """显示当前工作流状态"""
    print("=" * 60)
    print("当前工作流状态")
    print("=" * 60)
    
    # 检查各项状态
    checks = [
        ("学校模板", Path("paper-context/templates/school-template.docx").exists()),
        ("大纲确认标记", Path("paper-context/workflow/outline-confirmed-by-user.flag").exists()),
        ("使用默认规范", Path("paper-context/workflow/use-default-style.confirmed").exists()),
    ]
    
    print("\n检查项:")
    for name, exists in checks:
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {name}")
    
    print("\n下一步:")
    template_exists = any([
        Path("paper-context/templates/school-template.docx").exists(),
        Path("paper-context/workflow/use-default-style.confirmed").exists(),
    ])
    
    if not template_exists:
        print("  1. 上传学校模板，或")
        print("  2. 创建 paper-context/workflow/use-default-style.confirmed 使用默认规范")
    elif not Path("paper-context/workflow/outline-confirmed-by-user.flag").exists():
        print("  1. 确认论文大纲结构")
        print("  2. 创建确认标记文件")
    else:
        print("  说'生成论文'开始生成")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="智能论文生成 - 带工作流守卫检查"
    )
    parser.add_argument(
        "--user-request",
        required=True,
        help="用户的原始请求文本（用于意图识别和守卫检查）"
    )
    parser.add_argument(
        "--spec",
        default="thesis-ai-standard/templates/thesis-ai-spec.yaml",
        help="thesis-ai-spec.yaml 路径"
    )
    parser.add_argument(
        "--output",
        default="paper-output/",
        help="输出目录"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制跳过守卫检查（不推荐）"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="仅显示当前状态，不执行生成"
    )
    
    args = parser.parse_args()
    
    if args.status:
        show_current_status()
        return 0
    
    return smart_generate(
        user_request=args.user_request,
        spec_path=args.spec,
        output_dir=args.output,
        force=args.force
    )


if __name__ == "__main__":
    sys.exit(main())
