# 工作流守卫使用指南

## 概述

工作流守卫机制确保论文生成遵循正确的流程：

```
用户上传材料 -> 等待模板 -> 确认大纲 -> 用户说"生成论文" -> 执行生成
        |              |            |                    |
        v              v            v                    v
   [OK:解析材料]  [BLOCKED]   [BLOCKED]           [GENERATE]
```

## 新增模块

| 模块 | 功能 | 位置 |
|------|------|------|
| `workflow_guard.py` | 工作流守卫检查 | `scripts/workflow_guard.py` |
| `user_intent.py` | 用户意图识别 | `scripts/user_intent.py` |
| `smart_generate.py` | 智能生成入口 | `scripts/smart_generate.py` |

## 守卫检查规则

### 检查 1: 模板检查
**触发条件**: 生成论文前  
**通过条件**: 
- 上传了学校模板 (`paper-context/templates/school-template.docx`)
- 或明确使用默认规范 (`paper-context/workflow/use-default-style.confirmed`)

**阻止消息**:
```
[BLOCKED] 被阻止: missing_template
原因: 未找到学校论文模板
建议操作:
   [FILE] 请上传学校论文模板（.docx 或 .pdf）
   [WRITE] 或确认使用默认规范
```

### 检查 2: 大纲确认
**触发条件**: 模板检查通过后  
**通过条件**: 
- 创建确认标记文件 `paper-context/workflow/outline-confirmed-by-user.flag`
- 或在 `user-decisions.md` 中记录"大纲已确认"

**阻止消息**:
```
[BLOCKED] 被阻止: outline_not_confirmed
原因: 论文大纲尚未经用户确认
建议操作:
   [LIST] 请查看并确认论文大纲结构
   [OK] 确认后创建标记文件
```

### 检查 3: 用户明确指令
**触发条件**: 大纲确认后  
**通过条件**: 用户明确说以下关键词之一：
- "生成论文"
- "开始生成"
- "写论文"
- "generate thesis"
- "start writing"

**阻止消息**:
```
[BLOCKED] 被阻止: user_did_not_request_generation
原因: 用户未明确请求生成论文
建议操作:
   [THINK] 您上传了材料，但未明确说'生成论文'
   [TIP] 请说'生成论文'或'开始写论文'以继续
```

## 使用方式

### 方式 1: 命令行使用

```bash
# 查看当前状态
python scripts/smart_generate.py --status

# 尝试生成（带守卫检查）
python scripts/smart_generate.py --user-request="生成论文"

# 强制生成（不推荐）
python scripts/smart_generate.py --user-request="生成论文" --force
```

### 方式 2: Python 导入

```python
from scripts.workflow_guard import workflow_guard, print_guard_result

# 检查是否可以生成
result = workflow_guard(user_request="生成论文")
print_guard_result(result)

if result.can_proceed:
    # 执行生成
    pass
else:
    # 显示建议
    for rec in result.recommendations:
        print(rec)
```

### 方式 3: 在 SKILL.md 工作流中集成

当用户上传材料时：

```python
from scripts.user_intent import detect_intent

intent = detect_intent(user_input)

if intent.value == "upload_materials":
    # 1. 解析材料
    # 2. 生成大纲建议
    # 3. 显示状态：等待模板和确认
    print("材料已接收。请：")
    print("1. 上传学校模板")
    print("2. 确认大纲")
    print("3. 说'生成论文'开始")
```

## 标记文件创建方法

### 确认使用默认规范
```bash
# 创建标记文件
echo "使用默认规范" > paper-context/workflow/use-default-style.confirmed
```

### 确认大纲
```bash
# 创建确认标记
echo "用户已确认大纲" > paper-context/workflow/outline-confirmed-by-user.flag
```

## 用户意图映射

| 用户输入 | 识别意图 | 是否生成 |
|----------|----------|----------|
| "这是我的源码" | upload_materials | ❌ |
| "大纲是什么样的" | ask_outline | ❌ |
| "确认大纲" | confirm_outline | ❌（需明确说生成） |
| "生成论文" | request_generate | ✅（通过守卫后） |
| "开始写吧" | request_generate | ✅（通过守卫后） |
| "修改第一章" | request_revise | ❌ |
| "你好" | general_chat | ❌ |

## 完整工作流示例

### 场景 1: 用户上传材料
```
用户: 这是我的源码和开题报告
AI:   [意图识别: upload_materials]
      [解析材料...]
      [生成大纲建议]
      [状态: 等待模板上传]
      
      我已收到您的材料！目前：
      ✅ 已解析开题报告
      ✅ 已分析源码结构
      
      下一步请：
      1. 上传学校论文模板（如没有请告知）
      2. 确认以下大纲结构是否合适
      3. 说"生成论文"开始写作
```

### 场景 2: 用户说生成但缺模板
```
用户: 生成论文
AI:   [意图识别: request_generate]
      [守卫检查: missing_template]
      
      ❌ 无法生成：未找到学校模板
      
      请执行以下操作之一：
      1. 上传学校论文模板
      2. 创建 use-default-style.confirmed 使用默认规范
```

### 场景 3: 全部条件满足
```
用户: 生成论文
AI:   [意图识别: request_generate]
      [守卫检查: 全部通过]
      [开始生成...]
      
      ✅ 正在生成论文...
      - 生成摘要
      - 生成正文
      - 生成参考文献
      - 导出 DOCX
```

## 注意事项

1. **守卫是强制的**: 默认情况下，不满足条件无法生成
2. **标记文件是人工确认的证据**: 表示用户已明确做出决定
3. **意图识别支持中英文**: 可以根据需要扩展关键词
4. **可以强制跳过**: 使用 `--force` 参数，但不推荐

## 未来扩展

- [ ] 自动检测上传的文件类型（模板/源码/开题报告）
- [ ] 根据模板自动调整守卫规则
- [ ] 记录每次守卫检查的历史
- [ ] 支持更多语言的意图识别
