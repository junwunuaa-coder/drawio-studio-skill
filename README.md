# Drawio Studio Skill

一个用于**快速生成、编辑、导出 drawio 图**的技能仓库。

> 目标：既能用模板秒出图，也能做完整图编辑（节点、连线、页面、样式、导出）。
>
> 设计原则：**不依赖外部代码仓库**，核心能力全部内置在本 Skill 中。

---

## 核心能力

## 1) 多风格模板（内置）

- **handdrawn**：手绘白板风
- **clean**：极简商务风
- **dark-tech**：深色科技风

支持从模板快速创建 `.drawio` 文件，并在创建时做文本替换。

---

## 2) 完整图编辑能力

该 Skill 提供完整操作分组：

### Project（项目）
- 新建图、打开图、保存
- 查看项目信息
- 查看原始 XML
- 查看页面尺寸预设

### Shape（节点）
- 增加节点（多种形状）
- 删除节点
- 查询节点列表与详情
- 修改节点文本
- 移动、缩放节点
- 设置节点样式（填充色、边框色、字号、圆角等）

### Connect（连线）
- 新增连线
- 删除连线
- 修改连线文案
- 设置连线样式（直线/直角/曲线等）
- 查询连线列表

### Page（多页）
- 新增页
- 删除页
- 重命名页
- 列出所有页

### Export（导出）
- 导出 `png / pdf / svg / vsdx / xml`
- 支持页码、缩放、宽高、透明背景、裁剪等参数

### Session（会话）
- 查看状态
- undo / redo
- 会话持久化与恢复

---

## 快速开始

## A. 模板能力（无需额外步骤）

```bash
python3 scripts/diagram_studio.py template list
python3 scripts/diagram_studio.py template create --style clean --output ~/Desktop/ai/my-arch.drawio
```

支持替换文案：

```bash
python3 scripts/diagram_studio.py template create \
  --style dark-tech \
  --output ~/Desktop/ai/my-arch.drawio \
  --replacements '{"Architecture Diagram (Dark Tech Template)":"权限系统总览"}'
```

## B. 完整编辑能力（零外部仓库依赖）

无需下载任何第三方代码仓库，脚本可直接本地读写 `.drawio` XML：

```bash
python3 scripts/diagram_studio.py project new --preset 16:9 -o ~/Desktop/ai/demo.drawio
python3 scripts/diagram_studio.py --project ~/Desktop/ai/demo.drawio shape add rectangle -l "API Gateway" --x 120 --y 120
python3 scripts/diagram_studio.py --project ~/Desktop/ai/demo.drawio shape list
```

导出说明：
- 导出 `.drawio/.xml`：内置支持
- 导出 `png/pdf/svg/vsdx`：需要本机安装 draw.io Desktop（或设置 `DRAWIO_STUDIO_DRAWIO_BIN`）

示例：

```bash
python3 scripts/diagram_studio.py --project ~/Desktop/ai/demo.drawio export render ~/Desktop/ai/demo.png -f png --overwrite
```

查看全部分组说明：

```bash
python3 scripts/diagram_studio.py help-ops
```

---

## 项目结构

```text
drawio-studio-skill/
├─ SKILL.md
├─ README.md
├─ LICENSE
├─ assets/
│  └─ templates/
│     ├─ architecture-handdrawn.drawio
│     ├─ architecture-clean.drawio
│     └─ architecture-dark-tech.drawio
├─ scripts/
│  ├─ diagram_studio.py
│  ├─ create_from_template.py
│  └─ list_templates.py
└─ references/
   └─ style-guide.md
```

---

## 典型场景

- 技术架构图（分层、模块、调用链）
- 业务流程图（状态流、审批流）
- 排障图（问题路径、恢复路径）
- 会议复盘图（阶段与责任人）

---

## 可扩展方向（Roadmap）

- 泳道图模板
- 时序图模板
- 组织结构图模板
- 自动配色与排版规则
- 双语模板（中英切换）

---

## License

MIT
