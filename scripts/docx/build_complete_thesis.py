#!/usr/bin/env python3
"""
完整论文生成脚本

根据 thesis-ai-spec.yaml 和正文内容，生成包含以下部分的完整论文：
- 中文摘要 + 关键词
- 英文摘要 + 关键词
- 目录（自动生成）
- 正文（各章节）
- 参考文献
- 致谢（可选）
- 附录（单独文件）

使用方法:
    python scripts/docx/build_complete_thesis.py \
        --spec thesis-ai-standard/templates/thesis-ai-spec.yaml \
        --body paper-output/thesis-body.md \
        --refs paper-context/literature/cnki-references.txt \
        --output paper-output/ \
        --title "论文标题"
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


def set_run_fonts(run, east_asia_font: str, latin_font: str, size_pt: float, *, bold: bool = False) -> None:
    """设置字体"""
    run.bold = bold
    run.font.size = Pt(size_pt)
    run.font.name = latin_font
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:eastAsia"), east_asia_font)
    r_fonts.set(qn("w:ascii"), latin_font)
    r_fonts.set(qn("w:hAnsi"), latin_font)


def add_page_break(doc: Document) -> None:
    """添加分页符"""
    doc.add_page_break()


def add_centered_heading(doc: Document, text: str, font_cn: str = "黑体", font_en: str = "Times New Roman", size: float = 18, bold: bool = True) -> None:
    """添加居中标题"""
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    set_run_fonts(run, font_cn, font_en, size, bold=bold)
    paragraph.paragraph_format.space_before = Pt(24)
    paragraph.paragraph_format.space_after = Pt(24)
    paragraph.paragraph_format.line_spacing = 1.25


def add_paragraph_with_style(
    doc: Document,
    text: str,
    font_cn: str = "宋体",
    font_en: str = "Times New Roman",
    size: float = 12,
    bold: bool = False,
    align: str = "left",
    first_line_indent: float = 24,
    line_spacing: float = 1.25
) -> None:
    """添加带样式的段落"""
    paragraph = doc.add_paragraph()
    
    if align == "center":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "justify":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    run = paragraph.add_run(text)
    set_run_fonts(run, font_cn, font_en, size, bold=bold)
    
    paragraph.paragraph_format.first_line_indent = Pt(first_line_indent)
    paragraph.paragraph_format.line_spacing = line_spacing
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)


def add_keywords(doc: Document, label: str, keywords: list[str], is_english: bool = False) -> None:
    """添加关键词"""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.25
    paragraph.paragraph_format.space_before = Pt(12)
    
    # 标签
    if is_english:
        label_run = paragraph.add_run(label)
        set_run_fonts(label_run, "Times New Roman", "Times New Roman", 12, bold=True)
    else:
        label_run = paragraph.add_run(label)
        set_run_fonts(label_run, "黑体", "Times New Roman", 12, bold=True)
    
    # 关键词内容
    content = " ".join(keywords) if is_english else " ".join(keywords)
    if not is_english:
        content = content.replace(" ", "；")
    
    content_run = paragraph.add_run(content)
    if is_english:
        set_run_fonts(content_run, "Times New Roman", "Times New Roman", 12)
    else:
        set_run_fonts(content_run, "宋体", "Times New Roman", 12)


def build_abstract_cn(doc: Document, spec: dict) -> None:
    """构建中文摘要"""
    abstract_data = spec.get("abstract_cn", {})
    
    # 摘要标题
    add_centered_heading(doc, "摘  要", size=16)
    
    # 背景
    background = abstract_data.get("background", "").strip()
    if background:
        add_paragraph_with_style(doc, background, first_line_indent=24)
    
    # 目的
    purpose = abstract_data.get("purpose", "").strip()
    if purpose:
        add_paragraph_with_style(doc, purpose, first_line_indent=24)
    
    # 方法
    methods = abstract_data.get("methods", "").strip()
    if methods:
        add_paragraph_with_style(doc, methods, first_line_indent=24)
    
    # 结果
    results = abstract_data.get("results", "").strip()
    if results:
        add_paragraph_with_style(doc, results, first_line_indent=24)
    
    # 结论
    conclusion = abstract_data.get("conclusion", "").strip()
    if conclusion:
        add_paragraph_with_style(doc, conclusion, first_line_indent=24)
    
    # 关键词
    keywords = abstract_data.get("keywords", [])
    if keywords:
        add_keywords(doc, "关键词：", keywords, is_english=False)


def build_abstract_en(doc: Document, spec: dict) -> None:
    """构建英文摘要"""
    abstract_data = spec.get("abstract_en", {})
    
    # Abstract 标题
    add_centered_heading(doc, "Abstract", font_cn="Times New Roman", font_en="Times New Roman", size=16)
    
    # Background
    background = abstract_data.get("background", "").strip()
    if background:
        add_paragraph_with_style(doc, background, font_cn="Times New Roman", font_en="Times New Roman", first_line_indent=21)
    
    # Purpose
    purpose = abstract_data.get("purpose", "").strip()
    if purpose:
        add_paragraph_with_style(doc, purpose, font_cn="Times New Roman", font_en="Times New Roman", first_line_indent=21)
    
    # Methods
    methods = abstract_data.get("methods", "").strip()
    if methods:
        add_paragraph_with_style(doc, methods, font_cn="Times New Roman", font_en="Times New Roman", first_line_indent=21)
    
    # Results
    results = abstract_data.get("results", "").strip()
    if results:
        add_paragraph_with_style(doc, results, font_cn="Times New Roman", font_en="Times New Roman", first_line_indent=21)
    
    # Conclusion
    conclusion = abstract_data.get("conclusion", "").strip()
    if conclusion:
        add_paragraph_with_style(doc, conclusion, font_cn="Times New Roman", font_en="Times New Roman", first_line_indent=21)
    
    # Keywords
    keywords = abstract_data.get("keywords", [])
    if keywords:
        add_keywords(doc, "Keywords: ", keywords, is_english=True)


def add_toc_field(doc: Document) -> None:
    """
    添加Word可更新的TOC目录域
    生成的目录在Word中按F9可自动更新
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.5
    
    # 添加目录域开始标记
    run = paragraph.add_run()
    fldChar_begin = OxmlElement('w:fldChar')
    fldChar_begin.set(qn('w:fldCharType'), 'begin')
    
    instrText = OxmlElement('w:instrText')
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'  # 目录指令：1-3级标题，超链接，页码右对齐
    
    fldChar_separate = OxmlElement('w:fldChar')
    fldChar_separate.set(qn('w:fldCharType'), 'separate')
    
    run._r.append(fldChar_begin)
    run._r.append(instrText)
    run._r.append(fldChar_separate)
    
    # 添加占位文本（目录生成前显示的内容）
    placeholder_run = paragraph.add_run("（右键点击此处 → 更新域 → 更新整个目录）")
    set_run_fonts(placeholder_run, "宋体", "Times New Roman", 10.5)
    
    # 添加目录域结束标记
    end_run = paragraph.add_run()
    fldChar_end = OxmlElement('w:fldChar')
    fldChar_end.set(qn('w:fldCharType'), 'end')
    end_run._r.append(fldChar_end)


