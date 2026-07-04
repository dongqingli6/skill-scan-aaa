#!/usr/bin/env python3
"""
GitHub / GitLab PR Review 评论解析器 — TechBoss.skill 专用

支持的输入格式：
1. GitHub REST API 导出 JSON（PR review comments）
2. GitHub CLI 导出 JSON
3. GitLab merge request notes JSON
4. 手动复制的 PR 评论文本

主要提取：
- Tech Boss 的代码 review 评论（最高质量素材）
- 他 Approve / Request Changes 时的评论
- 按语言风格分类（性能 / 设计模式 / 洁癖批评 / 大饼 / 否定）

导出方式（推荐使用 GitHub CLI）：
  # 安装 GitHub CLI: https://cli.github.com
  gh api repos/{owner}/{repo}/pulls/{pr}/comments > pr_comments.json
  gh api repos/{owner}/{repo}/pulls/{pr}/reviews > pr_reviews.json

用法：
  python3 github_pr_parser.py --comments pr_comments.json --target "王总" --output output.txt
  python3 github_pr_parser.py --reviews pr_reviews.json --target "王总" --output output.txt
  python3 github_pr_parser.py --comments pr_comments.json --reviews pr_reviews.json --target "王总" --output output.txt
  python3 github_pr_parser.py --text "直接粘贴的评论文本" --target "王总" --output output.txt
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ─── 技术偏好关键词分类 ────────────────────────────────────────────────────────

PERFORMANCE_KEYWORDS = [
    "o(n", "complexity", "复杂度", "performance", "slow", "fast", "optimize",
    "cache", "缓存", "index", "索引", "latency", "throughput", "benchmark",
    "profile", "n+1", "query", "p99", "p95",
]

SOLID_KEYWORDS = [
    "srp", "single responsibility", "open closed", "liskov", "interface segregation",
    "dependency inversion", "solid", "clean architecture", "domain", "ddd",
    "bounded context", "aggregate", "值对象", "领域",
]

PATTERN_KEYWORDS = [
    "factory", "singleton", "observer", "strategy", "decorator", "adapter",
    "facade", "template method", "设计模式", "design pattern", "抽象", "接口",
    "多态", "继承", "组合优于继承",
]

CLOUD_NATIVE_KEYWORDS = [
    "kubernetes", "k8s", "docker", "container", "microservice", "service mesh",
    "circuit breaker", "resilience", "sidecar", "istio", "cloud native",
    "12 factor", "cloud-native",
]

CLEANLINESS_KEYWORDS = [
    "clean", "readable", "naming", "命名", "变量名", "函数名", "elegant",
    "hacky", "magic number", "hard-code", "注释", "comment", "self-documenting",
    "todo", "fixme", "technical debt", "重构",
]

BEST_PRACTICE_KEYWORDS = [
    "netflix", "google", "uber", "airbnb", "aws", "meta", "twitter",
    "github", "stripe", "这里", "大厂", "业界", "best practice",
    "engineering blog", "我之前", "以前公司",
]

APPROVE_DENY_KEYWORDS = {
    "approve": ["lgtm", "looks good", "ship it", "approved", "great", "nice", ":+1:", "合并"],
    "request_changes": ["not production ready", "needs work", "major issue", "blocking",
                        "design issue", "性能问题", "需要重写", "重新设计", "不行", "有问题",
                        "不 production ready"],
    "neutral": ["nit", "suggestion", "consider", "minor", "optional", "建议", "可以考虑"],
}


# ─── 解析 GitHub PR Review Comments ──────────────────────────────────────────

def parse_github_comments(file_path: str, target_name: str) -> list[dict]:
    """
    解析 GitHub REST API 导出的 PR review comments JSON。
    API: GET /repos/{owner}/{repo}/pulls/{pull_number}/comments
    每条 comment 包含：user.login, body, path, position, created_at 等
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        # 可能包在 data / comments 字段里
        comments = data.get("comments") or data.get("data") or []
    elif isinstance(data, list):
        comments = data
    else:
        return []

    results = []
    for c in comments:
        if not isinstance(c, dict):
            continue

        user_info = c.get("user", {}) or {}
        username = (
            user_info.get("login", "")
            or user_info.get("name", "")
            or user_info.get("displayName", "")
        ) if isinstance(user_info, dict) else str(user_info)

        if target_name not in username:
            continue

        body = c.get("body", "").strip()
        if not body:
            continue

        results.append({
            "type": "inline_comment",
            "author": username,
            "body": body,
            "file": c.get("path", ""),
            "created_at": c.get("created_at", ""),
            "pr_url": c.get("pull_request_url", ""),
        })

    return results


