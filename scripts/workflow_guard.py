#!/usr/bin/env python3
"""
工作流守卫模块 - 强制执行论文生成前的检查

规则：
1. 缺少模板时必须警告
2. 用户未确认大纲时必须等待
3. 用户未明确说"生成论文"时不执行
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class BlockerType(Enum):
    NO_BLOCKER = "no_blocker"
    MISSING_TEMPLATE = "missing_template"
    OUTLINE_NOT_CONFIRMED = "outline_not_confirmed"
    USER_DID_NOT_REQUEST_GENERATION = "user_did_not_request_generation"


@dataclass
class WorkflowCheckResult:
    can_proceed: bool
    blocker_type: BlockerType
    blocker_reason: str
    recommendations: list[str]
    

def check_template_exists() -> bool:
    """检查是否上传了学校模板"""
    # 检查常见模板文件位置
    template_paths = [
        Path("paper-context/templates/school-template.docx"),
        Path("paper-context/templates/school-template.pdf"),
        Path("thesis-ai-standard/templates/school-template.docx"),
        Path("uploads/").glob("*模板*.docx"),
        Path("uploads/").glob("*template*.docx"),
    ]
    
    for path in template_paths:
        if isinstance(path, Path):
            if path.exists():
                return True
        else:
            # glob 结果
            if list(path):
                return True
    
    # 检查是否明确标记为使用默认规范
    default_flag = Path("paper-context/workflow/use-default-style.confirmed")
    if default_flag.exists():
        return True
        
    return False


def check_outline_confirmed() -> bool:
    """检查用户是否已确认论文大纲"""
    # 检查大纲确认文件
    confirmed_flag = Path("paper-context/workflow/outline-confirmed-by-user.flag")
    if confirmed_flag.exists():
        return True
    
    # 检查 user-decisions.md 中是否有确认记录
    decisions_file = Path("paper-context/workflow/user-decisions.md")
    if decisions_file.exists():
        content = decisions_file.read_text(encoding="utf-8")
        if "大纲已确认" in content or "outline confirmed" in content.lower():
            return True
    
    # 检查 workflow-status.md 中的阶段
    status_file = Path("paper-context/workflow/workflow-status.md")
    if status_file.exists():
        content = status_file.read_text(encoding="utf-8")
        if "outline_confirmed" in content or "writing_allowed" in content:
            return True
    
    return False


def check_user_explicitly_requested_generation(user_request: Optional[str] = None) -> bool:
    """
    检查用户是否明确说了"生成论文"
    
    Args:
        user_request: 用户的原始请求文本
    """
    if user_request is None:
        # 从上下文或环境变量获取（需要调用方提供）
        return False
    
    # 明确的生成指令关键词
    generation_keywords = [
        "生成论文",
        "开始生成",
        "写论文",
        "生成docx",
        "生成完整论文",
        "produce thesis",
        "generate thesis",
        "generate the thesis",
        "start writing",
    ]
    
    request_lower = user_request.lower()
    for keyword in generation_keywords:
        if keyword.lower() in request_lower:
            return True
    
    return False


def workflow_guard(
    user_request: Optional[str] = None,
    force: bool = False
) -> WorkflowCheckResult:
    """
    工作流守卫 - 检查是否可以执行论文生成
    
    Args:
        user_request: 用户的原始请求文本
        force: 是否强制跳过检查（不推荐）
    
    Returns:
        WorkflowCheckResult 包含检查结果和建议
    """
    
    if force:
        return WorkflowCheckResult(
            can_proceed=True,
            blocker_type=BlockerType.NO_BLOCKER,
            blocker_reason="强制跳过检查",
            recommendations=["[WARN] 强制模式：跳过所有工作流检查"]
        )
    
    # 检查 1: 是否有模板
    has_template = check_template_exists()
    if not has_template:
        return WorkflowCheckResult(
            can_proceed=False,
            blocker_type=BlockerType.MISSING_TEMPLATE,
            blocker_reason="未找到学校论文模板",
            recommendations=[
                "[FILE] 请上传学校论文模板（.docx 或 .pdf）",
                "[WRITE] 或确认使用默认规范（创建 paper-context/workflow/use-default-style.confirmed）",
                "[WAIT] 当前阶段：等待模板上传"
            ]
        )
    
    # 检查 2: 大纲是否已确认
    outline_confirmed = check_outline_confirmed()
    if not outline_confirmed:
        return WorkflowCheckResult(
            can_proceed=False,
            blocker_type=BlockerType.OUTLINE_NOT_CONFIRMED,
            blocker_reason="论文大纲尚未经用户确认",
            recommendations=[
                "[LIST] 请查看并确认论文大纲结构",
                "[OK] 确认后创建标记文件：paper-context/workflow/outline-confirmed-by-user.flag",
                "[WAIT] 当前阶段：大纲确认"
            ]
        )
    
    # 检查 3: 用户是否明确说生成
    explicitly_requested = check_user_explicitly_requested_generation(user_request)
    if not explicitly_requested:
        return WorkflowCheckResult(
            can_proceed=False,
            blocker_type=BlockerType.USER_DID_NOT_REQUEST_GENERATION,
            blocker_reason="用户未明确请求生成论文",
            recommendations=[
                "[THINK] 您上传了材料，但未明确说'生成论文'",
                "[TIP] 请说'生成论文'或'开始写论文'以继续",
                "[LIST] 或先确认大纲结构是否符合预期",
                "[WAIT] 当前阶段：等待用户明确指令"
            ]
        )
    
    # 所有检查通过
    return WorkflowCheckResult(
        can_proceed=True,
        blocker_type=BlockerType.NO_BLOCKER,
        blocker_reason="",
        recommendations=["[PASS] 工作流检查通过，可以开始生成论文"]
    )


def print_guard_result(result: WorkflowCheckResult) -> None:
    """打印守卫检查结果"""
    print("=" * 60)
    print("工作流检查")
    print("=" * 60)
    
    if result.can_proceed:
        print("\n[OK] 检查通过")
        for rec in result.recommendations:
            print(f"   {rec}")
    else:
        print(f"\n[BLOCKED] 被阻止: {result.blocker_type.value}")
        print(f"\n原因: {result.blocker_reason}")
        print("\n建议操作:")
        for rec in result.recommendations:
            print(f"   {rec}")
    
    print("=" * 60)


def main():
    """命令行入口 - 用于测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description="工作流守卫检查")
    parser.add_argument("--user-request", help="用户的原始请求文本")
    parser.add_argument("--force", action="store_true", help="强制跳过检查")
    args = parser.parse_args()
    
    result = workflow_guard(
        user_request=args.user_request,
        force=args.force
    )
    
    print_guard_result(result)
    
    sys.exit(0 if result.can_proceed else 1)


if __name__ == "__main__":
    main()
