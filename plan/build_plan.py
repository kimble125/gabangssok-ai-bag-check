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
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IMG = os.path.join(HERE, "img")
SHOTS = os.path.join(REPO, "docs", "assets", "shots")
MASCOT = os.path.join(REPO, "poc", "donghyun", "app", "static", "mascot", "ssok_hello.png")
POC_URL = "https://kimble125.github.io/gabangssok-ai-bag-check/"

TITLE = "가방쏙 기획안"
TAGLINE = "가정통신문에서 가방까지: 엄마가 넣으면, 아이가 스스로 챙겨요"
META = "엘리스 AI 챌린지 2026 · 성인 부문"

# 종류: p 문단 / h 작은 제목 / b 글머리표 / n 번호가 글 안에 든 줄 / img 그림(파일, 너비 mm, 설명)
# 2쪽 안에서 읽기 쉽게: 칸마다 서너 줄, 숫자의 분모와 조사 방법은 맨 아래 출처로 내린다.
ROWS = [
    ("1. 참가 정보", [
        ("p", "**팀명** 잘챙겨조　 **팀원** 김호연(대표) · 김동현"),
    ]),
    ("2. 문제 정의", [
        ("h", "현장체험학습 전날 저녁, 엄마와 초등 저학년 아이"),
        ("p", "통신문에는 ‘개인 도시락, 간식, 물, 음료수, 멀미약, 비닐 봉투 (장난감 등 불가)’라고 적혀 있다. 가방에 넣을 것과 두고 갈 것이 한 줄에 섞여 있다."),
        ("p", "팀이 읽은 통신문 23건에서 준비물을 한 줄로 쓴 19건 중 **10건(53%)이 ‘등’으로 끝났다.** 아이가 혼자 읽기 어렵고, 엄마는 금지·조건까지 기억해 챙겨야 한다."),
        ("p", "아버지 설문에서 준비물 파악·구입은 **어머니 담당이 52.3%**였다¹. 취학 뒤 어려움 중 숙제 지도·준비물 챙기기는 22.9%였다². 빠뜨리는 빈도는 아직 재지 않았다."),
    ]),
    ("3. 서비스 개요", [
        ("p", "**서비스명 · 가방쏙**　엄마가 대신 챙기던 가방을 이제 아이가 친구 쏙이와 함께 ‘우리 미션’으로 직접 싼다."),
        ("p", "**기대 효과**　아이는 학교의 조건과 금지를 지키며 스스로 챙기고, 엄마는 확인하고 칭찬한다. 추천은 학교가 지정한 필수품과 구별한다."),
        ("p", "**이번 범위**　가방에 넣기와 귀가 뒤 확인 한 화면까지. 집 안에서 물건 찾기와 쏙이와의 자유 대화는 다음 단계다."),
    ]),
    ("4. 서비스 활용 방식", [
        ("h", "한 장면 · 내일 체험학습인데, 유리병을 챙겨도 될까?"),
        ("n", "① **엄마가 통신문을 넣는다.** 물은 준비물, 유리병은 금지라는 원문을 함께 본다. 행사일과 회신 마감은 엄마가 확인해 달력에 넣는다."),
        ("n", "② **아이가 쏙이와 ‘우리 미션’을 시작한다.** 추천은 골라 담고 준비물을 펼친다. 유리병이 보이면 ‘이건 두고 가자’. 사진에 안 보인 것은 하나씩 넣으며 직접 확인한다."),
        ("n", "③ **아이가 ‘다 챙겼지!’를 엄마에게 보여 준다.** 엄마는 대신 가방을 열어 보지 않고 칭찬 스티커를 붙인다. 귀가 뒤에는 가져간 것을 다시 확인할 수 있다."),
        ("img", "strip.png", 152, "예시판 화면: 통신문 넣기 → 금지·조건·추천 → 아이 미션 → 이건 두고 가자 → 다 챙겼지!"),
    ]),
    ("5. AI 활용 계획", [
        ("p", "**공개 예시판**　브라우저에서 통신문을 규칙으로 읽는다. AI 모델을 호출하지 않으며, 사진 판정은 미리 준비한 고정 결과다."),
        ("p", "**실제판 · Docker 로컬**　Claude API가 통신문의 글·사진을 읽고 준비물 사진에서 보이는 물건을 찾는다. 캘린더 MCP 서버는 일정을 다룬다. 공개 예시판에서는 이 서버를 실행하지 않는다."),
        ("p", "**MCP에서 확인한 범위**　Claude 데스크톱에서 예시 서버의 packing_plan이 가상 통신문의 준비물·금지물을 돌려준 것까지 확인했다. 실제판 서버의 도구 등록은 미확인이다."),
        ("img", "flow.png", 152, "실제판: Claude가 읽고 본다 → 규칙이 근거와 목록을 대조한다 → 아이와 엄마가 확인한다"),
        ("h", "같은 통신문 23건에 규칙을 다시 적용한 결과"),
        ("p", "금지물은 표현을 보완한 뒤 **35/43 → 43/43, 오탐 1개**였다. ‘등’은 11/11건 찾았다. 준비물은 머리말이 있는 19건에서 114/114개였지만, **머리말 없는 표·학년별 목록 4건은 0/78개**였다. AI가 만든 정답표와 느슨하게 대조한 값으로, 새 통신문이나 사진의 정확도가 아니다."),
        ("p", "**모델은 보고, 규칙은 판단한다.** 금지·조건·추천·완료 판정은 근거 문장을 쓰는 규칙이 맡는다(자동 시험 62개). 안 보인 것은 아이가 확인하고, 약은 보호자에게만 보인다. 아이와 AI의 직접 대화·사진 저장·위치 수집은 하지 않는다."),
        ("p", "**다음 검증**　실제 사진 12장 이상에서 금지물을 놓친 수와 잘못 본 수를 따로 잰다. 오류가 많으면 사진보다 하나씩 챙기기를 우선한다."),
        ("p", "**제작 도구**　Claude·GPT로 조사·초안·코드·검토를 보조하고, 쏙이 그림에 이미지 생성 AI를 사용했다. 결과는 팀이 확인했다."),
    ]),
    ("6. 핵심 기능 (3가지)", [
        ("n", "① **통신문을 일정과 준비물로**　행사일·회신 마감을 나누고 준비물·금지·조건에 원문을 붙인다. 구글 캘린더에는 일정 작성 링크나 .ics 파일로 내보낸다."),
        ("n", "② **‘등’ 뒤에 빠진 준비물 추천**　통신문 23건의 유사 사례, Open-Meteo 날씨·미세먼지, 아이 특성을 반영한다. ‘비슷한 알림장 2건에서 봤어요’처럼 이유를 붙여 필수품과 나눈다."),
        ("n", "③ **쏙이와 함께하는 ‘우리 미션’**　아이가 직접 사진에 안 보인 물건을 하나씩 확인한다. 다 챙겼을 때만 완료하고, 엄마는 칭찬 스티커로 답한다."),
    ]),
    ("7. 차별점", [
        ("p", "리마인디는 통신문에서 준비물을 뽑고, TurtleWiz는 목록과 사진을 대조한다(스토어 설명 기준). **가방쏙은 ‘왜 두고 가야 하는지’까지 아이에게 보여 준다.** 추천과 학교 지시를 섞지 않고, 아이가 직접 고르고 챙긴 결과를 엄마의 칭찬으로 잇는다."),
    ]),
    ("8. 역할 분담", [
        ("p", "**김호연**　기획·서비스 설계, 추천·금지 규칙과 MCP 도구 설계, 아이 화면·통합"),
        ("p", "**김동현**　개발·배포·운영 담당: 통신문 추출, 캘린더 MCP 서버, 날씨·알림"),
    ]),
]
FOOT = [
    f"**공개 예시판 · 주소**　{POC_URL}",
    "**근거**　팀 조사: 초등학교 홈페이지 통신문 23건(2026.11.19). ¹ 인구보건복지협회, 초등 이하 자녀를 둔 아버지 524명(KBC, 2026.11.15). ² 장명림·김선미(2018), 2015년 초등 학부모 2,579명의 복수응답 4,268건 중 976건.",
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
    """실제판에서 모델·규칙·사람이 나눠 맡는 일."""
    im = Image.new("RGB", (1580, 131), "white")
    d = ImageDraw.Draw(im)
    for i, (title, sub, bg) in enumerate([
        ("Claude API · 읽기와 보기", "통신문 읽기 / 사진 속 물건 찾기", "#EEEAFB"),
        ("규칙 코드 · 대조와 판정", "금지·조건에 원문 붙이기 / 세기", "#E6F1EB"),
        ("아이와 엄마 · 최종 확인", "안 보인 물건 직접 확인 / 칭찬", "#FBF0DD"),
    ]):
        x = i * 548
        d.rounded_rectangle((x, 1, x+480, 128), radius=14, fill=bg)
        d.text((x+18, 17), title, font=font(34, True), fill=INK)
        d.text((x+18, 76), sub, font=font(28), fill=INK)
        if i < 2:
            d.text((x+495, 45), "→", font=font(34, True), fill=SOFT)
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
        if POC_URL in line:
            write_runs(p, line.split(POC_URL)[0], size=9)
            link = OxmlElement("w:hyperlink")
            link.set(qn("r:id"), p.part.relate_to(POC_URL, RT.HYPERLINK, is_external=True))
            run = p.add_run(POC_URL); run.font.size = Pt(9); run.underline = True
            run.font.color.rgb = RGBColor(70, 50, 155)
            link.append(run._r); p._p.append(link)
        else:
            write_runs(p, line, size=8, color=(70, 70, 82))
    core = doc.core_properties
    core.title, core.author, core.subject = TITLE, "잘챙겨조(김호연, 김동현)", META
    doc.save(path)


# ---------- 인쇄용 HTML ----------
def rich(text):
    return "".join(f"<b>{html.escape(s)}</b>" if bold else html.escape(s) for s, bold in parts(text))


def build_html(path):
    blocks = []
    for i, (label, items) in enumerate(ROWS):
        body = []
        for j, it in enumerate(items):
            if it[0] == "img":
                body.append(f'<img class="fig {it[1].split(".")[0]}" src="img/{it[1]}" alt="{html.escape(it[3])}">')
            else:
                name = 'scope' if i == 4 and j < 3 else it[0]
                body.append(f'<p class="{name}">{rich(it[1])}</p>')
        num, name = label.split('. ', 1)
        blocks.append(f'<section><h2><span>{int(num):02d}</span> {html.escape(name)}</h2>{"".join(body)}</section>')
    css = """
    @font-face {font-family:Nanum;src:url('fonts/NanumGothic-Regular.ttf');font-weight:400;}
    @font-face {font-family:Nanum;src:url('fonts/NanumGothic-Bold.ttf');font-weight:700;}
    @page {size:A4;margin:12mm 15mm;}
    * {box-sizing:border-box;} body {margin:0;color:#202237;font:11pt/1.38 Nanum,'Malgun Gothic',sans-serif;word-break:keep-all;overflow-wrap:anywhere;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
    article {min-height:271mm;display:flex;flex-direction:column;} article+article {break-before:page;}
    header {border-bottom:1mm solid #5a3aaf;padding-bottom:2.4mm;margin-bottom:1.3mm;}
    .topline {display:flex;justify-content:space-between;align-items:center;color:#474259;font-size:8.4pt;font-weight:bold;}
    .title {display:flex;align-items:center;gap:3mm;margin-top:1mm;}.title img{height:12mm;} h1,h2,p {margin:0;}
    h1 {font-size:23pt;line-height:1.1;color:#352162;} .tag {font-size:11pt;margin-top:.6mm;}
    .sub {font-size:16.5pt;line-height:1.35;margin-top:1mm;color:#352162;}
    section {padding:2mm 0 1.3mm;border-bottom:.28mm solid #d9d7e2;}
    h2 {font-size:12pt;color:#33244f;margin:0 0 1mm;} h2 span{display:inline-block;font-size:9pt;padding:.35mm 1.6mm;color:#fff;background:#593c92;vertical-align:1px;margin-right:1mm;}
    p+p {margin-top:.8mm;} p.h {color:#4d307d;font-weight:700;} .fig{display:block;margin:2mm auto 1mm;max-width:100%;}.strip{width:170mm;}.flow{width:170mm;}
    .scope {background:#f3f0f8;border-left:.65mm solid #7253a5;padding:.9mm 2mm;}
    footer {margin-top:auto;padding-top:2mm;} .url {font-size:10pt;color:#392064;font-weight:700;} .source {font-size:8.4pt;line-height:1.4;color:#454457;} a{color:#4a2d85;}
    @media screen {body{background:#eeedf2;} article{width:210mm;min-height:297mm;background:white;margin:4mm auto;padding:12mm 15mm;}}
    """
    pages = []
    for i in range(2):
        title = (f'<div class="title"><img src="img/ssok.png" alt="쏙이"><div><h1>{TITLE}</h1><p class="tag">{TAGLINE}</p></div></div>'
                 if i == 0 else '<h1 class="sub">가방쏙은 어디까지 스스로 판단할까?</h1>')
        footer = rich(FOOT[i]).replace(POC_URL, f'<a href="{POC_URL}">{POC_URL}</a>')
        pages.append(f'<article><header><div class="topline"><span>{META}</span><span>잘챙겨조　·　{i+1} / 2</span></div>{title}</header>{"".join(blocks[i*4:i*4+4])}<footer class="{"url" if i==0 else "source"}">{footer}</footer></article>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE} · 잘챙겨조</title><style>{css}</style></head><body>{"".join(pages)}</body></html>')


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
