#!/usr/bin/env python3
"""가방쏙 2쪽 기획안을 한 원고에서 세 가지로 만든다: Word(.docx), 인쇄용 HTML(→ PDF), 글(proposal.md).

    python3 plan/build_plan.py

- 원고는 이 파일의 ROWS 하나다. 주최 측이 정한 8가지 순서 그대로다(plan/README.md).
- 그림 두 장(화면 줄, 동작 구조도)도 여기서 만든다. 화면 그림은 docs/assets/shots 의 프로토타입 화면이다.
- PDF 는 gabangssok_plan.html 을 브라우저에서 A4 로 인쇄해 만든다(여백은 HTML 에 들어 있다).
- 필요한 것: python-docx, Pillow.
"""
from __future__ import annotations

import html
import os
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IMG = os.path.join(HERE, "img")
SHOTS = os.path.join(REPO, "docs", "assets", "shots")
MASCOT = os.path.join(REPO, "poc", "donghyun", "app", "static", "mascot", "ssok_hello.png")
POC_URL = "https://kimble125.github.io/chaenggyeojwo-ai-bag-check/"

TITLE = "가방쏙 기획안"
TAGLINE = "가정통신문에서 가방까지: 엄마가 넣으면, 아이가 스스로 챙겨요"
META = "엘리스 AI 챌린지 2026 · 성인 부문"

