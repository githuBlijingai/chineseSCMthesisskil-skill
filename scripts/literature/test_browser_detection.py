#!/usr/bin/env python3
"""
测试本地浏览器检测功能
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from .cnki_crawler import find_local_browser, PLAYWRIGHT_AVAILABLE

def test_browser_detection():
    """测试浏览器检测"""
    print("=" * 50)
    print("本地浏览器检测测试")
    print("=" * 50)
    
    # 检查Playwright
    if PLAYWRIGHT_AVAILABLE:
        print("[OK] Playwright 已安装")
    else:
        print("[FAIL] Playwright 未安装")
        print("   请运行: pip install playwright")
        return False
    
    # 检测本地浏览器
    print("\n检测本地浏览器...")
    browser_path = find_local_browser()
    
    if browser_path:
        print(f"[OK] 找到本地浏览器: {browser_path}")
        
        # 判断浏览器类型
        if 'chrome' in browser_path.lower():
            print("   类型: Google Chrome")
        elif 'edge' in browser_path.lower() or 'msedge' in browser_path.lower():
            print("   类型: Microsoft Edge")
        elif 'firefox' in browser_path.lower():
            print("   类型: Mozilla Firefox")
        else:
            print("   类型: 未知")
        
        print("\n[OK] CNKI 爬虫现在可以使用本地浏览器，无需下载Chromium！")
        return True
    else:
        print("[FAIL] 未找到本地浏览器")
        print("\n支持的浏览器:")
        print("  - Google Chrome")
        print("  - Microsoft Edge")
        print("  - Mozilla Firefox")
        print("\n请安装以上任一浏览器，或手动下载Chromium:")
        print("  playwright install chromium")
        return False

if __name__ == "__main__":
    success = test_browser_detection()
    sys.exit(0 if success else 1)
