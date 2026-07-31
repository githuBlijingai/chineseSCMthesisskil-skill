#!/usr/bin/env python3
"""
Literature module for chinese-thesis-workbench-skill

提供文献检索、引用生成、参考文献格式化等功能。
"""

import shutil

# 检测 uvx 是否可用，决定使用哪种 CNKI 检索方式
if shutil.which("uvx"):
    # 优先使用 MCP 方式（功能更完整）
    from .cnki_mcp_client import CNKIPaper, CNKIMCPClient, CNKIPoolBuilder
else:
    # uvx 不可用时，使用 Playwright 直接爬取方式
    from .cnki_crawler import CNKIPaper, CNKIPoolBuilder
    CNKIMCPClient = None  # MCP 客户端不可用

from .build_cnki_pool import build_cnki_pool, extract_keywords, load_spec
from .citation_manager import CitationManager, Citation
from .auto_build_literature import auto_build_literature

__all__ = [
    "CNKIPaper",
    "CNKIMCPClient", 
    "CNKIPoolBuilder",
    "build_cnki_pool",
    "extract_keywords",
    "load_spec",
    "CitationManager",
    "Citation",
    "auto_build_literature",
]
