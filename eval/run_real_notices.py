"""가방쏙 규칙 코드(guard, simple_extract)가 실제 통신문 23건 인용 문장을 얼마나 맞게 읽는지 잰다.

실행: python3 eval/run_real_notices.py   (저장소 맨 위에서, 표준 라이브러리만)
정답표: eval/real_notices_23.json (AI가 인용 문장만 읽고 적음, 사람 검수 없음)
결과: 화면 표 + eval/real_notices_23_result.json

이름 비교 기준: 두 이름에서 공백을 모두 뺀 뒤, 한쪽이 다른 쪽 안에 들어 있으면 같은 물건으로 본다.
정답표의 unsure_fields 에 든 항목은 본 집계에서 빼고 '애매' 칸에 따로 센다.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "poc", "donghyun"))
os.environ.setdefault("DB_PATH", "/tmp/eval23.db")
from app.chaeng import guard, simple_extract  # noqa: E402

MATCH_RULE = "공백을 모두 뺀 뒤 한쪽 이름이 다른 쪽 안에 들어 있으면 같은 물건으로 봄(느슨). 참고용 엄격 기준: 공백을 뺀 이름이 똑같을 때만 같음"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def same(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    return bool(a) and bool(b) and (a in b or b in a)


def same_strict(a: str, b: str) -> bool:
    return norm(a) == norm(b)


def to_text(quote: str) -> str:
    q = re.sub(r"^\s*\(표\)\s*", "", quote)
    return q.replace(" / ", "\n")


def run_case(c: dict) -> dict:
    text = to_text(c["quote"])
    ev = simple_extract.extract("안내\n" + text)["events"]
    got = {
        "list_open": guard.list_open(text),
        "forbidden": [f["name"] for f in guard.find_forbidden(text)],
        "items": ev[0]["items"] if ev else [],
    }
    e = c["expected"]
    f_hit = [x for x in e["forbidden"] if any(same(x, y) for y in got["forbidden"])]
    f_miss = [x for x in e["forbidden"] if x not in f_hit]
    f_wrong = [y for y in got["forbidden"] if not any(same(x, y) for x in e["forbidden"])]
    i_hit = [x for x in e["items"] if any(same(x, y) for y in got["items"])]
    i_miss = [x for x in e["items"] if x not in i_hit]
    i_extra = [y for y in got["items"] if not any(same(x, y) for x in e["items"])]
    f_strict = [x for x in e["forbidden"] if any(same_strict(x, y) for y in got["forbidden"])]
    i_strict = [x for x in e["items"] if any(same_strict(x, y) for y in got["items"])]
    return {"forbidden_hit_strict": f_strict, "items_hit_strict": i_strict, "n": c["n"], "school": c["school"], "text": text, "expected": e, "got": got,
            "unsure_fields": c.get("unsure_fields", []), "unsure": c.get("unsure"),
            "forbidden_hit": f_hit, "forbidden_miss": f_miss, "forbidden_wrong": f_wrong,
            "items_hit": i_hit, "items_miss": i_miss, "items_extra": i_extra}


def main() -> None:
    key = json.load(open(os.path.join(ROOT, "eval", "real_notices_23.json"), encoding="utf-8"))
    rows = [run_case(c) for c in key["cases"]]

    def use(r, f):
        return f not in r["unsure_fields"]

    lo = [r for r in rows if use(r, "list_open")]
    lo_t = [r for r in lo if r["expected"]["list_open"]]
    lo_f = [r for r in lo if not r["expected"]["list_open"]]
    fb = [r for r in rows if use(r, "forbidden")]
    fb_cases = [r for r in fb if r["expected"]["forbidden"]]
    it = [r for r in rows if use(r, "items") and r["expected"]["has_item_line"]]
    S = {
        "match_rule": MATCH_RULE,
        "cases": len(rows),
        "unsure": {f: [r["n"] for r in rows if f in r["unsure_fields"]] for f in ("list_open", "forbidden", "items")},
        "list_open": {"expected_true": len(lo_t), "code_true_of_those": sum(r["got"]["list_open"] for r in lo_t),
                      "expected_false": len(lo_f), "code_true_wrongly": sum(r["got"]["list_open"] for r in lo_f)},
        "forbidden": {"expected_total": sum(len(r["expected"]["forbidden"]) for r in fb),
                      "found": sum(len(r["forbidden_hit"]) for r in fb),
                      "found_strict": sum(len(r["forbidden_hit_strict"]) for r in fb),
                      "wrong_found": sum(len(r["forbidden_wrong"]) for r in fb),
                      "cases_with_forbidden": len(fb_cases),
                      "cases_any_found": sum(1 for r in fb_cases if r["forbidden_hit"])},
        "items": {"cases_with_line": len(it), "cases_read_any": sum(1 for r in it if r["got"]["items"]),
                  "expected_total": sum(len(r["expected"]["items"]) for r in it),
                  "found": sum(len(r["items_hit"]) for r in it),
                  "found_strict": sum(len(r["items_hit_strict"]) for r in it),
                  "extra_not_in_key": sum(len(r["items_extra"]) for r in it)},
    }
    # 애매 건 따로
    S["unsure_detail"] = [{"n": r["n"], "fields": r["unsure_fields"], "why": r["unsure"],
                           "expected": {f: r["expected"][f] for f in r["unsure_fields"]},
                           "got": {f: r["got"][f] for f in r["unsure_fields"]}} for r in rows if r["unsure_fields"]]

    print(f"{'n':>2} {'학교':<14} 등(정답/코드) 금지(맞음/정답/잘못) 준비물(맞음/정답/코드)")
    for r in rows:
        u = "*" if r["unsure_fields"] else " "
        print(f"{r['n']:>2}{u}{r['school'][:12]:<14} {str(r['expected']['list_open'])[0]}/{str(r['got']['list_open'])[0]}"
              f"          {len(r['forbidden_hit'])}/{len(r['expected']['forbidden'])}/{len(r['forbidden_wrong'])}"
              f"              {len(r['items_hit'])}/{len(r['expected']['items'])}/{len(r['got']['items'])}")
    print("(* = 애매 항목 있음, 본 집계에서 그 항목만 뺌)")
    print(json.dumps({k: S[k] for k in ("unsure", "list_open", "forbidden", "items")}, ensure_ascii=False, indent=1))
    json.dump({"summary": S, "rows": rows}, open(os.path.join(ROOT, "eval", "real_notices_23_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
