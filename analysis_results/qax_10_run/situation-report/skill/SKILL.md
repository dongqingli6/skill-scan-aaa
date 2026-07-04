---
name: situation-report
description: 全球态势感知 - 新闻、市场、加密货币、经济数据实时报告
metadata: { "openclaw": { "emoji": "🌍" } }
---

# 态势感知报告

获取全球实时态势数据，包括新闻、市场行情、加密货币、美联储经济指标。

## 触发方式
- "今天全球有什么大事"
- "给我一份态势报告"
- "现在市场怎么样"
- "加密货币行情"
- "美联储最新数据"
- "situation report"

## 使用方法

### 完整态势报告（新闻 + 市场 + 加密 + 经济）
python3 /root/workspace/skills/situation-report/sitrep.py full

### 仅新闻
python3 /root/workspace/skills/situation-report/sitrep.py news
python3 /root/workspace/skills/situation-report/sitrep.py news --topic china
python3 /root/workspace/skills/situation-report/sitrep.py news --topic "artificial intelligence"
python3 /root/workspace/skills/situation-report/sitrep.py news --topic ukraine --limit 10

### 仅市场（需要 Finnhub API Key）
python3 /root/workspace/skills/situation-report/sitrep.py markets

### 仅加密货币
python3 /root/workspace/skills/situation-report/sitrep.py crypto
python3 /root/workspace/skills/situation-report/sitrep.py crypto --coins bitcoin,ethereum,solana

### 仅美联储经济数据
python3 /root/workspace/skills/situation-report/sitrep.py fed

### 自定义关键词监控
python3 /root/workspace/skills/situation-report/sitrep.py watch --keywords "tariff,trade war,sanctions"

## 输出
脚本输出 JSON 格式的结构化数据。拿到数据后，请用自然语言总结关键要点，
按重要性排序，标注时间和来源。如果用户使用中文提问，请用中文回答。
