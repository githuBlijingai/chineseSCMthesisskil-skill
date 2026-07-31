#!/usr/bin/env python3
"""SKILL 修改完整性最终检查"""

import os
import py_compile
from pathlib import Path
import yaml

def check_files():
    """检查关键文件"""
    print("1. 关键文件检查:")
    files = [
        'requirements.txt',
        'scripts/literature/cnki_crawler.py',
        'scripts/literature/build_cnki_pool.py',
        'scripts/docx/build_complete_thesis.py',
        'scripts/docx/auto_generate_abstract.py',
        'scripts/workflow_guard.py',
        'scripts/user_intent.py',
        'scripts/smart_generate.py',
        '.gitignore'
    ]
    
    for f in files:
        if Path(f).exists():
            print(f"  [OK] {f}")
        else:
            print(f"  [FAIL] {f} 不存在!")

def check_directories():
    """检查目录结构"""
    print("\n2. 工作目录检查:")
    if Path('thesis-ai-standard/templates').exists():
        print("  [WARN] thesis-ai-standard/templates 仍存在")
    else:
        print("  [OK] thesis-ai-standard/templates 已删除")
    
    print("\n3. 默认模板检查:")
    if Path('assets/thesis-ai-standard/templates').exists():
        count = len(list(Path('assets/thesis-ai-standard/templates').glob('*')))
        print(f"  [OK] assets/thesis-ai-standard/templates ({count} files)")
    
    print("\n4. 单片机专用配置检查:")
    mcu_config = Path('assets/thesis-ai-standard/templates/chapter-profile-mcu.yaml')
    if mcu_config.exists():
        print(f"  [OK] chapter-profile-mcu.yaml 存在")
    else:
        print(f"  [FAIL] chapter-profile-mcu.yaml 不存在")

def check_syntax():
    """检查Python语法"""
    print("\n4. Python语法检查:")
    scripts = [
        'scripts/literature/cnki_crawler.py',
        'scripts/docx/build_complete_thesis.py',
        'scripts/docx/auto_generate_abstract.py',
    ]
    
    for s in scripts:
        try:
            py_compile.compile(s, doraise=True)
            print(f"  [OK] {Path(s).name}")
        except Exception as e:
            print(f"  [FAIL] {Path(s).name}: {e}")

def check_configs():
    """检查关键配置"""
    print("\n5. 关键配置检查:")
    
    # 检查 thesis-ai-spec.yaml
    with open('assets/thesis-ai-standard/templates/thesis-ai-spec.yaml', 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f)
    
    threshold = spec.get('literature', {}).get('cnki', {}).get('min_reference_threshold')
    if threshold == 25:
        print(f"  [OK] CNKI threshold: {threshold}")
    else:
        print(f"  [FAIL] CNKI threshold: {threshold} (expected 25)")
    
    # 检查绪论章节
    chapters = spec.get('chapters', [])
    if chapters:
        intro_required = chapters[0].get('required_sections', [])
        has_method = any('研究方法与技术路线' in str(s) for s in intro_required)
        has_structure = any('论文结构' in str(s) for s in intro_required)
        if has_method and not has_structure:
            print("  [OK] 绪论章节: 研究方法与技术路线")
        else:
            print(f"  [WARN] 绪论章节检查: method={has_method}, structure={has_structure}")
    
    # 检查 ai-prompts.md
    with open('assets/thesis-ai-standard/templates/ai-prompts.md', 'r', encoding='utf-8') as f:
        content = f.read()
        if '禁止机械列点' in content:
            print("  [OK] ai-prompts.md: 禁止机械列点")
        else:
            print("  [FAIL] ai-prompts.md: 缺少禁止机械列点")

def check_cnki_browser_support():
    """检查CNKI本地浏览器支持"""
    print("\n6. CNKI本地浏览器支持:")
    with open('scripts/literature/cnki_crawler.py', 'r', encoding='utf-8') as f:
        crawler = f.read()
        if 'find_local_browser' in crawler:
            print("  [OK] find_local_browser() 函数已添加")
        else:
            print("  [FAIL] find_local_browser() 函数不存在")
        
        if 'executable_path' in crawler:
            print("  [OK] 本地浏览器路径支持已添加")
        else:
            print("  [FAIL] 本地浏览器路径支持不存在")

def main():
    print("=" * 60)
    print("SKILL 修改完整性最终检查")
    print("=" * 60)
    
    check_files()
    check_directories()
    check_syntax()
    check_configs()
    check_cnki_browser_support()
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
