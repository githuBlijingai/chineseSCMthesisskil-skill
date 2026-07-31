# 硬件设计文件解析使用指南

## 概述

Skill v1.1 新增了硬件设计文件解析功能，可以自动从PCB布局、原理图、BOM表等文件中提取论文证据。

## 支持的文件格式

### PCB设计文件
| 格式 | 扩展名 | 工具 |
|------|--------|------|
| Altium Designer | `.pcbdoc`, `.prjpcb` | Altium Designer |
| KiCad | `.kicad_pcb` | KiCad |
| Cadence | `.brd` | Cadence OrCAD |
| Eagle | `.brd` | Eagle |

### 原理图文件
| 格式 | 扩展名 | 工具 |
|------|--------|------|
| Altium Designer | `.schdoc` | Altium Designer |
| KiCad | `.sch`, `kicad_sch` | KiCad |
| Cadence | `.dsn` | Cadence OrCAD |
| Generic | `.sch` | 多种工具 |

### BOM物料清单
| 格式 | 扩展名 | 说明 |
|------|--------|------|
| CSV | `.csv` | 通用格式 |
| Excel | `.xlsx`, `.xls` | 支持中文列名 |
| 文本 | `.txt` | 制表符分隔 |

### Gerber制造文件
| 扩展名 | 说明 |
|--------|------|
| `.gtl` | 顶层铜 |
| `.gbl` | 底层铜 |
| `.gbs` | 阻焊顶层 |
| `.gbo` | 阻焊底层 |
| `.gml` | 丝印顶层 |
| `.gko` | 轮廓 |
| `.drl` | 钻孔 |

## 使用方法

### 方法1：单独解析硬件文件

```bash
# 解析指定目录下的硬件设计文件
python scripts/evidence/parse_hardware_files.py <硬件项目目录> --out paper-context/evidence

# 示例
python scripts/evidence/parse_hardware_files.py ./hardware --out paper-context/evidence
```

### 方法2：自动检测（推荐）

```bash
# 自动检测项目中的硬件文件并解析
python scripts/evidence/build_hardware_evidence.py --project-path <项目目录>

# 强制解析（即使未检测到硬件文件）
python scripts/evidence/build_hardware_evidence.py --project-path . --force
```

### 方法3：在证据构建流程中集成

在 `build_project_evidence.py` 执行后，硬件证据会自动生成。

## 输出文件

解析完成后，会在 `paper-context/evidence/` 目录生成：

```
paper-context/evidence/
├── hardware-evidence.json    # 结构化证据（机器可读）
└── hardware-evidence.md      # Markdown格式（便于阅读）
```

### JSON输出结构

```json
{
  "project_name": "my_mcu_project",
  "project_type": "hardware_design",
  "detected_tools": ["Altium Designer"],
  "pcb_boards": [
    {
      "name": "main_board",
      "width": 100.0,
      "height": 80.0,
      "layers": 4,
      "thickness": 1.6,
      "component_count": 45
    }
  ],
  "schematic_pages": [
    {
      "title": "main_schematic",
      "sheet_number": 1,
      "component_count": 38,
      "net_count": 62
    }
  ],
  "bom_components": [
    {
      "designator": "U1",
      "part_number": "STM32F103C8T6",
      "description": "MCU",
      "manufacturer": "ST",
      "package": "LQFP-48",
      "value": "",
      "quantity": 1
    }
  ],
  "gerber_files": ["gerber/top_copper.gtl", "gerber/bottom_copper.gbl"],
  "source_files": ["main.pcbdoc", "main.schdoc", "BOM.csv"]
}
```

### Markdown输出示例

```
# 硬件设计项目证据

**项目名称**: my_mcu_project
**项目类型**: hardware_design
**检测工具**: Altium Designer

## 汇总
| 类型 | 数量 |
|------|------|
| 原理图页数 | 1 |
| PCB板数 | 1 |
| BOM元器件 | 45 |
| Gerber文件 | 6 |
| 源文件总数 | 8 |

## BOM元器件清单
| 位号 | 型号 | 描述 | 值 | 封装 | 数量 |
|------|------|------|-----|------|------|
| U1 | STM32F103C8T6 | MCU | | LQFP-48 | 1 |
| C1 | 100nF | 电容 | 100nF | 0805 | 10 |
...
```

## 在论文中使用硬件证据

### 硬件设计章节（第3章）

根据 `chapter-profile-mcu.yaml` 的证据绑定要求，硬件章节需要：

1. **主控单元电路（3.1）**
   - 引用原理图中的MCU连接
   - 引用BOM中的芯片型号
   - 标注原理图截图位置

2. **电源电路设计（3.2）**
   - 引用BOM中的电容、电感
   - 电源参数计算依据

3. **传感器接口电路（3.3）**
   - 传感器选型依据（BOM）
   - 接口电路原理图

4. **通信接口电路（3.4）**
   - 通信芯片型号（BOM）
   - 接口原理图

5. **PCB设计与布局（3.5）**
   - PCB布局截图
   - 层叠结构说明（从PCB文件提取）

### 软件设计章节（第4章）

- 源码文件结构
- 主程序流程图
- 关键模块代码

### 系统测试章节（第5章）

- 测试环境说明
- 测试数据和截图

## BOM列名支持

解析器支持多种BOM列名格式：

| 字段 | 支持的列名 |
|------|------------|
| 位号 | 位号, Designator, Part Reference, Ref |
| 型号 | 型号, Part Number, MPN, Part# |
| 描述 | 描述, Description, Desc |
| 制造商 | 制造商, Manufacturer, Mfr |
| 封装 | 封装, Package, Footprint |
| 值 | 值, Value |
| 数量 | 数量, Quantity, Qty |

## 常见问题

### Q: 为什么BOM解析结果为空？

1. 检查文件是否包含中文表头
2. 确认文件编码是否为UTF-8
3. 检查列名是否符合上述格式

### Q: 原理图元器件提取不完整？

当前版本主要提取：
- 有明确位号的元器件（如U1, R2, C3）
- 部分元器件型号信息

完整解析需要专业库（如Altium脚本）。

### Q: PCB尺寸为0？

由于PCB文件格式复杂，部分工具的PCB文件无法完全解析尺寸信息。
可通过手动测量或从导出文件获取后，在 `hardware-evidence.json` 中补充。

## 更新日志

- **v1.1** (2026-05-27): 新增硬件设计文件解析
  - 支持PCB、原理图、BOM、Gerber文件解析
  - 自动检测硬件设计工具
  - 生成结构化证据文件

## 相关文件

- `scripts/evidence/parse_hardware_files.py` - 硬件文件解析器
- `scripts/evidence/build_hardware_evidence.py` - 自动构建脚本
- `assets/.../chapter-profile-mcu.yaml` - 章节配置（含硬件证据配置）
