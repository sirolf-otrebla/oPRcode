#!/usr/bin/env python3
"""Write and validate PR-review finding files.

A finding is a single Markdown file with YAML frontmatter and fixed sections.
This script enforces the shared contract so reviewers cannot emit malformed
findings.

Usage:
  write_finding.py <finding.json> --out-dir <reviewer_dir>
  write_finding.py --check <finding.md>
  write_finding.py --check-dir <reviewer_dir>
  write_finding.py --help

The JSON input uses these fields:

  reviewer    one of the nine reviewer names
  severity    critical | high | medium | low | nitpick
  confidence  integer 0..100
  file        repository-relative path
  start_line  positive integer
  end_line    positive integer, >= start_line
  side        new | old
  head_sha    frozen head SHA from the manifest
  title       concise problem title
  comment     concrete impact
  evidence    reachable proof or reproduction
  code        bounded relevant snippet
  suggestion  smallest practical fix or regression test
  slug        optional short title for the filename (defaults to title)
"""

import json
import re
import sys
import os

REVIEWERS = {
    "slap",
    "kiss",
    "keep_short",
    "oop",
    "scope",
    "logic",
    "documentation",
    "side_effects",
    "complexity",
}
SEVERITIES = {"critical", "high", "medium", "low", "nitpick"}
SIDES = {"new", "old"}


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text or "unnamed"


def validate_meta(data):
    errors = []
    reviewer = data.get("reviewer")
    if reviewer not in REVIEWERS:
        errors.append(f"reviewer must be one of {sorted(REVIEWERS)}")
    if data.get("severity") not in SEVERITIES:
        errors.append(f"severity must be one of {sorted(SEVERITIES)}")
    confidence = data.get("confidence")
    if not isinstance(confidence, int) or not 0 <= confidence <= 100:
        errors.append("confidence must be an integer 0..100")
    file_path = data.get("file")
    if not isinstance(file_path, str) or not file_path.strip():
        errors.append("file must be a non-empty repository-relative path")
    elif file_path.startswith("/") or ".." in file_path.split("/"):
        errors.append("file must be repository-relative with no absolute path or '..'")
    start = data.get("start_line")
    end = data.get("end_line")
    if not isinstance(start, int) or start < 1:
        errors.append("start_line must be a positive integer")
    if not isinstance(end, int) or end < 1:
        errors.append("end_line must be a positive integer")
    if isinstance(start, int) and isinstance(end, int) and end < start:
        errors.append("end_line must be >= start_line")
    if data.get("side") not in SIDES:
        errors.append("side must be 'new' or 'old'")
    head_sha = data.get("head_sha")
    if not isinstance(head_sha, str) or not head_sha.strip():
        errors.append("head_sha must be a non-empty string")
    return errors


def validate_body(data):
    errors = []
    for field in ("title", "comment", "evidence", "suggestion"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    if not isinstance(data.get("code"), str):
        errors.append("code must be a string")
    return errors


def yaml_string(value):
    return json.dumps(str(value))


def build_finding(data):
    slug = normalize(data.get("slug") or data["title"])
    path_slug = normalize(data["file"])
    reviewer = data["reviewer"]
    severity = data["severity"]
    start = data["start_line"]
    finding_id = f"{reviewer}_{path_slug}_{start}_{slug}"
    filename = f"{severity}_{path_slug}_{start}_{slug}.md"
    lines = [
        "---",
        f"id: {yaml_string(finding_id)}",
        f"reviewer: {yaml_string(reviewer)}",
        f"severity: {yaml_string(severity)}",
        f"confidence: {data['confidence']}",
        f"file: {yaml_string(data['file'])}",
        f"start_line: {start}",
        f"end_line: {data['end_line']}",
        f"side: {yaml_string(data['side'])}",
        f"head_sha: {yaml_string(data['head_sha'])}",
        "---",
        f"# {data['title']}",
        "",
        "## Comment",
        data["comment"].strip(),
        "",
        "## Evidence",
        data["evidence"].strip(),
        "",
        "## Code",
        "```text",
        data["code"].strip(),
        "```",
        "",
        "## Suggestion",
        data["suggestion"].strip(),
        "",
    ]
    return filename, "\n".join(lines)


def write_finding(json_path, out_dir):
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    errors = validate_meta(data) + validate_body(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
    filename, content = build_finding(data)
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, filename)
    if os.path.exists(target):
        fail(f"refusing to overwrite existing finding: {target}")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content)
    print(f"wrote {target}")


