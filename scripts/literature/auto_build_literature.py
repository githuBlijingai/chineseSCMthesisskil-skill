#!/usr/bin/env python3
"""
自动文献构建入口

在 build_evidence 阶段后自动调用，智能判断是否启用 CNKI 检索：
1. 如果用户提供了开题报告/任务书且有足够参考文献，优先使用
2. 如果没有提供参考文献或文献数量不足，自动启用 CNKI 检索
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from .build_cnki_pool import build_cnki_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto_build_literature")

# 默认最小参考文献数量阈值（论文要求25篇参考文献）
DEFAULT_MIN_REFERENCE_THRESHOLD = 25

# 开题报告已有文献的最小数量（≥此数量时可跳过CNKI）
MIN_PROPOSAL_REFERENCES_THRESHOLD = 5


def load_spec(spec_path: Path) -> dict:
    """加载 thesis-ai-spec.yaml"""
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_existing_references(output_dir: Path) -> tuple[int, list]:
    """
    检查是否已有用户提供的参考文献
    
    Returns:
        (文献数量, 文献列表)
    """
    ref_json = output_dir / "reference-extraction.json"
    
    if not ref_json.exists():
        logger.info("No reference-extraction.json found.")
        return 0, []
    
    try:
        with open(ref_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 支持两种格式：列表或字典
        if isinstance(data, list):
            references = data
        elif isinstance(data, dict):
            # 尝试从字典中提取参考文献列表
            references = data.get("references", [])
            if not references and "papers" in data:
                references = data.get("papers", [])
        else:
            references = []
        
        count = len(references)
        logger.info(f"Found {count} references from user-provided documents.")
        return count, references
        
    except Exception as e:
        logger.warning(f"Failed to parse reference-extraction.json: {e}")
        return 0, []


def check_proposal_pdf(work_dir: Path) -> bool:
    """
    检查用户是否上传了开题报告/任务书PDF
    
    Returns:
        是否找到PDF文件
    """
    # 常见开题报告/任务书文件名模式
    pdf_patterns = [
        "*开题报告*.pdf",
        "*任务书*.pdf",
        "*proposal*.pdf",
        "*task*.pdf",
        "*选题*.pdf",
    ]
    
    # 检查 papers/ 目录
    papers_dir = work_dir / "papers"
    if papers_dir.exists():
        for pattern in pdf_patterns:
            if list(papers_dir.glob(pattern)):
                logger.info(f"Found proposal PDF in papers/ directory.")
                return True
    
    # 检查根目录
    for pattern in pdf_patterns:
        if list(work_dir.glob(pattern)):
            logger.info(f"Found proposal PDF in workspace root.")
            return True
    
    return False


def should_use_cnki(
    spec: dict,
    reference_count: int,
    has_proposal_pdf: bool,
    output_dir: Path
) -> tuple[bool, str]:
    """
    智能判断是否应启用 CNKI 检索
    
    优先级：
    1. 用户配置（enabled: true/false）
    2. 开题报告优先：有开题报告且已有≥5篇参考文献 → 跳过CNKI
    3. 文献数量判断：≥25篇 → 跳过CNKI，<25篇 → 启用CNKI
    
    Returns:
        (是否启用CNKI, 原因说明)
    """
    cnki_config = spec.get("literature", {}).get("cnki", {})
    
    # 读取配置
    enabled = cnki_config.get("enabled")  # True, False, or None
    threshold = cnki_config.get("min_reference_threshold", DEFAULT_MIN_REFERENCE_THRESHOLD)
    proposal_threshold = cnki_config.get("proposal_reference_threshold", MIN_PROPOSAL_REFERENCES_THRESHOLD)
    
    # 情况1: 用户明确禁用CNKI (enabled: false)
    if enabled is False:
        return False, "CNKI is explicitly disabled in config (enabled: false)."
    
    # 情况2: 用户明确启用CNKI（enabled: true）
    if enabled is True:
        return True, "CNKI is enabled (enabled: true), building literature pool."
    
    # 情况3: 开题报告优先模式
    # 如果有开题报告且已有足够参考文献（≥5篇），优先使用已有文献
    if has_proposal_pdf and reference_count >= proposal_threshold:
        return False, (
            f"Proposal PDF detected with {reference_count} references (>= {proposal_threshold}). "
            f"Using existing references from proposal. Set enabled: true to force CNKI."
        )
    
    # 情况4: 按文献总数判断（标准阈值25篇）
    if reference_count >= threshold:
        return False, (
            f"Found {reference_count} references (>= {threshold} required). "
            f"Using existing references. Set enabled: true to force CNKI if needed."
        )
    else:
        return True, (
            f"Only {reference_count} references found (< {threshold} required). "
            f"Auto-enabling CNKI search to reach minimum requirement."
        )


def auto_build_literature(
    spec_path: Path,
    output_dir: Path,
    work_dir: Path | None = None
) -> bool:
    """
    自动构建文献池
    
    智能判断逻辑：
    1. 检查用户是否提供了开题报告/任务书
    2. 提取其中的参考文献
    3. 如果文献数量不足或没有提供，自动启用CNKI检索
    
    Args:
        spec_path: thesis-ai-spec.yaml 路径
        output_dir: 输出目录
        work_dir: 工作目录（用于查找开题报告PDF），默认为spec所在目录
        
    Returns:
        是否成功（失败不阻断，返回 True 并记录警告）
    """
    # 加载配置
    try:
        spec = load_spec(spec_path)
    except Exception as e:
        logger.error(f"Failed to load spec: {e}")
        return True  # 不阻断
    
    # 确定工作目录
    if work_dir is None:
        work_dir = spec_path.parent
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 步骤1: 检查用户是否提供了参考文献
    reference_count, references = check_existing_references(output_dir)
    
    # 步骤2: 检查是否上传了开题报告PDF
    has_proposal_pdf = check_proposal_pdf(work_dir)
    
    # 读取阈值用于日志显示
    cnki_config = spec.get("literature", {}).get("cnki", {})
    threshold = cnki_config.get("min_reference_threshold", DEFAULT_MIN_REFERENCE_THRESHOLD)
    
    # 步骤3: 智能判断是否启用CNKI
    should_enable, reason = should_use_cnki(spec, reference_count, has_proposal_pdf, output_dir)
    
    logger.info(f"Literature check: {reason}")
    logger.info(f"  - Proposal PDF: {'Yes' if has_proposal_pdf else 'No'}")
    logger.info(f"  - Existing references: {reference_count}")
    logger.info(f"  - Threshold: {threshold}")
    logger.info(f"  - CNKI enabled: {'Yes' if should_enable else 'No'}")
    
    # 记录判断结果
    decision_log = output_dir / "literature-decision-log.md"
    with open(decision_log, "w", encoding="utf-8") as f:
        f.write("# 文献来源决策记录\n\n")
        f.write(f"## 判断结果\n\n")
        f.write(f"- **决策时间**: 自动生成\n")
        f.write(f"- **是否启用CNKI**: {'是' if should_enable else '否'}\n")
        f.write(f"- **决策原因**: {reason}\n\n")
        f.write(f"## 检测状态\n\n")
        f.write(f"- 发现开题报告PDF: {'是' if has_proposal_pdf else '否'}\n")
        f.write(f"- 已有参考文献数量: {reference_count}\n")
        f.write(f"- 最小阈值: {threshold}\n\n")
        if references:
            f.write("## 已有参考文献列表\n\n")
            for i, ref in enumerate(references[:10], 1):  # 只显示前10条
                title = ref.get("title", ref.get("题名", "未知"))
                f.write(f"{i}. {title}\n")
            if len(references) > 10:
                f.write(f"\n... 还有 {len(references) - 10} 条未显示\n")
    
    # 如果不启用CNKI，直接返回
    if not should_enable:
        logger.info("Using existing references. No CNKI search needed.")
        return True
    
    # 执行 CNKI 检索
    logger.info("Building CNKI literature pool...")
    
    try:
        success = build_cnki_pool(spec_path, output_dir)
        if success:
            logger.info("CNKI literature pool built successfully.")
            # 记录CNKI补充说明
            with open(decision_log, "a", encoding="utf-8") as f:
                f.write("\n## CNKI 检索结果\n\n")
                f.write("CNKI 检索已完成并补充到文献池。\n")
        else:
            logger.warning("CNKI search completed but no papers found.")
        return True  # 不阻断主流程
    except Exception as e:
        logger.error(f"CNKI search failed: {e}")
        logger.warning("Continuing without CNKI literature. Please check network or keywords.")
        return True  # 不阻断主流程


def main():
    parser = argparse.ArgumentParser(
        description="Auto build literature pool with intelligent CNKI detection"
    )
    parser.add_argument(
        "--spec",
        type=Path,
        required=True,
        help="Path to thesis-ai-spec.yaml"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper-context/literature"),
        help="Output directory for literature pool"
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Working directory to search for proposal PDFs (default: spec parent dir)"
    )
    
    args = parser.parse_args()
    
    success = auto_build_literature(args.spec, args.output, args.work_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
