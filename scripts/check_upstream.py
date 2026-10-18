#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_upstream.py — Đối chiếu cấu hình rubric/ của repo này với dữ liệu công
khai do hmyt-book xuất ra (nguồn: repo HMYT, docs/data/), thay cho chép tay.

  <base>/data/projects.json  → danh sách đề tài (slug, id, link)
  <base>/data/rubric.json    → trọng số các mốc (rubric 'standard')

Kiểm: cùng tập đề tài; topic_id khớp id; page khớp <base> + link; trọng số
M1–M4, FINAL trong rubric/rubric.json khớp. Lệch → thoát 1. Không tải được
dữ liệu (mạng, site chưa xuất) → cảnh báo, thoát 0 (không chặn CI vì lý do ngoài repo).

Dùng: python scripts/check_upstream.py [--base https://fossbk-spec.github.io/hmyt-book]
      python scripts/check_upstream.py --base /duong/dan/dist   (thư mục build cục bộ)
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://fossbk-spec.github.io/hmyt-book"
SITE = "https://fossbk-spec.github.io/hmyt-book"


def load(base, name):
    if base.startswith(("http://", "https://")):
        with urllib.request.urlopen(f"{base.rstrip('/')}/data/{name}", timeout=30) as r:
            return json.load(r)
    return json.loads((Path(base) / "data" / name).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    base = ap.parse_args().base
    try:
        projects = {p["slug"]: p for p in load(base, "projects.json")["projects"]}
        upstream_rubric = load(base, "rubric.json")["standard"]
    except Exception as e:  # noqa: BLE001 — mọi lỗi tải đều chỉ là cảnh báo
        print(f"::warning title=check_upstream::Không tải được dữ liệu từ {base} ({e}) — bỏ qua đối chiếu.")
        return 0

    errors = []
    local = {}
    for f in sorted((ROOT / "rubric" / "topics").glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        local[t.get("topic_slug", f.stem)] = t
    for slug in sorted(set(projects) - set(local)):
        errors.append(f"Đề tài {slug} ({projects[slug]['id']}) có trên hmyt-book nhưng thiếu rubric/topics/{slug}.json")
    for slug in sorted(set(local) - set(projects)):
        errors.append(f"rubric/topics/{slug}.json không có trên hmyt-book")
    for slug in sorted(set(local) & set(projects)):
        t, p = local[slug], projects[slug]
        if str(t.get("topic_id")) != str(p["id"]):
            errors.append(f"{slug}: topic_id {t.get('topic_id')} ≠ {p['id']} (hmyt-book)")
        expect_page = SITE + p["link"]
        if t.get("page") and t["page"] != expect_page:
            errors.append(f"{slug}: page {t['page']} ≠ {expect_page}")

    rubric = json.loads((ROOT / "rubric" / "rubric.json").read_text(encoding="utf-8"))["rubrics"]["standard"]
    weights = {m["id"]: m.get("weight") for m in rubric["milestones"]}
    for mid, v in upstream_rubric.items():
        if weights.get(mid) != v["points"]:
            errors.append(f"rubric.json standard/{mid}: weight {weights.get(mid)} ≠ {v['points']} (hmyt-book)")

    if errors:
        print(f"[FAILED] rubric/ lệch dữ liệu hmyt-book ({base}):")
        for e in errors:
            print("  ❌", e)
        return 1
    print(f"[PASSED] {len(local)} đề tài và trọng số {len(upstream_rubric)} mốc khớp hmyt-book ({base}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