def parse_github_reviews(file_path: str, target_name: str) -> list[dict]:
    """
    解析 GitHub PR reviews JSON。
    API: GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews
    每条 review 包含：user.login, state, body, submitted_at
    state: APPROVED / CHANGES_REQUESTED / COMMENTED
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    reviews = data if isinstance(data, list) else data.get("reviews", [])

    results = []
    for r in reviews:
        if not isinstance(r, dict):
            continue

        user_info = r.get("user", {}) or {}
        username = (
            user_info.get("login", "")
            or user_info.get("name", "")
        ) if isinstance(user_info, dict) else str(user_info)

        if target_name not in username:
            continue

        body = r.get("body", "").strip()
        state = r.get("state", "").upper()

        if not body and state not in ("APPROVED", "CHANGES_REQUESTED"):
            continue

        results.append({
            "type": f"review_{state.lower()}",
            "author": username,
            "body": body or f"({state}，无附加说明)",
            "state": state,
            "submitted_at": r.get("submitted_at", ""),
        })

    return results


def parse_gitlab_notes(file_path: str, target_name: str) -> list[dict]:
    """
    解析 GitLab MR notes JSON。
    API: GET /projects/{id}/merge_requests/{mr_iid}/notes
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    notes = data if isinstance(data, list) else data.get("notes", [])

    results = []
    for n in notes:
        if not isinstance(n, dict):
            continue

        author_info = n.get("author", {}) or {}
        author_name = (
            author_info.get("name", "")
            or author_info.get("username", "")
        ) if isinstance(author_info, dict) else str(author_info)

        if target_name not in author_name:
            continue

        body = n.get("body", "").strip()
        if not body:
            continue

        results.append({
            "type": "gitlab_note",
            "author": author_name,
            "body": body,
            "created_at": n.get("created_at", ""),
            "resolvable": n.get("resolvable", False),
        })

    return results


# ─── 分类 ─────────────────────────────────────────────────────────────────────

def classify_comment(body: str) -> list[str]:
    """识别评论所属的技术 PUA 流派"""
    text_lower = body.lower()
    cats = []

    if any(kw in text_lower for kw in PERFORMANCE_KEYWORDS):
        cats.append("🔬 性能偏执派")
    if any(kw in text_lower for kw in SOLID_KEYWORDS):
        cats.append("🏛️ SOLID传教士")
    if any(kw in text_lower for kw in PATTERN_KEYWORDS):
        cats.append("📚 设计模式考官")
    if any(kw in text_lower for kw in CLOUD_NATIVE_KEYWORDS):
        cats.append("☁️ 云原生布道者")
    if any(kw in text_lower for kw in CLEANLINESS_KEYWORDS):
        cats.append("🧹 代码洁癖患者")
    if any(kw in text_lower for kw in BEST_PRACTICE_KEYWORDS):
        cats.append("🌐 大厂最佳实践")

    # approve/deny 判断
    for sentiment, keywords in APPROVE_DENY_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            cats.append(f"verdict:{sentiment}")

    return cats or ["💬 通用评论"]


def detect_pua_patterns(body: str) -> list[str]:
    """识别评论中的 PUA 手法"""
    patterns = []
    text_lower = body.lower()

    if re.search(r"o\s*\(\s*n\s*[\^²]\s*2?\s*\)", text_lower):
        patterns.append("复杂度审判")
    if "clean" in text_lower and not any(w in text_lower for w in ["how to", "suggestion", "consider"]):
        patterns.append("洁癖绑架")
    if any(kw in text_lower for kw in ["maintenance", "接手", "maintainable", "可维护"]):
        patterns.append("可维护性恐吓")
    if any(kw in text_lower for kw in ["best practice", "大厂", "netflix", "google", "uber"]):
        patterns.append("最佳实践武器化")
    if re.search(r"coverage|测试覆盖率|\d+%", text_lower):
        patterns.append("测试覆盖率暴政")
    if any(kw in text_lower for kw in ["pattern", "设计模式", "factory", "strategy", "observer"]):
        patterns.append("设计模式强迫")
    if "production ready" in text_lower or "production-ready" in text_lower:
        patterns.append("production ready审判")

    return patterns


# ─── 格式化输出 ───────────────────────────────────────────────────────────────

