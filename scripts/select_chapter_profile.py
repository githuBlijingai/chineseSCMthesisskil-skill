#!/usr/bin/env python3
"""
章节配置选择器
根据论文类型自动选择合适的章节配置文件
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import yaml


def detect_mcu_thesis(spec_path: str) -> bool:
    """检测是否为单片机类论文"""
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        # 检查 type_profile
        type_profile = spec.get('paper', {}).get('type_profile', '').lower()
        if 'mcu' in type_profile or '单片机' in type_profile:
            return True
        
        # 检查 thesis_type
        thesis_type = spec.get('paper', {}).get('type', '').lower()
        if any(kw in thesis_type for kw in ['单片机', '嵌入式', 'stm32', 'mcu', '51']):
            return True
        
        # 检查技术栈
        tech_stack = spec.get('technology_or_method_stack', {})
        hardware = str(tech_stack.get('hardware', [])).lower()
        if any(kw in hardware for kw in ['stm32', '单片机', 'mcu', 'arduino', 'esp32']):
            return True
        
        return False
    except Exception as e:
        print(f"[ERROR] 检测失败: {e}")
        return False


def get_chapter_profile_config(spec_path: str) -> dict:
    """
    根据论文类型获取章节配置
    
    Returns:
        {
            "profile_type": "mcu_system_design" | "system_design" | ...,
            "config_file": "chapter-profile-mcu.yaml" | None,
            "config_path": Path | None
        }
    """
    templates_dir = Path(spec_path).parent
    
    # 检测单片机论文
    if detect_mcu_thesis(spec_path):
        mcu_config = templates_dir / "chapter-profile-mcu.yaml"
        if mcu_config.exists():
            return {
                "profile_type": "mcu_system_design",
                "config_file": "chapter-profile-mcu.yaml",
                "config_path": mcu_config
            }
    
    # 读取 spec 中的 chapter_profiles
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        chapter_profiles = spec.get('chapter_profiles', {})
        
        # 如果有 mcu_system_design 且标记了使用
        if 'mcu_system_design' in chapter_profiles:
            mcu_config = templates_dir / "chapter-profile-mcu.yaml"
            if mcu_config.exists():
                return {
                    "profile_type": "mcu_system_design",
                    "config_file": "chapter-profile-mcu.yaml",
                    "config_path": mcu_config
                }
        
        # 默认返回 system_design
        return {
            "profile_type": "system_design",
            "config_file": None,
            "config_path": None
        }
    
    except Exception as e:
        print(f"[ERROR] 读取配置失败: {e}")
        return {
            "profile_type": "system_design",
            "config_file": None,
            "config_path": None
        }


def load_mcu_config(config_path: Path) -> dict:
    """加载单片机专用配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] 加载MCU配置失败: {e}")
        return {}


def print_config_info(config: dict):
    """打印配置信息"""
    print("=" * 60)
    print("章节配置信息")
    print("=" * 60)
    print(f"配置类型: {config['profile_type']}")
    
    if config['config_file']:
        print(f"配置文件: {config['config_file']}")
        print(f"配置路径: {config['config_path']}")
        
        # 如果是MCU配置，显示关键特性
        if config['profile_type'] == 'mcu_system_design':
            mcu_config = load_mcu_config(config['config_path'])
            if mcu_config:
                print("\n[MCU专用配置特性]")
                
                # 段落结构
                para_struct = mcu_config.get('paragraph_structure', {})
                print("\n段落长度控制:")
                for para_type in ['short_paragraph', 'medium_paragraph', 'long_paragraph']:
                    if para_type in para_struct:
                        info = para_struct[para_type]
                        print(f"  {para_type}: {info.get('min_chars', 0)}-{info.get('max_chars', 0)}字")
                
                # 内容密度
                density = mcu_config.get('content_density_requirements', {})
                print("\n内容密度要求:")
                per_para = density.get('per_paragraph_minimum', {})
                print(f"  每段技术关键词: ≥{per_para.get('technical_keywords', 0)}个")
                print(f"  每段具体参数: ≥{per_para.get('specific_parameters', 0)}个")
                
                # 章节结构
                chapters = mcu_config.get('chapters', {})
                print("\n推荐章节结构:")
                for ch_id, ch_info in chapters.items():
                    print(f"  {ch_info.get('title', ch_id)}")
                    print(f"    段落模式: {ch_info.get('paragraph_pattern', [])}")
    else:
        print("使用默认配置 (system_design)")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="根据论文类型自动选择章节配置"
    )
    parser.add_argument(
        "--spec",
        default="thesis-ai-standard/templates/thesis-ai-spec.yaml",
        help="thesis-ai-spec.yaml 路径"
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="仅检测是否为单片机论文"
    )
    
    args = parser.parse_args()
    
    if args.detect_only:
        is_mcu = detect_mcu_thesis(args.spec)
        print(f"检测结果: {'是' if is_mcu else '否'}单片机论文")
        sys.exit(0 if is_mcu else 1)
    
    config = get_chapter_profile_config(args.spec)
    print_config_info(config)
    
    # 输出配置文件路径（供其他脚本使用）
    if config['config_path']:
        print(f"\nCONFIG_PATH={config['config_path']}")


if __name__ == "__main__":
    main()
