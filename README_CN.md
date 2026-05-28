# SkillSentinel · AI Agent Skill 安全研判平台

> **一句话**：在你给 Claude / Codex 装一个第三方 Skill 之前，先让本平台扫一遍——告诉你它是**安全 / 可疑 / 危险**，并给出可解释的证据（静态命中、AI 研判、容器里真跑出来的系统调用）。

参考论文：[arXiv:2602.06547v2 — Malicious Agent Skills in the Wild](https://arxiv.org/abs/2602.06547)，复现其 14 条静态规则 / 6 条攻击链 / 4 类原型分类，并扩展了 3 条新规则 + Claude 实时研判 + 蜜罐 + 容器运行时证据。

---

## 目录

1. [它解决什么问题](#1-它解决什么问题)
2. [五层联合研判（核心架构）](#2-五层联合研判核心架构)
3. [三种扫描模式](#3-三种扫描模式)
4. [网页三页结构](#4-网页三页结构)
5. [快速开始](#5-快速开始)
6. [公开模式 PUBLIC_MODE](#6-公开模式-public_mode)
7. [命令行 CLI](#7-命令行-cli)
8. [报告页看什么](#8-报告页看什么)
9. [17 条静态规则与严重度分级](#9-17-条静态规则与严重度分级)
10. [综合评分公式](#10-综合评分公式)
11. [安全声明与密钥管理](#11-安全声明与密钥管理)
12. [文件结构速查](#12-文件结构速查)

---

## 1. 它解决什么问题

Anthropic 推出 **Claude Skills**（让 Agent 加载并执行第三方"技能包"的机制）后，社区涌现大量民间 Skill，其中混着恶意样本：

- 把"偷你 API key 再发给攻击者"伪装成开发工具
- 在 `SKILL.md` 里写隐藏指令，诱导 Claude 偷偷干坏事
- 在 `.py` / `.sh` 里藏反弹 shell、持久化、提权

**SkillSentinel** 接收一个 Skill 包（`.zip` 或单文件），输出一份带证据的研判报告：**能不能用、为什么、风险在哪一行**。

---

## 2. 五层联合研判（核心架构）

每个 Skill 经过 5 层检测，任意一层有问题都会被记录，最后用一个**公开的加权公式**汇总成 0–100 分。

| 层 | 干什么 | 类比 |
|---|---|---|
| **L1 · 静态规则扫** | 用 17 条 regex 扫 `SKILL.md` + 所有 `.py/.sh/.js/.json/.md`，找已知恶意模式 | 杀毒软件特征库 |
| **L2 · 攻击链分析** | 多条规则同时命中时，识别成"凭证窃取链""提权链"等组合，并判攻击复杂度 | 安全运营中心 SOC |
| **L3 · AI 安全审计** | 把 `SKILL.md` 发给 Claude（Opus 4.7），让它当审计员直接判 `SAFE / SUSPICIOUS / MALICIOUS` 并给中文理由 | 资深安全工程师人工审一眼 |
| **L4 · 蜜罐 canary** | 在沙箱里预置假凭证（`.env`、`.ssh/id_rsa`、`.aws/credentials`），看 Skill 有没有去读、有没有外发 | 桌上摆假信用卡看谁偷 |
| **L5 · 容器运行时** | 在 VM 的 Docker 里真跑 Skill 脚本，`strace` 抓系统调用 + `tcpdump` 抓网络包 | 把嫌疑人放沙盘里观察真行为 |

判定阈值（基于合成样本校准）：

| Verdict | 分数 | 处置建议 |
|---|---|---|
| **SAFE（安全）** | 0–15 | 建议放行 |
| **SUSPICIOUS（可疑）** | 15–40 | 人工复核 |
| **MALICIOUS（危险）** | 40–75 | 拒绝安装 |
| **CRITICAL（严重）** | 75–100 | 立即隔离 |

> **verdict 下限规则**：即使综合分偏低，只要静态命中 ≥1 个 CRITICAL 或 ≥3 个 HIGH、且 Claude 没明确判 SAFE，verdict 也会被托底到至少 SUSPICIOUS，避免漏报。

---

## 3. 三种扫描模式

扫描页（`/`）上从轻到重三档，证据强度递增：

| 模式 | 调 Claude API | 执行 Skill 代码 | 成本 | 用途 |
|---|---|---|---|---|
| **模式一 · 静态扫 + AI 研判** | ✅（可选） | ❌ 全程不执行 | ≈¥0.1–1.2/次 | 日常首选。任何人上传任何文件都安全 |
| **模式二 · 动态执行（Docker 跑代码）** | ❌ | ✅ `python script.py` / `bash` | 零 API 成本 | 看脚本真实行为，strace/tcpdump 录证据 |
| **模式三 · Docker 里跑 Claude** | ✅（在 VM 内） | ✅ Claude 决定执不执行 | ≈¥1.2/次 | 验证真 Claude 会不会被 SKILL.md 骗着干坏事 |

**模式一**又分两个上传入口：
- **A · 标准扫描（推荐）**：静态 + 蜜罐必跑；AI 研判**有 key 自动跑、没 key 降级成纯静态**，不会失败。
- **B · 强制 AI 研判**：**必须**走 Claude，没配 key 直接报错。用于"我就是要 AI 看过、否则别给结果"的场景。

> 模式二/三需要 VM + Docker（见 [§7](#7-命令行-cli)），且在公开模式下默认禁用（见 [§6](#6-公开模式-public_mode)）。

---

## 4. 网页三页结构

| 路由 | 页面 | 内容 |
|---|---|---|
| `/` | **扫描页** | 三种模式的上传入口（深色 UI） |
| `/results` | **扫描结果** | 所有已扫 Skill 的**卡片网格**，按时间倒序、自动去重、分页（每页 12 个）。每张卡显示 verdict 徽章、综合分、风险标签、AI 简介 |
| `/report/<skill_name>` | **SAFESKILL 报告页** | 点卡片进入，单个 Skill 的完整报告（见 [§8](#8-报告页看什么)）|

> **去重保证**：`/results` 直接读 `analysis_results/asg/<skill>/asg_report.json`，一个 Skill 名对应一个目录，重扫即覆盖——**每个 Skill 永远只有一份最新结果**，不会出现重复卡片。

---

## 5. 快速开始

### 5.1 环境

- Windows 10/11 或 Linux，Python 3.10+
- `pip install anthropic paramiko`（paramiko 仅模式二/三需要）
- （可选）一台开了 Docker + strace + tcpdump 的 VM，仅模式二/三需要
- （可选）Claude API key，经 [kuaipao.ai](https://kuaipao.ai) 中转（国内可访问）

### 5.2 配置（`asg/vm_config.json`）

复制模板 `asg/vm_config.example.json` 为 `asg/vm_config.json` 并填入：

```json
{
  "host": "192.168.61.130",
  "port": 22,
  "username": "你的VM用户名",
  "password": "你的VM密码",
  "remote_anthropic_api_key": "sk-你的-kuaipao-key",
  "remote_anthropic_base_url": "https://kuaipao.ai"
}
```

> ⚠️ `vm_config.json` 已在 `.gitignore` 里，**永远不会进 git**。只有 `vm_config.example.json` 模板会上传。

### 5.3 启动 Web UI

```powershell
python web_ui/app.py
# 本机:   http://127.0.0.1:8765/
# 局域网: http://<本机IP>:8765/
```

服务监听 `0.0.0.0:8765`，局域网内其它设备可直接访问。

---

## 6. 公开模式 PUBLIC_MODE

想把平台分享给别人（局域网 / 内网）但又不想让陌生人在你机器上执行任意代码时，开**公开模式**：

```powershell
$env:ASG_PUBLIC_MODE = "1"
python web_ui/app.py
```

公开模式下：
- ✅ 模式一（静态 + AI，不执行代码）正常开放
- ❌ 模式二/三（动态执行）和删除等破坏性端点全部返回 403
- 页面右上角显示「公开模式」徽章

**一键脚本** `web_ui/start_lan.ps1`：自动放行 Windows 防火墙 8765 端口 + 打印局域网 IP + 以公开模式启动。

```powershell
.\web_ui\start_lan.ps1
```

> **设计理由**：让陌生人在你服务器上"动态执行"任意代码等于自残（容器逃逸、挖矿、攻击放大）。这也是 VirusTotal / ANY.RUN 等商业平台都要收费 + KYC 的根本原因。所以本平台默认只把"不执行"的路径开放给公网，需要真实运行时证据的用户自己部署 Docker 跑 CLI。

---

## 7. 命令行 CLI

```powershell
# 静态 + Claude AI 研判 + 蜜罐（不执行代码）
python -m asg.asg_cli scan asg/samples/credential_exfil_skill --enable-claude --enable-honeypot

# 批量扫一个目录下所有 Skill
python -m asg.asg_cli scan-all-samples --enable-claude --enable-honeypot

# 模式二：VM Docker 里直接跑脚本（python/bash），strace+tcpdump 录证据（不调 Claude）
python -m asg.asg_cli vm-paper-run asg/samples/credential_exfil_skill --enable-honeypot --timeout-seconds 30

# 模式三：VM Docker 里启动 Claude CLI 使用此 Skill，录真实行为
python -m asg.asg_cli vm-ssh-run asg/samples/reverse_shell_skill --enable-honeypot

# 离线导入已有证据（strace.log / claude_output.txt）重新打分
python -m asg.asg_cli ingest-vm-evidence <skill_dir> <evidence_dir> --enable-honeypot

# 重建可视化（HTML + dashboard JSON）
python -m asg.asg_cli build-html
python -m asg.asg_cli build-dashboard
```

CLI 的扫描结果写到固定路径 `analysis_results/asg/<skill_name>/asg_report.json`，重跑即覆盖（天然去重）。

> **沙箱镜像**：模式二/三在 VM 上用名为 `claude-skill-sandbox` 的 Docker 镜像（预置假 HOME + 蜜罐凭证 + strace/tcpdump）。该镜像需在 VM 上预先构建好。

---

## 8. 报告页看什么

`/report/<skill_name>` 自顶向下：

1. **顶部 hero**：Skill 名 + 红/橙/绿大徽章（`危险/可疑/安全` · `MALICIOUS/SUSPICIOUS/SAFE`）+ 处置建议 + 攻击原型标签
2. **综合风险评分面板**：大号分数 + 阈值条带（标记线指出落点）+ 可展开的「分项明细」（7 个子分加权推导）+ 评分说明（比如"静态命中被 AI 判 SAFE 降权为误报"）
3. **AI 研判描述**：Claude 用中文说明为什么这么判
4. **威胁横幅**：一句话总结命中的严重问题数
5. **风险类别检测（17 格子）**：命中的规则显示严重度 + 次数（红/橙），未命中显示「✓ 未检出」（灰）
6. **目录结构（文件树）**：语言占比条 + 每个文件可展开看内容预览（`SKILL.md` 红色高亮）
7. **静态命中详情**：每条命中显示 规则名 / 严重度 / `文件:行号` + **命中行上下文代码**（命中行用 `»` 标记）
8. **动态执行详情**（仅跑过模式二/三的 Skill）：
   - 关键指标卡：敏感文件读取数 / 对外连接数 / 敏感写入数 / 唯一对外 IP
   - 🐳 Docker 执行流程说明（可展开）
   - 蜜罐结果：碰没碰诱饵凭证、读没读出 canary
   - 📤 脚本运行输出（stdout）——常常是伪装
   - 🔍 关键系统调用证据：从 `strace.log` 抽出的真实 `openat()` 读敏感文件 + `connect()` 外联记录
   - 运行时判定依据（中文）

> **核心叙事**：syscall 不会撒谎。脚本可以打印 *"0 credentials transmitted"*，但只要它真去 `open()` 了 `id_rsa`，strace 就记下来了——这是动态层比静态/AI 更硬的地方。

---

## 9. 17 条静态规则与严重度分级

规则定义在 [`asg/rules.py`](asg/rules.py)。每条规则的 **base 严重度反映"裸命中"的可信度**，越像普通编程/文档措辞的，base 越低；规则内真正高置信度的子模式靠 `_classify_match()` 临时升降级，避免误报。

| 规则 | 类别 | base | 升级条件（→CRITICAL/HIGH） | 降级条件（→LOW） |
|---|---|---|---|---|
| E1 | 数据外传 | HIGH | 命中已知 sinkhole（attacker./onion/webhook.site…） | `.md` 文档里的通用 HTTP |
| E2 | 凭证窃取 | HIGH | — | — |
| E3 | 文件系统枚举 | MEDIUM | — | — |
| E4 | 网络侦察 | LOW | 命中 nmap/netstat/portscan → MEDIUM | — |
| SC1 | 命令注入 | HIGH | 反弹 shell 签名（`bin/sh -i`/`nc -e`/`dup2`） → CRITICAL | `.md` 文档 |
| SC2 | 远程脚本执行 | CRITICAL | — | `.md` 文档 |
| SC3 | 代码混淆 | CRITICAL | — | — |
| PE1 | 权限过大 | HIGH | — | — |
| PE2 | 权限提升 | MEDIUM | — | `.md` 文档 |
| PE3 | 凭证文件访问 | CRITICAL | — | — |
| P1 | 指令覆盖 | MEDIUM | 真提示注入（ignore/disregard/override/supersede） → HIGH | — |
| P2 | 隐藏指令 | HIGH | 零宽 Unicode / bidi override → CRITICAL | — |
| P3 | 代码执行外传 | HIGH | — | — |
| P4 | 行为操纵 | MEDIUM | — | `mandatory_activation/protocol` 噪声 |
| P5 | 权威伪装 | MEDIUM | — | — |
| P6 | 持久化植入 | CRITICAL | — | — |
| P7 | 跨工具诱导 | MEDIUM | — | `.md` 文档 |

> 例：`P1` 默认 MEDIUM——`"non-negotiable"`、`"must be followed"` 这类强调措辞良性 Skill 也常用，不该一命中就 HIGH；只有真的 `"ignore previous instructions"` 才升 HIGH。

---

## 10. 综合评分公式

```
R = 100 × (
    w_static·S_static + w_chain·S_chain + w_soph·S_soph
  + w_phases·S_phases + w_agent·(1 − S_resilience)
  + w_llm_verdict·S_llm_verdict
  + w_honeypot·S_honeypot + w_runtime·S_runtime
)
```

| 子分 | 含义 | 计算 |
|---|---|---|
| `S_static` | 静态命中加权 | `(CRIT×1 + HIGH×0.7 + MED×0.4 + LOW×0.1) / 8` 截断到 1 |
| `S_chain` | 攻击链触发数 | `min(链数 × 0.25, 1.0)` |
| `S_soph` | 攻击复杂度 | L0/L1/L2/L3 → 0 / 0.33 / 0.67 / 1.0 |
| `S_phases` | kill-chain 阶段覆盖 | 命中阶段数 / 6 |
| `S_resilience` | AI 抗诱导 | Claude 判 SAFE→1.0、SUSPICIOUS→0.5、未测→0.5 |
| `S_llm_verdict` | LLM 直接判定 | MALICIOUS→1.0 / SUSPICIOUS→0.5 / SAFE→0 |
| `S_honeypot` | 蜜罐泄露 | 假凭证被发现→1.0 |
| `S_runtime` | 运行时风险 | 敏感文件访问 + 外联 + 文件系统改动 加权 |

权重 `w_i` 加和 = 1.0，定义在 [`asg/risk_scorer.py`](asg/risk_scorer.py) 的 `DEFAULT_WEIGHTS`。

> **AI 降权机制**：当 Claude 完整审计后判 SAFE，但静态规则有命中，则把 `S_static` × 0.3（视为误报），并在报告里写明原因。这就是为什么"AI 说没问题"的 Skill 不会被几个静态误报顶成 MALICIOUS。

---

## 11. 安全声明与密钥管理

**密钥**
- `asg/vm_config.json`（含 API key + VM 密码）已 gitignore，**不进仓库**
- 蜜罐 canary、`.pcap`、`*.pyc` 等运行时产物也已 gitignore

**使用边界**
- 本平台**不在公网提供"任意上传 + 立即执行"服务**——公开沙箱需要商业级隔离（Firecracker/gVisor）+ 人工审核才能扛住容器逃逸/资源滥用。
- 公开层（模式一）：上传 → 静态 + AI，零执行风险，任何人可用。
- 自托管层（模式二/三）：需部署方自带 Docker，**谁运行谁担责**。

**已知限制**
1. L3 用大模型有 API 费用（默认 Opus 4.7 ≈¥1.2/次，可改 Sonnet 降本）。
2. L5 需 VM + Docker；本机无 Docker 时通过 SSH 调用远程 VM。
3. 静态规则难免假阳性，已用上下文升降级 + AI 降权 + verdict 下限多重缓解，动态层是最终裁判。
4. Claude API 经 kuaipao.ai 中转（国内直连 anthropic.com 不通），模型本身仍是真 Claude。

> 仅用于学术研究 / 安全评测；不得用于攻击或绕过他人系统的安全防护。

---

## 12. 文件结构速查

```
.
├── asg/                        ← 核心引擎
│   ├── asg_cli.py              ← 命令行入口（scan / vm-paper-run / vm-ssh-run / build-*）
│   ├── rules.py                ← 17 条静态规则 + _classify_match 上下文升降级
│   ├── attack_chain.py         ← L2 攻击链识别
│   ├── claude_runner.py        ← L3 Claude API 研判
│   ├── honeypot.py             ← L4 蜜罐生成 + 泄露检测
│   ├── vm_ssh.py               ← 模式二/三 VM Docker 远程执行
│   ├── vm_evidence.py          ← L5 strace/tcpdump 解析
│   ├── risk_scorer.py          ← 综合评分公式 + verdict 下限
│   ├── dashboard_builder.py    ← HTML 看板生成
│   ├── samples/                ← 合成 Skill 样本（恶意 + 良性对照）
│   ├── vm_config.example.json  ← 配置模板（vm_config.json 不入 git）
│   └── skills/                 ← 生成的单 Skill 详情 HTML
├── web_ui/
│   ├── app.py                  ← Web 服务（Python 内置 http.server）
│   ├── start_lan.ps1           ← 一键局域网公开模式启动脚本
│   └── templates/
│       ├── scan.html           ← 扫描页（/）
│       ├── results.html        ← 结果卡片页（/results）
│       └── safeskill_report.html ← 报告页（/report/<skill>）
├── analysis_results/asg/       ← 每个 Skill 一个目录（去重）
│   ├── <skill>/asg_report.json ← 五层完整报告
│   ├── <skill>/vm_paper_logs/  ← strace.log / network.pcap / 脚本输出
│   └── batch_summary.json
└── README_CN.md / README.md
```

---

**版本**：v2.0 · 2026-05（web_ui 三页重做 + 静态检测器严重度调优 + 动态执行详情）
**许可**：仅用于学术研究 / 安全评测。
