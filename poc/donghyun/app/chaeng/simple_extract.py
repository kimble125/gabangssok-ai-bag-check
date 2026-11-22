"""모델 없이 알림장 글에서 일정과 준비물을 뽑는 규칙(예시 모드, API 키가 없을 때의 대체 길).

extract.py(모델)와 같은 모양을 돌려준다. 정해진 꼴("준비물 : …", "일시 : …")만 읽는다.
못 읽은 것은 지어내지 않고 notes 에 '확인해 주세요'로 남긴다.
"""
from __future__ import annotations

import re
from datetime import date as Date, timedelta

SAMPLES = [
    {
        "key": "a", "title": "2학년 가을 현장체험학습 안내", "posted": None,
        "text": "2학년 가을 현장체험학습 안내\n1. 일시 : {d1} 09:00–14:30\n2. 장소 : ○○숲체험원\n"
                "3. 준비물 : 도시락, 마실 물(플라스틱 물통), 개인용 돗자리, 모자, 간식, 물티슈, 개인 약품(멀미약 등 필요한 학생), 우천 시 우산 또는 우의 등\n"
                "4. 유의 사항 : 유리병·탄산음료와 장난감, 귀중품은 가져오지 않습니다. 간편한 복장과 운동화를 착용합니다.\n"
                "---- 절 취 선 ----\n참가 신청서({d0}까지 제출)",
    },
    {
        "key": "b", "title": "4학년 현장체험학습(역사박물관) 안내", "posted": None,
        "text": "4학년 현장체험학습(역사박물관) 안내\n1. 일시 : {d1}, 8시 40분까지 교실로 등교\n"
                "2. 준비물 : 필기도구(연필 2자루, 지우개), 체험학습 활동지(지난주에 나눠 준 것), 물통, 작은 가방(백팩) 등\n"
                "3. 선택 : 얇은 겉옷, 손수건\n4. 소요 경비 : 체험비 12,000원(학교 예산 지원)\n"
                " ※ 체험비에 점심 식사 포함(도시락 지참하지 않음)\n5. 교통카드는 필요 없습니다(전세버스 이용).",
    },
    {
        "key": "c", "title": "[1학년 3반 알림장]", "posted": None,
        "text": "[1학년 3반 알림장]\n1. 내일은 가을 소풍입니다. 체육복 입고 오기\n2. 준비물: 도시락, 물, 돗자리, 물티슈, 비닐봉지 2장\n"
                "3. 과자는 한 봉지만! 탄산음료 X\n4. 비가 오면 교실에서 합니다(준비물 같음)\n5. 가정통신문 회신서 내일까지 내기\n"
                "6. 멀미하는 친구는 멀미약 먹고 오기, 개인 약은 가방에",
    },
]
_OUTDOOR = re.compile(r"체험|소풍|숲|운동회|체육대회|탐사|농장|야외|공원|수련|캠프|썰매|갯벌")


def sample(key: str = "a", today: Date | None = None) -> dict:
    """지어낸 예시 알림장(실제 학교 문서 아님). 날짜는 오늘 기준으로 채운다."""
    today = today or Date.today()
    s = next((x for x in SAMPLES if x["key"] == key), SAMPLES[0])
    d1, d0 = today + timedelta(days=1), today
    fmt = lambda d: f"{d.month}월 {d.day}일"
    return {"title": s["title"], "posted": today.isoformat(), "attachments": [], "url": f"sample:{s['key']}",
            "text": s["text"].format(d1=fmt(d1), d0=fmt(d0))}


_ITEM_HEAD = re.compile(r"^[\s\d.※\-•·*◦■□▶○]*(?:(?:학생|개인|학습|복장\s*및)\s*)*(?:준비물|챙길\s?것|지참물)\s*[:：]?\s*")


_BAN_PAREN = re.compile(r"\s*[(（][^()（）]*(?:불가|금지|안\s?됨|안\s?됩니다|않음|않습니다|하지\s?않|[X✕×])[^()（）]*[)）]\s*$")


