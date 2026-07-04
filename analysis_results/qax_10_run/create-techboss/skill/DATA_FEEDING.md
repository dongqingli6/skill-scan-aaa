# 数据喂养指南 — DATA_FEEDING.md

> *"他写的每一条 review 评论，每一句'这个复杂度 O(n²) 了吧'，都是训练他 AI 替身的优质语料。"*

---

## 核心原则

**数量 > 质量 > 格式**

- 最好：原话截图 / 原始文本（PR 评论、Jira、飞书消息）
- 其次：转述 + 上下文（"他上周评审说……"）
- 兜底：一句话描述管理风格（没有素材也能生成）

**哪些内容最有价值：**

| 数据类型 | 价值 | 原因 |
|---------|------|------|
| GitHub / GitLab PR 评论 | ⭐⭐⭐⭐⭐ | 最真实还原代码审查语言风格和技术偏好 |
| 飞书 / Slack 技术讨论消息 | ⭐⭐⭐⭐⭐ | 还原日常 PUA 句式和口头禅 |
| Jira ticket 评论 | ⭐⭐⭐⭐ | 还原任务管理风格和推卸责任模式 |
| 架构评审 / 技术会议纪要 | ⭐⭐⭐⭐ | 还原评审发言风格和大饼话术 |
| 1v1 会议记录 / 录音转文字 | ⭐⭐⭐⭐ | 还原对下属的管理沟通模式 |
| 邮件（.eml 或文本） | ⭐⭐⭐ | 还原正式沟通风格 |
| 他发的技术博客 / 文章 | ⭐⭐⭐ | 还原技术偏好和布道风格 |
| 他的 LinkedIn / 简介 | ⭐⭐ | 还原自我定位和"大厂经历"炫耀模式 |
| 口述描述 | ⭐⭐ | 兜底，但比没有强 |

---

## 数据来源 A：GitHub / GitLab PR 评论

### 方式一：导出 JSON（推荐）

GitHub API 导出单个 PR 的评论：

```bash
# 安装 GitHub CLI
brew install gh  # macOS
# 或 winget install --id GitHub.cli  # Windows

# 导出 PR 评论
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments > pr_comments.json

# 或使用 curl（替换 token 和 PR 信息）
curl -H "Authorization: token YOUR_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments" \
  > pr_comments.json
```

然后喂给 techboss-skill：
```
/create-techboss
# 选择 [C] 上传文件
# 提供 pr_comments.json 文件路径
```

### 方式二：截图直接上传

1. 打开 PR 页面，截包含 review 评论的截图
2. 在 `/create-techboss` 时选择 `[A] 上传截图`
3. AI 自动识别截图中的评论文字

### 方式三：复制粘贴文本

直接从 PR 页面复制评论文本，在 `/create-techboss` 时选择 `[B] 粘贴文本`。

**效果最大化技巧**：
- 优先提供：review 被 Request Changes 的评论（批评性最强，最能还原语言风格）
- 同时提供：他 approve 时的评论（呈现对比）
- 数量建议：至少 5-10 个 PR 的评论，覆盖不同项目

---

## 数据来源 B：飞书聊天记录

### 方式一：飞书消息 JSON 导出

飞书支持导出聊天记录为 JSON 格式（企业管理员权限）：

```bash
# 使用内置工具解析飞书消息 JSON
python3 techboss-skill/tools/feishu_parser.py \
  --file lark_export.json \
  --target "王总" \
  --output ./knowledge/feishu_out.txt
```

### 方式二：截图（推荐）

最简单的方式：截飞书群聊截图，包含 Tech Boss 的原话，在 `/create-techboss` 上传。

### 重点截图内容

截以下类型的消息，效果最好：

```
✅ 高质量素材清单：

[ ] 他在技术群里的代码评审相关消息
[ ] 他在项目群里说"这个 scalability 考虑了吗"之类的话
[ ] 他宣布技术决策的消息（"我们要用微服务"）
[ ] 他催进度的方式（"今晚能上线吗""这个影响不大吧"）
[ ] 他甩锅的话术（"这是基础设施的问题""团队经验不足"）
[ ] 他画饼的消息（"等这个项目完成有很多机会"）
[ ] 他在 incident 时的反应（可能是最珍贵的素材）
```

### 方式三：全自动采集（需要飞书机器人权限）

```bash
python3 techboss-skill/tools/feishu_auto_collector.py \
  --name "王总" \
  --output-dir ./raw_data/
```

---

## 数据来源 C：Jira 评论和 Ticket

### 方式一：Jira CSV 导出

1. 进入 Jira → Issues → 搜索由他评论过的 ticket
2. 右上角 Export → Export Excel CSV
3. 用内置工具解析：

```bash
python3 techboss-skill/tools/jira_parser.py \
  --file jira_export.csv \
  --target "王总" \
  --output ./knowledge/jira_out.txt
```