def build_toc_placeholder(doc: Document) -> None:
    """构建目录（包含可更新的TOC域）"""
    add_centered_heading(doc, "目  录", size=16)
    
    # 添加使用说明
    add_paragraph_with_style(
        doc,
        "（注：打开文档后，右键点击下方目录区域，选择[更新域]->[更新整个目录]生成正式目录）",
        size=10.5,
        first_line_indent=0,
        align="center"
    )
    
    doc.add_paragraph()  # 空行
    
    # 添加可更新的TOC域
    add_toc_field(doc)
    
    doc.add_paragraph()  # 空行
    
    # 添加目录结构预览（帮助用户了解章节安排）
    preview_para = doc.add_paragraph()
    preview_para.paragraph_format.first_line_indent = Pt(0)
    preview_para.paragraph_format.line_spacing = 1.0
    preview_para.paragraph_format.space_before = Pt(12)
    
    preview_run = preview_para.add_run("【论文结构预览】")
    set_run_fonts(preview_run, "黑体", "Times New Roman", 10.5, bold=True)
    
    toc_preview = [
        "第1章 绪论",
        "第2章 相关技术与开发环境", 
        "第3章 系统需求分析",
        "第4章 系统总体设计",
        "第5章 系统详细实现",
        "第6章 系统测试",
        "第7章 结论与展望",
        "参考文献",
        "致谢",
    ]
    
    for item in toc_preview:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.left_indent = Pt(21)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        
        r = p.add_run("• " + item)
        set_run_fonts(r, "宋体", "Times New Roman", 9)


