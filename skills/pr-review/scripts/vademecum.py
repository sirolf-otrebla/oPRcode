#!/usr/bin/env python3
"""Build and verify a Markdown-only PR-review vademecum.

Commands:
  vademecum.py prepare --manifest MANIFEST --patch PATCH --out-dir DIR
  vademecum.py build --dir DIR --patch PATCH
  vademecum.py check --dir DIR --patch PATCH

``prepare`` reads ``head_sha`` and ``merge_base_sha`` from a conventional
Markdown manifest (either ``## Head SHA``/``## Merge Base SHA`` sections or
the repository's existing frontmatter fields), inventories a unified Git patch,
and atomically writes ``DIR/_inventory.md``. Inventory IDs are derived from the
change itself and therefore do not depend on patch order.

Authors create ``DIR/_draft.md`` using exactly this heading format (repeat the
Card block; ``None`` is the empty value for list sections):

    # Vademecum Draft
    ## Head SHA
    <full SHA from _inventory.md>
    ## Merge Base SHA
    <full SHA from _inventory.md>
    ## Card CH-001
    ### Kind
    CH
    ### Title
    A concise, single-line title (at most 80 characters)
    ### Facts
    - One concrete, single-line fact (at most 240 characters)
    - Up to eight non-duplicated facts
    ### Anchors
    - `src/example.py#L10-L14@new`
    ### Links
    - `OV-001`
    ### Covers
    - `I-0123456789abcdef`

Card IDs are ``KIND-NNN`` and KIND must be one of OV, CH, FL, CT, SE, ST, DP,
TS, DC, SC, or UN. The Kind value must equal the ID prefix. Anchors use
repository-relative ``path@new|old``, ``path#Lstart@new|old``, or
``path#Lstart-Lend@new|old`` syntax. Path-only anchors exist for changes with
no meaningful line, such as binary, rename, copy, or mode-only items. Links
name other cards. Covers name inventory items; only CH cards may cover items,
every item must be covered, and a CH card may only cover items whose target
path it anchors on the required side (``@new`` for existing paths, ``@old``
only for deletions). Every changed file must therefore be anchored and
described somewhere. No YAML, JSON, frontmatter, HTML, or non-Markdown files
are used inside the vademecum directory.

``build`` validates the complete draft before replacing generated artifacts,
then writes ``_index.md``, ``cards/*.md``, and ``_seal.md`` and removes the
draft. ``check`` rejects incomplete or unexpected artifacts and revalidates
their structure and SHA-256 hashes. All writes use temporary files and rename.
"""

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile


KINDS = {"OV", "CH", "FL", "CT", "SE", "ST", "DP", "TS", "DC", "SC", "UN"}
SHA_RE = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?")
CARD_ID_RE = re.compile(r"([A-Z]{2})-([0-9]{3})")
ANCHOR_RE = re.compile(r"(.+?)(?:#L([1-9][0-9]*)(?:-L([1-9][0-9]*))?)?@(new|old)")


def parse_anchor(anchor):
    """Return (path, start_line, end_line, side) or raise ContractError."""
    match = ANCHOR_RE.fullmatch(anchor)
    require(match is not None, f"invalid anchor: {anchor}")
    path = match.group(1)
    require(not path.endswith("#"), f"invalid anchor: {anchor}")
    return path, match.group(2), match.group(3), match.group(4)
ITEM_ID_RE = re.compile(r"I-[0-9a-f]{16}")
TITLE_LIMIT = 80
FACT_LIMIT = 240
FACT_COUNT_LIMIT = 8


class ContractError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".md", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def clean_value(lines, label):
    value = "\n".join(lines).strip()
    require(value and "\n" not in value, f"{label} must be one non-empty line")
    require(not value.startswith("---"), f"{label} may not use frontmatter")
    return value


def heading_sections(text, level):
    marker = "#" * level + " "
    sections = []
    current = None
    body = []
    for line in text.splitlines():
        if line.startswith(marker) and not line.startswith(marker + "#"):
            if current is not None:
                sections.append((current, body))
            current = line[len(marker):].strip()
            body = []
        elif current is not None:
            body.append(line)
    if current is not None:
        sections.append((current, body))
    return sections


