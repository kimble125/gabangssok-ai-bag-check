"""알림장 글에서 금지·조건을 놓치지 않게 뽑는 규칙(모델 호출 없음, 표준 라이브러리만).

- 금지: "유리병·탄산음료와 장난감은 가져오지 않습니다", "( 장난감 등 불가 )", "탄산음료 X"
- 조건: "마실 물(플라스틱 물통)" → 조건 '플라스틱 물통'
- 열린 목록: 준비물 줄이 "… 등"으로 끝남 → 추천으로 채울 자리
- 사람·상황에 따라 다른 것: "필요한 학생", "우천 시"
- 원문 근거: 항목이 나온 줄을 그대로 붙인다(알림장 전문은 저장하지 않고 그 줄만)

여기서 뽑은 것은 판정이 아니라 표시다. 아이·보호자가 화면에서 보고 직접 확인한다.
"""
from __future__ import annotations

import re

_PAREN = re.compile(r"^(.*?)\s*[(（](.+?)[)）]\s*(.*)$")
_QTY = re.compile(r"(\d+|한|두|세)\s*(개|장|자루|권|벌|켤레|병|봉지|통|쪽)")
_SPLIT_NAMES = re.compile(r"\s*(?:[·,、/]|와\s|과\s|및\s|이나\s|\s또는\s|\s혹은\s|\s등의?\s)\s*")   # "핸드폰 등 귀중품" → 핸드폰, 귀중품
_BAN_VERB = re.compile(
    r"([^.!?()（）\n]{1,60}?)\s*(?:은|는|을|를|도)?\s*"
    r"(?:가져오지|가져가지|가지고\s?오지|가지고\s?가지|갖고\s?오지|지참하지|싸\s?오지|들고\s?오지|휴대하지|소지하지"
    r"|(?:가지고|갖고)\s?등교하지|착용하지)\s*(?:않|말|마|못)(?!아도|어도)")
_BAN_MARK = re.compile(
    r"([가-힣A-Za-z0-9 ·,、/]{1,40}?)\s*(?:등)?\s*(?:은|는|의)?\s*"
    r"(?:(?:지참|반입|사용|휴대|소지|착용)\s*(?:은|는|이|을|를)?\s*)?(불가|금지|안\s?됩니다|안\s?돼요|안\s?됨|[X✕×])(?:합니다|입니다|됩니다|해요|예요)?(?![가-힣A-Za-z])")
_BAN_HEAD = re.compile(                              # "(※ 입장제한: 래쉬가드, 수경)", "※ 휴대지참 금지 품목: 게임기, 폭죽 등"
    r"(?:입장\s?제한|(?:휴대\s?)?(?:지참\s?)?(?:반입\s?)?금지\s?(?:품목|물품|물건)?|가져오지\s?않는\s?것)\s*[:：]\s*(.+)$")
_BAN_IF = re.compile(                                # "장난감을 가져오면 안 됩니다"
    r"([^.!?()（）\n]{1,60}?)\s*(?:은|는|을|를|도)?\s*"
    r"(?:가져오면|가져오시면|가지고\s?오면|갖고\s?오면|지참하면|들고\s?오면|넣어\s?오면|휴대하면|소지하면)\s*안\s?(?:됩니다|돼요|돼|됨|되어요|된다|되요)")
_NOT_NEEDED = re.compile(r"([가-힣A-Za-z0-9 ·,]{1,30}?)\s*(?:은|는)\s*(?:필요\s?없|준비하지\s?않아도|가져오지\s?않아도)")
_NEEDED_ONLY = re.compile(r"필요한\s*(?:학생|사람|어린이|친구)|해당\s*(?:학생|자)|희망자|복용\s*중")
_RAIN_ONLY = re.compile(r"우천\s?시|비\s?(?:가)?\s?(?:오면|올\s?경우|올\s?때)")
_WEAR = re.compile(r"복장|옷차림|입고|착용|신고|체육복|활동복|운동화|긴바지|긴팔|반티|단체복")
_SUBMIT = re.compile(r"회신서|신청서|동의서|참가서|확인서|회신")
_CONSUMED = re.compile(r"간식|과자|음료|물티슈|휴지|티슈|비닐|봉지|봉투|약$|멀미약|밴드|도시락$|김밥|과일|회신서|신청서|동의서")
_KEEP = re.compile(r"도시락\s?통|물통|텀블러|수저|젓가락")
_TRIM = re.compile(r"^[\s※\-•·*\d.)◦○■□▶★]+|[\s.,·]+$")
_ADVICE = re.compile(r"(?:자제|지양|권장|삼가)$")             # "이동차량 내 취식 자제"는 물건이 아니라 행동 권고
_ACTION_BAN = re.compile(r"(?:^|\s)(?:세탁|환불|교환|반품|주차|출입|입장|변경|취소|대여|재사용|수선)$")   # "속옷(여벌, 세탁 불가)": 세탁할 수 없다는 설명
_STOP = {"", "등", "것", "물건", "물품", "기타", "그 외", "준비물"}
_ONE = {"캔", "껌", "칼", "돈", "물", "빵", "떡", "총", "공", "술", "약"}      # 한 글자여도 물건인 것