# 종류: p 문단 / h 작은 제목 / b 글머리표 / n 번호가 글 안에 든 줄 / img 그림(파일, 너비 mm, 설명)
# 2쪽 안에서 읽기 쉽게: 칸마다 서너 줄, 숫자의 분모와 조사 방법은 맨 아래 출처로 내린다.
ROWS = [
    ("1. 참가 정보", [
        ("p", "**팀명** 잘챙겨조　**구성원** 김호연(대표), 김동현"),
    ]),
    ("2. 문제 정의", [
        ("h", "해결하고 싶은 문제"),
        ("b", "가정통신문의 준비물은 한 줄로 나열되고, **조건과 금지는 괄호나 다른 줄에 숨어 있음.** 실제 통신문: \"준비물 : 개인 도시락, 간식, 물, 음료수, 멀미약, 비닐 봉투 (장난감 등 불가)\""),
        ("b", "통신문 23건을 직접 읽어 보니 한 줄 준비물 19건 중 **10건(53%)이 \"… 등\"으로 끝남** → 목록에 없는 것이 더 있음"),
        ("b", "그래서 엄마가 읽고 머릿속으로 챙김. 숨은 조건, \"등\"이 가린 것, 입고 가는 것을 놓치기 쉬움 (얼마나 자주 빠뜨리는지 잰 통계는 찾지 못해, 사용자 시험으로 확인할 가설)"),
        ("h", "문제를 겪는 사람"),
        ("b", "**초등 저학년 아이와 엄마.** 준비물 파악·구입은 어머니 담당이 52.3%¹. 취학 뒤 어려움으로 '숙제 지도 및 준비물 챙겨주기'를 꼽은 응답이 22.9%²"),
        ("b", "1학년 담임의 조언은 \"아이가 직접 다음 날의 준비물을 챙기고 가방에 넣도록\"³. 그러나 아이 혼자 통신문을 읽고 챙기기는 어려움"),
    ]),
    ("3. 서비스 개요", [
        ("p", "**서비스명** 가방쏙 (가방 친구 '쏙이'가 안내)"),
        ("p", "**제작 목적** 통신문 읽기와 가방 싸기를 **아이가 스스로 하고, 엄마는 확인하고 칭찬하는 일**로 바꿈"),
        ("p", "**기대 효과** ① 숨은 조건과 금지를 놓치지 않음 ② \"등\"이 가린 준비물을 추천으로 채움 ③ 아이는 스스로 해내고 칭찬받음"),
        ("p", "**범위** 이번 PoC는 **넣기(가방 싸기)** 와 돌아오기(한 화면). 다음 단계는 수납 위치 찾기, 쏙이와의 대화, 외부 캘린더 직접 연동"),
    ]),
    ("4. 서비스 활용 방식", [
        ("n", "① 엄마가 통신문을 넣음(링크·글·사진) → 일정, 회신 마감, 준비물, '가져오지 않는 것'이 정리되어 달력과 알림으로"),
        ("n", "② 통신문에 없는 것은 근거와 함께 '추천'으로 따로 나옴"),
        ("n", "③ 아이가 미션으로 가방을 쌈: 펼쳐서 사진 → 안 보인 것만 하나씩 → \"다 챙겼지!\""),
        ("n", "④ 가져가면 안 되는 것이 보이면 \"이건 두고 가자\""),
        ("n", "⑤ 엄마는 결과를 보고 칭찬 스티커를 붙임. 집에 오면 다시 확인(돌아오기)"),
        ("img", "strip.png", 152, "프로토타입 화면: ① 통신문 넣기 ② 금지·조건·추천 ③ 아이 미션 ④ 이건 두고 가자 ⑤ 다 챙겼지!"),
    ]),
    ("5. AI 활용 계획", [
        ("img", "flow.png", 152, "동작 구조도: AI 모델이 하는 일과 규칙 코드가 하는 일"),
        ("b", "**Claude API(AI 모델)**: 통신문(글·사진) 읽기, 펼친 준비물 사진에서 보이는 것 찾기"),
        ("b", "**규칙 코드**: 금지·조건·\"등\" 찾기, 추천, 세기, \"다 챙겼지\" 판정 → 자동 시험 62개. 통신문의 그 줄을 근거로 같이 보여 줌. 실제 통신문 23건의 문장으로 재 보니 \"등\" 11건 중 11건, 금지 물건 43개 중 35개 → 놓친 표현을 고친 뒤 43개(같은 23건으로 다시 잰 값. 못 읽는 글 형식은 PoC 페이지에 공개)"),
        ("b", "**MCP · Open-Meteo**: 캘린더와 가방쏙 규칙을 MCP 도구로 엶. Claude 앱에 연결해 '뭘 챙겨야 해?'에 규칙 코드의 값으로 답하는 것을 확인 · 날씨와 미세먼지 예보"),
        ("b", "**이렇게 나눈 이유**: 사진을 보는 모델은 틀릴 수 있음(GPT-4V 정답률: 원본 79.6% → 손본 이미지 38.4%)⁴ → 세기와 판정은 규칙이 맡고, 사진에서는 보이는지만 물음. **안 보인 것은 아이가 직접 확인**"),
        ("b", "**아이를 지키는 것**: 아이는 AI와 직접 대화하지 않음. 약은 보호자 화면에만 나옴. 사진은 저장하지 않고 위치도 쓰지 않음"),
        ("b", "**확인 계획**(아직 재지 않음): 실제 사진 12장 이상으로 금지물을 놓친 수와 잘못 본 수를 잼. 못 미치면 사진 확인을 줄이고 '하나씩' 미션 중심으로"),
        ("b", "**생성형 AI 활용 범위**: (서비스) 통신문 읽기와 사진 보기 / (제작) 조사·초안·코드·검토에 Claude·GPT, 마스코트 그림에 이미지 생성 AI. 결과는 팀이 확인하고 고침"),
    ]),
    ("6. 핵심 기능 (3가지)", [
        ("n", "① **통신문 → 일정·준비물·금지 정리**: 행사일과 회신 마감을 따로 일정으로 만들고, 조건과 '가져오지 않는 것'을 통신문의 그 줄과 함께 보여 줌. 구글 캘린더로도 내보냄"),
        ("n", "② **\"등\"을 채우는 추천**: 실제 통신문 23건, 날씨·미세먼지, 아이 특성으로 추천. \"비슷한 알림장 3건에서 봤어요\"처럼 근거를 붙이고 통신문 준비물과 섞지 않음"),
        ("n", "③ **아이 스스로 챙기기 미션**: 사진으로 한 번에, 안 보인 것만 하나씩. 다 넣었을 때만 \"다 챙겼지!\". 엄마는 칭찬 스티커로 답함"),
    ]),
    ("7. 차별점", [
        ("b", "**이미 있는 것**(스토어 설명 기준): 통신문에서 준비물 뽑기(리마인디), 목록과 사진 대조(TurtleWiz), 체크리스트(다 챙겼지?), 날씨 알림(챙겨줘, 우산)"),
        ("b", "**가방쏙이 다른 점**: ① 금지와 조건을 통신문 문장과 함께 아이 화면까지 가져감 ② 추천을 통신문과 섞지 않고 근거를 붙임 ③ **아이가 하고 엄마가 칭찬하는** 두 사람의 흐름 (견준 앱들의 설명과 화면에서는 찾지 못함)"),
        ("b", "범용 AI 채팅과 견주면: 같은 일을 **아이가 혼자 할 수 있는 화면**과 **근거를 보여 주는 규칙**으로 바꾼 것"),
    ]),
    ("8. 역할 분담", [
        ("p", "**김호연** 기획, 서비스 설계, AI 활용 설계(추천·금지 규칙, MCP 도구), 아이 화면, 전체 합치기"),
        ("p", "**김동현** 개발·배포·운영(통신문 추출, 캘린더 MCP 서버, 날씨·알림, 서버)"),
    ]),
]
FOOT = [
    f"**PoC** {POC_URL} · 설치·로그인 없이 눌러 보는 프로토타입과 한눈에 보기. 공개 PoC는 예시 판(AI 모델을 부르지 않고 통신문을 규칙으로 읽으며, 사진 확인은 준비된 결과). Claude API와 MCP를 쓰는 실제 판은 코드가 있고 공개 주소에서는 돌리지 않음",
    "**출처** ¹ 인구보건복지협회 2026년 설문, 초등 이하 자녀를 둔 아버지 524명(KBC 2026-11-15 보도) ² 장명림·김선미(2018), 2015년 초등 학부모 2,579명 조사의 복수응답 4,268건 중 976건 ³ 부산일보 2025-03-17 ⁴ HallusionBench(CVPR 2024), 우리 사진으로 잰 값이 아님. 통신문 23건: 초등학교 홈페이지 게시글을 팀이 읽음(2026-11-19)",
]

