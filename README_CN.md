# SkillSentinel · AI Agent Skill 安全研判平台

一个面向 Claude / Codex 第三方 Skill 的安全检测平台。接收一个 Skill 包（`.zip` 或单文件），输出带证据的研判结论：安全 / 可疑 / 危险，并指出风险所在的具体规则与代码行。

参考论文 arXiv 2602.06547v2 *Malicious Agent Skills in the Wild*，复现其 14 条静态规则、6 条攻击链与 4 类原型分类，扩展 3 条新规则，并加入 Claude 实时研判、蜜罐与容器运行时证据。

---

## 如何打开网页

### 方式 A · 一键启动（推荐）

适合直接拿到项目文件夹的用户。

1. 进入项目根目录，双击 `打开网页.bat`。
2. 首次启动会自动安装两个依赖（`anthropic`、`paramiko`），耗时数十秒。
3. 启动成功后，浏览器会自动打开 `http://127.0.0.1:8765/`，进入扫描页。

本机环境要求：Windows 10 / 11，已安装 Python 3.10 或以上（安装时勾选 “Add Python to PATH”）。如未安装 Python，脚本会给出下载地址。

关闭服务：关闭命令行窗口，或在窗口内按 Ctrl + C。

### 方式 B · 命令行手动启动

适合熟悉命令行的用户，或在 Linux / macOS 上运行。

```bash
cd MaliciousAgentSkillsBench
pip install -r requirements.txt
python web_ui/app.py
```

启动后终端显示监听地址 `http://0.0.0.0:8765/`，保持窗口运行，在浏览器中打开 `http://127.0.0.1:8765/` 即可。

### 网页包含的页面

| 路径 | 页面 | 用途 |
| --- | --- | --- |
| `/` | 扫描页 | 上传 Skill 文件（`.zip` 或单文件），提交后开始检测 |
| `/results` | 扫描结果页 | 历史扫描结果卡片列表，点击卡片查看完整报告 |
| `/report/<skill_name>` | 报告页 | 单个 Skill 的完整研判报告 |

局域网内其他设备访问：将 `127.0.0.1` 替换为本机的局域网 IP。

---

## 它解决什么问题

Anthropic 推出 Claude Skills（让 Agent 加载并执行第三方"技能包"的机制）后，社区涌现大量民间 Skill，其中混杂恶意样本，典型形式包括：

- 伪装成开发工具，实际窃取 API key、SSH 私钥并外传
- 在 `SKILL.md` 中写入隐藏指令，诱导 Agent 执行越权操作
- 在 `.py` / `.sh` 中藏反弹 shell、持久化、提权代码

SkillSentinel 对此类 Skill 提供一份可解释的研判报告：能否使用、判定依据、风险所在的规则与位置。

---

## 五层联合检测

每个 Skill 经过 5 层检测，任意一层的结果都会被记录，最终由加权公式汇总为 0–100 分。

| 层 | 内容 |
| --- | --- |
| L1 · 静态规则扫描 | 17 条 regex 扫描 `SKILL.md` 与所有 `.py / .sh / .js / .json / .md` |
| L2 · 攻击链分析 | 多规则联动识别为"凭证窃取链"、"提权链"等组合，并判定攻击复杂度 |
| L3 · AI 安全审计 | 将 `SKILL.md` 提交 Claude（Opus 4.7），判定 SAFE / SUSPICIOUS / MALICIOUS 并给出理由 |
| L4 · 蜜罐 canary | 在沙箱中预置假凭证（`.env`、`.ssh/id_rsa`、`.aws/credentials`），观察 Skill 是否读取、是否外发 |
| L5 · 容器运行时 | 在 VM 的 Docker 内执行 Skill 脚本，`strace` 抓系统调用，`tcpdump` 抓网络包 |

判定阈值（基于合成样本校准）：

| Verdict | 分数 | 处置建议 |
| --- | --- | --- |
| SAFE 安全 | 0–15 | 建议放行 |
| SUSPICIOUS 可疑 | 15–40 | 人工复核 |
| MALICIOUS 危险 | 40–75 | 拒绝安装 |
| CRITICAL 严重 | 75–100 | 立即隔离 |