# 금지된 것이 어떤 준비물의 '안 되는 대체물'인지(같은 자리에 놓일 수 있는 것)
_SUBSTITUTE_OF = [
    (re.compile(r"유리병|유리\s?용기|캔"), re.compile(r"^(?:마실\s?)?물$|음료|물통|텀블러|생수")),
    (re.compile(r"탄산|콜라|사이다"), re.compile(r"^(?:마실\s?)?물$|음료|생수")),
    (re.compile(r"일회용"), re.compile(r"도시락|수저|물통")),
    (re.compile(r"슬리퍼|샌들|크록스"), re.compile(r"운동화|신발")),
]


def _clean(name: str) -> str:
    name = _TRIM.sub("", name)
    name = re.sub(r"\s*(?:등|같은\s?것)$", "", name).strip()
    return re.sub(r"\s+", " ", name)


def _names(chunk: str) -> list[str]:
    out = []
    for part in _SPLIT_NAMES.split(chunk):
        n = _clean(part)
        n = re.sub(r"^(?:그리고|또한|단|특히)\s*", "", n)
        n = re.sub(r"(?:은|는)?\s+[가-힣]+(?:으로|에)$", "", n)  # "개인 귀중품은 수영장으로" → "개인 귀중품"
        n = re.sub(r"^[가-힣]+\s내\s+", "", n)                # "체험시설 내 외부 음식" → "외부 음식"
        n = re.sub(r"(?<=[가-힣])(?:을|를)$", "", n)          # "장난감을" → "장난감"
        n = re.sub(r"(?<=[가-힣]{2})(?:은|는)$", "", n)
        if _ADVICE.search(n):
            continue
        if n not in _STOP and (1 < len(n) <= 16 or n in _ONE) and not re.search(r"습니다|세요|니다$|가져오|가지고|갖고|지참하|들고", n):
            out.append(n)
    return out


def lines_of(text: str) -> list[str]:
    out = []
    for raw in (text or "").replace("\r", "").split("\n"):
        for s in re.split(r"(?<=[.!?。])\s+|\s*※\s*", raw):
            s = s.strip()
            if s:
                out.append(s)
    return out


def split_name(name: str) -> tuple[str, str]:
    """'마실 물(플라스틱 물통)' → ('마실 물', '플라스틱 물통')"""
    name = name.strip()
    start = min((i for i in (name.find("("), name.find("（")) if i >= 0), default=-1)
    if start < 0:
        return name, ""
    depth = 0
    for i in range(start, len(name)):                 # 겹친 괄호: 바깥 괄호의 짝을 찾는다
        if name[i] in "(（":
            depth += 1
        elif name[i] in ")）":
            depth -= 1
            if depth == 0:
                return (name[:start] + " " + name[i + 1:]).strip(), name[start + 1:i].strip()
    return name[:start].strip(), name[start + 1:].strip()


def find_forbidden(text: str) -> list[dict]:
    """알림장 글에서 가져오면 안 되는 것. [{name, evidence}] (같은 이름은 한 번만)"""
    seen, out = set(), []
    for line in lines_of(text):
        heads = [m.group(1) for m in _BAN_HEAD.finditer(line)]
        line_wo = _BAN_HEAD.sub(" ", line)                 # 머리말 뒤 목록은 통째로 읽고, 아래 규칙이 다시 읽지 않게 뺀다
        chunks = [m.group(1) for m in _BAN_IF.finditer(line_wo)]
        rest = _BAN_IF.sub(" ", line_wo)                   # 위에서 읽은 토막은 아래 규칙이 다시 읽지 않게 뺀다
        chunks += [m.group(1) for m in _BAN_VERB.finditer(rest)]
        chunks += [m.group(1) for m in _BAN_MARK.finditer(rest) if not _ACTION_BAN.search(m.group(1).strip())]
        chunks = [re.split(r"위해서?|위하여|때문에|인해|(?:문제|이유)로", c)[-1] for c in chunks]      # "식중독 예방을 위해 외부음식 반입은 금지" → "외부음식"
        chunks = [c.split(":")[-1].split("：")[-1] for c in chunks]
        for h in heads:                                    # 목록 안의 괄호 설명은 떼고 이름만 읽는다
            chunks += [re.sub(r"[(（][^)）]*[)）]?", "", x).strip(" )）") for x in re.split(r"[,、]", h)]
        for chunk in chunks:
            for n in _names(chunk):
                if n not in seen:
                    seen.add(n)
                    out.append({"name": n, "evidence": line[:140]})
    return out


def find_not_needed(text: str) -> list[dict]:
    seen, out = set(), []
    for line in lines_of(text):
        for m in _NOT_NEEDED.finditer(line):
            for n in _names(m.group(1)):
                if n not in seen:
                    seen.add(n)
                    out.append({"name": n, "evidence": line[:140]})
    return out