VIOLET, INK, SOFT = (124, 92, 255), (35, 38, 58), (98, 97, 109)
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT, size, index=6 if bold else 2)
    except OSError:                                   # 다른 컴퓨터: 기본 글꼴(한글이 깨질 수 있다)
        return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def make_strip(path):
    """프로토타입 화면 다섯 장을 한 줄로."""
    names = ["1_notice", "2_ban_recs", "3_kid_lay", "5_kid_warn", "7_kid_done"]
    labels = ["① 통신문 넣기", "② 금지·조건·추천", "③ 아이 미션", "④ 이건 두고 가자", "⑤ 다 챙겼지!"]
    w, h, gap, pad, cap = 320, 640, 34, 10, 56
    W = len(names) * w + (len(names) - 1) * gap + pad * 2
    im = Image.new("RGB", (W, h + cap + pad * 2), "white")
    d = ImageDraw.Draw(im)
    for i, (n, lab) in enumerate(zip(names, labels)):
        x = pad + i * (w + gap)
        shot = Image.open(os.path.join(SHOTS, n + ".webp")).convert("RGB").resize((w - 12, h - 12))
        mask = Image.new("L", shot.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, shot.size[0] - 1, shot.size[1] - 1], radius=26, fill=255)
        d.rounded_rectangle([x, pad, x + w - 1, pad + h - 1], radius=32, fill=INK)
        im.paste(shot, (x + 6, pad + 6), mask)
        f = font(27, bold=True)
        d.text((x + (w - d.textlength(lab, font=f)) / 2, pad + h + 14), lab, font=f, fill=INK)
        if i < len(names) - 1:
            d.text((x + w + 6, pad + h / 2 - 16), "→", font=font(26), fill=SOFT)
    im.save(path, optimize=True)


