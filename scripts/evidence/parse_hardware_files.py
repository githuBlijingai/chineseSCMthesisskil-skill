#!/usr/bin/env python3
"""
硬件设计文件解析器
支持解析：PCB布局、原理图、BOM表、Gerber文件等

支持的格式：
- Altium Designer: .PcbDoc, .PrjPcb, .SchDoc
- KiCad: .kicad_pcb, .sch, .pro
- EasyEDA/立创EDA: .json
- Cadence: .brd, .dsn
- Eagle: .brd, .sch
- BOM: .xlsx, .csv, .txt
- Gerber: .gtl, .gbl, .gbs, .gbo, .drl

用法：
    python scripts/evidence/parse_hardware_files.py <项目目录> [--out <输出目录>]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional
import zipfile


@dataclass
class HardwareComponent:
    """电子元器件"""
    designator: str          # 元器件位号（如 R1, C2, U3）
    part_number: str         # 型号（如 STM32F103C8T6）
    description: str         # 描述
    manufacturer: str        # 制造商
    package: str             # 封装（如 SOIC-8）
    value: str               # 值（如 10KΩ, 100nF）
    quantity: int = 1       # 数量


@dataclass
class PCBBoard:
    """PCB板信息"""
    name: str
    width: float             # 宽度 mm
    height: float           # 高度 mm
    layers: int              # 层数
    thickness: float = 1.6  # 板厚 mm
    trace_class: str = ""    # 最小线宽/间距
    via_class: str = ""      # 最小过孔
    components: list[HardwareComponent] = field(default_factory=list)


@dataclass
class SchematicPage:
    """原理图页面"""
    title: str
    sheet_number: int
    components: list[HardwareComponent] = field(default_factory=list)
    nets: list[str] = field(default_factory=list)  # 网络名列表


@dataclass
class HardwareEvidence:
    """硬件设计证据"""
    project_name: str
    project_type: str                    # 硬件项目类型
    pcb_boards: list[PCBBoard] = field(default_factory=list)
    schematic_pages: list[SchematicPage] = field(default_factory=list)
    bom_components: list[HardwareComponent] = field(default_factory=list)
    gerber_files: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    detected_tools: list[str] = field(default_factory=list)


# ============ 文件检测 ============

PCB_EXTENSIONS = {
    '.pcbdoc', '.prjpcb', '.brd',           # Altium, Cadence, Eagle
    '.kicad_pcb', 'kicad_pcb',               # KiCad
}

SCH_EXTENSIONS = {
    '.schdoc', '.sch', '.dsn', '.opj',       # Altium, KiCad, Cadence
    'kicad_sch',                             # KiCad
}

BOM_EXTENSIONS = {'.xlsx', '.csv', '.txt', '.xls'}

GERBER_EXTENSIONS = {
    '.gtl', '.gbl', '.gbs', '.gbo', '.gbl',  # 层
    '.gml', '.gbo',                          # 丝印
    '.gbs', '.gbo',                          # 阻焊
    '.drl', '.txt',                          # 钻孔
    '.g1', '.g2',                            # 中间层
}


def detect_hardware_tools(project_path: Path) -> list[str]:
    """检测使用的硬件设计工具"""
    tools = []
    
    # 检查文件扩展名
    for f in project_path.rglob('*'):
        if f.is_file():
            name = f.name.lower()
            ext = f.suffix.lower()
            
            if 'altium' in name or ext in ['.pcbdoc', '.prjpcb', '.schdoc']:
                tools.append('Altium Designer')
            elif 'kicad' in name or ext == '.kicad_pcb' or 'kicad_sch' in name:
                tools.append('KiCad')
            elif 'easyeda' in name or 'lceda' in name:
                tools.append('EasyEDA/立创EDA')
            elif ext in ['.brd', '.dsn']:
                tools.append('Cadence')
            elif ext == '.brd' or ext == '.sch':
                tools.append('Eagle')
    
    return list(set(tools))


# ============ BOM解析 ============

def parse_bom_csv(filepath: Path) -> list[HardwareComponent]:
    """解析CSV格式BOM"""
    components = []
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 尝试匹配常见列名
                designator = row.get('位号', row.get('Designator', row.get('Part Reference', '')))
                part_number = row.get('型号', row.get('Part Number', row.get('MPN', '')))
                description = row.get('描述', row.get('Description', ''))
                manufacturer = row.get('制造商', row.get('Manufacturer', ''))
                package = row.get('封装', row.get('Package', row.get('Footprint', '')))
                value = row.get('值', row.get('Value', ''))
                quantity = row.get('数量', row.get('Quantity', '1'))
                
                if designator:
                    try:
                        qty = int(quantity) if quantity else 1
                    except:
                        qty = 1
                        
                    components.append(HardwareComponent(
                        designator=designator,
                        part_number=part_number,
                        description=description,
                        manufacturer=manufacturer,
                        package=package,
                        value=value,
                        quantity=qty
                    ))
    except Exception as e:
        print(f"[WARN] BOM解析失败: {e}")
    
    return components


def parse_bom_txt(filepath: Path) -> list[HardwareComponent]:
    """解析文本格式BOM（可能是表格形式）"""
    components = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 尝试按行解析
        lines = content.strip().split('\n')
        for line in lines:
            # 跳过空行和分隔行
            if not line.strip() or line.startswith('---') or line.startswith('==='):
                continue
            
            # 尝试用制表符或逗号分割
            parts = re.split(r'[\t,;|]+', line.strip())
            if len(parts) >= 2:
                designator = parts[0]
                part_number = parts[1] if len(parts) > 1 else ''
                description = parts[2] if len(parts) > 2 else ''
                value = parts[3] if len(parts) > 3 else ''
                
                components.append(HardwareComponent(
                    designator=designator,
                    part_number=part_number,
                    description=description,
                    manufacturer='',
                    package='',
                    value=value
                ))
    except Exception as e:
        print(f"[WARN] TXT BOM解析失败: {e}")
    
    return components


def parse_bom_file(filepath: Path) -> list[HardwareComponent]:
    """根据文件扩展名选择BOM解析方法"""
    ext = filepath.suffix.lower()
    
    if ext == '.csv':
        return parse_bom_csv(filepath)
    elif ext in ['.txt', '.xls', '.xlsx']:
        # 先尝试CSV解析
        components = parse_bom_csv(filepath)
        if not components:
            components = parse_bom_txt(filepath)
        return components
    
    return []


# ============ 原理图解析 ============

def extract_schematic_info(filepath: Path, tool: str) -> SchematicPage:
    """提取原理图信息"""
    components = []
    nets = []
    title = filepath.stem
    
    try:
        if tool == 'Altium Designer' and filepath.suffix.lower() == '.schdoc':
            # Altium原理图是XML格式
            components, nets = parse_altium_sch(filepath)
        elif tool == 'KiCad' or 'kicad_sch' in str(filepath):
            components, nets = parse_kicad_sch(filepath)
        else:
            # 通用文本解析
            components = parse_generic_schematic(filepath)
    except Exception as e:
        print(f"[WARN] 原理图解析失败: {e}")
    
    return SchematicPage(
        title=title,
        sheet_number=1,
        components=components,
        nets=nets
    )


def parse_altium_sch(filepath: Path) -> tuple[list[HardwareComponent], list[str]]:
    """解析Altium原理图"""
    components = []
    nets = []
    
    try:
        # Altium SchDoc 是 XML 格式
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # 查找元器件（简化解析）
        for comp in root.iter():
            if 'Component' in comp.tag or 'Part' in comp.tag:
                designator = comp.get('Designator', '')
                part_number = comp.get('PartNumber', comp.get('ComponentName', ''))
                if designator:
                    components.append(HardwareComponent(
                        designator=designator,
                        part_number=part_number,
                        description='',
                        manufacturer='',
                        package='',
                        value=''
                    ))
            
            # 查找网络名
            if 'Net' in comp.tag:
                net_name = comp.get('Name', '')
                if net_name:
                    nets.append(net_name)
    except Exception as e:
        print(f"[WARN] Altium原理图详细解析失败: {e}")
        # 尝试文本提取
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # 简单提取元器件位号
            designators = re.findall(r'(R\d+|C\d+|U\d+|D\d+|L\d+|J\d+|P\d+|K\d+)\s*[-=]?\s*(\w+)', content)
            for des, part in designators[:20]:  # 限制数量
                components.append(HardwareComponent(
                    designator=des,
                    part_number=part,
                    description='',
                    manufacturer='',
                    package='',
                    value=''
                ))
    
    return components, nets


def parse_kicad_sch(filepath: Path) -> tuple[list[HardwareComponent], list[str]]:
    """解析KiCad原理图"""
    components = []
    nets = []
    
    try:
        # KiCad 原理图 .sch 是 S-Expression 格式
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取元器件
        comp_pattern = r'\(comp\s+\(ref\s+(\w+)\)\s+\(value\s+([^\)]+)\)'
        for match in re.finditer(comp_pattern, content):
            designator = match.group(1)
            value = match.group(2).strip()
            if designator[0] in 'RCUDJPLKQ' or designator.startswith('U'):
                components.append(HardwareComponent(
                    designator=designator,
                    part_number=value,
                    description='',
                    manufacturer='',
                    package='',
                    value=value
                ))
        
        # 提取网络名
        net_pattern = r'\(net\s+\(code\s+\d+\)\s+\(name\s+([^\)]+)\)'
        for match in re.finditer(net_pattern, content):
            net_name = match.group(1).strip().strip('"')
            if net_name and net_name != 'Net-':
                nets.append(net_name)
                
    except Exception as e:
        print(f"[WARN] KiCad原理图解析失败: {e}")
    
    return components, nets


def parse_generic_schematic(filepath: Path) -> list[HardwareComponent]:
    """通用原理图解析"""
    components = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 提取元器件位号和型号
        # 常见格式：U1 STM32F103C8T6, R1 10K
        pattern = r'(R\d+|C\d+|U\d+|D\d+|L\d+|J\d+|P\d+|K\d+|Q\d+|VR\d+|F\d+)\s+([^\s,\n]+)'
        for match in re.finditer(pattern, content):
            designator = match.group(1)
            part_number = match.group(2).strip()
            if part_number and len(part_number) < 30:  # 过滤过长内容
                components.append(HardwareComponent(
                    designator=designator,
                    part_number=part_number,
                    description='',
                    manufacturer='',
                    package='',
                    value=''
                ))
    except Exception as e:
        print(f"[WARN] 通用原理图解析失败: {e}")
    
    return components


# ============ PCB解析 ============

def extract_pcb_info(filepath: Path, tool: str) -> Optional[PCBBoard]:
    """提取PCB板信息"""
    try:
        if tool == 'Altium Designer' and filepath.suffix.lower() == '.pcbdoc':
            return parse_altium_pcb(filepath)
        elif tool == 'KiCad':
            return parse_kicad_pcb(filepath)
        
        # 通用PCB解析
        return parse_generic_pcb(filepath)
    except Exception as e:
        print(f"[WARN] PCB解析失败: {e}")
        return None


def parse_altium_pcb(filepath: Path) -> Optional[PCBBoard]:
    """解析Altium PCB文件"""
    # Altium PcbDoc 是二进制+XML混合格式
    # 简化处理：提取基本信息
    
    board = PCBBoard(
        name=filepath.stem,
        width=0,
        height=0,
        layers=2,
        thickness=1.6
    )
    
    try:
        # 尝试读取XML头部信息
        with open(filepath, 'rb') as f:
            content = f.read(10000)  # 读取前10KB
            
        # 简单提取尺寸信息（可能有）
        # 实际解析需要专用库
        print(f"[INFO] Altium PCB: {filepath.name} - 需要专业工具提取详细信息")
        
    except Exception as e:
        print(f"[WARN] Altium PCB解析: {e}")
    
    return board


def parse_kicad_pcb(filepath: Path) -> Optional[PCBBoard]:
    """解析KiCad PCB文件"""
    board = PCBBoard(
        name=filepath.stem,
        width=0,
        height=0,
        layers=2,
        thickness=1.6
    )
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取PCB参数
        # (pcb (width 100mm) (height 80mm) (layers 4))
        width_match = re.search(r'\(width\s+(\d+\.?\d*)\s*(\w+)\)', content)
        height_match = re.search(r'\(height\s+(\d+\.?\d*)\s*(\w+)\)', content)
        layers_match = re.search(r'\(layers\s+(\d+)\)', content)
        
        if width_match:
            board.width = float(width_match.group(1))
            board.height = float(height_match.group(1)) if height_match else 0
        if layers_match:
            board.layers = int(layers_match.group(1))
            
    except Exception as e:
        print(f"[WARN] KiCad PCB解析: {e}")
    
    return board


def parse_generic_pcb(filepath: Path) -> Optional[PCBBoard]:
    """通用PCB解析"""
    return PCBBoard(
        name=filepath.stem,
        width=0,
        height=0,
        layers=2
    )


# ============ Gerber解析 ============

def find_gerber_files(project_path: Path) -> list[str]:
    """查找Gerber文件"""
    gerber_files = []
    
    for f in project_path.rglob('*'):
        if f.is_file():
            ext = f.suffix.lower().lstrip('.')
            # 检查是否为Gerber扩展名
            if ext in ['gtl', 'gbl', 'gbs', 'gbo', 'gml', 'gbo', 'drl', 'g1', 'g2', 'gbs', 'gko', 'gpt']:
                gerber_files.append(str(f.relative_to(project_path)))
            # 检查文件名模式
            elif f.name.lower().startswith('gerber') or 'gerber' in f.name.lower():
                gerber_files.append(str(f.relative_to(project_path)))
    
    return gerber_files


# ============ 主解析器 ============

def parse_hardware_project(project_path: Path, output_path: Optional[Path] = None) -> HardwareEvidence:
    """解析整个硬件设计项目"""
    
    project_path = project_path.resolve()
    print(f"[INFO] 解析硬件项目: {project_path}")
    
    # 检测硬件设计工具
    tools = detect_hardware_tools(project_path)
    print(f"[INFO] 检测到工具: {tools or '未知'}")
    
    evidence = HardwareEvidence(
        project_name=project_path.name,
        project_type='hardware_design',
        detected_tools=tools,
        source_files=[]
    )
    
    # 扫描源文件
    for f in project_path.rglob('*'):
        if not f.is_file():
            continue
            
        rel_path = str(f.relative_to(project_path))
        ext = f.suffix.lower()
        name_lower = f.name.lower()
        
        # 记录所有硬件相关文件
        if (ext in PCB_EXTENSIONS or ext in SCH_EXTENSIONS or 
            ext in BOM_EXTENSIONS or ext in GERBER_EXTENSIONS or
            'pcbdoc' in name_lower or 'schdoc' in name_lower or
            'kicad' in name_lower or name_lower.endswith('.kicad_pcb')):
            evidence.source_files.append(rel_path)
    
    # 解析BOM文件
    print("[INFO] 解析BOM文件...")
    for bom_file in project_path.rglob('*'):
        if bom_file.is_file() and bom_file.suffix.lower() in BOM_EXTENSIONS:
            # 排除非BOM文件
            if 'bom' in bom_file.name.lower() or '物料' in bom_file.name or '器件' in bom_file.name:
                components = parse_bom_file(bom_file)
                if components:
                    print(f"[INFO] 解析BOM: {bom_file.name} - {len(components)} 个元器件")
                    evidence.bom_components.extend(components)
    
    # 解析原理图
    print("[INFO] 解析原理图文件...")
    for sch_file in project_path.rglob('*'):
        if sch_file.is_file():
            is_schematic = False
            ext = sch_file.suffix.lower()
            name = sch_file.name.lower()
            
            if ext in SCH_EXTENSIONS:
                is_schematic = True
            elif 'sch' in name and ext in ['.doc', '.xml', '']:
                is_schematic = True
            
            if is_schematic:
                tool = tools[0] if tools else 'Unknown'
                schematic = extract_schematic_info(sch_file, tool)
                if schematic.components:
                    evidence.schematic_pages.append(schematic)
                    print(f"[INFO] 解析原理图: {sch_file.name} - {len(schematic.components)} 个元器件")
    
    # 解析PCB文件
    print("[INFO] 解析PCB文件...")
    for pcb_file in project_path.rglob('*'):
        if pcb_file.is_file():
            is_pcb = False
            ext = pcb_file.suffix.lower()
            name = pcb_file.name.lower()
            
            if ext in PCB_EXTENSIONS or 'pcbdoc' in name or name.endswith('.kicad_pcb'):
                is_pcb = True
            
            if is_pcb:
                tool = tools[0] if tools else 'Unknown'
                board = extract_pcb_info(pcb_file, tool)
                if board:
                    evidence.pcb_boards.append(board)
                    print(f"[INFO] 解析PCB: {pcb_file.name}")
    
    # 查找Gerber文件
    print("[INFO] 查找Gerber文件...")
    gerber_files = find_gerber_files(project_path)
    if gerber_files:
        evidence.gerber_files = gerber_files
        print(f"[INFO] 找到 {len(gerber_files)} 个Gerber文件")
    
    return evidence


def evidence_to_markdown(evidence: HardwareEvidence) -> str:
    """将证据转换为Markdown格式"""
    
    md = []
    md.append(f"# 硬件设计项目证据\n")
    md.append(f"**项目名称**: {evidence.project_name}\n")
    md.append(f"**项目类型**: {evidence.project_type}\n")
    md.append(f"**检测工具**: {', '.join(evidence.detected_tools) or '未知'}\n")
    
    # 汇总
    md.append(f"\n## 汇总\n")
    md.append(f"| 类型 | 数量 |\n")
    md.append(f"|------|------|\n")
    md.append(f"| 原理图页数 | {len(evidence.schematic_pages)} |\n")
    md.append(f"| PCB板数 | {len(evidence.pcb_boards)} |\n")
    md.append(f"| BOM元器件 | {len(evidence.bom_components)} |\n")
    md.append(f"| Gerber文件 | {len(evidence.gerber_files)} |\n")
    md.append(f"| 源文件总数 | {len(evidence.source_files)} |\n")
    
    # BOM元器件清单
    if evidence.bom_components:
        md.append(f"\n## BOM元器件清单\n")
        md.append(f"| 位号 | 型号 | 描述 | 值 | 封装 | 数量 |\n")
        md.append(f"|------|------|------|-----|------|------|\n")
        
        # 按类型分组显示（前20个）
        for comp in evidence.bom_components[:20]:
            md.append(f"| {comp.designator} | {comp.part_number} | {comp.description} | {comp.value} | {comp.package} | {comp.quantity} |")
        
        if len(evidence.bom_components) > 20:
            md.append(f"\n*共 {len(evidence.bom_components)} 个元器件，详细清单见JSON文件*\n")
    
    # PCB板信息
    if evidence.pcb_boards:
        md.append(f"\n## PCB板信息\n")
        for board in evidence.pcb_boards:
            md.append(f"### {board.name}\n")
            md.append(f"- 尺寸: {board.width:.1f}mm × {board.height:.1f}mm\n")
            md.append(f"- 层数: {board.layers}\n")
            md.append(f"- 板厚: {board.thickness}mm\n")
            if board.components:
                md.append(f"- 元器件: {len(board.components)} 个\n")
    
    # 原理图页
    if evidence.schematic_pages:
        md.append(f"\n## 原理图结构\n")
        for page in evidence.schematic_pages:
            md.append(f"### {page.title}\n")
            md.append(f"- 元器件数量: {len(page.components)}\n")
            md.append(f"- 网络数量: {len(page.nets)}\n")
            
            if page.components:
                comp_types = {}
                for comp in page.components:
                    prefix = comp.designator[0] if comp.designator else '?'
                    comp_types[prefix] = comp_types.get(prefix, 0) + 1
                
                md.append(f"- 元器件分布: {', '.join(f'{k}:{v}' for k, v in sorted(comp_types.items()))}\n")
    
    # Gerber文件
    if evidence.gerber_files:
        md.append(f"\n## Gerber文件\n")
        for gf in evidence.gerber_files:
            md.append(f"- {gf}\n")
    
    # 源文件列表
    if evidence.source_files:
        md.append(f"\n## 源文件清单\n")
        # 按扩展名分组
        ext_groups = {}
        for f in evidence.source_files:
            ext = Path(f).suffix or '(无扩展名)'
            if ext not in ext_groups:
                ext_groups[ext] = []
            ext_groups[ext].append(f)
        
        for ext, files in sorted(ext_groups.items()):
            md.append(f"\n### {ext} ({len(files)} 个)\n")
            for f in files[:10]:
                md.append(f"- {f}\n")
            if len(files) > 10:
                md.append(f"- ... 还有 {len(files) - 10} 个\n")
    
    return ''.join(md)


def save_evidence(evidence: HardwareEvidence, output_path: Path):
    """保存证据文件"""
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 保存JSON格式
    json_file = output_path / 'hardware-evidence.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        # 转换为可JSON序列化的格式
        data = {
            'project_name': evidence.project_name,
            'project_type': evidence.project_type,
            'detected_tools': evidence.detected_tools,
            'pcb_boards': [
                {
                    'name': b.name,
                    'width': b.width,
                    'height': b.height,
                    'layers': b.layers,
                    'thickness': b.thickness,
                    'component_count': len(b.components)
                }
                for b in evidence.pcb_boards
            ],
            'schematic_pages': [
                {
                    'title': s.title,
                    'sheet_number': s.sheet_number,
                    'component_count': len(s.components),
                    'net_count': len(s.nets)
                }
                for s in evidence.schematic_pages
            ],
            'bom_components': [
                asdict(c) for c in evidence.bom_components
            ],
            'gerber_files': evidence.gerber_files,
            'source_files': evidence.source_files
        }
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 保存JSON: {json_file}")
    
    # 保存Markdown格式
    md_file = output_path / 'hardware-evidence.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(evidence_to_markdown(evidence))
    print(f"[OK] 保存Markdown: {md_file}")


def main():
    parser = argparse.ArgumentParser(
        description='解析硬件设计项目，提取论文证据'
    )
    parser.add_argument(
        'project_path',
        help='硬件项目目录路径'
    )
    parser.add_argument(
        '--out', '-o',
        default='paper-context/evidence',
        help='输出目录（默认: paper-context/evidence）'
    )
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"[ERROR] 目录不存在: {project_path}")
        sys.exit(1)
    
    output_path = Path(args.out)
    
    print("=" * 60)
    print("硬件设计项目解析器")
    print("=" * 60)
    
    # 解析项目
    evidence = parse_hardware_project(project_path, output_path)
    
    # 保存证据
    save_evidence(evidence, output_path)
    
    print("=" * 60)
    print("解析完成!")
    print("=" * 60)
    print(f"\n汇总:")
    print(f"  - 检测工具: {', '.join(evidence.detected_tools) or '未知'}")
    print(f"  - 原理图: {len(evidence.schematic_pages)} 页")
    print(f"  - PCB: {len(evidence.pcb_boards)} 块")
    print(f"  - BOM: {len(evidence.bom_components)} 个元器件")
    print(f"  - Gerber: {len(evidence.gerber_files)} 个文件")
    print(f"\n输出目录: {output_path}")


if __name__ == "__main__":
    main()
