#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$repo_root/skills"
target_dir="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills"

"$repo_root/scripts/validate.sh"
mkdir -p "$target_dir"

# Refuse every conflict before replacing anything.
for source in "$source_dir"/*; do
  test -d "$source" || continue
  name="$(basename "$source")"
  target="$target_dir/$name"
  if test -e "$target" && test ! -f "$target/.pr-review-skill-managed"; then
    printf 'refusing to replace unmanaged skill: %s\n' "$target" >&2
    exit 1
  fi
done

transaction="$(mktemp -d "$target_dir/.pr-review-skill-install.XXXXXX")"
stage="$transaction/stage"
backup="$transaction/backup"
mkdir -p "$stage" "$backup"
activated=()
backed_up=()
committed=0

rollback() {
  if test "$committed" = 1; then
    return
  fi
  local target
  for target in "${activated[@]}"; do
    rm -rf "$target"
  done
  for target in "${backed_up[@]}"; do
    mv "$backup/$(basename "$target")" "$target"
  done
  rm -rf "$transaction"
}
trap rollback EXIT INT TERM HUP

# Prepare every replacement before touching active skills.
for source in "$source_dir"/*; do
  name="$(basename "$source")"
  cp -R "$source" "$stage/$name"
  : > "$stage/$name/.pr-review-skill-managed"
done

# Back up current managed skills, including obsolete ones from this package.
for target in "$target_dir"/pr-review*; do
  test -e "$target" || continue
  test -f "$target/.pr-review-skill-managed" || continue
  mv "$target" "$backup/$(basename "$target")"
  backed_up+=("$target")
done

for source in "$stage"/*; do
  name="$(basename "$source")"
  target="$target_dir/$name"
  mv "$source" "$target"
  activated+=("$target")
done

committed=1
trap - EXIT INT TERM HUP
rm -rf "$transaction"

printf 'installed skills in %s\n' "$target_dir"
