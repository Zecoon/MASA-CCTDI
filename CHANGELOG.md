# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

## [1.0.0] - 2024-10-12

### Added

#### 核心系统
- 🤖 **四智能体协作架构**
  - ScenarioDirectorAgent（导演智能体）- 系统总控制器
  - AdaptiveNavigatorAgent（导航智能体）- 自适应用户交互
  - DiagnosticAgent（诊断智能体）- 信息充足性判断
  - ScoringAgent（评分智能体）- 精细化评分系统

#### 评估功能
- 📊 **CCTDI 7维度评估**
  - 寻找真理、开放思想、分析能力、系统化能力
  - 批判性思维自信、求知欲、认知成熟度
  - 每维度10-60分，总分420分

#### 交互模式
- 💬 **三种自适应交互模式**
  - 鼓励模式：针对消极或简短回答
  - 正常模式：标准对话流程
  - 追问模式：深入探索详细回答

#### 智能诊断
- 🔍 **3-5轮自适应诊断**
  - 智能判断信息充足性
  - 动态调整交互轮次
  - 避免过度或不足评估

#### 三种运行模式
- 🖥️ **CLI命令行版本** (`cctdi_system.py`)
  - 交互式命令行界面
  - 适合单用户实时评估
  - 完整的对话记录和评估报告

- 🌐 **Web界面版本** (`web_app.py`)
  - 基于Streamlit的现代化Web界面
  - 支持多用户并发访问
  - 实时进度追踪和可视化
  - 在线下载评估报告

- ⚡ **并发测试版本** (`auto_simu_concurrent.py`)
  - 基于ThreadPoolExecutor的多线程并发
  - 虚拟用户自动化测试
  - 线程安全的文件写入
  - 批量测试和性能优化

#### 数据管理
- 💾 **完整的数据记录系统**
  - CSV对话记录（详细交互历史）
  - JSON评估报告（结构化评估结果）
  - 用户评分汇总表（快速对比分析）

#### 虚拟用户系统
- 👥 **虚拟用户画像支持**
  - 基于LLM的虚拟用户回答生成
  - 支持自定义用户画像
  - 批量自动化测试

### Features

- **多语言模型支持**: 兼容OpenAI API及各类第三方兼容接口
- **环境变量配置**: 使用.env文件管理API密钥，提高安全性
- **错误重试机制**: LLM调用失败自动重试（最多3次）
- **线程安全**: 并发版本实现完整的线程安全机制
- **详细日志**: 完整的时间戳和状态追踪

### Documentation

- 📖 **完整的项目文档**
  - 详细的README.md（577行）
  - 系统架构说明
  - API使用文档
  - 故障排除指南

- 📝 **代码注释**
  - 完整的函数和类注释
  - 清晰的代码结构
  - 便于二次开发

### Configuration

- ⚙️ **灵活的配置系统**
  - 支持环境变量配置
  - 可自定义模型和参数
  - 适配多种部署环境

---

## [Unreleased]

### Planned Features (v2.0)

- 🌐 多语言支持（英文、日文等）
- 📊 实时评分可视化
- 📈 历史数据对比分析
- 🎨 自定义评估维度
- 🎤 语音交互支持
- 📱 移动端APP

### Long-term Roadmap

- 多模态评估（图像、视频）
- 群体评估模式
- 教师/HR管理后台
- 数据分析与报告生成
- 云服务部署

---

## Version History

- **1.0.0** (2024-10-12): 首次发布，包含完整的四智能体系统和三种运行模式

---

## Notes

- 本项目基于Apache License 2.0开源
- 欢迎提交Issue和Pull Request
- 更多信息请查看[README.md](README.md)

[1.0.0]: https://github.com/zecoon/MASA-CCTDI/releases/tag/v1.0.0
[Unreleased]: https://github.com/zecoon/MASA-CCTDI/compare/v1.0.0...HEAD
