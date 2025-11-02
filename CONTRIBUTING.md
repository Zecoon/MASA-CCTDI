# 贡献指南

感谢您对 MASA-CCTDI 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复或新功能
- 🌐 翻译文档

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [提交指南](#提交指南)
- [代码规范](#代码规范)
- [Pull Request流程](#pull-request流程)

---

## 行为准则

参与本项目即表示您同意遵守我们的行为准则：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

---

## 如何贡献

### 报告 Bug

在提交 Bug 报告之前，请先搜索[现有 Issues](https://github.com/zecoon/MASA-CCTDI/issues)，确保问题尚未被报告。

提交 Bug 时，请包含：

- **清晰的标题**：简洁描述问题
- **详细描述**：问题是什么，期望行为是什么
- **复现步骤**：如何重现该问题
- **环境信息**：Python版本、操作系统、依赖版本等
- **错误日志**：完整的错误堆栈信息
- **截图**（如适用）：帮助说明问题

### 提出功能建议

功能建议应该包含：

- **清晰的用例**：为什么需要这个功能
- **详细描述**：功能的具体行为
- **替代方案**：是否考虑过其他实现方式
- **附加信息**：示意图、参考链接等

---

## 开发环境设置

### 1. Fork 并克隆仓库

```bash
# Fork 仓库（在GitHub网页上点击Fork按钮）

# 克隆您的 Fork
git clone https://github.com/your-username/MASA-CCTDI.git
cd MASA-CCTDI

# 添加上游仓库
git remote add upstream https://github.com/zecoon/MASA-CCTDI.git
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest black flake8
```

### 4. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填写您的API密钥
```

### 5. 验证安装

```bash
# 运行CLI版本测试
python cctdi_system.py cli

# 运行Web版本测试
streamlit run web_app.py
```

---

## 提交指南

### Git 提交规范

我们使用[约定式提交](https://www.conventionalcommits.org/zh-hans/)规范：

```
<类型>(<范围>): <简短描述>

<详细描述>（可选）

<页脚>（可选）
```

**类型**：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构（既不是新功能也不是Bug修复）
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

**示例**：
```
feat(agents): 添加新的评估维度支持

实现了对自定义评估维度的支持，允许用户扩展CCTDI量表。

Closes #123
```

---

## 代码规范

### Python代码风格

遵循 [PEP 8](https://peps.python.org/pep-0008/) 代码规范：

```python
# 使用 black 格式化代码
black cctdi_system.py

# 使用 flake8 检查代码
flake8 cctdi_system.py
```

### 命名约定

- **类名**：使用 `PascalCase`（如 `ScenarioDirectorAgent`）
- **函数名**：使用 `snake_case`（如 `generate_question`）
- **常量**：使用 `UPPER_SNAKE_CASE`（如 `MAX_RETRIES`）
- **私有方法**：前缀 `_`（如 `_call_llm`）

### 文档字符串

使用 docstring 注释函数和类：

```python
def generate_question(self, dimension_id: int) -> str:
    """
    生成针对指定维度的评估问题

    Args:
        dimension_id: 维度编号（1-7）

    Returns:
        str: 生成的问题文本

    Raises:
        ValueError: 如果维度编号无效
    """
    pass
```

### 类型注解

优先使用类型注解提高代码可读性：

```python
from typing import Dict, List, Optional

def process_response(user_input: str, context: Optional[Dict] = None) -> List[str]:
    """处理用户响应"""
    pass
```

---

## Pull Request流程

### 1. 创建分支

```bash
# 确保主分支是最新的
git checkout main
git pull upstream main

# 创建新分支
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 进行代码修改

# 运行测试（如果有）
pytest

# 格式化代码
black .

# 检查代码风格
flake8 .
```

### 3. 提交更改

```bash
# 添加修改的文件
git add .

# 提交（遵循提交规范）
git commit -m "feat: 添加新功能描述"

# 推送到您的 Fork
git push origin feature/your-feature-name
```

### 4. 创建 Pull Request

1. 访问您的 Fork 仓库页面
2. 点击 "New Pull Request" 按钮
3. 填写 PR 标题和描述：
   - **标题**：简洁描述更改内容
   - **描述**：详细说明更改原因、实现方式、测试情况
   - **关联 Issue**：使用 `Closes #123` 关联相关Issue

4. 提交 PR 并等待审查

### 5. 响应审查意见

- 及时响应 Reviewer 的评论
- 根据反馈修改代码
- 推送新的提交到同一分支（PR会自动更新）

```bash
# 修改代码后
git add .
git commit -m "fix: 根据审查意见修改XX"
git push origin feature/your-feature-name
```

---

## 版本发布流程

版本发布由项目维护者负责：

1. 更新 `CHANGELOG.md`
2. 更新版本号
3. 创建 Git tag
4. 发布到 GitHub Releases

---

## 许可协议

通过向本项目贡献代码，您同意您的贡献将在 [Apache License 2.0](LICENSE) 下发布。

---

## 获取帮助

如有任何问题，您可以：

- 📧 发送邮件至维护者
- 💬 在 [Discussions](https://github.com/zecoon/MASA-CCTDI/discussions) 中提问
- 📝 提交 [Issue](https://github.com/zecoon/MASA-CCTDI/issues)

---

**感谢您的贡献！** 🎉
