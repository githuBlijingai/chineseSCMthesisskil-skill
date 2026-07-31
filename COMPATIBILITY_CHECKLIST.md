# Chinese Thesis Workbench - 跨设备兼容性检查清单

## 首次使用检查清单

### 1. Python 环境
- [ ] Python 3.8+ 已安装
- [ ] pip 可用

### 2. 依赖安装
```bash
pip install -r requirements.txt
```
- [ ] pdfplumber
- [ ] pypdf
- [ ] python-docx
- [ ] PyYAML
- [ ] playwright>=1.40.0

### 3. 浏览器准备（二选一）

#### 方案A：使用本地浏览器（推荐）
确保以下浏览器之一已安装：
- [ ] Google Chrome
- [ ] Microsoft Edge
- [ ] Mozilla Firefox

skill会自动检测并使用本地浏览器。

#### 方案B：自动下载 Chromium
```bash
playwright install chromium
```
- [ ] 约100MB下载空间
- [ ] 网络连接正常（国内CDN）

### 4. 初始化工作空间
```bash
python scripts/workspace/init_thesis_workspace.py
```
- [ ] 从 `assets/thesis-ai-standard/` 复制模板到工作目录
- [ ] 创建 `paper-context/` 和 `paper-output/` 目录

### 5. 配置学校规范
编辑 `thesis-ai-standard/templates/standard-profile.yaml`：
- [ ] 学校名称
- [ ] 学院/专业
- [ ] 论文格式要求

### 6. 配置论文信息
编辑 `thesis-ai-standard/templates/thesis-ai-spec.yaml`：
- [ ] 论文标题
- [ ] 作者信息
- [ ] 摘要内容
- [ ] 章节大纲

### 7. 测试 CNKI 检索
```bash
python scripts/literature/test_cnki_search.py
```
- [ ] 检测到本地浏览器 或 成功下载 Chromium
- [ ] 成功检索到知网文献

### 8. 测试论文生成
```bash
# 生成摘要
python scripts/docx/auto_generate_abstract.py \
    --body paper-output/thesis-body.md \
    --spec thesis-ai-standard/templates/thesis-ai-spec.yaml

# 生成完整论文
python scripts/docx/build_complete_thesis.py \
    --spec thesis-ai-standard/templates/thesis-ai-spec.yaml \
    --body paper-output/thesis-body.md \
    --output paper-output/
```
- [ ] 成功生成DOCX文件
- [ ] 包含摘要、目录、正文、参考文献、致谢

## 常见问题排查

### Q1: Playwright 未安装
**症状**: `ModuleNotFoundError: No module named 'playwright'`
**解决**: `pip install playwright`

### Q2: 找不到本地浏览器
**症状**: `未找到本地浏览器`
**解决**: 
- 安装 Chrome/Edge/Firefox
- 或运行 `playwright install chromium`

### Q3: 无法访问 CNKI
**症状**: 搜索超时或返回空结果
**解决**:
- 检查网络连接
- CNKI可能有反爬，稍后再试
- 考虑手动提供参考文献

### Q4: 生成DOCX失败
**症状**: `ImportError: No module named 'docx'`
**解决**: `pip install python-docx`

## 平台兼容性

| 操作系统 | 状态 | 说明 |
|----------|------|------|
| Windows 10/11 | ✅ 完全支持 | 主要测试平台 |
| macOS | ⚠️ 理论支持 | 浏览器路径需适配 |
| Linux | ⚠️ 理论支持 | 需安装Chrome/Firefox |

## 最低系统要求

- **内存**: 4GB+（推荐8GB）
- **磁盘**: 500MB+ 可用空间
- **网络**: 首次使用需下载Playwright浏览器（约100MB）
- **浏览器**: Chrome/Edge/Firefox 任一（或自动下载Chromium）
