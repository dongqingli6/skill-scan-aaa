#!/usr/bin/env python3
"""
Pre-Package Pipeline: Quality assurance for skill packaging.

Orchestrates validation, security scanning, writing quality checks,
and packaging into a single pre-flight gate.
"""

import sys
import os
import json
import argparse
import zipfile
import re
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any, List, Optional


class PipelineStage:
    """Base class for pipeline stages."""

    def __init__(self, name: str):
        self.name = name
        self.status = None
        self.errors = []
        self.warnings = []
        self.data = {}

    def run(self, skill_dir: Path, tools_dir: Optional[Path] = None) -> bool:
        """Run stage. Return True if gate passes, False if blocked."""
        raise NotImplementedError

    def format_output(self) -> str:
        """Format stage result for console output."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Serialize stage result to dict."""
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "data": self.data,
        }


class ValidationStage(PipelineStage):
    """Skill structure and metadata validation."""

    def __init__(self):
        super().__init__("Skill Validation")

    def run(self, skill_dir: Path, tools_dir: Optional[Path] = None) -> bool:
        """Validate skill structure and metadata."""
        self.errors = []
        self.warnings = []

        # Check SKILL.md exists
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            self.errors.append("SKILL.md not found in skill root")
            self.status = "FAIL"
            return False

        # Validate YAML frontmatter
        try:
            with open(skill_md, "r") as f:
                content = f.read()
                if not content.startswith("---"):
                    self.errors.append(
                        "SKILL.md missing YAML frontmatter (must start with ---)"
                    )
                    self.status = "FAIL"
                    return False

                # Extract frontmatter
                parts = content.split("---", 2)
                if len(parts) < 3:
                    self.errors.append("SKILL.md frontmatter not properly closed")
                    self.status = "FAIL"
                    return False

                fm = parts[1]
                if "name:" not in fm:
                    self.errors.append("SKILL.md frontmatter missing 'name' field")
                    self.status = "FAIL"
                    return False

                if "description:" not in fm:
                    self.errors.append(
                        "SKILL.md frontmatter missing 'description' field"
                    )
                    self.status = "FAIL"
                    return False

        except Exception as e:
            self.errors.append(f"Error reading SKILL.md: {str(e)}")
            self.status = "FAIL"
            return False

        # Extract skill name from frontmatter
        try:
            with open(skill_md, "r") as f:
                for line in f:
                    if line.startswith("name:"):
                        self.data["skill_name"] = line.split(":", 1)[1].strip()
                        break
        except ValueError as e:
            # Log parsing errors but don't block validation
            print(f"Warning: Could not parse skill name from frontmatter: {e}", file=sys.stderr)

        self.status = "PASS"
        return True

    def format_output(self) -> str:
        status_str = f"{self.status}"
        return f"✓ {self.name}: {status_str}"


class SecurityScanStage(PipelineStage):
    """Run security checks on skill code."""

    def __init__(self):
        super().__init__("Security Scan")

    def run(self, skill_dir: Path, tools_dir: Optional[Path] = None) -> bool:
        """Scan skill for security issues."""
        self.errors = []
        self.warnings = []

        # Check for common security issues
        for py_file in skill_dir.glob("**/*.py"):
            try:
                with open(py_file, "r") as f:
                    content = f.read()
                    if "eval(" in content or "exec(" in content:
                        self.errors.append(f"{py_file}: Contains eval() or exec()")
                    if "__import__" in content:
                        self.warnings.append(f"{py_file}: Uses __import__()")
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}", file=sys.stderr)

        self.status = "PASS" if not self.errors else "FAIL"
        return not self.errors

    def format_output(self) -> str:
        status_str = f"{self.status}"
        output = f"✓ {self.name}: {status_str}"
        if self.errors:
            output += "\n  Errors:\n    " + "\n    ".join(self.errors)
        if self.warnings:
            output += "\n  Warnings:\n    " + "\n    ".join(self.warnings)
        return output


