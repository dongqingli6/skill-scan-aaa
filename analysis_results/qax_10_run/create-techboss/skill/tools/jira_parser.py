#!/usr/bin/env python3
"""
Jira 评论导出解析器 — TechBoss.skill 专用

支持的导出格式：
1. Jira CSV 导出（Issue Navigator → Export → Export Excel CSV）
2. Jira JSON 导出（REST API 导出）
3. 手动复制的文本

主要提取：
- 目标人物（Tech Boss）的评论内容
- Ticket 标题 + 他的评论（还原任务推进风格）
- 他关闭/拒绝 ticket 时的理由（甩锅模式）
- 他推迟任务的理由（大饼话术）

用法：
    python3 jira_parser.py --file jira_export.csv --target "王总" --output output.txt
    python3 jira_parser.py --file jira_api.json --target "王总" --output output.txt
    python3 jira_parser.py --text "直接粘贴的评论内容" --target "王总" --output output.txt
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path


# ─── 关键词分类 ────────────────────────────────────────────────────────────────

BLAME_KEYWORDS = [
    "基础设施", "历史遗留", "技术债", "tech debt", "上游", "依赖", "接口问题",
    "产品没想清楚", "需求变化", "团队经验", "时间紧", "历史原因", "这个不是我们的锅",
    "这属于", "应该是", "的问题", "那边的问题",
]

DELAY_KEYWORDS = [
    "下个 sprint", "下期", "MVP 完了", "稳定了再", "先上线", "后面排",
    "有时间再", "暂时先", "优先级不高", "以后处理", "todo", "暂缓",
    "下季度", "下个版本", "等用户量上来",
]

CAKE_KEYWORDS = [
    "重构", "refactor", "你来主导", "有机会", "等这个完了", "下个项目",
    "你升", "tech lead", "架构师", "开源", "影响力", "大厂", "期权",
]

REVIEW_DECISION_KEYWORDS = [
    "不行", "有问题", "重新", "需要返工", "设计有问题", "不符合", "不够",
    "可以 merge", "lgtm", "approve", "looks good", "ship it",
    "scalability", "clean", "复杂度", "o(n", "单测", "coverage",
]


# ─── CSV 解析 ──────────────────────────────────────────────────────────────────

def parse_jira_csv(file_path: str, target_name: str) -> list[dict]:
    """
    解析 Jira CSV 导出文件。
    Jira CSV 列通常包含：Issue Key, Summary, Status, Assignee, Reporter,
    Comment, Description, Created, Updated 等。
    """
    results = []

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        for row in reader:
            # 找包含评论的列（Jira CSV 评论列名不统一）
            comment_cols = [c for c in fieldnames if "comment" in c.lower()]
            description_cols = [c for c in fieldnames if "description" in c.lower() or "summary" in c.lower()]

            # 收集所有评论文本
            comments_text = ""
            for col in comment_cols:
                val = row.get(col, "").strip()
                if val:
                    comments_text += val + "\n"

            if not comments_text:
                continue

            # 过滤：只保留目标人物的评论
            # Jira 评论格式通常含有 "作者名; 日期; 内容" 或直接是内容
            target_comments = _extract_target_comments(comments_text, target_name)
            if not target_comments:
                continue

            # 提取 ticket 信息
            issue_key = _first_value(row, ["Issue Key", "Key", "Issue id", "ID", "编号"])
            summary = _first_value(row, ["Summary", "Title", "标题", "概要"])
            status = _first_value(row, ["Status", "状态"])
            assignee = _first_value(row, ["Assignee", "指派给", "负责人"])

            results.append({
                "issue_key": issue_key,
                "summary": summary,
                "status": status,
                "assignee": assignee,
                "comments": target_comments,
                "source": "csv",
            })

    return results


def _first_value(row: dict, keys: list) -> str:
    """从 dict 中取第一个匹配的键值（大小写不敏感）"""
    row_lower = {k.lower(): v for k, v in row.items()}
    for k in keys:
        v = row_lower.get(k.lower(), "")
        if v:
            return v.strip()
    return ""


def _extract_target_comments(comments_text: str, target_name: str) -> list[str]:
    """
    从评论块文本中提取目标人物的评论。
    Jira CSV 把多条评论合并在一个字段里，格式通常为：
      - "用户名; 2024-01-01T10:00:00+0800; 评论内容"
      - 或 "[用户名|datetime]: 评论内容"
      - 或直接是内容（无法区分作者时全部保留）
    """
    # 格式一：姓名; 日期时间; 内容
    pattern_semicolon = re.compile(
        r"([^;]+);\s*(\d{4}-\d{2}-\d{2}[^;]*);\s*(.+?)(?=\n\n|\Z)",
        re.DOTALL
    )
    matches = pattern_semicolon.findall(comments_text)
    if matches:
        return [
            content.strip()
            for author, _, content in matches
            if target_name in author
        ]

    # 格式二：[作者名|日期]: 内容
    pattern_bracket = re.compile(
        r"\[([^\|]+)\|[^\]]+\]:\s*(.+?)(?=\n\[|\Z)",
        re.DOTALL
    )
    matches2 = pattern_bracket.findall(comments_text)
    if matches2:
        return [
            content.strip()
            for author, content in matches2
            if target_name in author
        ]

    # 兜底：如果整段评论文本包含目标名，保留整段
    if target_name in comments_text:
        return [comments_text.strip()]

    return []


# ─── JSON 解析 ─────────────────────────────────────────────────────────────────

def parse_jira_json(file_path: str, target_name: str) -> list[dict]:
    """
    解析 Jira REST API 导出的 JSON 格式。
    支持两种格式：
    1. Jira Cloud API: {"issues": [{"key": ..., "fields": {"comment": {"comments": [...]}}}]}
    2. 简化格式：直接是 issue 数组
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    issues = []
    if isinstance(data, dict):
        issues = data.get("issues") or data.get("data") or []
    elif isinstance(data, list):
        issues = data

    results = []
    for issue in issues:
        if isinstance(issue, dict):
            fields = issue.get("fields", issue)
            key = issue.get("key", "")
            summary = fields.get("summary", "") or fields.get("title", "")
            status_raw = fields.get("status", {})
            status = status_raw.get("name", "") if isinstance(status_raw, dict) else str(status_raw)

            # 提取评论
            comment_block = fields.get("comment", {})
            if isinstance(comment_block, dict):
                raw_comments = comment_block.get("comments", [])
            elif isinstance(comment_block, list):
                raw_comments = comment_block
            else:
                raw_comments = []

            target_comments = []
            for c in raw_comments:
                if not isinstance(c, dict):
                    continue
                author_info = c.get("author", {})
                author_name = (
                    author_info.get("displayName", "")
                    or author_info.get("name", "")
                    or str(author_info)
                ) if isinstance(author_info, dict) else str(author_info)

                if target_name not in author_name:
                    continue

                body = c.get("body", "") or c.get("renderedBody", "")
                if isinstance(body, dict):
                    # Atlassian Document Format
                    body = _adf_to_text(body)
                if body and body.strip():
                    target_comments.append(body.strip())

            if target_comments:
                results.append({
                    "issue_key": key,
                    "summary": summary,
                    "status": status,
                    "assignee": "",
                    "comments": target_comments,
                    "source": "json",
                })

    return results