def cut_note(body: str) -> str:
    """준비물 줄 안에서 괄호 밖의 ※나 ' * ' 뒤는 안내문이다. "간편 복장 등 ※실내 수영장에서 …" → "간편 복장 등" """
    depth = 0
    for i, ch in enumerate(body):
        if ch in "(（":
            depth += 1
        elif ch in ")）":
            depth = max(0, depth - 1)
        elif depth == 0 and (ch == "※" or (ch == "*" and i > 0 and body[i - 1] == " ")):
            return body[:i]
    return body


def split_items(chunk: str) -> list[str]:
    """쉼표로 나누되 괄호 안의 쉼표는 건드리지 않는다. 끝의 '등'과 금지 괄호는 뗀다."""
    out, buf, depth = [], "", 0
    for ch in cut_note(chunk):
        if ch in "(（":
            depth += 1
        elif ch in ")）":
            depth = max(0, depth - 1)
        if ch in ",、" and depth == 0:
            out.append(buf)
            buf = ""
        else:
            buf += ch
    out.append(buf)
    items = []
    for x in out:
        x = _BAN_PAREN.sub("", x.strip())             # "비닐 봉투 (장난감 등 불가)" → "비닐 봉투" (금지는 guard가 통신문 글에서 따로 읽음)
        x = re.sub(r"\s+등\s*[.]?\s*$", "", x).strip(" .")
        x = re.sub(r"만\s*준비$", "", x).strip()       # "음료수와 물만 준비" → "음료수와 물"
        x = re.sub(r"\s*착용$", "", x)                 # "운동화 착용" → "운동화"
        if x and x != "등":
            items.append(x)
    return items


def _date(m: re.Match, base: Date) -> Date | None:
    """'11월 20일' 또는 '2026년 11월 20일' → 날짜. 적힌 연도가 있으면 그대로, 없으면 기준일에서 가까운 앞날. 없는 날짜면 None."""
    year, month, day = m.group(1), int(m.group(2)), int(m.group(3))
    for y in ([int(year)] if year else [base.year, base.year + 1]):
        try:
            d = Date(y, month, day)
        except ValueError:
            continue
        if year or (base - d).days <= 60:
            return d
    return None


