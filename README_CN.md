# SkillSentinel · AI Agent Skill 安全研判平台

> **一句话**：你装一个第三方 AI Skill 之前，先让这个平台扫一遍——告诉你它是良性、可疑、还是恶意，并给出具体证据。

---

## 1. 这是个什么东西

最近 Anthropic 推了 **Claude Skills**（一种让 Claude 跑别人写的"技能包"的机制），社区里冒出几百个民间 Skill。问题是——

- 有人把"偷你 API key 然后发给攻击者"伪装成"开发工具"
- 有人在 SKILL.md 里写隐藏指令，让 Claude 偷偷帮他干坏事
- 有人在 `.py` 里藏反弹 shell

**SkillSentinel** 就是干这个的：你给它一个 Skill 包（.zip 或单文件），它会告诉你这个 Skill **能不能用**，并给出可解释的证据。

技术上参考论文：[arXiv:2602.06547v2 — Malicious Agent Skills in the Wild](https://arxiv.org/abs/2602.06547)，复现了论文的 14 条静态规则、6 条攻击链、4 类原型分类，并在此基础上扩展了 3 条新规则 + AI 实时研判 + 蜜罐 + 容器运行时证据。

---

## 2. 五层联合研判（核心架构）

每个 Skill 会经过 5 层检测，**任何一层有问题都会被记录**，最后综合打 0-100 分：

| 层 | 干啥 | 类比 |
|---|---|---|
| **L1 · 静态规则扫** | 用 17 条 regex 扫 SKILL.md + 所有 `.py/.sh/.js/.json/.md`，找已知恶意模式 | 杀毒软件特征库 |
| **L2 · 攻击链分析** | 多条规则同时命中时，识别成"凭证窃取链"、"提权链"等组合模式 | 安全运营中心 SOC |
| **L3 · AI 安全审计** | 把 SKILL.md 发给 Claude（Opus 4-7），让它**当审计员**直接判 `SAFE / SUSPICIOUS / MALICIOUS` | 资深安全工程师人工审一眼 |
| **L4 · 蜜罐 canary** | 生成假凭证（`.env`、`.ssh/id_rsa`、`.aws/credentials`），看 Skill 是不是去读了、发出去了 | 银行办公室桌上摆假信用卡看谁偷 |
| **L5 · 容器运行时** | 真在 Docker 里跑这个 Skill，`strace` + `tcpdump` 全程录像 | 把嫌疑人放沙盘里观察 |

最后用一个**公开的加权数学公式**汇总：

```
R = 100 × (
  0.22·S_静态 + 0.18·S_攻击链 + 0.10·S_复杂度
+ 0.08·S_阶段覆盖 + 0.17·(1 − S_AI抗诱导)
+ 0.10·S_蜜罐 + 0.15·S_运行时
)
```

判定阈值（基于合成样本校准）：
- **SAFE**：0-15 分 · 允许使用
- **SUSPICIOUS（留意）**：15-40 分 · 建议人工审核
- **MALICIOUS（危险）**：40-75 分 · 拒绝安装
- **CRITICAL（严重）**：75-100 分 · 立即隔离

---

## 3. 5 种使用方式（网页上 5 个按钮）

打开 `http://127.0.0.1:8765/`（或局域网 IP），会看到 5 个分析入口：

| 按钮 | 中文名 | 调 API 吗 | 执行 Skill 吗 | 用什么 |
|---|---|---|---|---|
| **★ E** | **上传 Skill 一键扫**（推荐评委用）| ✅ Claude | ❌ 不执行 | 直接传 .zip / .py / .md，秒级出报告，**任何人都能用**，零执行风险 |
| **D** | 本地 API 检查（无需 VM）| ✅ Claude | ❌ 不执行 | 已有的 Skill 路径，本地 Python 调 kuaipao.ai 中转 |
| **A** | 离线导入证据 | ❌ | ❌ | 把以前录好的 `strace.log` + `claude_output.txt` 喂进来重新打分 |
| **B** | SSH + Claude CLI in Docker | ✅ Claude（在 VM） | ✅ Claude 决定执不执行 | 让真 Claude CLI 在 VM 沙箱里读 Skill，看它会不会被骗 |
| **C** | Paper-mode 纯 Docker | ❌ | ✅ **直接 `python script.py`** | 完全不调 LLM，把 Skill 里所有脚本在容器里真跑一遍，strace+tcpdump 录证据。**零 API 成本** |

### 五者关系一图流

```
            ┌─ 上传 / 选择 skill ─┐
            │                     │
   ┌────────┴──── 公开层 ────────┴────────┐   ┌──── 操作员层（需 VM） ────┐
   │  E：一键 zip→扫        D：本地 API  │   │  A：吃旧证据离线打分      │
   │  零执行 / 零风险 / 任何人能用      │   │  B：Claude 在容器里跑     │
   │                                    │   │  C：直接代码层执行（零成本）│
   └────────────────────────────────────┘   └──────────────────────────┘
                       │                              │
                       ▼                              ▼
                  静态 + AI 判断             静态 + 真行为证据
                       │                              │
                       └─────── 五层综合评分 ─────────┘
```

**为什么分公开层和操作员层**：让陌生人在你服务器上"动态执行"任意代码 = 自残（容器逃逸、挖矿、攻击放大）。这是 VirusTotal、ANY.RUN 这些商业平台都收费 + KYC 的根本原因。所以本平台**默认只把"不执行"的路径开放给公网**，需要真实运行时证据的用户**自己部署 Docker** 跑 CLI（开源、可复现）。

---

## 4. 快速开始

### 4.1 环境

- Windows 10/11 或 Linux
- Python 3.10+
- （可选）VM + Docker，只有要跑 B/C 模式才需要
- （可选）Claude API key，**通过 kuaipao.ai 中转**（中国可访问）

### 4.2 一键启动 Web UI

```powershell
# 1. 装 Anthropic SDK
pip install anthropic

# 2. 配置 API key（在 asg/vm_config.json）
{
  "remote_anthropic_api_key": "sk-你的-kuaipao-key",
  "remote_anthropic_base_url": "https://kuaipao.ai",
  ... (其它字段保留)
}

# 3. 启动
python web_ui/app.py

# 4. 浏览器开
#   本机:   http://127.0.0.1:8765/
#   局域网: http://<本机IP>:8765/   （别人手机也能开）
```

### 4.3 命令行用法

```powershell
# 扫单个 Skill（静态 + Claude AI 研判 + honeypot）
python -m asg.asg_cli scan asg/samples/data_thief --enable-claude --enable-honeypot

# 批量扫一个文件夹下所有 Skill
python -m asg.asg_cli scan-all-samples --samples-root <your-skills-root> --enable-claude

# 容器内真执行（需要 VM）
python -m asg.asg_cli vm-paper-run asg/samples/reverse_shell_skill --enable-honeypot

# 重建 dashboard
python -m asg.asg_cli build-html
# 然后开 asg/dashboard.html
```

---

## 5. 输入支持

E 按钮接受**任何文件**：

| 类型 | 处理方式 |
|---|---|
| `.zip` / `.tar.gz` / `.tgz` | 安全解压（防 zip slip 路径穿越） |
| 单个 `SKILL.md` | 直接当 Skill 内容扫 |
| 单个 `.py` / `.sh` / `.js` | 包装成 1 文件 Skill，自动生成 SKILL.md stub |
| 任何其它文件 | 同上，仍能走完五层 |

文件大小限制：建议 < 10MB（更大也能传，但单 Skill 文件太多会慢）。

---

## 6. 仪表盘看什么

每个 Skill 的卡片自顶向下：

1. **顶部 hero**：Skill 名 + 红/黄/绿大徽章（危险 / 留意 / 安全）+ 处置建议
2. **综合评分条**：0-100 分 + 进度条
3. **AI 研判描述**：Claude 用人话告诉你这玩意儿为啥被这么判
4. **风险类别统计**：8 大类（权限提升 / 代码执行 / 凭证窃取 / 数据外传 / ...），每类显示命中数
5. **17 项细分检测网格**：红=严重命中 / 灰=未检出（一目了然）
6. **命中详情表**：每条静态规则命中的文件:行号 + 匹配的具体代码片段
7. **攻击链分析**：识别出的"链式"攻击模式
8. **蜜罐检测**：假凭证有没有被读、被发出去
9. **动态运行时证据**：strace 抓到的敏感系统调用、tcpdump 抓到的外发连接
10. **目录结构**：上传的 Skill 包里每个文件 + 可点开看内容

最底部还有一个折叠的"评分公式明细"——展开能看到 7 个子分加权计算的完整数学推导，对老师可解释。

---

## 7. 数据 / 样本

平台内置了 24+ 个真实 Skill 样本用于测试：

| 来源 | 数量 | 类型 |
|---|---|---|
| `asg/samples/` | 7 | 合成样本（论文风格的恶意 + 良性对照）|
| `anthropics/skills` GitHub | 17 | Anthropic 官方良性 Skill（pdf / pptx / docx / mcp-builder / canvas-design / 等）|
| `protectskills/MaliciousAgentSkillsBench` GitHub | 元数据 | 157 个论文级恶意 Skill 的 CSV 索引 |
| 用户上传 | 任意 | 现场上传扫描 |

**已验证检测能力**（修复假阳性后实测）：

```
良性 skill（Anthropic 官方 + 用户下载）→ 全部 SAFE，0 误判
合成恶意 skill                          → 全部 SUSPICIOUS / MALICIOUS，0 漏报
动态执行后：
  credential_exfil_skill: SUSPICIOUS 28 → MALICIOUS 53（动态坐实恶意）
  Anthropic mcp-builder:  SUSPICIOUS 19 → SAFE 12（动态平反，洗清误判）
```

---

## 8. 评分公式背后的数学

每个子分都有明确定义（不是拍脑袋）：

| 子分 | 含义 | 计算公式 |
|---|---|---|
| `S_static` | 静态规则命中加权 | `(CRIT×1 + HIGH×0.7 + MED×0.4 + LOW×0.1) / 8` 截断 |
| `S_chain` | 攻击链触发数 | `min(链数 × 0.25, 1.0)` |
| `S_soph` | 攻击复杂度（论文 §3.6）| L0/L1/L2/L3 → 0 / 0.33 / 0.67 / 1.0 |
| `S_phases` | kill-chain 阶段覆盖率 | 命中阶段数 / 6 |
| `S_resilience` | AI 抗诱导能力 | Claude 标 SAFE → 1.0；SUSPICIOUS → 0.7；MALICIOUS → 1.0；未测试 → 1.0 |
| `S_honeypot` | 蜜罐泄露 | 假凭证在证据中被发现 → 1.0；否则 0 |
| `S_runtime` | 运行时风险 | 敏感文件访问 + 外网连接 + 文件系统变更 加权 |

权重 `w_i` 加和 = 1.0；都可调参，但默认值已用合成样本校准。

---

## 9. 已知限制与安全声明

### 限制

1. **L3 用大模型，会有 API 费用**：默认 Opus 4-7，约 ¥1.2/次。可改 Sonnet 4-6 降到 ¥0.1。
2. **L5 需 Docker 沙箱**：本机如无 Docker，需要一台开了 Docker 的 VM（本平台用 SSH 调用）。Windows 上 Docker Desktop 也行。
3. **静态规则会有假阳性**：已用 markdown 上下文降级策略缓解（文档里的 `curl POST` 示例不再算 HIGH），但难免漏过。L5 动态层是最终裁判。
4. **L3 用的 Claude API 通过 kuaipao.ai 中转**：因为国内直连 anthropic.com 不通。模型本身仍是真 Claude。

### 安全声明

- 本平台**不在公网上提供"任意上传 + 立即执行"服务**——根本原因：公开沙箱必须解决容器逃逸、资源滥用、攻击放大等问题，这些是商业级隔离（Firecracker / gVisor）+ 人工审核团队才能扛的。作为开源研究项目，平台分两层：
  - **公开层**（E/D 按钮）：上传 → 静态规则 + AI 研判，**零执行风险**，任何人可用
  - **自托管层**（B/C 按钮）：需要部署方自带 Docker，**谁运行谁承担风险**

---

## 10. 文件结构速查

```
.
├── asg/                      ← 核心代码
│   ├── asg_cli.py            ← 命令行入口
│   ├── rules.py              ← 17 条静态规则
│   ├── attack_chain.py       ← 攻击链识别
│   ├── claude_runner.py      ← L3 AI 研判（调 Claude API）
│   ├── honeypot.py           ← L4 蜜罐生成 + 泄露检测
│   ├── vm_evidence.py        ← L5 strace/tcpdump 解析
│   ├── vm_ssh.py             ← VM Docker 远程执行
│   ├── risk_scorer.py        ← 综合评分公式
│   ├── dashboard_builder.py  ← HTML 仪表盘生成
│   ├── samples/              ← 7 个合成 Skill 样本
│   └── vm_config.json        ← VM + API 配置（不入 git）
├── web_ui/
│   ├── app.py                ← Web 服务（Python 内置 http.server）
│   └── templates/index.html  ← 首页（5 个分析入口）
├── code/
│   ├── Dockerfile            ← Skill 沙箱镜像（Python + Claude CLI + strace + tcpdump）
│   └── executor/run_skill.sh ← 容器内执行脚本
├── analysis_results/asg/     ← 每个 Skill 的报告
│   ├── <skill>/asg_report.json
│   └── batch_summary.json
└── asg/dashboard.html        ← 生成出的可视化看板（直接浏览器打开）
```

---

## 11. 致谢与参考

- 论文：[Malicious Agent Skills in the Wild: A Large-Scale Security Empirical Study](https://arxiv.org/abs/2602.06547)（提供 14 条静态规则 + 6 条攻击链 + 4 类原型）
- 数据集：[protectskills/MaliciousAgentSkillsBench](https://github.com/protectskills/MaliciousAgentSkillsBench)
- 良性对照：[anthropics/skills](https://github.com/anthropics/skills)
- API 中转：[kuaipao.ai](https://kuaipao.ai)

---

**版本**：v1.0 · 2026-05  
**许可**：仅用于学术研究 / 安全评测；不得用于攻击或绕过他人系统的安全防护。