def _adf_to_text(adf: dict) -> str:
    """简单展开 Atlassian Document Format 为纯文本"""
    texts = []
    _collect_adf_text(adf, texts)
    return " ".join(texts)


def _collect_adf_text(node: dict, out: list):
    if not isinstance(node, dict):
        return
    if node.get("type") == "text":
        out.append(node.get("text", ""))
    for child in node.get("content", []):
        _collect_adf_text(child, out)


# ─── 分类与输出 ────────────────────────────────────────────────────────────────

def classify_comments(issues: list[dict]) -> dict:
    """把评论按行为模式分类"""
    blame_comments = []
    delay_comments = []
    cake_comments = []
    review_decision_comments = []
    other_comments = []

    def _classify_one(issue_key: str, summary: str, comment: str):
        text_lower = comment.lower()
        cats = []
        if any(kw.lower() in text_lower for kw in BLAME_KEYWORDS):
            cats.append("blame")
        if any(kw.lower() in text_lower for kw in DELAY_KEYWORDS):
            cats.append("delay")
        if any(kw.lower() in text_lower for kw in CAKE_KEYWORDS):
            cats.append("cake")
        if any(kw.lower() in text_lower for kw in REVIEW_DECISION_KEYWORDS):
            cats.append("review_decision")
        return cats or ["other"]

    for issue in issues:
        key = issue["issue_key"]
        summary = issue["summary"]
        for comment in issue["comments"]:
            cats = _classify_one(key, summary, comment)
            entry = {"key": key, "summary": summary, "comment": comment}
            if "blame" in cats:
                blame_comments.append(entry)
            if "delay" in cats:
                delay_comments.append(entry)
            if "cake" in cats:
                cake_comments.append(entry)
            if "review_decision" in cats:
                review_decision_comments.append(entry)
            if cats == ["other"]:
                other_comments.append(entry)

    return {
        "blame": blame_comments,
        "delay": delay_comments,
        "cake": cake_comments,
        "review_decision": review_decision_comments,
        "other": other_comments,
    }


