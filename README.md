# Drawio Studio Skill

一个用于**快速生成与美化 drawio 架构图/流程图**的技能仓库。

> 目标：让你在几分钟内得到可展示、可复用、可二次编辑的 `.drawio` 图文件。

---

## 功能总览

### 1) 多风格模板（开箱即用）

仓库内置 3 套模板：

- **手绘风（handdrawn）**
  - 适合白板分享、教学、故事化讲解
  - 圆角卡片、柔和配色、草图感视觉

- **极简商务风（clean）**
  - 适合汇报文档、PRD、方案评审
  - 分层清晰、箭头规整、文本可读性高

- **深色科技风（dark-tech）**
  - 适合路演、技术宣讲、投屏展示
  - 深色背景 + 高对比色，视觉冲击更强

---

### 2) 模板快速生成

支持从模板一键生成新图文件，避免重复搭骨架。

```bash
python3 scripts/create_from_template.py --template clean --output ~/Desktop/ai/my-architecture.drawio
```

---

### 3) 文本批量替换

支持在生成时替换标题/模块文案，快速产出定制版本。

```bash
python3 scripts/create_from_template.py \
  --template dark-tech \
  --output ~/Desktop/ai/my-architecture.drawio \
  --replacements '{"Architecture Diagram (Dark Tech Template)":"权限系统总览"}'
```

---

### 4) 结构化图层建议

模板默认采用分层结构，便于统一团队表达：

- Layer 1：平台/打包层
- Layer 2：API 与 Service 层
- Layer 3：UI/交互层
- Layer 4：测试/验证层

并预置主链路箭头（调用、执行、状态回流）。

---

### 5) 可扩展模板体系

你可以继续按同样规范新增模板：

- `assets/templates/architecture-xxx.drawio`
- 在 `scripts/create_from_template.py` 注册即可复用

---

## 项目结构

```text
drawio-studio-skill/
├─ SKILL.md
├─ README.md
├─ assets/
│  └─ templates/
│     ├─ architecture-handdrawn.drawio
│     ├─ architecture-clean.drawio
│     └─ architecture-dark-tech.drawio
├─ scripts/
│  ├─ list_templates.py
│  └─ create_from_template.py
└─ references/
```

---

## 使用方法

### 1. 查看可用模板

```bash
python3 scripts/list_templates.py
```

### 2. 生成图文件

```bash
python3 scripts/create_from_template.py --template handdrawn --output ~/Desktop/ai/demo.drawio
```

### 3. 用 draw.io / diagrams.net 打开并继续编辑

- 调整模块文本
- 调整连线
- 导出 PNG / PDF

---

## 适用场景

- 技术架构讲解
- 业务流程梳理
- 权限与调用链说明
- 项目复盘图示
- 会议纪要图形化

---

## 后续可扩展能力（Roadmap）

- 自动生成泳道图模板
- 自动生成时序图模板
- 自动生成多页图（overview + detail）
- 增加中英双语模板

---

## License

MIT