def parse_identity(text, source):
    values = {}
    for heading, body in heading_sections(text, 2):
        key = heading.lower().replace("-", " ").replace("_", " ")
        if key in {"head sha", "merge base sha"}:
            values[key] = clean_value(body, f"{source} {heading}").lower()
    for key, normalized in (("head_sha", "head sha"), ("merge_base_sha", "merge base sha")):
        match = re.search(rf"(?m)^{key}:\s*[\"']?([^\s\"']+)", text)
        if match and normalized not in values:
            values[normalized] = match.group(1).lower()
    for key in ("head sha", "merge base sha"):
        require(key in values, f"{source}: missing {key.title()}")
        require(SHA_RE.fullmatch(values[key]) is not None, f"{source}: invalid {key}")
    return values["head sha"], values["merge base sha"]


def git_path(raw):
    raw = raw.strip()
    if raw.startswith('"'):
        value, end = parse_git_path_token(raw, 0)
        require(not raw[end:].strip(), f"invalid quoted patch path: {raw}")
        return value
    return decode_git_path(raw)


def decode_git_path(value):
    """Decode Git's quoted octal UTF-8 path representation."""
    output = bytearray()
    index = 0
    escapes = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13}
    while index < len(value):
        if value[index] != "\\":
            output.extend(value[index].encode("utf-8"))
            index += 1
            continue
        index += 1
        require(index < len(value), f"invalid Git path escape: {value}")
        if value[index] in "01234567":
            end = index
            while end < min(index + 3, len(value)) and value[end] in "01234567":
                end += 1
            output.append(int(value[index:end], 8))
            index = end
        else:
            escaped = value[index]
            output.append(escapes.get(escaped, ord(escaped)))
            index += 1
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"Git path is not valid UTF-8: {value}") from exc


def parse_git_path_token(text, start):
    while start < len(text) and text[start].isspace():
        start += 1
    require(start < len(text), f"missing Git path in: {text}")
    if text[start] != '"':
        end = start
        while end < len(text) and not text[end].isspace():
            end += 1
        return decode_git_path(text[start:end]), end
    index = start + 1
    encoded = []
    while index < len(text):
        if text[index] == '"':
            return decode_git_path("".join(encoded)), index + 1
        if text[index] == "\\":
            require(index + 1 < len(text), f"invalid quoted Git path: {text}")
            encoded.extend((text[index], text[index + 1]))
            index += 2
        else:
            encoded.append(text[index])
            index += 1
    raise ContractError(f"unterminated quoted Git path: {text}")


def valid_repo_path(path, label="path"):
    require(path and "\x00" not in path and "\n" not in path, f"invalid {label}")
    pure = PurePosixPath(path)
    require(not pure.is_absolute(), f"{label} must be repository-relative: {path}")
    require(".." not in pure.parts and "." not in pure.parts, f"{label} may not traverse: {path}")
    require(path not in {"/dev/null", "dev/null"}, f"invalid {label}: {path}")
    return path


def diff_paths(line):
    prefix = "diff --git "
    require(line.startswith(prefix), f"invalid diff header: {line}")
    old, end = parse_git_path_token(line, len(prefix))
    new, end = parse_git_path_token(line, end)
    require(not line[end:].strip(), f"invalid diff header: {line}")
    require(old.startswith("a/") and new.startswith("b/"), f"invalid diff paths: {line}")
    return old[2:], new[2:]


def item_id(material):
    return "I-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def forbid_frontmatter(text, label):
    require(not text.lstrip().startswith("---"), f"{label}: frontmatter is forbidden")


def split_patch_blocks(text):
    lines = text.splitlines()
    blocks = []
    start = None
    for index, line in enumerate(lines):
        if line.startswith("diff --git "):
            if start is not None:
                blocks.append(lines[start:index])
            start = index
    require(start is not None, "patch has no 'diff --git' entries")
    blocks.append(lines[start:])
    return blocks