def format_output(target_name: str, issues: list[dict], classified: dict) -> str:
    total = sum(len(issue["comments"]) for issue in issues)

    lines = [
        f"# Jira 评论提取结果 — {target_name}",
        f"共提取评论：{total} 条 / 涉及 ticket：{len(issues)} 个",
        "",
        "---",
        "",
        "## 甩锅 / 归因模式（高价值）",
        "",
    ]
    for e in classified["blame"]:
        lines.append(f"[{e['key']}] {e['summary']}")
        lines.append(f"  > {e['comment']}")
        lines.append("")

    lines += ["---", "", "## 延期 / 拖延话术（大饼检测）", ""]
    for e in classified["delay"]:
        lines.append(f"[{e['key']}] {e['summary']}")
        lines.append(f"  > {e['comment']}")
        lines.append("")

    lines += ["---", "", "## 画饼 / 承诺类（大饼鉴定素材）", ""]
    for e in classified["cake"]:
        lines.append(f"[{e['key']}] {e['summary']}")
        lines.append(f"  > {e['comment']}")
        lines.append("")

    lines += ["---", "", "## 技术评审 / 决策评论（代码审查 PUA 素材）", ""]
    for e in classified["review_decision"]:
        lines.append(f"[{e['key']}] {e['summary']}")
        lines.append(f"  > {e['comment']}")
        lines.append("")

    lines += ["---", "", "## 其他评论（语言风格参考）", ""]
    for e in classified["other"][:50]:  # 只取前 50 条
        lines.append(f"[{e['key']}] > {e['comment']}")
    lines.append("")

    return "\n".join(lines)


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="解析 Jira 导出文件，提取 Tech Boss 的评论",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 解析 Jira CSV 导出
  python3 jira_parser.py --file jira_export.csv --target "王总" --output output.txt

  # 解析 Jira API JSON 导出
  python3 jira_parser.py --file issues.json --target "王总" --output output.txt

  # 直接分析粘贴的文本
  python3 jira_parser.py --text "评论内容" --target "王总" --output output.txt
        """,
    )
    parser.add_argument("--file", help="Jira 导出文件路径（.csv 或 .json）")
    parser.add_argument("--text", help="直接提供评论文本（用于单条分析）")
    parser.add_argument("--target", required=True, help="目标人物姓名")
    parser.add_argument("--output", default=None, help="输出文件路径（默认 stdout）")
    args = parser.parse_args()

    if not args.file and not args.text:
        parser.error("需要提供 --file 或 --text")

    issues = []

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"错误：文件不存在 {path}", file=sys.stderr)
            sys.exit(1)

        if path.suffix.lower() == ".json":
            issues = parse_jira_json(str(path), args.target)
        elif path.suffix.lower() in (".csv", ".xlsx"):
            issues = parse_jira_csv(str(path), args.target)
        else:
            print(f"错误：不支持的文件格式 {path.suffix}，请使用 .csv 或 .json", file=sys.stderr)
            sys.exit(1)

    elif args.text:
        issues = [{
            "issue_key": "MANUAL",
            "summary": "(手动输入)",
            "status": "",
            "assignee": "",
            "comments": [args.text.strip()],
            "source": "text",
        }]

    if not issues:
        print(f"警告：未找到 '{args.target}' 的评论", file=sys.stderr)
        print("提示：检查姓名是否与 Jira 中的显示名一致", file=sys.stderr)
        sys.exit(0)

    classified = classify_comments(issues)
    output = format_output(args.target, issues, classified)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        total = sum(len(i["comments"]) for i in issues)
        print(f"已输出到 {args.output}，共 {total} 条评论 / {len(issues)} 个 ticket")
    else:
        print(output)


if __name__ == "__main__":
    main()
