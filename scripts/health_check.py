#!/usr/bin/env python3
"""
Chinese Thesis Workbench Skill 健康检查

运行此脚本验证skill是否开箱即用
"""

import sys
import shutil
from pathlib import Path

def check_module(name, import_path):
    """检查模块是否能正常导入"""
    try:
        exec(f"import {import_path}")
        return True, f"[OK] {name}"
    except Exception as e:
        return False, f"[FAIL] {name}: {str(e)[:50]}"

def main():
    print("=" * 60)
    print("Chinese Thesis Workbench Skill 健康检查")
    print("=" * 60)
    
    # 检查 Python 版本
    print(f"\nPython 版本: {sys.version.split()[0]}")
    
    # 检查 uvx 可用性
    has_uvx = shutil.which("uvx") is not None
    print(f"uvx 可用: {has_uvx}")
    
    # 检查关键依赖
    print("\n--- 依赖检查 ---")
    deps = [
        ("playwright", "playwright"),
        ("yaml", "yaml"),
        ("dataclasses", "dataclasses"),
    ]
    
    for name, module in deps:
        ok, msg = check_module(name, module)
        print(msg)
    
    # 检查核心模块
    print("\n--- 核心模块检查 ---")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    modules = [
        ("CNKI Crawler", "scripts.literature.cnki_crawler"),
        ("CNKI MCP Client", "scripts.literature.cnki_mcp_client"),
        ("Literature Module", "scripts.literature"),
        ("Workflow Guard", "scripts.workflow_guard"),
        ("Citation Manager", "scripts.literature.citation_manager"),
    ]
    
    all_ok = True
    for name, module in modules:
        ok, msg = check_module(name, module)
        print(msg)
        if not ok:
            all_ok = False
    
    # 检查 CNKI 功能
    print("\n--- CNKI 功能检查 ---")
    try:
        from scripts.literature import CNKIPoolBuilder, CNKIPaper
        
        # 测试 CNKIPaper
        paper = CNKIPaper(
            title="测试",
            authors=["测试作者"],
            inferred_type="期刊论文"
        )
        print(f"[OK] CNKIPaper 创建成功 (inferred_type={paper.inferred_type})")
        
        # 测试 CNKIPoolBuilder
        builder = CNKIPoolBuilder(
            keywords=["测试"],
            max_results=1
        )
        print(f"[OK] CNKIPoolBuilder 创建成功")
        
    except Exception as e:
        print(f"[FAIL] CNKI 功能: {e}")
        all_ok = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_ok:
        print("[PASS] 所有检查通过，Skill 可以正常使用")
        print(f"       CNKI 模式: {'MCP (uvx)' if has_uvx else 'Playwright (浏览器)'}")
    else:
        print("[FAIL] 部分检查失败，请查看上方错误信息")
    print("=" * 60)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
