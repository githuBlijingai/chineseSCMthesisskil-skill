#!/usr/bin/env python3
"""
CNKI 文献池构建脚本

根据 thesis-ai-spec.yaml 配置，自动检索 CNKI 文献并生成文献池。
采用直接集成方式，无需 MCP 服务器。
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

# 导入直接集成的 CNKI 爬虫
from .cnki_crawler import CNKIPoolBuilder, close_browser_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_cnki_pool")


def load_spec(spec_path: Path) -> dict:
    """加载 thesis-ai-spec.yaml"""
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_keywords(spec: dict) -> list[str]:
    """
    从 spec 中提取搜索关键词
    
    优先级：
    1. literature.cnki.custom_terms（用户自定义）
    2. thesis.keywords（论文关键词）
    3. 从开题报告/技术栈提取技术关键词
    4. paper.title/thesis.title（论文标题，智能提取技术术语）
    """
    from .cnki_crawler import extract_tech_keywords_from_text
    
    keywords = []
    
    # 1. 用户自定义
    cnki_config = spec.get("literature", {}).get("cnki", {})
    custom_terms = cnki_config.get("custom_terms", [])
    if custom_terms:
        keywords.extend(custom_terms)
        logger.info(f"Using custom terms: {custom_terms}")
        return keywords
    
    # 2. 论文关键词（优先从thesis，其次从paper）
    thesis_keywords = spec.get("thesis", {}).get("keywords", [])
    if thesis_keywords:
        keywords.extend(thesis_keywords)
        logger.info(f"Using thesis keywords: {thesis_keywords}")
        return keywords
    
    # 3. 从技术栈提取技术关键词
    tech_stack = spec.get("technology_or_method_stack", {})
    tech_text = ""
    for category in ["hardware", "software", "protocol", "algorithm"]:
        items = tech_stack.get(category, [])
        if isinstance(items, list):
            tech_text += " ".join(str(item) for item in items) + " "
    
    if tech_text:
        tech_keywords = extract_tech_keywords_from_text(tech_text)
        if tech_keywords:
            logger.info(f"Extracted tech keywords: {tech_keywords}")
            return tech_keywords[:5]
    
    # 4. 从标题提取技术关键词
    title = spec.get("thesis", {}).get("title", "") or spec.get("paper", {}).get("title", "")
    if title and title != "填写论文题目":
        title_keywords = extract_tech_keywords_from_text(title)
        if title_keywords:
            logger.info(f"Extracted keywords from title: {title_keywords}")
            return title_keywords[:5]
    
    # 如果没有找到任何关键词，返回空列表
    logger.warning("No keywords found in spec. Please set thesis.keywords or literature.cnki.custom_terms")
    return []


def load_existing_references(output_dir: Path) -> set[str]:
    """
    加载已有的参考文献（从开题报告提取的）
    
    Returns:
        已有文献标题集合（用于去重）
    """
    existing_titles = set()
    
    # 1. 从 reference-extraction.json 加载
    ref_json = output_dir / "reference-extraction.json"
    if ref_json.exists():
        try:
            import json
            with open(ref_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for ref in data:
                    title = ref.get("title", "")
                    if title:
                        existing_titles.add(title.lower())
            elif isinstance(data, dict):
                refs = data.get("references", []) or data.get("papers", [])
                for ref in refs:
                    title = ref.get("title", "")
                    if title:
                        existing_titles.add(title.lower())
            
            logger.info(f"Found {len(existing_titles)} existing references from proposal")
        except Exception as e:
            logger.warning(f"Failed to load existing references: {e}")
    
    # 2. 从 local-pool.json 加载
    local_pool = output_dir / "local-pool.json"
    if local_pool.exists():
        try:
            import json
            with open(local_pool, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            papers = data.get("papers", [])
            for paper in papers:
                title = paper.get("title", "")
                if title:
                    existing_titles.add(title.lower())
        except Exception as e:
            logger.warning(f"Failed to load local pool: {e}")
    
    return existing_titles


def remove_duplicate_papers(papers: list, existing_titles: set[str]) -> list:
    """
    移除与已有文献重复的论文
    
    Args:
        papers: CNKI检索到的论文列表
        existing_titles: 已有文献标题集合
    
    Returns:
        去重后的论文列表
    """
    if not existing_titles:
        return papers
    
    unique_papers = []
    seen_titles = set()
    
    for paper in papers:
        title = paper.title if hasattr(paper, 'title') else paper.get("title", "")
        title_lower = title.lower()
        
        # 跳过与已有文献重复的
        if title_lower in existing_titles:
            logger.debug(f"Skipping duplicate paper: {title}")
            continue
        
        # 跳过已在此列表中的
        if title_lower in seen_titles:
            continue
        
        seen_titles.add(title_lower)
        unique_papers.append(paper)
    
    logger.info(f"Removed {len(papers) - len(unique_papers)} duplicate papers")
    return unique_papers


def build_cnki_pool(spec_path: Path, output_dir: Path) -> bool:
    """
    构建 CNKI 文献池
    
    功能：
    1. 智能提取技术关键词
    2. 与已有文献（开题报告）去重
    3. 按文献类型优先级排序
    
    Args:
        spec_path: thesis-ai-spec.yaml 路径
        output_dir: 输出目录
        
    Returns:
        是否成功
    """
    from .cnki_crawler import filter_papers_by_literature_type
    
    # 加载配置
    spec = load_spec(spec_path)
    
    # 检查是否启用 CNKI
    cnki_config = spec.get("literature", {}).get("cnki", {})
    enabled = cnki_config.get("enabled")
    
    # enabled: True -> 强制启用, False -> 强制禁用, null/未设置 -> 默认启用
    if enabled is False:
        logger.info("CNKI search is explicitly disabled (enabled: false). Skipping.")
        return True
    
    # enabled为True或null时都启用CNKI（auto_build_literature会处理智能判断）
    if enabled is True:
        logger.info("CNKI search is explicitly enabled (enabled: true).")
    else:
        logger.info("CNKI search is enabled by default (enabled: null). Use enabled: false to disable.")
    
    # 提取关键词
    keywords = extract_keywords(spec)
    if not keywords:
        logger.error("No keywords available for CNKI search")
        return False
    
    # 获取配置参数
    max_results = cnki_config.get("max_results", 10)
    min_citations = cnki_config.get("min_citations", 0)
    year_range = cnki_config.get("year_range")
    search_type = cnki_config.get("search_type", "主题")
    sort = cnki_config.get("sort", "被引")
    target_types = cnki_config.get("literature_types", ["期刊论文", "学位论文", "会议论文", "外文期刊"])
    
    if year_range and len(year_range) == 2:
        year_range = tuple(year_range)
    else:
        year_range = None
    
    logger.info(f"CNKI config: max_results={max_results}, min_citations={min_citations}")
    logger.info(f"Literature types: {target_types}")
    logger.info(f"Search keywords: {keywords}")
    
    # 加载已有文献（用于去重）
    existing_titles = load_existing_references(output_dir)
    if existing_titles:
        logger.info(f"Found {len(existing_titles)} existing references for deduplication")
    
    # 构建文献池
    builder = CNKIPoolBuilder(
        keywords=keywords,
        max_results=max_results * 2,  # 检索更多，过滤后保留足够数量
        min_citations=min_citations,
        year_range=year_range,
        search_type=search_type,
        sort=sort
    )
    
    papers = builder.build()
    
    if not papers:
        logger.warning("No papers found from CNKI. Check network or keywords.")
        # 不阻断流程，只是警告
        return True
    
    logger.info(f"Retrieved {len(papers)} papers from CNKI")
    
    # 步骤1: 与已有文献去重
    papers = remove_duplicate_papers(papers, existing_titles)
    logger.info(f"After deduplication: {len(papers)} papers")
    
    # 步骤2: 按文献类型过滤和排序
    papers_data = [p.to_dict() for p in papers]
    filtered_data = filter_papers_by_literature_type(papers_data, target_types)
    logger.info(f"After literature type filtering: {len(filtered_data)} papers")
    
    # 限制最终数量
    final_papers = filtered_data[:max_results]
    
    # 更新 builder 的 papers
    from .cnki_crawler import CNKIPaper
    builder.papers = [CNKIPaper(**p) for p in final_papers]
    
    # 保存结果
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 保存完整数据
    json_path = output_dir / "cnki-pool.json"
    builder.save_to_json(json_path)
    
    # 2. 生成参考文献列表
    refs = builder.generate_references(style="gb7714")
    refs_path = output_dir / "cnki-references.txt"
    with open(refs_path, "w", encoding="utf-8") as f:
        f.write("# CNKI 检索参考文献 (GB/T 7714)\n")
        f.write(f"# 检索关键词: {', '.join(keywords)}\n")
        f.write(f"# 文献类型: {', '.join(target_types)}\n")
        f.write(f"# 去重后文献数: {len(final_papers)}\n\n")
        for ref in refs:
            f.write(ref + "\n")
    
    logger.info(f"CNKI pool saved: {json_path}")
    logger.info(f"References saved: {refs_path}")
    logger.info(f"Final papers: {len(final_papers)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Build CNKI literature pool")
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
        help="Output directory for CNKI pool"
    )
    
    args = parser.parse_args()
    
    try:
        success = build_cnki_pool(args.spec, args.output)
    finally:
        # 确保关闭浏览器池
        close_browser_pool()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