def parse_metadata_line(line):
    for prefix, width in (("rename from ", 12), ("rename to ", 10),
                          ("copy from ", 10), ("copy to ", 8)):
        if line.startswith(prefix):
            return prefix[:-1], git_path(line[width:])
    if line.startswith(("old mode ", "new mode ", "new file mode ", "deleted file mode ")):
        return "mode", line
    if line.startswith("Binary files ") or line == "GIT binary patch":
        return "binary", line
    return None, None


def classify_block(block, old_path, new_path):
    rename_from = rename_to = copy_from = copy_to = None
    binary = False
    modes = []
    hunks = []
    for index, line in enumerate(block[1:], 1):
        kind, value = parse_metadata_line(line)
        if kind == "rename from":
            rename_from = value
        elif kind == "rename to":
            rename_to = value
        elif kind == "copy from":
            copy_from = value
        elif kind == "copy to":
            copy_to = value
        elif kind == "mode":
            modes.append(value)
        elif kind == "binary":
            binary = True
        elif line.startswith("@@ "):
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            require(match is not None, f"malformed hunk header: {line}")
            end = index + 1
            while end < len(block) and not block[end].startswith(("@@ ", "diff --git ")):
                end += 1
            hunks.append((line, block[index:end], match.groups()))
    return {
        "rename_from": rename_from, "rename_to": rename_to,
        "copy_from": copy_from, "copy_to": copy_to,
        "binary": binary, "modes": modes, "hunks": hunks,
    }


def hunk_item(display_path, old_path, new_path, metadata):
    header, hunk_lines, groups = metadata
    old_start, old_count, new_start, new_count = groups
    old_count = old_count or "1"
    new_count = new_count or "1"
    material = "hunk\0" + (old_path or "") + "\0" + (new_path or "") + "\0" + "\n".join(hunk_lines)
    return {
        "id": item_id(material), "path": display_path, "change": "hunk",
        "old_path": old_path, "new_path": new_path,
        "old": f"{old_start},{old_count}", "new": f"{new_start},{new_count}",
        "detail": header,
    }


def hunkless_item(display_path, old_path, new_path, block, metadata):
    changes = []
    if metadata["binary"]:
        changes.append("binary")
    if metadata["rename_from"] is not None or metadata["rename_to"] is not None:
        require(metadata["rename_from"] is not None and metadata["rename_to"] is not None,
                "incomplete rename metadata")
        changes.append("rename")
    if metadata["copy_from"] is not None or metadata["copy_to"] is not None:
        require(metadata["copy_from"] is not None and metadata["copy_to"] is not None,
                "incomplete copy metadata")
        changes.append("copy")
    if metadata["modes"]:
        changes.append("mode")
    require(changes, f"hunkless change has no binary, rename/copy, or mode metadata: {display_path}")
    detail = "; ".join(filter(None, [
        f"{metadata['rename_from']} -> {metadata['rename_to']}" if metadata["rename_from"] else "",
        f"{metadata['copy_from']} -> {metadata['copy_to']}" if metadata["copy_to"] else "",
        ", ".join(metadata["modes"]),
    ])) or "binary content"
    material = "hunkless\0" + (old_path or "") + "\0" + (new_path or "") + "\0" + "\n".join(block[1:])
    return {
        "id": item_id(material), "path": display_path, "change": "+".join(changes),
        "old_path": old_path, "new_path": new_path,
        "old": "None", "new": "None", "detail": detail,
    }


def parse_block(block):
    raw_old, raw_new = diff_paths(block[0])
    old_path = None if raw_old == "/dev/null" else raw_old
    new_path = None if raw_new == "/dev/null" else raw_new
    if raw_new == "/dev/null" or any(
            line.startswith("deleted file mode ") for line in block[1:]):
        new_path = None
    for parsed in (old_path, new_path):
        if parsed is not None:
            valid_repo_path(parsed)
    metadata = classify_block(block, old_path, new_path)
    display_path = metadata["rename_to"] or metadata["copy_to"] or new_path or old_path
    require(display_path is not None, f"change has no display path: {block[0]}")
    display_path = valid_repo_path(display_path)
    if metadata["hunks"]:
        return [hunk_item(display_path, old_path, new_path, hunk) for hunk in metadata["hunks"]]
    return [hunkless_item(display_path, old_path, new_path, block, metadata)]