def add_heading_with_style(doc: Document, text: str, level: int = 1) -> None:
    """
    添加带Word标题样式的段落（用于目录生成）
    level: 1=Heading 1, 2=Heading 2, 3=Heading 3
    """
    from docx.enum.style import WD_STYLE_TYPE
    
    # 获取或创建标题样式
    styles = {
        1: ("Heading 1", "黑体", 16),
        2: ("Heading 2", "黑体", 14),
        3: ("Heading 3", "黑体", 12),
    }
    
    style_name, font_cn, font_size = styles.get(level, ("Normal", "宋体", 12))
    
    # 使用Word内置标题样式
    paragraph = doc.add_paragraph(style=style_name)
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT if level > 1 else WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.space_before = Pt(12 if level == 1 else 6)
    paragraph.paragraph_format.space_after = Pt(6 if level == 1 else 3)
    
    run = paragraph.add_run(text)
    set_run_fonts(run, font_cn, "Times New Roman", font_size, bold=True)


def insert_body_content(doc: Document, body_path: Path) -> None:
    """插入正文内容（使用Word标题样式，支持目录生成）"""
    if not body_path.exists():
        print(f"警告: 正文文件不存在: {body_path}")
        return
    
    content = body_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    in_code_block = False
    code_buffer = []
    code_lang = ""
    
    for line in lines:
        stripped = line.strip()
        
        # 处理代码块
        if stripped.startswith("```"):
            if in_code_block:
                # 结束代码块
                if code_buffer:
                    # 添加代码内容
                    for code_line in code_buffer:
                        add_paragraph_with_style(
                            doc,
                            code_line,
                            font_cn="Consolas",
                            font_en="Consolas",
                            size=9,
                            first_line_indent=0
                        )
                in_code_block = False
                code_buffer = []
                code_lang = ""
            else:
                # 开始代码块
                in_code_block = True
                code_lang = stripped[3:].strip()
            continue
        
        if in_code_block:
            code_buffer.append(line.rstrip())
            continue
        
        # 跳过空行
        if not stripped:
            continue
        
        # 处理标题 - 使用Word标题样式（支持TOC目录）
        if stripped.startswith("# "):
            # 一级标题（论文标题）- 不加入目录
            add_centered_heading(doc, stripped[2:].strip(), size=18)
        elif stripped.startswith("## "):
            # 二级标题（章节）- Heading 1
            text = stripped[3:].strip()
            add_heading_with_style(doc, text, level=1)
        elif stripped.startswith("### "):
            # 三级标题（节）- Heading 2
            text = stripped[4:].strip()
            add_heading_with_style(doc, text, level=2)
        elif stripped.startswith("#### "):
            # 四级标题（小节）- Heading 3
            text = stripped[5:].strip()
            add_heading_with_style(doc, text, level=3)
        else:
            # 普通段落
            # 处理Markdown格式
            text = stripped
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # 粗体
            text = re.sub(r'\*(.+?)\*', r'\1', text)      # 斜体
            text = re.sub(r'`(.+?)`', r'\1', text)        # 代码
            
            add_paragraph_with_style(doc, text, first_line_indent=24)


