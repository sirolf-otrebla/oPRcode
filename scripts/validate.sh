#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skills_dir="$repo_root/skills"
expected=(
  pr-review
  pr-review-description
  pr-review-slap
  pr-review-kiss
  pr-review-keep-short
  pr-review-oop
  pr-review-scope
  pr-review-logic
  pr-review-documentation
  pr-review-side-effects
  pr-review-complexity
  pr-review-validator
  pr-review-presenter
)

is_expected() {
  local candidate="$1"
  local name
  for name in "${expected[@]}"; do
    test "$candidate" = "$name" && return 0
  done
  return 1
}

for path in "$skills_dir"/*; do
  test -d "$path" || { printf 'unexpected file in skills/: %s\n' "$path" >&2; exit 1; }
  is_expected "$(basename "$path")" || {
    printf 'unexpected skill directory: %s\n' "$path" >&2
    exit 1
  }
done

for name in "${expected[@]}"; do
  file="$skills_dir/$name/SKILL.md"
  test -f "$file" || { printf 'missing %s\n' "$file" >&2; exit 1; }
  first_name="$(awk '/^name: / { print $2; exit }' "$file")"
  test "$first_name" = "$name" || {
    printf 'name mismatch: %s declares %s\n' "$file" "$first_name" >&2
    exit 1
  }
  grep -q '^description: .\+' "$file" || {
    printf 'missing description: %s\n' "$file" >&2
    exit 1
  }
done

helper="$skills_dir/pr-review/scripts/write_finding.py"
test -f "$helper" || { printf 'missing finding helper: %s\n' "$helper" >&2; exit 1; }

vademecum="$skills_dir/pr-review/scripts/vademecum.py"
test -f "$vademecum" || { printf 'missing vademecum helper: %s\n' "$vademecum" >&2; exit 1; }

python3 -m unittest discover -s "$repo_root/tests" -p 'test_*.py'

printf 'validated %s skills\n' "${#expected[@]}"
