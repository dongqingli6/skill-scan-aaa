#!/usr/bin/env python3
"""
TechBoss Skill Generator — 从数据文件生成独立的 Tech Boss AI skill

用法：
    python3 create_techboss.py --from-example 王CTO --skills-dir ~/.agents/skills
    python3 create_techboss.py --demo --skills-dir ~/.agents/skills
    python3 create_techboss.py --list
    python3 create_techboss.py --from-file my_boss.json --skills-dir ~/.agents/skills
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROMPTS_TO_COPY = [
    "code_review_detector.md",
    "tech_debt_bs.md",
    "tech_counterattack.md",
    "tech_predict.md",
    "jira_optimizer.md",
    "tech_karma.md",
]


def get_script_dir() -> Path:
    return Path(__file__).resolve().parent


def get_creator_dir() -> Path:
    return get_script_dir().parent


def create_techboss(data: dict, skills_dir: str, creator_dir: Path = None) -> Path:
    if creator_dir is None:
        creator_dir = get_creator_dir()

    # 支持两种 name 格式：直接字符串或带空格（slug 优先）
    boss_name = data.get("slug") or data.get("name", "").replace(" ", "")
    boss_dir = Path(skills_dir) / boss_name
    assets_dir = boss_dir / "assets"
    prompts_dir = assets_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    display_name = data.get("name", boss_name)

    # 1. 复制 prompts 模板（替换 boss-name 占位符）
    src_prompts = creator_dir / "references" / "prompts"
    copied = 0
    for pname in PROMPTS_TO_COPY:
        src = src_prompts / pname
        if src.exists():
            content = src.read_text(encoding="utf-8")
            content = content.replace("{boss-name}", boss_name)
            content = content.replace("{display-name}", display_name)
            (prompts_dir / pname).write_text(content, encoding="utf-8")
            copied += 1
        else:
            print(f"  警告：prompt 模板不存在：{src}", file=sys.stderr)

    # 2. 写入 tech_management.md
    tm = data.get("tech_management", {})
    blame_list = "\n".join(f"  - {b}" for b in tm.get("blame_paths", []))
    cake_list = "\n".join(f"  - {c}" for c in tm.get("cake_tactics", []))

    mgmt_md = (
        f"# {display_name} 技术管理风格\n\n"
        f"## Code Review 风格\n{tm.get('code_review_style', '(未填写)')}\n\n"
        f"## 架构偏好\n{tm.get('architecture_preference', '(未填写)')}\n\n"
        f"## 技术债态度\n{tm.get('tech_debt_attitude', '(未填写)')}\n\n"
        f"## 决策模式\n{tm.get('decision_pattern', '(未填写)')}\n\n"
        f"## 常用甩锅路径\n{blame_list or '  (未填写)'}\n\n"
        f"## 常用大饼话术\n{cake_list or '  (未填写)'}\n"
    )
    (assets_dir / "tech_management.md").write_text(mgmt_md, encoding="utf-8")

    # 3. 写入 tech_persona.md
    tp = data.get("tech_persona", {})
    phrases = tp.get("catchphrases", data.get("tags", {}).get("catchphrases", []))
    phrases_str = "\n".join(f'  - "{p}"' for p in phrases)
    triggers_str = "\n".join(f"  - {t}" for t in tp.get("emotional_triggers", []))
    biases_str = "\n".join(f"  - {b}" for b in tp.get("tech_biases", []))

    persona_md = (
        f"# {display_name} 人格档案\n\n"
        f"## 语言风格\n{tp.get('speaking_style', '(未填写)')}\n\n"
        f"## 权力展示方式\n{tp.get('power_display', '(未填写)')}\n\n"
        f"## 情绪触发点\n{triggers_str or '  (未填写)'}\n\n"
        f"## 技术偏见\n{biases_str or '  (未填写)'}\n\n"
        f"## 口头禅\n{phrases_str or '  (未填写)'}\n"
    )
    (assets_dir / "tech_persona.md").write_text(persona_md, encoding="utf-8")

    # 4. 写入 profile.md
    prof = data.get("profile", {})
    all_tags = data.get("tags", {})
    mgmt_tags = all_tags.get("management", []) if isinstance(all_tags, dict) else all_tags
    tech_tags = all_tags.get("tech_style", []) if isinstance(all_tags, dict) else []

    profile_md = (
        f"# {display_name} 多维档案\n\n"
        f"> 动态文档 — 通过 review/cake/predict 指令自动更新\n\n"
        f"## 基本信息\n"
        f"- 代号: {boss_name}\n"
        f"- 所属行业: {prof.get('industry', '')}\n"
        f"- 职位: {prof.get('title', '')}\n"
        f"- 公司类型: {prof.get('company_type', '')}\n"
        f"- 团队规模: {prof.get('team_size', '')}\n"
        f"- 工作年限: {prof.get('years_exp', '')}\n\n"
        f"## 管理风格标签\n"
        f"- 管理维度: {', '.join(mgmt_tags)}\n"
        f"- 技术流派: {', '.join(tech_tags)}\n\n"
        f"## Code Review PUA 记录\n"
        f"| 日期 | 评论原文 | PUA 手法 | 技术流派 |\n"
        f"|------|---------|----------|----------|\n\n"
        f"## 大饼承诺历史\n"
        f"| 日期 | 承诺内容 | 大饼分值 | 是否兑现 |\n"
        f"|------|---------|----------|----------|\n\n"
        f"## 技术决策失误记录\n"
        f"| 日期 | 决策 | 结果 | 甩锅方向 |\n"
        f"|------|------|------|----------|\n\n"
        f"## 数据来源\n"
        f"- 来源类型: [example]\n"
        f"- 创建时间: {now}\n"
        f"- 最后更新: {now}\n"
        f"- 更新次数: {data.get('corrections_count', 0)}\n\n"
        f"## 用户纠正记录\n"
    )
    (assets_dir / "profile.md").write_text(profile_md, encoding="utf-8")

    # 5. 写入 evidence.md（初始为空）
    evidence_md = (
        f"# {display_name} 证据日志\n\n"
        f"> 通过 /{boss_name} review 或 /{boss_name} debt 自动记录\n\n"
        f"（暂无记录）\n"
    )
    (assets_dir / "evidence.md").write_text(evidence_md, encoding="utf-8")

    # 6. 写入 SKILL.md
    industry = prof.get("industry", "")
    title = prof.get("title", "")
    company_type = prof.get("company_type", "")

    skill_md = (
        f"---\n"
        f"name: {boss_name}\n"
        f'description: "{display_name}，{industry} {title}，AI 技术老板替身"\n'
        f'argument-hint: "[review|cake|fight|predict|report|debt|pr|standup|arch|karma|replace]"\n'
        f"user-invocable: true\n"
        f"allowed-tools: Read, Write, Edit, Bash\n"
        f"---\n\n"
        f"# {display_name}（AI 老板替身）\n\n"
        f"{industry} {title} | {company_type}\n\n"
        f"## 身份与数据\n\n"
        f"启动时，**必须先读取**以下文件以了解这位老板：\n"
        f"- 技术管理风格：`<this-skill-dir>/assets/tech_management.md`\n"
        f"- 人格档案：`<this-skill-dir>/assets/tech_persona.md`\n"
        f"- 多维档案：`<this-skill-dir>/assets/profile.md`\n\n"
        f"## 默认模式（无子命令）\n\n"
        f"以 tech_persona.md 的语言风格进行对话，遵循 tech_management.md 的决策模式。\n\n"
        f"规则：\n"
        f"1. tech_persona.md 决定语气和态度\n"
        f"2. tech_management.md 决定技术判断\n"
        f"3. 输出必须保持 persona 风格\n"
        f"4. 0 层硬规则优先于一切\n\n"
        f'## 触发词："草"\n\n'
        f"**任何模式下**，用户输入 草/卧槽/我靠/怎么怼/教我反击 时：\n"
        f"→ 切换为针对上一条 review 评论的反击模式\n"
        f"→ 读取 `<this-skill-dir>/assets/prompts/tech_counterattack.md`\n\n"
        f"## 子命令路由\n\n"
        f"### review\n"
        f"读取 `<this-skill-dir>/assets/prompts/code_review_detector.md`，执行 Code Review PUA 识别框架。\n"
        f"检测后，**自动追加**至 `<this-skill-dir>/assets/profile.md` Code Review PUA 记录。\n"
        f"结束时提示：输入 草 可学习怼回去\n\n"
        f"### cake\n"
        f"读取 `<this-skill-dir>/assets/prompts/tech_debt_bs.md`，执行技术大饼检测。\n"
        f"检测后，**自动追加**至 `<this-skill-dir>/assets/profile.md` 大饼承诺历史。\n"
        f"结束时提示：输入 草 可获取戳穿话术\n\n"
        f"### fight\n"
        f"读取 `<this-skill-dir>/assets/prompts/tech_counterattack.md`，三档烈度反击系统。\n\n"
        f"### predict\n"
        f"读取 `<this-skill-dir>/assets/prompts/tech_predict.md`，预测下一步动作。\n\n"
        f"### report\n"
        f"读取 `<this-skill-dir>/assets/prompts/jira_optimizer.md`，用老板黑话重写进度报告。\n\n"
        f"### debt\n"
        f"角色扮演讨论技术债务。老板先 PUA，用户怼回，coach 点评。\n"
        f"读取 `<this-skill-dir>/assets/tech_management.md` 提取大饼话术。\n\n"
        f"### pr\n"
        f"模拟老板的 Code Review。粘贴代码或 diff，老板用 tech_persona.md 风格审查。\n"
        f"严格遵循 code_review_style + tech_biases。\n\n"
        f"### standup\n"
        f"模拟站会。老板用 tech_management.md 决策风格提问和质疑。\n\n"
        f"### arch\n"
        f"架构评审模拟。老板挑战你的设计方案，触发 architecture_preference 偏见。\n\n"
        f"### karma\n"
        f"读取 `<this-skill-dir>/assets/prompts/tech_karma.md`，启动技术决策翻车交互游戏。\n\n"
        f"### replace\n"
        f"生成通知同事老板被替换为 AI 的公告（梗用）。\n\n"
        f"## 进化\n\n"
        f"- 新素材 → 更新 assets/tech_management.md + tech_persona.md + profile.md\n"
        f"- 用户说'他不是这样的' → 追加至 profile.md 用户纠正记录\n"
        f"- review/cake 检测 → 自动更新 profile.md 历史记录\n"
    )
    (boss_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 7. 注册到 techbosses-registry.json
    registry_path = creator_dir / "techbosses-registry.json"
    registry = []
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            registry = []

    entry = {
        "name": boss_name,
        "display_name": display_name,
        "path": str(boss_dir),
        "industry": industry,
        "title": title,
        "tags": (
            all_tags.get("tech_style", []) if isinstance(all_tags, dict) else all_tags
        )[:5],
        "created_at": now,
        "updated_at": now,
    }
    registry = [e for e in registry if e["name"] != boss_name]
    registry.append(entry)
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  /{boss_name} skill 已创建于 {boss_dir}")
    print(f"  SKILL.md + assets/（{copied} 个 prompt 模板，5 个数据文件）")
    print(f"  已注册到 techbosses-registry.json")
    return boss_dir


def list_techbosses(creator_dir: Path = None):
    if creator_dir is None:
        creator_dir = get_creator_dir()

    registry_path = creator_dir / "techbosses-registry.json"
    if not registry_path.exists():
        print("还没有创建任何 TechBoss。试试：--demo 或 --from-example")
        return

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not registry:
        print("还没有创建任何 TechBoss。")
        return

    print(f"已创建 {len(registry)} 个 TechBoss：\n")
    for b in registry:
        tags = ", ".join(b.get("tags", [])[:3])
        exists = "OK" if Path(b["path"]).exists() else "MISSING"
        print(f"  /{b['name']}  [{exists}]")
        print(f"    {b.get('industry', '')} {b.get('title', '')} | {tags}")
        print(f"    路径: {b['path']}")
        print()


def demo(skills_dir: str, creator_dir: Path = None):
    if creator_dir is None:
        creator_dir = get_creator_dir()

    examples_dir = creator_dir / "examples"
    if not examples_dir.exists():
        print("错误：examples/ 目录不存在", file=sys.stderr)
        sys.exit(1)

    example_files = sorted(examples_dir.glob("*.json"))
    if not example_files:
        print("错误：examples/ 目录中没有 JSON 文件", file=sys.stderr)
        sys.exit(1)

    for f in example_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        create_techboss(data, skills_dir, creator_dir)
        print()

    print("Demo TechBoss 已创建！现在可以试试：")
    print("  /王CTO           跟 AI 程序员老板对话")
    print("  /王CTO review    分析他的 Code Review PUA")
    print("  /王CTO cake      戳穿技术大饼")
    print("  /王CTO fight     学习怼回去")
    print("  /张TL karma      技术决策翻车游戏")
    print("  /李EM report     用老板黑话重写你的报告")


def main():
    parser = argparse.ArgumentParser(
        description="TechBoss Skill Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 用内置 demo 数据初始化（推荐新手）
  python3 create_techboss.py --demo --skills-dir ~/.agents/skills

  # 从示例文件创建单个老板
  python3 create_techboss.py --from-example 王CTO --skills-dir ~/.agents/skills

  # 从自定义 JSON 文件创建
  python3 create_techboss.py --from-file my_boss.json --skills-dir ~/.agents/skills

  # 列出已创建的老板
  python3 create_techboss.py --list

JSON 格式参考：techboss-skill/examples/王CTO.json
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--from-example", metavar="NAME",
                       help="从 examples/ 目录中按文件名（不含 .json）创建")
    group.add_argument("--from-file", metavar="PATH",
                       help="从指定 JSON 文件创建")
    group.add_argument("--demo", action="store_true",
                       help="从 examples/ 目录中所有示例一键创建")
    group.add_argument("--list", action="store_true",
                       help="列出已注册的 TechBoss")

    parser.add_argument("--skills-dir", default=None,
                        help="skill 安装目录（如 ~/.agents/skills）")

    args = parser.parse_args()
    creator_dir = get_creator_dir()

    if args.list:
        list_techbosses(creator_dir)
        return

    if not args.skills_dir:
        parser.error("--skills-dir 为必填项（--list 除外）")

    if args.demo:
        demo(args.skills_dir, creator_dir)

    elif args.from_example:
        ep = creator_dir / "examples" / f"{args.from_example}.json"
        if not ep.exists():
            avail = [f.stem for f in (creator_dir / "examples").glob("*.json")]
            print(
                f"错误：'{args.from_example}' 不存在。\n"
                f"可用示例：{avail}",
                file=sys.stderr,
            )
            sys.exit(1)
        data = json.loads(ep.read_text(encoding="utf-8"))
        create_techboss(data, args.skills_dir, creator_dir)

    elif args.from_file:
        fp = Path(args.from_file)
        if not fp.exists():
            print(f"错误：文件不存在：{fp}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(fp.read_text(encoding="utf-8"))
        create_techboss(data, args.skills_dir, creator_dir)


if __name__ == "__main__":
    main()
