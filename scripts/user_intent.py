#!/usr/bin/env python3
"""
用户意图识别模块

用于判断用户的请求属于哪个阶段：
- intake: 上传材料阶段
- outline_review: 大纲确认阶段
- generate_request: 明确请求生成论文
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class IntentType(Enum):
    UPLOAD_MATERIALS = "upload_materials"      # 上传材料
    ASK_OUTLINE = "ask_outline"                # 询问大纲
    CONFIRM_OUTLINE = "confirm_outline"        # 确认大纲
    REQUEST_GENERATE = "request_generate"      # 明确请求生成
    REQUEST_REVISE = "request_revise"          # 请求修改
    GENERAL_CHAT = "general_chat"              # 一般聊天


def detect_intent(user_input: str) -> IntentType:
    """
    识别用户意图
    
    Args:
        user_input: 用户输入的文本
    
    Returns:
        IntentType 意图类型
    """
    input_lower = user_input.lower().strip()
    
    # 明确生成论文的指令（最高优先级）
    generate_keywords = [
        "生成论文", "开始生成", "写论文", "写吧", "开始写",
        "生成docx", "生成完整论文", "生成全文",
        "produce thesis", "generate thesis", "generate the thesis",
        "start writing", "write the thesis", "create docx",
    ]
    for kw in generate_keywords:
        if kw in input_lower:
            return IntentType.REQUEST_GENERATE
    
    # 确认大纲
    confirm_keywords = [
        "确认大纲", "大纲可以", "大纲没问题", "就这样写",
        "开始写", "开始撰写", "开始编写", "可以开始",
        "outline confirmed", "confirm outline", "looks good",
    ]
    for kw in confirm_keywords:
        if kw in input_lower:
            return IntentType.CONFIRM_OUTLINE
    
    # 询问大纲
    outline_keywords = [
        "大纲", "结构", "章节", "怎么写", "如何组织",
        "outline", "structure", "chapters",
    ]
    for kw in outline_keywords:
        if kw in input_lower:
            return IntentType.ASK_OUTLINE
    
    # 上传材料（文件上传通常有特定格式）
    upload_keywords = [
        "上传", "给你", "这是", "看一下", "分析一下",
        "upload", "here is", "attached", "文件",
    ]
    for kw in upload_keywords:
        if kw in input_lower:
            return IntentType.UPLOAD_MATERIALS
    
    # 修改请求
    revise_keywords = [
        "修改", "调整", "重写", "改一下", "不对",
        "revise", "change", "modify", "update",
    ]
    for kw in revise_keywords:
        if kw in input_lower:
            return IntentType.REQUEST_REVISE
    
    # 默认为一般聊天
    return IntentType.GENERAL_CHAT


def should_generate_thesis(user_input: str, current_phase: Optional[str] = None) -> tuple[bool, str]:
    """
    判断是否应该生成论文
    
    Returns:
        (should_generate, reason)
    """
    intent = detect_intent(user_input)
    
    if intent == IntentType.REQUEST_GENERATE:
        return True, "用户明确请求生成论文"
    
    if intent == IntentType.CONFIRM_OUTLINE and current_phase == "outline_confirmed":
        return True, "用户确认了大纲且阶段已就绪"
    
    # 其他情况都不应该生成
    reason_map = {
        IntentType.UPLOAD_MATERIALS: "用户正在上传材料，未请求生成",
        IntentType.ASK_OUTLINE: "用户询问大纲，未确认",
        IntentType.CONFIRM_OUTLINE: "用户确认大纲，但需要等待明确生成指令",
        IntentType.REQUEST_REVISE: "用户请求修改，不是生成",
        IntentType.GENERAL_CHAT: "用户未明确请求生成论文",
    }
    
    return False, reason_map.get(intent, "未识别到生成指令")


# 预定义的阶段检查
PHASE_REQUIREMENTS = {
    "intake_only": {
        "can_generate": False,
        "needs": ["模板", "大纲确认", "生成指令"]
    },
    "evidence_built": {
        "can_generate": False,
        "needs": ["模板", "大纲确认", "生成指令"]
    },
    "outline_confirmed": {
        "can_generate": False,
        "needs": ["模板", "生成指令"],
        "note": "大纲已确认，等待生成指令"
    },
    "writing_allowed": {
        "can_generate": True,
        "needs": [],
        "note": "可以生成论文"
    },
}


def check_phase_requirements(current_phase: str, user_input: str) -> dict:
    """
    检查当前阶段是否满足生成要求
    
    Returns:
        {
            "can_proceed": bool,
            "missing": list[str],
            "message": str
        }
    """
    phase_info = PHASE_REQUIREMENTS.get(current_phase, {
        "can_generate": False,
        "needs": ["未知阶段，需要确认工作流状态"]
    })
    
    result = {
        "can_proceed": False,
        "missing": [],
        "message": ""
    }
    
    # 检查阶段本身是否允许
    if not phase_info["can_generate"]:
        result["missing"] = phase_info["needs"]
        result["message"] = f"当前阶段 '{current_phase}' 不满足生成条件"
        return result
    
    # 检查用户意图
    should_gen, reason = should_generate_thesis(user_input, current_phase)
    if not should_gen:
        result["missing"] = ["明确的生成指令"]
        result["message"] = reason
        return result
    
    # 全部通过
    result["can_proceed"] = True
    result["message"] = "满足所有生成条件"
    return result


if __name__ == "__main__":
    # 测试
    test_inputs = [
        "这是我的源码和开题报告",
        "生成论文",
        "大纲是什么样的",
        "确认大纲，开始写吧",
        "请修改第一章",
        "你好",
    ]
    
    print("用户意图识别测试:")
    print("=" * 50)
    for text in test_inputs:
        intent = detect_intent(text)
        should_gen, reason = should_generate_thesis(text)
        print(f"\n输入: {text}")
        print(f"  意图: {intent.value}")
        print(f"  是否生成: {should_gen} ({reason})")