def list_open(text: str) -> bool:
    """준비물 줄이 '등'으로 끝나는가(목록에 없는 것이 더 있을 수 있음)."""
    for line in lines_of(text):
        if re.search(r"준비물|챙길\s?것|지참물", line) and re.search(r"(?:^|[\s,、])등\s*(?:[.)]?\s*$|[(（*])", line):
            return True
    return False


def _segments(text: str, base: str) -> list[str]:
    """통신문에서 이 물건을 말하는 토막만(쉼표·마침표로 끊은 조각). 같은 줄의 다른 물건 조건은 끌어오지 않는다."""
    key = re.sub(r"\s+", "", base)
    if not text or len(key) < 2:
        return []
    out = []
    for line in lines_of(text):
        if re.search(r"준비물|챙길\s?것|지참물", line):
            continue                                   # 준비물 나열 줄은 항목 이름으로 이미 읽었다
        for seg in re.split(r"[,、!?]|\.\s", line):
            if key in re.sub(r"\s+", "", seg):
                out.append(seg.strip())
    return out


def annotate(name: str, text: str = "", forbidden: list[dict] | None = None) -> dict:
    """준비물 이름 하나에 조건·수량·종류·근거를 붙인다."""
    base, paren = split_name(name)
    meta: dict = {"base": base, "kind": "carry"}
    whole = name
    if paren:
        if _BAN_MARK.search(paren) or _BAN_VERB.search(paren):
            pass                                   # 괄호 안이 금지 문구면 조건으로 쓰지 않는다(금지 목록으로 간다)
        elif paren.strip() in ("선택", "선택 사항", "희망"):
            meta["optional_by_notice"] = True      # 알림장이 선택이라고 적은 것만 선택. 안 적혀 있으면 전부 챙길 것
        elif _NEEDED_ONLY.search(paren):
            meta["conditional"] = "needed"
        elif _RAIN_ONLY.search(paren):
            meta["conditional"] = "rain"
        else:
            meta["condition"] = paren
    if "conditional" not in meta:
        if _NEEDED_ONLY.search(whole) or re.search(r"개인\s?약|상비약", whole):
            meta["conditional"] = "needed"
        elif _RAIN_ONLY.search(whole):
            meta["conditional"] = "rain"
            base = _RAIN_ONLY.sub("", base).strip() or base
            meta["base"] = base
    q = _QTY.search(whole)
    if q:
        meta["quantity"] = q.group(0)
        rest = re.sub(r"\s+", " ", base.replace(q.group(0), "")).strip()
        if rest:
            meta["base"] = base = rest
    for seg in _segments(text, base):                  # 항목 이름에는 없고 통신문 글에만 있는 제한
        if "conditional" not in meta and _NEEDED_ONLY.search(seg):
            meta["conditional"] = "needed"
        if "conditional" not in meta and _RAIN_ONLY.search(seg):
            meta["conditional"] = "rain"
        qs = _QTY.search(seg)
        if qs and "quantity" not in meta:
            meta["quantity"] = qs.group(0) + ("만" if re.search(re.escape(qs.group(0)) + r"\s*만", seg) else "")
    alts = [a.strip() for a in re.split(r"\s(?:또는|혹은|or)\s", base) if a.strip()]
    if len(alts) > 1:
        meta["any_of"] = alts
    if _SUBMIT.search(base):
        meta["kind"] = "submit"
    elif _WEAR.search(whole) and not re.search(r"실내화|여벌|갈아입", whole):
        meta["kind"] = "wear"
    meta["bring_back"] = bool(_KEEP.search(base)) or not _CONSUMED.search(base)
    if meta["kind"] == "submit":
        meta["bring_back"] = False
    na = [f["name"] for f in (forbidden or [])
          if any(a.search(f["name"]) and b.search(base) for a, b in _SUBSTITUTE_OF)]
    if na:
        meta["not_accepted"] = na
    if text:
        key = re.sub(r"\s+", "", base)[:6]
        for line in lines_of(text):
            if key and key in re.sub(r"\s+", "", line):
                meta["evidence"] = line[:140]
                break
    return meta


def analyze(text: str, item_names: list[str]) -> dict:
    """알림장 글 + 뽑힌 준비물 이름 → 금지 목록, 열린 목록 여부, 항목별 표시."""
    forb = find_forbidden(text)
    for n in item_names:                       # 항목 괄호 안에 숨은 금지: "비닐 봉투 ( 장난감 등 불가 )"
        _, paren = split_name(n)
        if paren and (_BAN_MARK.search(paren) or _BAN_VERB.search(paren)):
            for f in find_forbidden(paren):
                if f["name"] not in {x["name"] for x in forb}:
                    forb.append({"name": f["name"], "evidence": n[:140]})
    return {
        "forbidden": forb,
        "not_needed": find_not_needed(text),
        "list_open": list_open(text) or any(re.search(r"등\s*$", n) for n in item_names[-1:]),
        "items": {n: annotate(n, text, forb) for n in item_names},
    }
