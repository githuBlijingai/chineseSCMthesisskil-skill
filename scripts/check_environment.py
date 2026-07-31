#!/usr/bin/env python3
"""
环境检查脚本
检测Python版本、依赖、浏览器等
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"[FAIL] Python版本过低: {version.major}.{version.minor}")
        print("       需要Python 3.8或更高版本")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖包"""
    required = [
        'pdfplumber',
        'pypdf',
        'python-docx',
        'yaml',
        'playwright'
    ]
    
    all_ok = True
    for pkg in required:
        try:
            if pkg == 'yaml':
                __import__('yaml')
            elif pkg == 'python-docx':
                __import__('docx')
            else:
                __import__(pkg)
            print(f"[OK] {pkg}")
        except ImportError:
            print(f"[FAIL] {pkg} 未安装")
            all_ok = False
    
    return all_ok

def check_browser():
    """检查本地浏览器"""
    import os
    
    # 检查常见浏览器路径
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    
    firefox_paths = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ]
    
    all_paths = [("Chrome", chrome_paths), ("Edge", edge_paths), ("Firefox", firefox_paths)]
    
    for name, paths in all_paths:
        for path in paths:
            if os.path.exists(path):
                print(f"[OK] 找到{name}: {path}")
                return True
    
    print("[FAIL] 未找到本地浏览器 (Chrome/Edge/Firefox)")
    return False

def main():
    print("=" * 60)
    print("环境检查")
    print("=" * 60)
    
    # 检查Python版本
    print("\n1. Python版本检查:")
    python_ok = check_python_version()
    
    # 检查依赖
    print("\n2. 依赖包检查:")
    deps_ok = check_dependencies()
    
    # 检查浏览器
    print("\n3. 浏览器检查:")
    browser_ok = check_browser()
    
    # 总结
    print("\n" + "=" * 60)
    if python_ok and deps_ok and browser_ok:
        print("[OK] 环境检查通过，可以正常使用！")
        print("=" * 60)
        return 0
    else:
        print("[WARN] 环境检查未完全通过")
        if not python_ok:
            print("  - 请升级Python到3.8+")
        if not deps_ok:
            print("  - 请运行: pip install -r requirements.txt")
        if not browser_ok:
            print("  - 请安装Chrome/Edge/Firefox，或运行: playwright install chromium")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