def make_flow(path):
    """동작 구조도: 누가(엄마·아이), AI 모델, 규칙 코드, 바깥 도구가 어느 차례에 무엇을 하나."""
    nodes = [
        ("엄마", "통신문 넣기", "링크, 붙여넣기, 종이 사진", "human"),
        ("AI · Claude API", "통신문 읽기", "일정, 회신 마감, 준비물을 정해진 틀로", "ai"),
        ("규칙 코드", "금지·조건·\"등\" 찾기", "통신문의 그 줄을 근거로 붙임", "rule"),
        ("캘린더(MCP) · 알림", "달력에 넣기", "전날 저녁, 당일 아침", "ext"),
        ("규칙 코드 + Open-Meteo", "추천 만들기", "통신문 23건 + 날씨 + 아이 특성", "rule"),
        ("아이", "미션 시작", "추천 고르기, 펼쳐서 사진", "kid"),
        ("AI · Claude API", "사진 보기", "보이는 것과 금지물. 애매하면 '안 보임'", "ai"),
        ("규칙 코드", "세기와 판정", "안 보인 것은 아이가 직접 확인", "rule"),
        ("엄마", "확인과 칭찬", "결과 한 줄, 칭찬 스티커", "human"),
        ("아이", "돌아오기", "집에 와서 다시 확인", "kid"),
    ]
    fill = {"human": (255, 241, 191), "kid": (220, 235, 255), "ai": (239, 234, 255), "rule": (226, 239, 233), "ext": (239, 236, 230)}
    line = {"ai": VIOLET, "rule": (47, 111, 94)}
    bw, bh, gx, gy, pad = 330, 150, 46, 34, 14
    W = 5 * bw + 4 * gx + pad * 2
    H = 2 * bh + gy + pad * 2 + 54
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    fk, ft, fb = font(20, bold=True), font(27, bold=True), font(21)
    for i, (who, title, body, kind) in enumerate(nodes):
        r, c = divmod(i, 5)
        x, y = pad + c * (bw + gx), pad + r * (bh + gy)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=20, fill=fill[kind], outline=line.get(kind), width=4 if kind in line else 0)
        d.text((x + 14, y + 10), who, font=fk, fill=line.get(kind, SOFT))
        d.text((x + 14, y + 38), title, font=ft, fill=INK)
        for k, ln in enumerate(wrap(d, body, fb, bw - 28)[:2]):
            d.text((x + 14, y + 80 + k * 28), ln, font=fb, fill=(60, 62, 80))
        if c < 4:
            d.text((x + bw + 9, y + bh / 2 - 18), "→", font=font(28), fill=SOFT)
        elif r == 0:
            d.text((x + bw - 150, y + bh + 2), "↓ 아랫줄로 이어짐", font=font(17), fill=SOFT)
    lx, ly = pad, H - 44
    for lab, kind in (("AI 모델이 하는 일(읽기·보기)", "ai"), ("규칙 코드가 하는 일(판단·세기)", "rule"), ("엄마", "human"), ("아이", "kid"), ("바깥 도구", "ext")):
        d.rounded_rectangle([lx, ly, lx + 26, ly + 26], radius=7, fill=fill[kind], outline=line.get(kind), width=3 if kind in line else 0)
        d.text((lx + 34, ly), lab, font=font(20), fill=INK)
        lx += 54 + d.textlength(lab, font=font(20))
    im.save(path, optimize=True)


