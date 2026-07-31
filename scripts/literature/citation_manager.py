#!/usr/bin/env python3
"""
引用管理器模块

管理 CNKI 文献池的加载、匹配、引用插入和参考文献列表生成。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from .cnki_crawler import CNKIPaper
except ImportError:
    from .cnki_crawler import CNKIPaper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("citation_manager")


@dataclass
class Citation:
    """引用记录"""
    paper: CNKIPaper
    citation_number: int
    context: str = ""  # 引用上下文（段落摘要）
    chapter_id: str = ""


class CitationManager:
    """
    引用管理器
    
    负责：
    - 加载 CNKI 文献池
    - 根据内容匹配相关文献
    - 管理引用编号
    - 生成参考文献列表
    """
    
    def __init__(self, pool_path: Optional[Path] = None):
        """
        初始化引用管理器
        
        Args:
            pool_path: CNKI 文献池 JSON 文件路径
        """
        self.pool_path = pool_path or Path("paper-context/literature/cnki-pool.json")
        self.papers: list[CNKIPaper] = []
        self.citations: list[Citation] = []
        self._paper_to_number: dict[str, int] = {}  # URL -> 引用编号
        self._next_number = 1
        
        self._load_pool()
    
    def _load_pool(self):
        """加载文献池"""
        if not self.pool_path.exists():
            logger.warning(f"CNKI pool not found: {self.pool_path}")
            return
        
        try:
            with open(self.pool_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for p in data.get("papers", []):
                paper = CNKIPaper(
                    title=p.get("title", ""),
                    url=p.get("url", ""),
                    authors=p.get("authors", []),
                    source=p.get("source", ""),
                    date=p.get("date", ""),
                    cited_count=p.get("cited_count", "0"),
                    download_count=p.get("download_count", "0"),
                    abstract=p.get("abstract", ""),
                    keywords=p.get("keywords", []),
                    institutions=p.get("institutions", []),
                    year=p.get("year", ""),
                    volume=p.get("volume", ""),
                    issue=p.get("issue", ""),
                    pages=p.get("pages", ""),
                    doi=p.get("doi", ""),
                    fund=p.get("fund", ""),
                )
                self.papers.append(paper)
            
            logger.info(f"Loaded {len(self.papers)} papers from CNKI pool")
            
        except Exception as e:
            logger.error(f"Failed to load CNKI pool: {e}")
    
    def has_papers(self) -> bool:
        """是否有可用文献"""
        return len(self.papers) > 0
    
    def match_papers(self, text: str, max_results: int = 3) -> list[CNKIPaper]:
        """
        根据文本内容匹配相关文献
        
        匹配策略：
        1. 提取文本关键词（中文词汇、技术术语）
        2. 计算与文献标题、关键词、摘要的相似度
        3. 返回最相关的文献
        
        Args:
            text: 待匹配的文本
            max_results: 最多返回几篇文献
            
        Returns:
            相关文献列表
        """
        if not self.papers:
            return []
        
        # 提取文本中的关键词
        text_keywords = self._extract_keywords(text)
        
        # 计算每篇文献的相关度分数
        scored_papers: list[tuple[float, CNKIPaper]] = []
        
        for paper in self.papers:
            score = self._calculate_relevance(paper, text_keywords, text)
            if score > 0:
                scored_papers.append((score, paper))
        
        # 按分数排序，返回前 N 篇
        scored_papers.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored_papers[:max_results]]
    
    def _extract_keywords(self, text: str) -> set[str]:
        """从文本中提取关键词"""
        keywords = set()
        
        # 提取中文词汇（2-8字）
        chinese_words = re.findall(r"[\u4e00-\u9fa5]{2,8}", text)
        
        # 过滤常见无意义词
        stop_words = {
            "基于", "研究", "设计", "实现", "系统", "应用", "分析", 
            "方法", "技术", "进行", "通过", "使用", "采用", "本文",
            "论文", "章节", "部分", "如下", "所示", "提出", "构建"
        }
        
        for word in chinese_words:
            if word not in stop_words and len(word) >= 2:
                keywords.add(word)
        
        # 提取英文技术术语（大写字母开头，或全大写缩写）
        english_terms = re.findall(r"[A-Z][a-zA-Z0-9]{2,}|[A-Z]{2,}", text)
        keywords.update(english_terms)
        
        return keywords
    
    def _calculate_relevance(self, paper: CNKIPaper, text_keywords: set[str], text: str) -> float:
        """
        计算文献与文本的相关度分数
        
        Returns:
            相关度分数（0-100）
        """
        score = 0.0
        
        # 1. 标题匹配（权重最高）
        title_keywords = self._extract_keywords(paper.title)
        title_match = len(text_keywords & title_keywords)
        score += title_match * 10
        
        # 2. 关键词匹配
        paper_keywords = set(paper.keywords) if paper.keywords else set()
        keyword_match = len(text_keywords & paper_keywords)
        score += keyword_match * 8
        
        # 3. 摘要匹配
        if paper.abstract:
            abstract_keywords = self._extract_keywords(paper.abstract)
            abstract_match = len(text_keywords & abstract_keywords)
            score += abstract_match * 5
        
        # 4. 被引数加权（高质量文献优先）
        try:
            cited = int(paper.cited_count) if paper.cited_count else 0
            if cited > 100:
                score += 5
            elif cited > 50:
                score += 3
            elif cited > 10:
                score += 1
        except:
            pass
        
        return score
    
    def add_citation(self, paper: CNKIPaper, context: str = "", chapter_id: str = "") -> int:
        """
        添加引用
        
        Args:
            paper: 被引用的文献
            context: 引用上下文
            chapter_id: 章节ID
            
        Returns:
            引用编号
        """
        # 检查是否已引用
        if paper.url in self._paper_to_number:
            return self._paper_to_number[paper.url]
        
        # 分配新编号
        number = self._next_number
        self._next_number += 1
        
        self._paper_to_number[paper.url] = number
        
        citation = Citation(
            paper=paper,
            citation_number=number,
            context=context,
            chapter_id=chapter_id
        )
        self.citations.append(citation)
        
        return number
    
    def get_citation_number(self, paper: CNKIPaper) -> Optional[int]:
        """获取文献的引用编号"""
        return self._paper_to_number.get(paper.url)
    
    def generate_citation_mark(self, paper: CNKIPaper) -> str:
        """
        生成引用标记，如 [1], [2,3], [4-6]
        
        Args:
            paper: 要引用的文献
            
        Returns:
            引用标记字符串
        """
        number = self.add_citation(paper)
        return f"[{number}]"
    
    def generate_references_list(self, style: str = "gb7714") -> list[str]:
        """
        生成参考文献列表
        
        Args:
            style: 格式类型（gb7714）
            
        Returns:
            格式化后的参考文献列表
        """
        if style != "gb7714":
            raise ValueError(f"Unsupported style: {style}")
        
        references = []
        
        # 按引用编号排序
        sorted_citations = sorted(self.citations, key=lambda c: c.citation_number)
        
        for citation in sorted_citations:
            ref = self._format_gb7714(citation.paper)
            references.append(f"[{citation.citation_number}] {ref}")
        
        return references
    
    def _format_gb7714(self, paper: CNKIPaper) -> str:
        """格式化为 GB/T 7714 格式"""
        authors = ", ".join(paper.authors) if paper.authors else "佚名"
        title = paper.title
        source = paper.source
        year = paper.year or (paper.date[:4] if paper.date else "")
        volume = paper.volume
        issue = paper.issue
        pages = paper.pages
        
        # 期刊论文格式: 作者. 题名[J]. 刊名, 年, 卷(期): 页码.
        if volume and issue and pages:
            return f"{authors}. {title}[J]. {source}, {year}, {volume}({issue}): {pages}."
        elif volume and issue:
            return f"{authors}. {title}[J]. {source}, {year}, {volume}({issue})."
        elif year:
            return f"{authors}. {title}[J]. {source}, {year}."
        else:
            return f"{authors}. {title}[J]. {source}."
    
    def save_citations(self, output_path: Path):
        """保存引用记录到 JSON"""
        data = {
            "total_citations": len(self.citations),
            "citations": [
                {
                    "number": c.citation_number,
                    "title": c.paper.title,
                    "url": c.paper.url,
                    "authors": c.paper.authors,
                    "context": c.context,
                    "chapter_id": c.chapter_id,
                }
                for c in self.citations
            ]
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(self.citations)} citations to {output_path}")
    
    def insert_citations_to_text(self, text: str, chapter_id: str = "", max_citations: int = 2) -> str:
        """
        自动在文本中插入引用标记
        
        策略：
        - 在段落末尾插入相关文献引用
        - 避免过度引用（每段最多 max_citations 个）
        
        Args:
            text: 原始文本
            chapter_id: 章节ID
            max_citations: 每段最大引用数
            
        Returns:
            插入引用后的文本
        """
        if not self.has_papers():
            return text
        
        paragraphs = text.split("\n\n")
        result_paragraphs = []
        
        for para in paragraphs:
            if not para.strip() or len(para) < 50:
                # 跳过空行和短段落
                result_paragraphs.append(para)
                continue
            
            # 匹配相关文献
            matched = self.match_papers(para, max_results=max_citations)
            
            if matched:
                # 生成引用标记
                marks = [self.generate_citation_mark(p) for p in matched]
                citation_str = "".join(marks)
                
                # 插入到段落末尾（句号前或段落末尾）
                if para.endswith("。") or para.endswith("；"):
                    para = para[:-1] + citation_str + para[-1]
                else:
                    para = para + citation_str
                
                # 记录上下文
                for paper in matched:
                    self.add_citation(paper, context=para[:100], chapter_id=chapter_id)
            
            result_paragraphs.append(para)
        
        return "\n\n".join(result_paragraphs)


def main():
    """测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Citation Manager")
    parser.add_argument("--pool", type=Path, default=Path("paper-context/literature/cnki-pool.json"))
    parser.add_argument("--text", help="Text to match citations")
    parser.add_argument("--output", type=Path, help="Output citations JSON")
    
    args = parser.parse_args()
    
    # 初始化管理器
    manager = CitationManager(args.pool)
    
    if not manager.has_papers():
        print("No papers in pool. Run build_cnki_pool.py first.")
        return
    
    if args.text:
        # 测试匹配
        print(f"\nInput text: {args.text[:100]}...")
        print("\nMatched papers:")
        
        matched = manager.match_papers(args.text, max_results=3)
        for i, paper in enumerate(matched, 1):
            mark = manager.generate_citation_mark(paper)
            print(f"\n{i}. {mark} {paper.title}")
            print(f"   作者: {', '.join(paper.authors)}")
            print(f"   来源: {paper.source}")
        
        # 生成参考文献列表
        print("\n\nReferences:")
        for ref in manager.generate_references_list():
            print(ref)
        
        # 保存
        if args.output:
            manager.save_citations(args.output)


if __name__ == "__main__":
    main()