def parse_patch(text):
    require(text.strip(), "patch is empty")
    items = [item for block in split_patch_blocks(text) for item in parse_block(block)]
    ids = [item["id"] for item in items]
    require(len(ids) == len(set(ids)), "patch contains duplicate inventory items")
    return sorted(items, key=lambda item: item["id"])


def render_inventory(head, merge_base, patch_hash, items):
    lines = [
        "# Vademecum Inventory", "", "## Head SHA", head, "", "## Merge Base SHA",
        merge_base, "", "## Patch SHA-256", patch_hash, "",
    ]
    for item in items:
        lines.extend([
            f"## Item {item['id']}", "", "### Path", f"`{item['path']}`", "",
            "### Change", item["change"], "",
            "### Old Path", f"`{item['old_path']}`" if item.get("old_path") else "None", "",
            "### New Path", f"`{item['new_path']}`" if item.get("new_path") else "None", "",
            "### Old Range", item["old"], "",
            "### New Range", item["new"], "", "### Detail", item["detail"], "",
        ])
    return "\n".join(lines)


def parse_inventory(text):
    forbid_frontmatter(text, "_inventory.md")
    require(text.startswith("# Vademecum Inventory\n"), "_inventory.md: invalid title")
    head, merge_base = parse_identity(text, "_inventory.md")
    patch_match = re.search(r"(?m)^## Patch SHA-256\n+([0-9a-f]{64})\s*\n", text)
    require(patch_match is not None, "_inventory.md: missing patch hash")
    items = {}
    matches = list(re.finditer(r"(?m)^## Item (I-[0-9a-f]{16})\s*$", text))
    require(matches, "_inventory.md: no inventory items")
    for index, match in enumerate(matches):
        item = match.group(1)
        require(item not in items, f"_inventory.md: duplicate item {item}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end]
        fields = {}
        for heading, value_lines in heading_sections(body, 3):
            fields[heading] = clean_value(value_lines, f"{item} {heading}")
        require(list(fields) == ["Path", "Change", "Old Path", "New Path", "Old Range", "New Range", "Detail"],
                f"_inventory.md: malformed fields for {item}")
        for key in ("Path", "Old Path", "New Path"):
            value = fields[key]
            if value == "None":
                continue
            require(value.startswith("`") and value.endswith("`"), f"{item}: {key} must be code quoted")
            valid_repo_path(value[1:-1], f"{item} {key.lower()}")
        items[item] = fields
    return head, merge_base, patch_match.group(1), items


def parse_list(lines, label, pattern=None):
    content = [line for line in lines if line.strip()]
    require(content, f"{label} must not be empty")
    if content == ["None"]:
        return []
    values = []
    for line in content:
        match = re.fullmatch(r"- `([^`]+)`", line)
        require(match is not None, f"{label} entries must be '- `value`'")
        value = match.group(1)
        require(pattern is None or pattern.fullmatch(value), f"{label}: invalid value {value}")
        values.append(value)
    require(len(values) == len(set(values)), f"{label} contains duplicates")
    return values


def parse_facts(lines, label):
    content = [line for line in lines if line.strip()]
    require(content, f"{label} must not be empty")
    facts = []
    for line in content:
        require(line.startswith("- ") and len(line) > 2, f"{label} entries must be '- fact'")
        fact = line[2:].strip()
        require(fact and "\n" not in fact, f"{label} entries must be one non-empty line")
        require(len(fact) <= FACT_LIMIT, f"{label} entry exceeds {FACT_LIMIT} characters")
        facts.append(fact)
    require(len(facts) <= FACT_COUNT_LIMIT,
            f"{label} has more than {FACT_COUNT_LIMIT} entries")
    require(len(facts) == len(set(facts)), f"{label} contains duplicates")
    return facts


def validate_anchor(anchor):
    path, start, end, _side = parse_anchor(anchor)
    valid_repo_path(path, "anchor path")
    if start and end:
        require(int(end) >= int(start), f"anchor range is reversed: {anchor}")


def path_value(fields, key):
    value = fields[key]
    require(value == "None" or (value.startswith("`") and value.endswith("`")),
            f"{key} must be code quoted or None")
    return None if value == "None" else value[1:-1]


def anchor_matches_target(anchors, target_path, required_side):
    for anchor in anchors:
        path, _start, _end, side = parse_anchor(anchor)
        if path == target_path and side == required_side:
            return True
    return False


def validate_cards(cards, inventory, head, merge_base, expected_identity):
    require((head, merge_base) == expected_identity, "draft identity does not match _inventory.md")
    require(cards, "draft must contain at least one card")
    coverage = {item: [] for item in inventory}
    for card_id, card in cards.items():
        match = CARD_ID_RE.fullmatch(card_id)
        require(match is not None, f"invalid card ID: {card_id}")
        require(match.group(1) in KINDS, f"invalid card kind in ID: {card_id}")
        require(card["kind"] in KINDS, f"{card_id}: invalid kind {card['kind']}")
        require(card["kind"] == match.group(1), f"{card_id}: Kind must match ID prefix")
        require(len(card["title"]) <= TITLE_LIMIT, f"{card_id}: title exceeds {TITLE_LIMIT} characters")
        require(card["facts"], f"{card_id}: at least one fact is required")
        require(len(card["facts"]) <= FACT_COUNT_LIMIT,
                f"{card_id}: more than {FACT_COUNT_LIMIT} facts")
        for fact in card["facts"]:
            require(len(fact) <= FACT_LIMIT,
                    f"{card_id}: fact exceeds {FACT_LIMIT} characters")
        require(not re.search(r"[<>]", card["title"] + "".join(card["facts"])),
                f"{card_id}: HTML is forbidden")
        for anchor in card["anchors"]:
            validate_anchor(anchor)
        require(card_id not in card["links"], f"{card_id}: self-link is forbidden")
        for link in card["links"]:
            require(link in cards, f"{card_id}: link targets missing card {link}")
        if card["covers"]:
            require(card["kind"] == "CH", f"{card_id}: only CH cards may cover inventory items")
        for item in card["covers"]:
            require(item in coverage, f"{card_id}: unknown inventory item {item}")
            fields = inventory[item]
            new_target = path_value(fields, "New Path")
            if new_target:
                target, side = new_target, "new"
            else:
                target, side = path_value(fields, "Old Path"), "old"
            require(anchor_matches_target(card["anchors"], target, side),
                    f"{card_id}: item {item} requires an anchor on `{target}@{side}`")
            coverage[item].append(card_id)
    missing = [item for item, owners in coverage.items() if not owners]
    require(not missing, "inventory items not covered by CH cards: " + ", ".join(missing))
    require(any(card["kind"] == "OV" for card in cards.values()),
            "vademecum requires at least one OV card")
    require(any(card["kind"] == "CH" for card in cards.values()),
            "vademecum requires at least one CH card")
    return coverage


def parse_cards_draft(text, inventory, expected_identity):
    forbid_frontmatter(text, "_draft.md")
    require(text.startswith("# Vademecum Draft\n"), "_draft.md: invalid title")
    require(not re.search(r"(?m)^```", text), "_draft.md: fenced data is forbidden")
    head, merge_base = parse_identity(text, "_draft.md")
    card_matches = list(re.finditer(r"(?m)^## Card ([A-Za-z0-9-]+)\s*$", text))
    require(card_matches, "_draft.md: no Card headings")
    prefix = text[:card_matches[0].start()]
    prefix_h2 = [name for name, _ in heading_sections(prefix, 2)]
    require(prefix_h2 == ["Head SHA", "Merge Base SHA"], "_draft.md: identity headings must precede cards")
    cards = {}
    for index, match in enumerate(card_matches):
        card_id = match.group(1)
        require(card_id not in cards, f"duplicate card ID: {card_id}")
        end = card_matches[index + 1].start() if index + 1 < len(card_matches) else len(text)
        fields = heading_sections(text[match.end():end], 3)
        require([name for name, _ in fields] == ["Kind", "Title", "Facts", "Anchors", "Links", "Covers"],
                f"{card_id}: headings must be Kind, Title, Facts, Anchors, Links, Covers")
        values = dict(fields)
        cards[card_id] = {
            "kind": clean_value(values["Kind"], f"{card_id} Kind"),
            "title": clean_value(values["Title"], f"{card_id} Title"),
            "facts": parse_facts(values["Facts"], f"{card_id} Facts"),
            "anchors": parse_list(values["Anchors"], f"{card_id} Anchors", ANCHOR_RE),
            "links": parse_list(values["Links"], f"{card_id} Links", CARD_ID_RE),
            "covers": parse_list(values["Covers"], f"{card_id} Covers", ITEM_ID_RE),
        }
    coverage = validate_cards(cards, inventory, head, merge_base, expected_identity)
    return cards, coverage


def render_card(card_id, card):
    def values(items, links=False):
        if not items:
            return ["None"]
        if links:
            return [f"- [{item}]({item}.md)" for item in items]
        return [f"- `{item}`" for item in items]
    lines = [
        f"# {card_id}: {card['title']}", "", "## Kind", f"`{card['kind']}`", "",
        "## Facts", *[f"- {fact}" for fact in card["facts"]], "",
        "## Anchors", *values(card["anchors"]), "",
        "## Links", *values(card["links"], True), "", "## Covers", *values(card["covers"]), "",
    ]
    return "\n".join(lines)


def render_index(head, merge_base, cards, coverage):
    lines = ["# Vademecum", "", "## Head SHA", head, "", "## Merge Base SHA", merge_base, "", "## Cards"]
    for kind in sorted(KINDS):
        selected = [(card_id, cards[card_id]) for card_id in sorted(cards)
                    if cards[card_id]["kind"] == kind]
        if not selected:
            continue
        lines.extend(["", f"### {kind}"])
        for card_id, card in selected:
            anchor = f" `{card['anchors'][0]}`" if card["anchors"] else ""
            links = ("; links " + ", ".join(card["links"])) if card["links"] else ""
            lines.append(
                f"- [{card_id}: {card['title']}](cards/{card_id}.md): "
                f"{card['facts'][0]}{anchor}{links}"
            )
    lines.append("")
    return "\n".join(lines)


def render_seal(head, merge_base, cards, coverage, hashes):
    lines = ["# Vademecum Seal", "", "## Head SHA", head, "", "## Merge Base SHA", merge_base,
             "", "## Card Inventory"]
    for card_id in sorted(cards):
        lines.extend([f"### Card {card_id}", f"`{cards[card_id]['kind']}`"])
    lines.extend(["", "## Coverage"])
    for item in sorted(coverage):
        lines.extend([f"### Item {item}", "- " + ", ".join(f"`{card}`" for card in sorted(coverage[item]))])
    lines.extend(["", "## SHA-256 Hashes"])
    for path in sorted(hashes):
        lines.append(f"### SHA-256 {hashes[path]} {path}")
    lines.append("")
    return "\n".join(lines)


def inspect_tree(directory, building=False):
    directory = Path(directory)
    require(directory.is_dir(), f"not a directory: {directory}")
    for path in directory.rglob("*"):
        relative = path.relative_to(directory)
        if path.is_symlink():
            raise ContractError(f"symlinks are forbidden: {relative}")
        if path.is_file():
            require(path.suffix == ".md", f"non-Markdown file in vademecum: {relative}")
        elif path.is_dir():
            require(relative == Path("cards"), f"unexpected directory: {relative}")
        else:
            raise ContractError(f"unsupported artifact: {relative}")
    allowed = {"_inventory.md", "_index.md", "_seal.md"}
    if building:
        allowed.add("_draft.md")
    for path in directory.iterdir():
        require(path.name in allowed or path.name == "cards", f"unexpected artifact: {path.name}")


def prepare(args):
    manifest = read_text(args.manifest)
    patch = read_text(args.patch)
    head, merge_base = parse_identity(manifest, str(args.manifest))
    items = parse_patch(patch)
    output = Path(args.out_dir)
    restore_interrupted_swap(output)
    if output.exists():
        inspect_tree(output, building=True)
    else:
        output.mkdir(parents=True)
    inventory = render_inventory(head, merge_base, sha256_text(patch), items)
    atomic_write(output / "_inventory.md", inventory)
    print(f"prepared {len(items)} inventory items in {output}")


def validate_inventory_patch(inventory_text, patch_path):
    head, merge_base, patch_hash, inventory = parse_inventory(inventory_text)
    patch = read_text(patch_path)
    require(sha256_text(patch) == patch_hash,
            "_inventory.md patch hash does not match the frozen patch")
    expected = render_inventory(head, merge_base, patch_hash, parse_patch(patch))
    require(inventory_text == expected,
            "_inventory.md does not match the frozen patch inventory")
    return head, merge_base, inventory


def build_outputs(directory, patch_path):
    inventory_text = read_text(directory / "_inventory.md")
    head, merge_base, inventory = validate_inventory_patch(inventory_text, patch_path)
    cards, coverage = parse_cards_draft(read_text(directory / "_draft.md"), inventory, (head, merge_base))
    rendered_cards = {f"cards/{card}.md": render_card(card, cards[card]) for card in sorted(cards)}
    index = render_index(head, merge_base, cards, coverage)
    hashes = {"_inventory.md": sha256_text(inventory_text), "_index.md": sha256_text(index)}
    hashes.update({path: sha256_text(text) for path, text in rendered_cards.items()})
    seal = render_seal(head, merge_base, cards, coverage, hashes)
    return index, rendered_cards, seal


def build(args):
    directory = Path(args.dir)
    restore_interrupted_swap(directory)
    inspect_tree(directory, building=True)
    require((directory / "_draft.md").is_file(), "missing _draft.md")
    index, cards, seal = build_outputs(directory, args.patch)

    def populate(stage):
        (stage / "cards").mkdir()
        atomic_write(stage / "_inventory.md", read_text(directory / "_inventory.md"))
        atomic_write(stage / "_index.md", index)
        atomic_write(stage / "_seal.md", seal)
        for relative, text in cards.items():
            atomic_write(stage / relative, text)
        check_directory(stage, args.patch)

    swap_with_backup(directory, populate)
    atomic_write(seal_hash_path(directory), sha256_text(seal))
    print(f"built {len(cards)} cards in {directory}")


def parse_rendered_card(path, card_id):
    text = read_text(path)
    title_match = re.match(rf"# {re.escape(card_id)}: ([^\n]+)\n", text)
    require(title_match is not None, f"{path}: invalid title")
    sections = heading_sections(text, 2)
    require([name for name, _ in sections] == ["Kind", "Facts", "Anchors", "Links", "Covers"],
            f"{path}: malformed headings")
    values = dict(sections)
    kind = clean_value(values["Kind"], f"{card_id} Kind")
    require(kind.startswith("`") and kind.endswith("`"), f"{card_id}: Kind must be code quoted")
    links = []
    link_lines = [line for line in values["Links"] if line.strip()]
    if link_lines != ["None"]:
        for line in link_lines:
            match = re.fullmatch(r"- \[([A-Z]{2}-[0-9]{3})\]\(\1\.md\)", line)
            require(match is not None, f"{card_id}: invalid rendered link")
            links.append(match.group(1))
    return {
        "kind": kind[1:-1], "title": title_match.group(1),
        "facts": parse_facts(values["Facts"], f"{card_id} Facts"),
        "anchors": parse_list(values["Anchors"], f"{card_id} Anchors", ANCHOR_RE),
        "links": links,
        "covers": parse_list(values["Covers"], f"{card_id} Covers", ITEM_ID_RE),
    }


def seal_hash_path(directory):
    return Path(str(directory) + ".seal-hash")


BACKUP_SUFFIX = ".vademecum-backup"


def backup_path(directory):
    return Path(str(directory) + BACKUP_SUFFIX)


def restore_interrupted_swap(directory):
    """Undo an interrupted swap: a missing target with a backup present means a
    previous process died between the two renames; move the backup back."""
    backup = backup_path(directory)
    if not directory.exists() and backup.is_dir():
        os.replace(backup, directory)


def swap_with_backup(directory, populate):
    """Atomically replace directory with a freshly staged, verified set.

    A crash between the two renames leaves the deterministic backup sibling in
    place, which restore_interrupted_swap rolls back on the next invocation.
    """
    directory = Path(directory)
    backup = backup_path(directory)
    require(not backup.exists(), f"stale backup exists: {backup}")
    stage = Path(tempfile.mkdtemp(prefix=".vademecum-build-", dir=directory.parent))
    completed = False
    try:
        populate(stage)
        os.replace(directory, backup)
        try:
            os.replace(stage, directory)
            completed = True
        except BaseException:
            print(f"warning: swap failed; verified stage preserved at {stage}",
                  file=sys.stderr)
            raise
    except BaseException:
        if backup.is_dir() and not directory.exists():
            os.replace(backup, directory)
        raise
    finally:
        if completed:
            shutil.rmtree(backup, ignore_errors=True)
        else:
            shutil.rmtree(stage, ignore_errors=True)


def check_seal_hash(directory, expected_hash):
    actual = sha256_text(read_text(directory / "_seal.md"))
    require(actual == expected_hash,
            f"seal hash mismatch: expected {expected_hash}, found {actual}")


def check_directory(directory, patch_path, expected_seal_hash=None):
    directory = Path(directory)
    inspect_tree(directory)
    required = {"_inventory.md", "_index.md", "_seal.md", "cards"}
    require({path.name for path in directory.iterdir()} == required, "artifact set is incomplete or unexpected")
    head, merge_base, inventory = validate_inventory_patch(
        read_text(directory / "_inventory.md"), patch_path)
    card_files = sorted((directory / "cards").iterdir())
    require(card_files, "cards directory is empty")
    cards = {}
    for path in card_files:
        require(path.is_file() and path.name.endswith(".md"), f"unexpected card artifact: {path.name}")
        card_id = path.stem
        require(CARD_ID_RE.fullmatch(card_id) is not None, f"invalid card filename: {path.name}")
        cards[card_id] = parse_rendered_card(path, card_id)
    coverage = validate_cards(cards, inventory, head, merge_base, (head, merge_base))
    expected_index = render_index(head, merge_base, cards, coverage)
    actual_index = read_text(directory / "_index.md")
    require(actual_index == expected_index, "_index.md does not match cards and inventory")
    hashes = {"_inventory.md": sha256_text(read_text(directory / "_inventory.md")),
              "_index.md": sha256_text(actual_index)}
    for card_id in sorted(cards):
        relative = f"cards/{card_id}.md"
        hashes[relative] = sha256_text(read_text(directory / relative))
    expected_seal = render_seal(head, merge_base, cards, coverage, hashes)
    require(read_text(directory / "_seal.md") == expected_seal, "_seal.md identity, coverage, inventory, or hashes are invalid")
    if expected_seal_hash is not None:
        check_seal_hash(directory, expected_seal_hash)
    return len(cards)


def check(args):
    directory = Path(args.dir)
    restore_interrupted_swap(directory)
    expected_seal_hash = None
    hash_file = seal_hash_path(directory)
    if hash_file.is_file():
        expected_seal_hash = read_text(hash_file).strip()
    count = check_directory(directory, args.patch, expected_seal_hash)
    print(f"checked {count} cards in {args.dir}")


def parser():
    result = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = result.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="create _inventory.md from a manifest and patch")
    prepare_parser.add_argument("--manifest", required=True, type=Path)
    prepare_parser.add_argument("--patch", required=True, type=Path)
    prepare_parser.add_argument("--out-dir", required=True, type=Path)
    prepare_parser.set_defaults(run=prepare)
    build_parser = commands.add_parser("build", help="validate _draft.md and build sealed artifacts")
    build_parser.add_argument("--dir", required=True, type=Path)
    build_parser.add_argument("--patch", required=True, type=Path)
    build_parser.set_defaults(run=build)
    check_parser = commands.add_parser("check", help="revalidate a built artifact set")
    check_parser.add_argument("--dir", required=True, type=Path)
    check_parser.add_argument("--patch", required=True, type=Path)
    check_parser.set_defaults(run=check)
    return result


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        args.run(args)
        return 0
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