def format_output(target_name: str, all_comments: list[dict]) -> str:
    if not all_comments:
        return f"# PR Review 提取结果 — {target_name}\n\n未找到相关评论。\n"

    # 统计流派分布
    all_cats: dict[str, int] = {}
    all_pua: dict[str, int] = {}

    enriched = []
    for c in all_comments:
        cats = classify_comment(c["body"])
        pua = detect_pua_patterns(c["body"])
        enriched.append({**c, "categories": cats, "pua_patterns": pua})
        for cat in cats:
            all_cats[cat] = all_cats.get(cat, 0) + 1
        for p in pua:
            all_pua[p] = all_pua.get(p, 0) + 1

    lines = [
        f"# PR Review 提取结果 — {target_name}",
        f"共提取评论：{len(all_comments)} 条",
        "",
        "## 流派分布统计",
        "",
    ]
    for cat, count in sorted(all_cats.items(), key=lambda x: -x[1]):
        if not cat.startswith("verdict:"):
            lines.append(f"- {cat}: {count} 次")
    lines.append("")

    if all_pua:
        lines += ["## PUA 手法统计", ""]
        for pua, count in sorted(all_pua.items(), key=lambda x: -x[1]):
            lines.append(f"- {pua}: {count} 次")
        lines.append("")

    # 按流派分组输出
    lines += ["---", "", "## 全部评论（按时间）", ""]

    deny_comments = [c for c in enriched if "verdict:request_changes" in c.get("categories", [])]
    approve_comments = [c for c in enriched if "verdict:approve" in c.get("categories", [])]
    other_comments = [c for c in enriched
                      if "verdict:request_changes" not in c.get("categories", [])
                      and "verdict:approve" not in c.get("categories", [])
                      and c.get("body", "").strip()]

    if deny_comments:
        lines += ["### 🔴 Request Changes / 否定性评论（PUA 素材）", ""]
        for c in deny_comments:
            _append_comment(lines, c)

    if other_comments:
        lines += ["### 💬 一般评论（语言风格素材）", ""]
        for c in other_comments[:40]:  # 最多 40 条
            _append_comment(lines, c)

    if approve_comments:
        lines += ["### ✅ 通过 / 正面评论（了解他的满意标准）", ""]
        for c in approve_comments:
            _append_comment(lines, c)

    return "\n".join(lines)


def _append_comment(lines: list, c: dict):
    meta_parts = []
    if c.get("file"):
        meta_parts.append(f"文件: {c['file']}")
    if c.get("created_at"):
        meta_parts.append(c["created_at"][:10])
    if c.get("categories"):
        clean_cats = [cat for cat in c["categories"] if not cat.startswith("verdict:")]
        if clean_cats:
            meta_parts.append(" | ".join(clean_cats))
    if c.get("pua_patterns"):
        meta_parts.append(f"PUA: {', '.join(c['pua_patterns'])}")

    if meta_parts:
        lines.append(f"[{' · '.join(meta_parts)}]")
    lines.append(f"> {c['body']}")
    lines.append("")


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="解析 GitHub/GitLab PR Review 评论，提取 Tech Boss 的风格",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 导出 PR 评论（需要 GitHub CLI）
  gh api repos/{owner}/{repo}/pulls/{pr_number}/comments > comments.json
  gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews > reviews.json

  # 解析
  python3 github_pr_parser.py --comments comments.json --target "wangwei" --output output.txt
  python3 github_pr_parser.py --reviews reviews.json --target "wangwei" --output output.txt
  python3 github_pr_parser.py --comments comments.json --reviews reviews.json --target "wangwei" --output output.txt

  # 直接分析文本
  python3 github_pr_parser.py --text "这里复杂度 O(n²) 了，考虑用哈希表优化" --target "wangwei" --output output.txt
        """,
    )
    parser.add_argument("--comments", help="PR inline comments JSON 文件路径")
    parser.add_argument("--reviews", help="PR reviews JSON 文件路径")
    parser.add_argument("--gitlab-notes", help="GitLab MR notes JSON 文件路径")
    parser.add_argument("--text", help="直接提供评论文本（单条分析）")
    parser.add_argument("--target", required=True, help="目标人物的 GitHub username 或姓名")
    parser.add_argument("--output", default=None, help="输出文件路径（默认 stdout）")
    args = parser.parse_args()

    if not any([args.comments, args.reviews, args.gitlab_notes, args.text]):
        parser.error("至少需要提供 --comments / --reviews / --gitlab-notes / --text 之一")

    all_results = []

    if args.comments:
        p = Path(args.comments)
        if not p.exists():
            print(f"错误：文件不存在 {p}", file=sys.stderr)
            sys.exit(1)
        results = parse_github_comments(str(p), args.target)
        all_results.extend(results)
        print(f"解析 PR comments：{len(results)} 条属于 '{args.target}'", file=sys.stderr)

    if args.reviews:
        p = Path(args.reviews)
        if not p.exists():
            print(f"错误：文件不存在 {p}", file=sys.stderr)
            sys.exit(1)
        results = parse_github_reviews(str(p), args.target)
        all_results.extend(results)
        print(f"解析 PR reviews：{len(results)} 条属于 '{args.target}'", file=sys.stderr)

    if args.gitlab_notes:
        p = Path(args.gitlab_notes)
        if not p.exists():
            print(f"错误：文件不存在 {p}", file=sys.stderr)
            sys.exit(1)
        results = parse_gitlab_notes(str(p), args.target)
        all_results.extend(results)
        print(f"解析 GitLab notes：{len(results)} 条属于 '{args.target}'", file=sys.stderr)

    if args.text:
        all_results.append({
            "type": "manual_input",
            "author": args.target,
            "body": args.text.strip(),
            "created_at": "",
        })

    if not all_results:
        print(f"警告：未找到 '{args.target}' 的评论", file=sys.stderr)
        print("提示：GitHub username 区分大小写，请检查是否完全匹配", file=sys.stderr)
        sys.exit(0)

    output = format_output(args.target, all_results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已输出到 {args.output}，共 {len(all_results)} 条评论")
    else:
        print(output)


if __name__ == "__main__":
    main()