def extract(text: str, title: str | None = None, posted: str | None = None, today: Date | None = None) -> dict:
    today = today or Date.today()
    try:
        base = Date.fromisoformat((posted or "").replace(".", "-")[:10]) if posted else today
    except ValueError:
        base = today
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return {"summary": "읽을 글이 없어요", "events": [], "usage": {"input": 0, "output": 0, "model": "규칙(모델 호출 없음)"}}
    ttl = re.sub(r"\s*안내\s*$", "", (title or lines[0]).strip("[] ")).strip() or "학교 일정"
    if "알림장" in ttl:                              # "[1학년 3반 알림장] 내일은 가을 소풍입니다" → "1학년 3반 가을 소풍"
        m = re.search(r"(?:내일은|내일|오늘은)\s*([가-힣 ]{2,14}?)\s*(?:입니다|이에요|예요|가는 날)", text)
        if m:
            ttl = (ttl.replace("알림장", "").strip() + " " + m.group(1).strip()).strip()
    md = re.compile(r"(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일")
    notes, when, start, end, loc = [], None, None, None, None
    for l in lines:
        if re.search(r"일시|날짜|언제", l) and md.search(l) and not when:
            when = _date(md.search(l), base)
            t = re.search(r"(\d{1,2}):(\d{2})\s*[–\-~]\s*(\d{1,2}):(\d{2})", l)
            if t:
                start, end = f"{int(t.group(1)):02d}:{t.group(2)}", f"{int(t.group(3)):02d}:{t.group(4)}"
            else:
                t = re.search(r"(\d{1,2})시\s*(\d{1,2})?분?", l)
                if t:
                    start = f"{int(t.group(1)):02d}:{int(t.group(2) or 0):02d}"
        if re.match(r"^[\d.\s]*장소", l):
            loc = re.split(r"[:：]", l, maxsplit=1)[-1].strip()
        if re.search(r"유의|주의|※|비가 오면", l) and not re.match(r"^[\d.\s]*(준비물|선택)", l) and not _ITEM_HEAD.match(l) and len(notes) < 3:
            notes.append(re.sub(r"^[\d.\s]*", "", l))
    if not when:
        if any("내일" in l for l in lines[:3]):
            when = base + timedelta(days=1)
        else:
            m = next((md.search(l) for l in lines if md.search(l) and not re.search(r"까지|제출|회신", l)), None)
            when = _date(m, base) if m else None
    if not when:
        when = base + timedelta(days=1)
        notes.append("날짜를 못 찾아 내일로 넣었어요. 확인해 주세요.")
    items: list[str] = []
    for l in lines:
        m_head = _ITEM_HEAD.match(l)
        if m_head:                                     # "5. 학생 준비물 : …", "※ 복장 및 준비물 : …", "4. 학생 준비물 수영복, …"
            body = re.sub(r"\s*[(（]\s*※?\s*(?:입장\s?제한|금지)[^)）]*[)）]?\s*$", "", l[m_head.end():])   # 줄 끝의 금지 괄호는 준비물이 아니다
            items += split_items(body)
        elif re.match(r"^[\d.\s]*선택\s*[:：]", l):
            items += [f"{x}(선택)" for x in split_items(re.split(r"[:：]", l, maxsplit=1)[-1])]
    for l in lines:                                   # 준비물 줄 밖에 있는 입고·신고 갈 것("체육복 입고 오기", "간편한 복장과 운동화를 착용합니다")
        if _ITEM_HEAD.match(l) or re.match(r"^[\d.\s]*선택", l):
            continue
        for seg in re.split(r"(?<=[.!?])\s+", l):
            if re.search(r"않|말아|마세요|금지|불가|안\s?됩|안\s?돼", seg):
                continue                               # "슬리퍼는 신고 오지 않습니다" 같은 금지 문장은 건너뛴다
            m = re.search(r"([가-힣 ]{2,24}?)\s*(?:을|를)?\s*입고\s*오기", seg)
            if m and not any(m.group(1).strip() in i for i in items):
                items.append(f"{m.group(1).strip()} 입고 오기")
                continue
            m = re.search(r"([가-힣 ]{2,24}?)\s*(?:을|를)\s*(?:착용|입고\s*(?:옵니다|와요|오세요|등교)|신고\s*(?:오기|옵니다|와요|오세요))", seg)
            if m:
                for name in re.split(r"\s*(?:,|와\s|과\s|및\s)\s*", re.sub(r"^.*[:：]\s*", "", m.group(1))):
                    name = name.strip()
                    if 1 < len(name) <= 12 and not any(name in i for i in items):
                        items.append(name)
    tgt = re.search(r"\d학년(?:\s*\d반)?", " ".join(lines[:2]))
    events = [{
        "title": ttl, "kind": "event", "date": when.isoformat(), "start_time": start, "end_time": end,
        "location": loc, "lat": None, "lon": None, "outdoor": bool(_OUTDOOR.search(" ".join(lines))) and not re.search(r"박물관|미술관|과학관|공연|실내|도서관", " ".join(lines)),
        "target": tgt.group(0) if tgt else None,
        "items": items, "ai_items": [], "notes": "\n".join(notes),
    }]
    for l in lines:                                   # 회신 마감은 따로 일정으로("11월 20일까지 제출", "내일까지 내기")
        if not re.search(r"까지\s*(제출|회신|내기|내\s?주)", l):
            continue
        m, rel = md.search(l), re.search(r"(오늘|내일|모레)\s*까지", l)
        due = _date(m, base) if m else base + timedelta(days={"오늘": 0, "내일": 1, "모레": 2}[rel.group(1)]) if rel else None
        if not due:
            notes.append("회신 마감 날짜를 못 읽었어요. 확인해 주세요.")
            events[0]["notes"] = "\n".join(notes)
            continue
        doc = re.search(r"(참가\s?신청서|회신서|신청서|동의서|확인서)", l)
        events.append({"title": f"{ttl} 회신 마감", "kind": "deadline", "date": due.isoformat(),
                       "start_time": None, "end_time": None, "location": None, "lat": None, "lon": None,
                       "outdoor": False, "target": None, "items": [doc.group(1) if doc else "회신서"], "ai_items": [], "notes": l})
    return {"summary": f"{ttl}: 준비물 {len(items)}개를 찾았어요 (규칙으로 읽은 예시 모드, 꼭 확인해 주세요)",
            "events": events, "usage": {"input": 0, "output": 0, "model": "규칙(모델 호출 없음)"}}