def build_references(doc: Document, refs_path: Optional[Path]) -> None:
    """构建参考文献"""
    add_centered_heading(doc, "参考文献", size=16)
    
    if not refs_path or not refs_path.exists():
        add_paragraph_with_style(
            doc,
            "（注：请在此处插入参考文献列表）",
            size=10.5,
            first_line_indent=0,
            align="center"
        )
        return
    
    content = refs_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # 参考文献格式：悬挂缩进
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Pt(-21)
        paragraph.paragraph_format.left_indent = Pt(21)
        paragraph.paragraph_format.line_spacing = 1.25
        
        run = paragraph.add_run(line)
        set_run_fonts(run, "宋体", "Times New Roman", 10.5)


def build_acknowledgements(doc: Document, spec: dict) -> None:
    """构建致谢"""
    add_centered_heading(doc, "致  谢", size=16)
    
    # 从配置中读取致谢内容，如果没有则添加占位符
    ack_content = spec.get("acknowledgements", "").strip()
    
    if ack_content:
        add_paragraph_with_style(doc, ack_content, first_line_indent=24)
    else:
        add_paragraph_with_style(
            doc,
            "（注：请在此处撰写致谢内容，感谢导师、同学、家人等在论文完成过程中的帮助和支持。）",
            size=10.5,
            first_line_indent=24
        )


def apply_page_setup(section) -> None:
    """应用页面设置"""
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)


def build_complete_thesis(
    spec_path: Path,
    body_path: Path,
    refs_path: Optional[Path],
    output_dir: Path,
    title: str
) -> tuple[Path, Path]:
    """
    构建完整论文
    
    Returns:
        (主论文路径, 附录路径)
    """
    # 加载配置
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    
    # 创建文档
    doc = Document()
    apply_page_setup(doc.sections[0])
    
    # 1. 中文摘要
    build_abstract_cn(doc, spec)
    add_page_break(doc)
    
    # 2. 英文摘要
    build_abstract_en(doc, spec)
    add_page_break(doc)
    
    # 3. 目录
    build_toc_placeholder(doc)
    add_page_break(doc)
    
    # 4. 正文
    insert_body_content(doc, body_path)
    
    # 5. 参考文献（新页面）
    add_page_break(doc)
    build_references(doc, refs_path)
    
    # 6. 致谢（新页面）
    add_page_break(doc)
    build_acknowledgements(doc, spec)
    
    # 保存主论文
    output_dir.mkdir(parents=True, exist_ok=True)
    main_docx_path = output_dir / f"{title}.docx"
    doc.save(str(main_docx_path))
    print(f"主论文已生成: {main_docx_path}")
    
    # 生成附录（如果正文中有代码块）
    appendix_docx_path = output_dir / f"{title}-附件.docx"
    try:
        # 尝试调用现有的附录生成脚本
        import subprocess
        result = subprocess.run(
            [
                "python",
                str(Path(__file__).parent / "generate_diagram_appendix_docx.py"),
                title,
                str(body_path),
                str(appendix_docx_path)
            ],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"附录已生成: {appendix_docx_path}")
        else:
            print(f"附录生成失败: {result.stderr}")
            appendix_docx_path = None
    except Exception as e:
        print(f"附录生成失败: {e}")
        appendix_docx_path = None
    
    return main_docx_path, appendix_docx_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="构建完整论文DOCX（包含摘要、目录、正文、参考文献、致谢）"
    )
    parser.add_argument(
        "--spec",
        type=Path,
        required=True,
        help="thesis-ai-spec.yaml 路径"
    )
    parser.add_argument(
        "--body",
        type=Path,
        required=True,
        help="正文Markdown文件路径"
    )
    parser.add_argument(
        "--refs",
        type=Path,
        default=None,
        help="参考文献文件路径（可选）"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper-output"),
        help="输出目录"
    )
    parser.add_argument(
        "--title",
        type=str,
        default="毕业论文",
        help="论文标题"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    try:
        main_path, appendix_path = build_complete_thesis(
            args.spec,
            args.body,
            args.refs,
            args.output,
            args.title
        )
        print(f"\n论文生成完成！")
        print(f"主论文: {main_path}")
        if appendix_path:
            print(f"附录: {appendix_path}")
        return 0
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
