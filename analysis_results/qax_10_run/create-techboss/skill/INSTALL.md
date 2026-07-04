# 安装指南 — TechBoss.skill

> 三种方式，从最简到最全，选一种就够了。

---

## 方式一：Claude Code（推荐，5 分钟搞定）

### macOS / Linux

```bash
# 全局安装（所有项目都能用）
git clone https://github.com/wentao3225/techboss-skill ~/.claude/skills/create-techboss

# 项目级安装（只在当前项目里用）
git clone https://github.com/wentao3225/techboss-skill .claude/skills/create-techboss
```

### Windows（PowerShell）

```powershell
# 全局安装
git clone https://github.com/wentao3225/techboss-skill "$env:USERPROFILE\.claude\skills\create-techboss"

# 项目级安装
git clone https://github.com/wentao3225/techboss-skill .claude\skills\create-techboss
```

### 验证安装

在 Claude Code 里输入：
```
/create-techboss-demo
```

如果看到三个 Tech Boss 被创建（王CTO / 张TL / 李EM），安装成功。

---

## 方式二：VS Code + GitHub Copilot Chat

### 1. 安装 GitHub Copilot Chat 扩展

确保已安装 [GitHub Copilot Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat)（版本 ≥ 0.22）。

### 2. Clone 到 skills 目录

```bash
# macOS / Linux
git clone https://github.com/wentao3225/techboss-skill ~/.agents/skills/create-techboss

# Windows（PowerShell）
git clone https://github.com/wentao3225/techboss-skill "$env:USERPROFILE\.agents\skills\create-techboss"
```

### 3. 在 VS Code 中使用

打开 Copilot Chat 面板，输入：
```
@create-techboss /create-techboss-demo
```

或者在 Agent 模式下直接输入：
```
/create-techboss
```

---

## 方式三：OpenClaw

```bash
git clone https://github.com/wentao3225/techboss-skill ~/.openclaw/workspace/skills/create-techboss
```

重启 OpenClaw，在工作区输入 `/create-techboss` 即可。

---

## 方式四：其他 AI CLI 工具

将仓库 clone 到你的 AI 工具的 skills/plugins 目录。TechBoss.skill 使用标准 OpenClaw 格式，兼容大多数支持该格式的工具。

---

## 创建你的第一个 Tech Boss

### 方法 A：使用 Demo 预设（最快）

安装完成后立即运行：
```
/create-techboss-demo
```

这会创建三个预置老板：**王CTO**（微服务传教士）、**张TL**（O(n²)侦探）、**李EM**（OKR炼金术师）。

### 方法 B：从数据文件创建

```bash
# 从示例 JSON 创建
python3 tools/create_techboss.py --from-example 王CTO --skills-dir ~/.claude/skills

# 从自定义 JSON 创建
python3 tools/create_techboss.py --from-file my_boss.json --skills-dir ~/.claude/skills
```

### 方法 C：直接在工具里创建

```
/create-techboss
```

按提示输入老板信息即可。

---

## 目录结构说明

安装后的 skill 目录结构：

```
~/.claude/skills/
└── create-techboss/          ← TechBoss.skill 主目录
    ├── SKILL.md              ← 主 skill 入口（AI 读取）
    ├── references/
    │   └── prompts/          ← 6 个功能模块 prompt
    ├── examples/             ← 3 个示例老板数据
    └── tools/                ← 数据解析工具

~/.claude/skills/
└── 王CTO/                    ← 创建的具体老板 skill
    ├── SKILL.md              ← 老板专属 skill 入口
    └── assets/
        ├── tech_management.md
        ├── tech_persona.md
        ├── profile.md
        ├── evidence.md
        └── prompts/          ← 复制的功能模块
```

---

## 升级

```bash
cd ~/.claude/skills/create-techboss
git pull
```

---

## 卸载

```bash
# 删除 TechBoss.skill 主目录
rm -rf ~/.claude/skills/create-techboss

# 删除某个具体老板（可选）
rm -rf ~/.claude/skills/王CTO
```

---

## 常见问题

**Q: `/create-techboss` 没有反应？**
A: 检查 clone 路径是否正确，skill 目录名必须是 `create-techboss`（和 SKILL.md 里的 `name` 字段一致）。

**Q: 创建 Demo 老板时报错"examples/ not found"？**
A: 当前工作目录不对，切换到 `create-techboss` 目录后重试，或使用绝对路径 `--from-example 王CTO`。

**Q: Python 报错？**
A: 需要 Python 3.9+。`python3 --version` 确认版本。核心功能不需要额外安装包，只有自动采集器才需要 `pip install -r requirements.txt`。

**Q: 可以同时管理多个老板吗？**
A: 可以。每次运行 `/create-techboss` 或 `--from-file` 都会在 skills-dir 下创建独立目录。用 `/王CTO`、`/张TL` 分别调用。
