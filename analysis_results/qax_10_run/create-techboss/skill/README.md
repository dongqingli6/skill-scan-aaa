<div align="center">

# TechBoss.skill

> *"不是哥们，我把程序员老板炼成 AI 了。"*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-orange)](https://github.com/openclaw)
[![Based on boss-skill](https://img.shields.io/badge/Based%20on-boss--skill-green)](https://github.com/nicepkg/boss-skill)

<br>

你的 Tech Lead 说这个需求"很简单，明天上线"，然后你改了两周？<br>
你的 EM 在全组面前说"你这个 O(n²) 了吧"，然后给不出优化方向？<br>
你的 CTO 每季度画一张微服务蓝图，然后说"先做 MVP，重构排下期"？<br>
你的架构师说"这个和我们系统不搭"，但他三年没写过生产代码？<br>
你的老板说"先把 tech debt 记着，下个 Sprint 还"，TODO comment 至今无人认领？<br>

**他把你的代码说成 shit mountain？没关系。AI 可以把他炼成 shit mountain 鉴赏家然后存档。**

<br>

一句话描述你的 Tech Boss → 生成专属 AI 替身<br>
**12 个实战模式**：代码审查 PUA 检测 · 技术大饼鉴定 · 架构质疑演练 · Tech Debt 甩锅分析 · PR 风格复刻 · 站会翻车预测 · 汇报优化器 · 反击话术三档<br>
整活的外壳，**认真保护 CRUD 工程师**的内核

[功能特性](#功能特性) · [安装](#安装) · [命令大全](#命令大全) · [数据喂养](#数据喂养) · [效果示例](#效果示例)

</div>

---

## 这是什么

`TechBoss.skill` 是基于 [nicepkg/boss-skill](https://github.com/nicepkg/boss-skill) 改造的**程序员专用版本**。

原版支持各类职场老板，TechBoss 专门针对**技术管理者（Tech Lead / Engineering Manager / CTO / 架构师）**，深度还原他们的：

- 🔬 代码审查 PUA 风格（"你这个不够 clean""这里应该用 Strategy Pattern"）
- 🍕 技术大饼话术（"MVP 完再优化""下个 Sprint 重构"）
- 🏛️ 架构会议表演（引用 Netflix 博客、质疑 scalability、推翻一切）
- 🔄 甩锅路径图谱（基础设施 → 团队年轻化 → 上游依赖 → 产品需求）
- 📊 指标崇拜表现（coverage % / P99 / error rate 三件套）

---

## 功能特性

### 程序员完整受难旅程：提 PR → 被审判 → 接受大饼 → 翻篇

**第一层：看清楚（到底发生了什么）**

| 模式 | 命令 | 说明 |
|------|------|------|
| **代码审查 PUA 检测** | `/{boss} review` | 拆解 review 评论，8大PUA手法 + 8大流派鉴定 |
| **技术大饼鉴定** | `/{boss} cake` | 5维度量化饼指数，告诉你这个重构承诺能不能信 |
| **Tech Debt 甩锅分析** | `/{boss} debt` | 预测他会怎么把此次问题甩给基础设施/团队/产品 |

**第二层：接招（学会怎么应对）**

| 模式 | 命令 | 说明 |
|------|------|------|
| **反击话术** | `/{boss} fight` 或输入 **草** | 三档：职场安全版 / 架构阴阳版 / 摊牌版 |
| **架构质疑演练** | `/{boss} arch` | 提前练习如何应对他对架构的否定 |
| **老板心理预测** | `/{boss} predict` | 评审会 / 1v1 前必用，预判雷区和甜区 |
| **汇报优化器** | `/{boss} report` | 用他的黑话重写你的 Jira / 周报 / 方案 |
| **PR Review 风格** | `/{boss} pr` | 模拟他写 PR 评论的风格，提前准备应对 |

**第三层：翻篇（准备好了就走）**

| 模式 | 命令 | 说明 |
|------|------|------|
| **技术决策翻车** | `/{boss} karma` | 互动文字游戏，复盘他的错误技术决策 |
| **站会模拟** | `/{boss} standup` | 模拟他在 Daily Standup 的神操作 |
| **替代公告** | `/{boss} replace` | 生成"本 CTO 已被 AI 替代"正式公告（整活） |

---

### "草"——史上最短的技术反击命令

在**任何模式**下，输入 **草** 即可触发技术反击话术。

不管是被说"O(n²)"还是被说"不够 production ready"，第一反应都是草。  
我们只是把这个草接住了，然后转化成三档专业话术。

---

### 8 大代码审查 PUA 流派鉴定

不只告诉你"这是 PUA"——还告诉你是哪个**门派**的技术 PUA：

🔬 **性能偏执派**（先问 O(n²)，哪怕数据量是 50 条）
🏛️ **SOLID 传教士**（每个 PR 必提设计原则，用原则否定实现）
☁️ **云原生布道者**（万物皆容器，不用 K8s 就落后了）
📊 **指标崇拜者**（coverage、latency、error rate 三件套压人）
🧩 **微服务原教旨**（反对任何单体思维，拆了再说）
📚 **设计模式考官**（每个函数都要有模式名，否则不专业）
🌐 **大厂最佳实践**（Netflix / Google / Airbnb 随时引用压人）
🧹 **代码洁癖患者**（主观审美包装成客观技术标准）

---

## 命令大全

```bash
# 创建 Tech Boss
/create-techboss

# 快速体验
/create-techboss-demo

# 核心功能示例（以 王CTO 为例）
/王CTO                    # 直接和 AI Tech Boss 对话，感受你的每日受难
/王CTO review             # 粘贴他的 code review 评论，AI 帮你拆解
/王CTO cake "下个季度微服务改造完成你来主导，到时候tech lead就是你的"
/王CTO fight              # 反击话术三档
/王CTO predict 架构评审    # 明天开架构会，先预判他会说什么
/王CTO report             # 用他的黑话重写你的周报
/王CTO debt               # 分析这个新需求会新增多少 tech debt
/王CTO pr                 # 模拟他评审这个 PR 会写什么
/王CTO standup            # 今天站会模拟
/王CTO arch               # 我有个架构方案，先过一遍他的质疑
/王CTO karma              # 复盘他的经典翻车决策，寓教于乐
/王CTO replace            # 生成"本 CTO 已被 GPT-99 替代"公告
草                        # 任何时候说"草"触发反击模式
```

---

## 快速体验

```bash
/create-techboss-demo
```

立刻体验三个预置 Tech Boss：

| 代号 | 身份 | 标签 | 推荐试玩 |
|------|------|------|---------|
| 王CTO | 互联网中厂 CTO | 微服务传教士 · 架构审判庭 · 大饼专家 | `/王CTO karma` |
| 张TL | 卷王 Tech Lead（前字节） | O(n²)侦探 · 单测覆盖率暴君 · 设计模式考官 | `/张TL review [你的代码]` |
| 李EM | B轮创业 EM | OKR炼金术士 · 敏捷布道师 · 上线再说论者 | `/李EM cake "Q3重构完你升P7"` |

---

## 安装

### Claude Code（推荐）

```bash
# Clone 到你的 Claude Code skills 目录
git clone https://github.com/wentao3225/techboss-skill ~/.claude/skills/create-techboss

# 或项目级安装
git clone https://github.com/wentao3225/techboss-skill .claude/skills/create-techboss
```

然后在 Claude Code 里直接运行：
```
/create-techboss
```

### OpenClaw

```bash
git clone https://github.com/wentao3225/techboss-skill ~/.openclaw/workspace/skills/create-techboss
```

### VS Code + GitHub Copilot Chat

详细步骤见 [INSTALL.md](INSTALL.md)

### 其他 AI CLI 工具

将本仓库 clone 到你的 AI CLI 的 skills 目录即可，无额外依赖。

---

## 数据喂养

> 喂的数据越多，AI Tech Boss 越像。
> 他写的每一条 review 评论，都是训练他 AI 替身的养料。

### 支持的数据源

| 数据类型 | 工具 | 效果 |
|---------|------|------|
| GitHub PR 评论 | 导出 JSON 或截图 | 最高质量（有代码上下文） |
| 飞书群消息 | 自动采集工具 | 还原日常沟通风格 |
| Jira 评论 | 导出 CSV | 还原任务推进风格 |
| 代码 Review 截图 | 直接 Read | 提取评论原话 |
| 会议纪要 / 录音转文字 | 粘贴文本 | 还原讲话风格 |
| 口述描述 | 直接输入 | 兜底方案，一句话也行 |

详细指南见 [DATA_FEEDING.md](DATA_FEEDING.md)

---

## 效果示例

### 代码审查 PUA 检测

输入他的 review 评论：
```
"这个 UserService 太臃肿了，SRP 完全没有遵守，整体来说不 production ready"
```

输出：
```
PUA 系数：82/100（SOLID传教士流派，混合可维护性恐吓）

◉ "SRP没有遵守" → 只有结论没有具体问题，建议回复：
  "能指出哪个方法需要拆分到哪个类吗？我按你的建议来"

◉ "不production ready" → 极度模糊，用来堵死 PR 的万能话术
  建议回复："production ready 的 checklist 在哪？我逐项对照"

真实 bug：没有（这次 review 是纯审美批评）
💡 草 → 三档怼回去话术
```

---

### 技术大饼鉴定

输入他的承诺：
```
"下个季度微服务改造，你来主导，tech lead 就是你的"
```

输出：
```
🥧 饼指数：79/100（大饼）

"你来主导" = 你背锅，他摘果子
"tech lead" = 没有 headcount 审批的虚画职位
"下个季度" = 产品需求永远排满，重构永远推后

建议：让他把微服务改造写成 RFC，tech lead 要对应职级晋升申请
```

---

## 相关项目

> - [boss-skill](https://github.com/nicepkg/boss-skill) —— 通用版老板蒸馏，本项目的上游
> - TechBoss.skill —— 专属程序员老板，你现在在这
>
> 赛博自保一条龙，从代码 review 到架构评审，老板的每一句话都可以被解构 🛡️

---

## License

MIT — 随便用，随便改，记得打工人互助，把工具传下去。

---

<div align="center">

*"他叫你 CRUD 工程师，但他连 CRUD 都让你写"*

*"他说你代码不够 clean，但他的 TODO comment 已经三年没还"*

*"他说 AI 会替代程序员，但他的决定已经先被 AI 复刻了"*

</div>