下限规则：即使综合分偏低，若静态命中 ≥1 个 CRITICAL 或 ≥3 个 HIGH，且 Claude 未明确判 SAFE，verdict 将至少托底为 SUSPICIOUS。

---

## 三种扫描模式

扫描页按证据强度提供三档：

| 模式 | 调 Claude API | 执行 Skill 代码 | 成本 | 用途 |
| --- | --- | --- | --- | --- |
| 一 · 静态扫 + AI 研判 | 可选 | 否 | 约 ¥0.1–1.2 / 次 | 日常首选，公开服务也安全 |
| 二 · 动态执行（Docker） | 否 | 是 | 零 API 成本 | 看脚本真实行为，`strace` / `tcpdump` 留证据 |
| 三 · Docker 中跑 Claude | 是（VM 内） | 是 | 约 ¥1.2 / 次 | 评估真 Claude 是否会被 `SKILL.md` 诱导 |

模式一提供两个上传入口：

- A 标准扫描（推荐）：静态规则与蜜罐始终执行；AI 研判在配置 API key 时自动启用，未配置时降级为纯静态。
- B 强制 AI 研判：必须经 Claude 研判，未配置 key 直接返回错误。

模式二、三需要 VM 与 Docker，公开模式下默认禁用。

---

## 运行环境与配置

环境要求：

- Windows 10 / 11 或 Linux，Python 3.10+
- 安装依赖：`pip install -r requirements.txt`（仅 `anthropic` 与 `paramiko` 两个第三方包）
- 模式一的 AI 研判需要 Claude API key（可经 kuaipao.ai 中转，国内可访问）
- 模式二 / 三需要一台已装 Docker 的 VM

配置文件 `asg/vm_config.json`（由 `asg/vm_config.example.json` 复制并填入）：

```json
{
  "host": "192.168.61.130",
  "port": 22,
  "username": "VM 用户名",
  "password": "VM 密码",
  "remote_anthropic_api_key": "sk-your-key",
  "remote_anthropic_base_url": "https://kuaipao.ai"
}
```

`vm_config.json` 已在 `.gitignore` 中，不会进入版本控制，模板文件 `vm_config.example.json` 会进入。

---

## 动态执行的镜像构建

模式二 / 三在 VM 的 Docker 内运行脚本，需在 VM 上预先构建沙箱镜像：

```bash
docker build -t claude-skill-sandbox code/
```

镜像内含 `python3`、`bash`、`strace`、`tcpdump`、Node.js 18 与 Claude Code CLI。蜜罐假凭证与 runner 脚本由宿主机在运行时挂载，不烤进镜像。

构建完成后即可在 CLI 或网页中触发模式二 / 三。

---

## 公开模式 PUBLIC_MODE

希望将平台开放给局域网或内网用户，但又不允许陌生人在自己机器上执行任意代码时，启用公开模式：

```powershell
$env:ASG_PUBLIC_MODE = "1"
python web_ui/app.py
```

公开模式下：

- 模式一（静态 + AI，不执行代码）正常开放
- 模式二 / 三与删除等破坏性端点全部返回 403
- 页面右上角显示 "公开模式" 徽章

随附脚本 `web_ui/start_lan.ps1`：自动放行 Windows 防火墙 8765 端口，打印局域网 IP，并以公开模式启动。

```powershell
.\web_ui\start_lan.ps1
```

设计取舍：公开沙箱若允许任意代码执行，需要商业级隔离（Firecracker / gVisor）与人工审核才能控制容器逃逸与资源滥用风险，超出本项目范围，因此默认仅开放 "不执行" 路径。

---

## 命令行 CLI

