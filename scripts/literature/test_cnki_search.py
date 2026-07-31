#!/usr/bin/env python3
"""
测试CNKI文献检索功能
"""

import sys
import argparse
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from .cnki_crawler import search_cnki, PLAYWRIGHT_AVAILABLE


def test_cnki(keyword: str = "计算机"):
    """测试CNKI搜索"""
    print("=" * 60)
    print("CNKI 文献检索测试")
    print("=" * 60)
    
    # 检查Playwright
    if not PLAYWRIGHT_AVAILABLE:
        print("[FAIL] Playwright 未安装")
        print("请运行: pip install playwright")
        return False
    
    print("[OK] Playwright 已安装\n")
    
    # 测试搜索关键词（使用通用学术关键词）
    test_keyword = keyword
    
    print(f"测试搜索: {test_keyword}")
    print("-" * 60)
    
    try:
        result = search_cnki(test_keyword, pages=1)
        
        if result.get("isError"):
            print(f"[FAIL] 搜索失败: {result.get('error')}")
            return False
        
        papers = result.get("papers", [])
        total = result.get("total_papers", 0)
        
        print(f"[OK] 搜索成功!")
        print(f"  找到论文: {len(papers)} 篇")
        print(f"  总计结果: {total} 篇\n")
        
        if papers:
            print("前3篇论文:")
            for i, paper in enumerate(papers[:3], 1):
                print(f"\n{i}. {paper.get('title', 'N/A')}")
                print(f"   作者: {', '.join(paper.get('authors', []))}")
                print(f"   来源: {paper.get('source', 'N/A')}")
                print(f"   被引: {paper.get('cited_count', '0')} 下载: {paper.get('download_count', '0')}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试CNKI文献检索功能")
    parser.add_argument(
        "--keyword",
        type=str,
        default="计算机",
        help="测试搜索关键词（默认: 计算机）"
    )
    args = parser.parse_args()
    
    success = test_cnki(keyword=args.keyword)
    print("\n" + "=" * 60)
    if success:
        print("测试通过! CNKI 可以正常使用。")
    else:
        print("测试失败! 请检查配置。")
    print("=" * 60)
    sys.exit(0 if success else 1)