INT_FIELDS = {"confidence", "start_line", "end_line", "findings", "inconclusive_candidates"}


def parse_frontmatter(path):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    frontmatter, body = parts[1], parts[2]
    fields = {}
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not match:
            continue
        key, raw = match.group(1), match.group(2).strip()
        if raw.startswith('"') and raw.endswith('"'):
            try:
                fields[key] = json.loads(raw)
            except json.JSONDecodeError:
                fields[key] = raw
        elif key in INT_FIELDS and raw.isdigit():
            fields[key] = int(raw)
        else:
            fields[key] = raw
    return fields, body


def extract_section(body, heading):
    idx = body.find(heading)
    if idx == -1:
        return None
    rest = body[idx + len(heading):]
    next_heading = rest.find("\n## ")
    content = rest if next_heading == -1 else rest[:next_heading]
    return content.strip()


def check_finding(path):
    fields, body = parse_frontmatter(path)
    if fields is None:
        fail(f"{path}: missing YAML frontmatter")
    errors = validate_meta(fields)
    for error in errors:
        print(f"{path}: {error}", file=sys.stderr)
    if errors:
        sys.exit(1)
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if not title_match or not title_match.group(1).strip():
        fail(f"{path}: missing non-empty title heading")
    for section in ("Comment", "Evidence", "Suggestion"):
        if not extract_section(body, f"## {section}"):
            fail(f"{path}: empty {section} section")
    code = extract_section(body, "## Code")
    if code is None:
        fail(f"{path}: missing Code section")
    code_body = re.sub(r"```.*?\n", "", code).replace("```", "").strip()
    if not code_body:
        fail(f"{path}: empty Code section")
    print(f"ok {path}")


def check_dir(reviewer_dir):
    if not os.path.isdir(reviewer_dir):
        fail(f"not a directory: {reviewer_dir}")
    status_path = os.path.join(reviewer_dir, "_status.md")
    if not os.path.isfile(status_path):
        fail(f"{reviewer_dir}: missing _status.md")
    status_fields, _ = parse_frontmatter(status_path)
    if status_fields is None:
        fail(f"{status_path}: missing YAML frontmatter")
    for field in ("reviewer", "result", "findings", "inconclusive_candidates"):
        if field not in status_fields:
            fail(f"{status_path}: missing field {field}")
    if status_fields["result"] not in {"complete", "partial", "blocked"}:
        fail(f"{status_path}: result must be complete|partial|blocked")
    finding_files = [
        name
        for name in os.listdir(reviewer_dir)
        if name.endswith(".md") and name != "_status.md"
    ]
    for name in finding_files:
        check_finding(os.path.join(reviewer_dir, name))
    declared = status_fields["findings"]
    if not isinstance(declared, int) or declared != len(finding_files):
        fail(
            f"{status_path}: findings={declared} but {len(finding_files)} finding files present"
        )
    print(f"ok {reviewer_dir}: {len(finding_files)} findings")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[1] == "--check":
        if len(argv) != 3:
            fail("usage: write_finding.py --check <finding.md>")
        check_finding(argv[2])
        return 0
    if argv[1] == "--check-dir":
        if len(argv) != 3:
            fail("usage: write_finding.py --check-dir <reviewer_dir>")
        check_dir(argv[2])
        return 0
    if len(argv) != 4 or argv[2] != "--out-dir":
        fail("usage: write_finding.py <finding.json> --out-dir <reviewer_dir>")
    write_finding(argv[1], argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
