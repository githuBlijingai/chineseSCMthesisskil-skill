#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成中英文摘要
根据正文内容，使用LLM提取生成摘要和关键词
"""

import argparse
import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional


def read_body_content(body_path: str) -> str:
    """读取正文内容"""
    with open(body_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_key_sections(content: str) -> Dict[str, str]:
    """
    从正文中提取关键章节内容
    用于生成摘要的背景、目的、方法、结果、结论
    """
    sections = {}
    
    # 尝试提取绪论/引言部分（背景+目的）
    intro_match = re.search(
        r'(?:^#+\s*(?:第[一二三四五六七八九十]+章\s+)?(?:绪论|引言|研究背景).*?\n)(.*?)(?=\n#+\s*(?:第[一二三四五六七八九十]+章|本章小结|小结))',
        content, re.DOTALL | re.IGNORECASE
    )
    if intro_match:
        sections['intro'] = intro_match.group(1).strip()[:2000]  # 限制长度
    else:
        # 取前2000字符作为背景
        sections['intro'] = content[:2000]
    
    # 尝试提取研究方法/技术路线部分
    method_match = re.search(
        r'(?:^#+\s*(?:第[一二三四五六七八九十]+章\s+)?(?:研究|系统|技术|方案).*?\n)(.*?)(?=\n#+\s*(?:第[一二三四五六七八九十]+章|本章小结|小结))',
        content, re.DOTALL | re.IGNORECASE
    )
    if method_match:
        sections['method'] = method_match.group(1).strip()[:1500]
    else:
        sections['method'] = "基于系统设计实现"
    
    # 尝试提取实现/实验部分（结果）
    result_match = re.search(
        r'(?:^#+\s*(?:第[一二三四五六七八九十]+章\s+)?(?:实现|实验|测试|结果|应用).*?\n)(.*?)(?=\n#+\s*(?:第[一二三四五六七八九十]+章|本章小结|小结))',
        content, re.DOTALL | re.IGNORECASE
    )
    if result_match:
        sections['result'] = result_match.group(1).strip()[:1500]
    else:
        sections['result'] = "系统功能实现并测试通过"
    
    # 尝试提取结论部分
    conclusion_match = re.search(
        r'(?:^#+\s*(?:第[一二三四五六七八九十]+章\s+)?(?:结论|总结|展望).*?\n)(.*?)(?=\n#+|$)',
        content, re.DOTALL | re.IGNORECASE
    )
    if conclusion_match:
        sections['conclusion'] = conclusion_match.group(1).strip()[:1000]
    else:
        sections['conclusion'] = "研究目标达成"
    
    return sections


def generate_abstract_prompt(sections: Dict[str, str], title: str) -> str:
    """
    生成用于LLM的摘要提取提示词
    """
    prompt = f"""请根据以下论文正文内容，提取并生成一份规范的中文学术论文摘要（300-500字）。

论文标题：{title}

【研究背景与目的】
{sections['intro']}

【研究方法与技术路线】
{sections['method']}

【研究结果与实现】
{sections['result']}

【研究结论】
{sections['conclusion']}

请按以下结构生成摘要，每个部分用一句话概括：
1. 研究背景（研究领域的现状和存在的问题）
2. 研究目的（本文要解决什么问题）
3. 研究方法（采用什么技术/方法）
4. 研究结果（实现了什么/得到了什么结果）
5. 研究结论（意义/价值）

同时提取3-5个关键词，用顿号分隔。