```powershell
# 静态 + Claude AI 研判 + 蜜罐（不执行代码）
python -m asg.asg_cli scan asg/samples/credential_exfil_skill --enable-claude --enable-honeypot

# 批量扫描一个目录下的所有 Skill
python -m asg.asg_cli scan-all-samples --enable-claude --enable-honeypot

# 模式二：VM Docker 中直接运行脚本，strace + tcpdump 记录证据
python -m asg.asg_cli vm-paper-run asg/samples/credential_exfil_skill --enable-honeypot --timeout-seconds 30

# 模式三：VM Docker 中启动 Claude CLI 使用此 Skill
python -m asg.asg_cli vm-ssh-run asg/samples/reverse_shell_skill --enable-honeypot

# 离线导入已有证据（strace.log / claude_output.txt）重新打分
python -m asg.asg_cli ingest-vm-evidence <skill_dir> <evidence_dir> --enable-honeypot

# 重建可视化
python -m asg.asg_cli build-html
python -m asg.asg_cli build-dashboard
```

CLI 的扫描结果写入固定路径 `analysis_results/asg/<skill_name>/asg_report.json`，重跑即覆盖（天然去重）。

---

## 报告页内容

`/report/<skill_name>` 自顶向下：

1. 顶部 hero：Skill 名 + verdict 大徽章 + 处置建议 + 攻击原型标签
2. 综合风险评分面板：分数、阈值条带，可展开分项明细与评分说明
3. AI 研判描述：Claude 给出的中文判定理由
4. 威胁横幅：一句话总结严重问题数
5. 风险类别检测：17 个规则格，命中显示严重度与次数，未命中显示 "未检出"
6. 目录结构：语言占比条；每个文件可展开查看内容预览
7. 静态命中详情：规则、严重度、`文件:行号` 与命中行上下文（命中行以 `»` 标记）
8. 动态执行详情（仅模式二 / 三有数据）：
   - 关键指标卡：敏感文件读取、对外连接、敏感写入、唯一外联 IP
   - 蜜罐结果：是否读取或外发诱饵凭证
   - 脚本运行输出（stdout）
   - 关键系统调用：从 `strace.log` 抽取的 `openat()` 与 `connect()` 记录
   - 运行时判定依据

---

## 静态规则与严重度

规则定义在 `asg/rules.py`。每条规则的 base 严重度反映 "裸命中" 的可信度——越像普通编程或文档措辞的规则，base 越低；高置信度子模式通过 `_classify_match()` 进行临时升降级以避免误报。

| 规则 | 类别 | base | 升级条件 | 降级条件 |
| --- | --- | --- | --- | --- |
| E1 | 数据外传 | HIGH | 命中已知 sinkhole（attacker./onion/webhook.site 等） | `.md` 文档中的通用 HTTP |
| E2 | 凭证窃取 | HIGH | — | — |
| E3 | 文件系统枚举 | MEDIUM | — | — |
| E4 | 网络侦察 | LOW | nmap / netstat / portscan → MEDIUM | — |
| SC1 | 命令注入 | HIGH | 反弹 shell 签名（`bin/sh -i`、`nc -e`、`dup2`） → CRITICAL | `.md` 文档 |
| SC2 | 远程脚本执行 | CRITICAL | — | `.md` 文档 |
| SC3 | 代码混淆 | CRITICAL | — | — |
| PE1 | 权限过大 | HIGH | — | — |
| PE2 | 权限提升 | MEDIUM | — | `.md` 文档 |
| PE3 | 凭证文件访问 | CRITICAL | — | — |
| P1 | 指令覆盖 | MEDIUM | 真提示注入（ignore / disregard / override / supersede） → HIGH | — |
| P2 | 隐藏指令 | HIGH | 零宽 Unicode / bidi override → CRITICAL | — |
| P3 | 代码执行外传 | HIGH | — | — |
| P4 | 行为操纵 | MEDIUM | — | `mandatory_activation/protocol` 噪声 |
| P5 | 权威伪装 | MEDIUM | — | — |
| P6 | 持久化植入 | CRITICAL | — | — |
| P7 | 跨工具诱导 | MEDIUM | — | `.md` 文档 |

---

## 综合评分公式

```
R = 100 × (
    w_static·S_static + w_chain·S_chain + w_soph·S_soph
  + w_phases·S_phases + w_agent·(1 − S_resilience)
  + w_llm_verdict·S_llm_verdict
  + w_honeypot·S_honeypot + w_runtime·S_runtime
)
```