class WritingQualityStage(PipelineStage):
    """Check writing quality in skill documentation."""

    def __init__(self):
        super().__init__("Writing Quality")

    def run(self, skill_dir: Path, tools_dir: Optional[Path] = None) -> bool:
        """Check writing quality."""
        self.errors = []
        self.warnings = []

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            self.errors.append("SKILL.md not found")
            self.status = "FAIL"
            return False

        try:
            with open(skill_md, "r") as f:
                content = f.read()
                # Check for minimum length
                lines = content.split("\n")
                if len(lines) < 5:
                    self.warnings.append("SKILL.md is very short (< 5 lines)")
        except Exception as e:
            print(f"Warning: Could not check writing quality: {e}", file=sys.stderr)

        self.status = "PASS"
        return True

    def format_output(self) -> str:
        status_str = f"{self.status}"
        output = f"✓ {self.name}: {status_str}"
        if self.warnings:
            output += "\n  Warnings:\n    " + "\n    ".join(self.warnings)
        return output


class PackagingStage(PipelineStage):
    """Package skill into .skill file."""

    def __init__(self):
        super().__init__("Packaging")

    def run(self, skill_dir: Path, tools_dir: Optional[Path] = None) -> bool:
        """Package skill."""
        self.errors = []
        self.warnings = []

        try:
            # Create skill package
            skill_name = skill_dir.name
            output_file = skill_dir.parent / f"{skill_name}.skill"

            with zipfile.ZipFile(output_file, "w") as zf:
                for file_path in skill_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(skill_dir.parent)
                        zf.write(file_path, arcname)

            self.data["package_path"] = str(output_file)
            self.data["package_size"] = output_file.stat().st_size

        except Exception as e:
            self.errors.append(f"Packaging failed: {str(e)}")
            self.status = "FAIL"
            return False

        self.status = "PASS"
        return True

    def format_output(self) -> str:
        status_str = f"{self.status}"
        output = f"✓ {self.name}: {status_str}"
        if "package_path" in self.data:
            output += f"\n  Package: {self.data['package_path']}"
            output += f"\n  Size: {self.data['package_size']} bytes"
        return output


class Pipeline:
    """Orchestrate all pipeline stages."""

    def __init__(self):
        self.stages = [
            ValidationStage(),
            SecurityScanStage(),
            WritingQualityStage(),
            PackagingStage(),
        ]

    def run(
        self, skill_dir: Path, tools_dir: Optional[Path] = None, verbose: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run all stages. Return (success, results)."""
        success = True
        results = {"skill": str(skill_dir), "timestamp": str(datetime.now())}

        for stage in self.stages:
            try:
                stage_success = stage.run(skill_dir, tools_dir)
                results[stage.name] = stage.to_dict()

                if verbose:
                    print(stage.format_output())

                if not stage_success and stage.name != "Writing Quality":
                    success = False
                    break

            except Exception as e:
                print(f"Error in {stage.name}: {e}", file=sys.stderr)
                success = False
                break

        return success, results

    def format_report(self, results: Dict[str, Any]) -> str:
        """Format pipeline results as report."""
        report = f"Pipeline Report: {results['timestamp']}\n"
        report += f"Skill: {results['skill']}\n"
        report += "=" * 60 + "\n"

        for stage_name, stage_data in results.items():
            if stage_name not in ("skill", "timestamp"):
                report += f"\n{stage_name}:\n"
                report += f"  Status: {stage_data['status']}\n"
                if stage_data["errors"]:
                    report += f"  Errors:\n"
                    for error in stage_data["errors"]:
                        report += f"    - {error}\n"
                if stage_data["warnings"]:
                    report += f"  Warnings:\n"
                    for warning in stage_data["warnings"]:
                        report += f"    - {warning}\n"

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pre-package pipeline for skill QA"
    )
    parser.add_argument("skill_dir", help="Path to skill directory")
    parser.add_argument(
        "--tools", help="Path to shared tools directory", default=None
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "-o", "--output", help="Output JSON file for results", default=None
    )

    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    if not skill_dir.exists():
        print(f"Error: Skill directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    pipeline = Pipeline()
    success, results = pipeline.run(skill_dir, args.tools, args.verbose)

    report = pipeline.format_report(results)
    print(report)

    if args.output:
        try:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            if args.verbose:
                print(f"Results saved to {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