# ---------- 글 조각: **굵게** 를 나눈다 ----------
def parts(text):
    out = []
    for i, seg in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if seg:
            out.append((seg, i % 2 == 1))
    return out


# ---------- Word ----------
def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def cell_margins(table, top=45, bottom=45, left=90, right=90):
    tblPr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); m.append(e)
    tblPr.append(m)


def write_runs(par, text, size=None, color=None):
    for seg, bold in parts(text):
        r = par.add_run(seg)
        r.bold = bold
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor(*color)


def build_docx(path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin = sec.bottom_margin = Mm(11)
    sec.left_margin = sec.right_margin = Mm(14)
    for name in ("Normal", "List Bullet"):
        st = doc.styles[name]
        st.font.name = "맑은 고딕"
        st.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "맑은 고딕")
        st.font.size = Pt(10.6)
        st.paragraph_format.space_before = st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.line_spacing = 1.1
    head = doc.add_paragraph()
    head.add_run().add_picture(MASCOT, height=Mm(11))
    write_runs(head, f" **{TITLE}**", size=18, color=VIOLET)
    write_runs(head, f"　{TAGLINE}", size=11)
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    write_runs(meta, META, size=8.5, color=SOFT)
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell_margins(table)
    wl, wc = Mm(24), Mm(158)
    for label, items in ROWS:
        row = table.add_row()
        a, b = row.cells
        a.width, b.width = wl, wc
        shade(a, "EFEAFF")
        write_runs(a.paragraphs[0], f"**{label}**")
        first = True
        for it in items:
            kind = it[0]
            if kind == "img":
                par = b.paragraphs[0] if first else b.add_paragraph()
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                par.paragraph_format.space_before = Pt(2)
                par.add_run().add_picture(os.path.join(IMG, it[1]), width=Mm(it[2]))
                first = False
                continue
            if kind == "b":
                par = b.add_paragraph(style="List Bullet")
                if first:                          # 첫 빈 문단을 없앤다
                    b._tc.remove(b.paragraphs[0]._p)
                par.paragraph_format.left_indent = Mm(3.2)
                par.paragraph_format.first_line_indent = Mm(-3.2)
            else:
                par = b.paragraphs[0] if first else b.add_paragraph()
                if kind == "n":
                    par.paragraph_format.left_indent = Mm(3.6)
                    par.paragraph_format.first_line_indent = Mm(-3.6)
                if kind == "h":
                    par.paragraph_format.space_before = Pt(0 if first else 2)
            first = False
            write_runs(par, f"**{it[1]}**" if kind == "h" else it[1], color=VIOLET if kind == "h" else None)
    for line in FOOT:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        write_runs(p, line, size=8, color=(70, 70, 82))
    core = doc.core_properties
    core.title, core.author, core.subject = TITLE, "잘챙겨조(김호연, 김동현)", META
    doc.save(path)


# ---------- 인쇄용 HTML ----------
def rich(text):
    return "".join(f"<b>{html.escape(s)}</b>" if bold else html.escape(s) for s, bold in parts(text))


def build_html(path):
    rows = []
    for label, items in ROWS:
        body = []
        for it in items:
            kind = it[0]
            if kind == "img":
                body.append(f'<img class="fig" style="width:{it[2]}mm" src="img/{it[1]}" alt="{html.escape(it[3])}">')
            else:
                body.append(f'<p class="{kind}">{rich(it[1])}</p>')
        rows.append(f"<tr><th>{html.escape(label)}</th><td>{''.join(body)}</td></tr>")
    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{TITLE} · 잘챙겨조</title>