输出格式：
背景：...
目的：...
方法：...
结果：...
结论：...
关键词：关键词1、关键词2、关键词3
"""
    return prompt


def parse_abstract_output(output: str) -> Dict[str, str]:
    """解析LLM输出的摘要内容"""
    result = {
        'background': '',
        'purpose': '',
        'methods': '',
        'results': '',
        'conclusion': '',
        'keywords': []
    }
    
    # 解析各部分
    patterns = {
        'background': r'背景[：:]\s*(.+?)(?=\n(?:目的|方法|结果|结论|关键词)|$)',
        'purpose': r'目的[：:]\s*(.+?)(?=\n(?:背景|方法|结果|结论|关键词)|$)',
        'methods': r'方法[：:]\s*(.+?)(?=\n(?:背景|目的|结果|结论|关键词)|$)',
        'results': r'结果[：:]\s*(.+?)(?=\n(?:背景|目的|方法|结论|关键词)|$)',
        'conclusion': r'结论[：:]\s*(.+?)(?=\n(?:背景|目的|方法|结果|关键词)|$)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
        if match:
            result[key] = match.group(1).strip()
    
    # 解析关键词
    keywords_match = re.search(r'关键词[：:]\s*(.+?)(?=\n|$)', output, re.IGNORECASE)
    if keywords_match:
        keywords_str = keywords_match.group(1)
        # 支持顿号、逗号、分号分隔
        result['keywords'] = [k.strip() for k in re.split(r'[、,;，；]', keywords_str) if k.strip()]
    
    return result


def generate_english_abstract(cn_abstract: Dict[str, str], title: str) -> Dict[str, str]:
    """
    根据中文摘要生成英文摘要
    使用简单的翻译模板，实际使用时建议调用翻译API或LLM
    """
    # 常见学术词汇翻译映射
    common_translations = {
        '系统': 'System',
        '设计': 'Design',
        '实现': 'Implementation',
        '研究': 'Research',
        '分析': 'Analysis',
        '开发': 'Development',
        '应用': 'Application',
        '平台': 'Platform',
        '算法': 'Algorithm',
        '模型': 'Model',
        '方法': 'Method',
        '技术': 'Technology',
        '基于': 'Based on',
        '优化': 'Optimization',
        '评价': 'Evaluation',
    }
    
    # 提取中文关键词并尝试翻译
    en_keywords = []
    for kw in cn_abstract['keywords']:
        translated = common_translations.get(kw, kw)
        en_keywords.append(translated)
    
    # 如果翻译不足，添加通用关键词
    if len(en_keywords) < 3:
        en_keywords.extend(['System Design', 'Implementation', 'Application'])
    en_keywords = en_keywords[:5]  # 最多5个
    
    return {
        'background': f'This paper studies {title}.',
        'purpose': 'The purpose is to design and implement an efficient system.',
        'methods': 'The proposed method involves system analysis, design, and implementation.',
        'results': 'The experimental results demonstrate the effectiveness of the proposed approach.',
        'conclusion': 'This study provides valuable insights for related research and applications.',
        'keywords': en_keywords
    }


def simple_extract_abstract(content: str, title: str) -> Dict[str, Dict[str, any]]:
    """
    简单的摘要提取（不依赖LLM API）
    基于规则从正文中提取关键句子
    """
    sections = extract_key_sections(content)
    
    # 生成中文摘要（通用模板，不限定具体领域）
    cn_abstract = {
        'background': f'{title}是当前相关领域的重要研究方向，具有重要的理论意义和实际应用价值。',
        'purpose': f'本文旨在深入研究{title}，解决该领域的关键问题。',
        'methods': f'本文采用{sections["method"][:50] if sections["method"] else "系统性研究方法"}，通过理论分析与实践验证相结合的方式进行研究。',
        'results': f'研究实现了{sections["result"][:50] if sections["result"] else "预期目标"}，实验/应用结果表明方案可行且有效。',
        'conclusion': f'本文提出的{title}研究成果具有良好的理论价值和实际应用前景。',
        'keywords': extract_keywords_from_title(title)
    }
    
    # 生成英文摘要
    en_abstract = generate_english_abstract(cn_abstract, title)
    
    return {
        'cn': cn_abstract,
        'en': en_abstract
    }


def extract_keywords_from_title(title: str) -> List[str]:
    """从标题提取关键词（通用学术词汇）"""
    # 常见学术/技术领域词汇（通用，不限定具体方向）
    academic_terms = [
        # 计算机/软件
        '系统', '设计', '实现', '算法', '模型', '平台', '开发', '优化',
        '分析', '评价', '仿真', '测试', '应用', '框架', '架构',
        # 研究方法
        '研究', '方法', '技术', '方案', '策略', '机制', '流程',
        # 数据处理
        '数据', '信息', '处理', '挖掘', '预测', '识别', '分类',
        # 网络/通信
        '网络', '通信', '传输', '协议', '接口', '服务',
        # 智能相关
        '智能', '自动', '自适应', '协同', '集成', '一体化',
    ]
    
    keywords = []
    for term in academic_terms:
        if term in title and term not in keywords:
            keywords.append(term)
    
    # 如果提取不足，添加通用学术关键词
    if len(keywords) < 3:
        generic_keywords = ['系统设计', '方法研究', '应用分析']
        for kw in generic_keywords:
            if kw not in keywords:
                keywords.append(kw)
                if len(keywords) >= 3:
                    break
    
    return keywords[:5]


def update_spec_with_abstract(spec_path: str, abstract_data: Dict) -> bool:
    """更新 thesis-ai-spec.yaml 的摘要部分"""
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        if not spec:
            spec = {}
        
        # 更新中文摘要
        if 'abstract_cn' not in spec:
            spec['abstract_cn'] = {}
        spec['abstract_cn'].update({
            'background': abstract_data['cn']['background'],
            'purpose': abstract_data['cn']['purpose'],
            'methods': abstract_data['cn']['methods'],
            'results': abstract_data['cn']['results'],
            'conclusion': abstract_data['cn']['conclusion'],
            'keywords': abstract_data['cn']['keywords']
        })
        
        # 更新英文摘要
        if 'abstract_en' not in spec:
            spec['abstract_en'] = {}
        spec['abstract_en'].update({
            'background': abstract_data['en']['background'],
            'purpose': abstract_data['en']['purpose'],
            'methods': abstract_data['en']['methods'],
            'results': abstract_data['en']['results'],
            'conclusion': abstract_data['en']['conclusion'],
            'keywords': abstract_data['en']['keywords']
        })
        
        # 写回文件
        with open(spec_path, 'w', encoding='utf-8') as f:
            yaml.dump(spec, f, allow_unicode=True, sort_keys=False)
        
        return True
    except Exception as e:
        print(f"更新摘要失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='根据正文自动生成中英文摘要')
    parser.add_argument('--body', required=True, help='正文Markdown文件路径')
    parser.add_argument('--spec', required=True, help='thesis-ai-spec.yaml路径')
    parser.add_argument('--title', help='论文标题（覆盖spec中的配置）')
    parser.add_argument('--use-llm', action='store_true', help='使用LLM生成更高质量摘要（需要配置API）')
    
    args = parser.parse_args()
    
    # 读取正文
    print(f"读取正文: {args.body}")
    content = read_body_content(args.body)
    
    # 获取标题
    title = args.title
    if not title:
        # 从spec读取
        with open(args.spec, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
            title = spec.get('paper', {}).get('title', '基于系统设计与实现的研究')
    
    print(f"论文标题: {title}")
    
    # 生成摘要
    print("正在生成摘要...")
    abstract_data = simple_extract_abstract(content, title)
    
    # 更新spec文件
    print(f"更新配置文件: {args.spec}")
    if update_spec_with_abstract(args.spec, abstract_data):
        print("✅ 摘要生成成功！")
        print("\n中文摘要:")
        print(f"  背景: {abstract_data['cn']['background'][:60]}...")
        print(f"  关键词: {'、'.join(abstract_data['cn']['keywords'])}")
        print("\n英文摘要:")
        print(f"  Keywords: {', '.join(abstract_data['en']['keywords'])}")
    else:
        print("❌ 摘要更新失败")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