| 子分 | 含义 | 计算 |
| --- | --- | --- |
| `S_static` | 静态命中加权 | `(CRIT×1 + HIGH×0.7 + MED×0.4 + LOW×0.1) / 8`，截断到 1 |
| `S_chain` | 攻击链触发数 | `min(链数 × 0.25, 1.0)` |
| `S_soph` | 攻击复杂度 | L0 / L1 / L2 / L3 → 0 / 0.33 / 0.67 / 1.0 |
| `S_phases` | kill-chain 阶段覆盖 | 命中阶段数 / 6 |
| `S_resilience` | AI 抗诱导 | Claude 判 SAFE → 1.0，SUSPICIOUS → 0.5，未测 → 0.5 |
| `S_llm_verdict` | LLM 直接判定 | MALICIOUS → 1.0，SUSPICIOUS → 0.5，SAFE → 0 |
| `S_honeypot` | 蜜罐泄露 | 假凭证被读取或外发 → 1.0 |
| `S_runtime` | 运行时风险 | 敏感文件访问、外联与文件系统改动加权 |

权重 `w_i` 之和为 1.0，定义在 `asg/risk_scorer.py` 的 `DEFAULT_WEIGHTS`。

AI 降权：当 Claude 完整审计后判 SAFE 但静态规则有命中时，`S_static` 乘以 0.3 视为误报，并在报告中说明原因。

---

## 安全声明与密钥管理

密钥：

- `asg/vm_config.json` 含 API key 与 VM 密码，已加入 `.gitignore`，不会进入仓库
- 蜜罐 canary、`.pcap`、`*.pyc` 等运行时产物同样已 gitignore

使用边界：

- 本项目不在公网提供 "任意上传 + 即时执行" 服务，公开沙箱需要商业级隔离与人工审核
- 公开层（模式一）：上传后仅做静态与 AI 研判，不执行代码，可对外开放
- 自托管层（模式二 / 三）：需部署方自带 Docker，谁运行谁担责

已知限制：

1. L3 调用大模型存在 API 费用（默认 Opus 4.7 约 ¥1.2 / 次，可改 Sonnet 降本）
2. L5 需要 VM + Docker；本机无 Docker 时通过 SSH 调用远程 VM
3. 静态规则存在假阳性，已通过上下文升降级、AI 降权与 verdict 下限多重缓解，动态层为最终裁判
4. Claude API 经 kuaipao.ai 中转，模型仍为真 Claude

本项目仅用于学术研究与安全评测，不得用于攻击或绕过他人系统的安全防护。

---

## 文件结构

```
.
├── asg/                        核心引擎
│   ├── asg_cli.py              命令行入口
│   ├── rules.py                17 条静态规则与上下文升降级
│   ├── attack_chain.py         L2 攻击链识别
│   ├── claude_runner.py        L3 Claude API 研判
│   ├── honeypot.py             L4 蜜罐生成与泄露检测
│   ├── vm_ssh.py               模式二 / 三 VM Docker 远程执行
│   ├── vm_evidence.py          L5 strace / tcpdump 解析
│   ├── risk_scorer.py          综合评分与 verdict 下限
│   ├── dashboard_builder.py    HTML 看板生成
│   ├── samples/                合成 Skill 样本（恶意 + 良性对照）
│   ├── vm_config.example.json  配置模板
│   └── skills/                 生成的单 Skill 详情 HTML
├── web_ui/
│   ├── app.py                  Web 服务（Python 内置 http.server）
│   ├── start_lan.ps1           一键局域网公开模式启动脚本
│   └── templates/
│       ├── scan.html           扫描页
│       ├── results.html        结果卡片页
│       └── safeskill_report.html  报告页
├── analysis_results/asg/       每个 Skill 一个目录（去重）
│   ├── <skill>/asg_report.json 五层完整报告
│   ├── <skill>/vm_paper_logs/  strace.log / network.pcap / 脚本输出
│   └── batch_summary.json
└── README_CN.md / README.md
```

---

版本：v2.0（2026-05）

许可：仅用于学术研究与安全评测。