### 方式二：截图或复制粘贴

截 Jira ticket 的评论区，直接上传或复制粘贴。

**效果最大化技巧**：
- 优先收集：他关闭 bug 时的评论（最能看出甩锅风格）
- 优先收集：他打回 Story 的理由（还原技术要求的模糊度）
- 优先收集：他推迟 ticket 的评论（还原大饼话术）

---

## 数据来源 D：会议纪要 / 录音转文字

### 架构评审会

最有价值的会议类型。包含他：
- 对技术方案的质疑方式（提什么问题、用什么大厂案例）
- 做决定的逻辑（真实技术考量 vs 个人偏好）
- 画饼时机（会议结尾的承诺）

如果有录音，可以用工具转文字：

```bash
# 使用 faster-whisper 转换（需要提前安装）
pip install faster-whisper
python3 -c "
from faster_whisper import WhisperModel
model = WhisperModel('base', compute_type='int8')
segments, _ = model.transcribe('meeting.mp3')
with open('meeting_transcript.txt', 'w') as f:
    for s in segments: f.write(s.text + '\n')
"
```

### 1v1 面谈记录

如果有会议记录（自己整理的），包含他的原话，直接粘贴。
重点关注他如何回应：
- 你提加薪时他怎么说
- 你提晋升时他怎么说
- 他批评你的技术时具体用了什么词

### Standup 会议

记录他在站会上问的问题，特别是：
- 提出与会议主题无关的技术话题
- 对谁的进度提出质疑
- 临时新增的"小需求"

---

## 数据来源 E：他的技术文章 / 博客

如果你的 Tech Boss 有技术博客、掘金文章、公众号、GitHub README，这些是了解他技术偏好的绝佳素材：

```bash
# 提供 URL，AI 自动抓取分析
/create-techboss
# 选择 [C] 上传文件
# 粘贴文章 URL 或上传 HTML 文件
```

**分析重点**：
- 他推崇哪些技术理念（会在评审时引用）
- 他引用哪些大厂案例（会在否定你方案时说出来）
- 他的技术偏见（会成为他 review 代码时最挑剔的点）

---

## 数据来源 F：代码仓库本身

你的 Tech Boss 可能自己也提交过代码，分析他的提交可以了解他真实的技术水平：

```bash
# 分析他的 commit 记录
git log --author="王总" --oneline > boss_commits.txt

# 分析他的代码风格
git log --author="王总" -p --no-merges > boss_code_changes.txt
```

**可以揭露的信息**：
- 他强调的代码规范，自己有没有遵守
- 他上次做的"暂时方案"今天是否还在
- 他三年前写的 TODO comment 有没有被还上

---

## 素材质量检验清单

喂给 AI 之前，检查你的素材是否包含以下任一类型：

```
必须项（至少有其一）：
[ ] 他批评代码时的原话（越多越好）
[ ] 他评估技术方案时的原话
[ ] 他催进度 / 分配任务的消息

加分项（有的话效果更好）：
[ ] 他说"先上线再说"类的话
[ ] 他推卸责任时的措辞
[ ] 他做技术承诺时的原话
[ ] 他引用大厂案例的原话（"Netflix 是这样……"）
[ ] 他在 incident 后的发言

可选项（进一步细化画像）：
[ ] 他的 LinkedIn 简介或个人介绍
[ ] 他写的技术文章/博客
[ ] 他在面试时问的技术问题（如果你有记录）
```

---

## 素材隐私处理

在喂数据之前，建议：

1. **脱敏**：替换真实姓名为代号（公司名、产品名等同理）
2. **本地运行**：数据只在本地处理，不上传到外部服务
3. **最小化**：只保留有价值的内容片段，不需要整段对话

```bash
# 脱敏示例：替换公司名和人名
sed 's/ACME Corporation/某互联网公司/g; s/王伟/王总/g' raw_data.txt > clean_data.txt
```

---

## 常见问题

**Q：没有任何素材，只知道他的几句口头禅，能用吗？**

A：完全可以。`/create-techboss` 口述模式下，告诉 AI：
- 他的职位和公司类型
- 2-3 个口头禅（越接近原话越好）
- 1-2 个大致管理标签（微操狂 / 画饼王 / 甩锅侠）

仅凭这些，就能生成一个可用版本，后续随时追加素材进化。

**Q：PR 评论太技术专业，AI 能理解吗？**

A：可以。AI 能读懂代码相关评论，提取评论者的技术偏好和沟通风格，不需要你额外解释。

**Q：素材主要是截图，能用吗？**

A：可以。`Read` 工具支持直接识别截图内容，中英文混合的技术截图都没问题。

**Q：他的评论很短，只有"这里有 bug"之类的，有用吗？**

A：有用，但价值较低。建议多收集他说的"否定性长评论"和"提技术建议的评论"，比短评论效果好得多。