<style>
  /* PDF에서 글을 뽑을 수 있게 TrueType 글꼴(나눔고딕, OFL)을 함께 둔다. Apple SD Gothic Neo는 인쇄 때 Type3로 들어가 띄어쓰기가 깨졌다. */
  @font-face {{ font-family: "GSNanum"; src: url("fonts/NanumGothic-Regular.ttf") format("truetype"); font-weight: 400; font-display: block; }}
  @font-face {{ font-family: "GSNanum"; src: url("fonts/NanumGothic-Bold.ttf") format("truetype"); font-weight: 600 700; font-display: block; }}
  @page {{ size: A4; margin: 11mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: "GSNanum", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; font-size: 11.4pt; line-height: 1.42; color: #16182a; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  header {{ display: flex; align-items: center; gap: 3mm; margin-bottom: 1.6mm; position: relative; padding-top: 1mm; }}
  header img {{ height: 12mm; }}
  header h1 {{ margin: 0; font-size: 20pt; color: #6a48f0; white-space: nowrap; }}
  header .tag {{ font-size: 10.5pt; font-weight: 600; white-space: nowrap; padding-top: 3mm; }}
  header .meta {{ position: absolute; right: 0; top: 0; font-size: 8.5pt; color: #62616d; white-space: nowrap; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ border: 0.25mm solid #b9b6c6; padding: 1.6mm 2.2mm; vertical-align: top; text-align: left; }}
  th {{ width: 26mm; background: #efeaff; font-weight: 700; font-size: 10.6pt; word-break: keep-all; }}
  td {{ word-break: keep-all; overflow-wrap: anywhere; }}
  td b {{ color: #1d1640; }}
  p {{ margin: 0; }}
  p.h {{ font-weight: 700; color: #6a48f0; margin-top: 1.4mm; }}
  p.b, p.n {{ margin-top: 0.7mm; }}
  td > p.h:first-child {{ margin-top: 0; }}
  p.b {{ padding-left: 3.2mm; text-indent: -3.2mm; }}
  p.b::before {{ content: "• "; }}
  p.n {{ padding-left: 3.6mm; text-indent: -3.6mm; }}
  img.fig {{ display: block; margin: 1mm auto 0.6mm; }}
  footer a {{ color: #4a2fd0; }}
  footer p {{ font-size: 8.4pt; line-height: 1.4; color: #464652; margin-top: 1mm; }}
  p, img.fig {{ break-inside: avoid; }}
</style></head><body>
<header><img src="img/ssok.png" alt=""><h1>{TITLE}</h1><span class="tag">{html.escape(TAGLINE)}</span><span class="meta">{META}</span></header>
<table>{''.join(rows)}</table>
<footer>{''.join(f'<p>{rich(x)}</p>' for x in FOOT).replace(POC_URL, f'<a href="{POC_URL}">{POC_URL}</a>')}</footer>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def build_md(path):
    out = [f"# {TITLE}", "", f"{TAGLINE} · {META}", ""]
    for label, items in ROWS:
        out += [f"## {label}", ""]
        for it in items:
            kind = it[0]
            if kind == "img":
                out += ["", f"![{it[3] or '동작 구조도'}](img/{it[1]})", ""]
            elif kind == "h":
                out += ["", f"**{it[1]}**", ""]
            elif kind == "b":
                out.append(f"- {it[1]}")
            else:
                out += [it[1], ""]
        out.append("")
    out += ["---", ""] + [x + "\n" for x in FOOT]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip() + "\n")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    make_strip(os.path.join(IMG, "strip.png"))
    make_flow(os.path.join(IMG, "flow.png"))
    Image.open(MASCOT).save(os.path.join(IMG, "ssok.png"))
    build_docx(os.path.join(HERE, "gabangssok_plan.docx"))
    build_html(os.path.join(HERE, "gabangssok_plan.html"))
    build_md(os.path.join(HERE, "proposal.md"))
    chars = sum(len(re.sub(r"\*\*", "", it[1])) for _l, items in ROWS for it in items if it[0] != "img") + sum(len(x) for x in FOOT)
    print(f"만듦: gabangssok_plan.docx, gabangssok_plan.html, proposal.md, img/strip.png, img/flow.png · 글자 수 약 {chars}")
