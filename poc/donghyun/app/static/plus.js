/* 부모 화면 추가 기능(호연 몫). app.js 뒤에 읽는다. app.js 는 거의 그대로 두고 여기서 덧붙인다.
   - 통신문을 캘린더에 넣은 뒤 금지·조건·근거를 붙인다(/api/plus/…/analyze)
   - 일정 상세: 가져오지 않는 것, 추천(받아들이기), 보호자가 정할 것, 아이 결과와 칭찬 스티커, 달력 말투, 돌아오기
   - 설정: 아이 정보(추천에 씀) · 통신문 탭: 알림장 없는 평소 일정
   추가 기능 주소가 없는 서버에서는 아무것도 하지 않는다. */
// 받침에 맞는 조사를 고른다(한글로 끝나지 않으면 둘 다 적는다)
function josa(word, withFinal, noFinal) {
  const ch = String(word || "").trim().replace(/\s*[(（][^)）]*[)）]$/, "").replace(/["'”’\s]+$/, "").slice(-1), code = ch.charCodeAt(0);
  if (!(code >= 0xac00 && code <= 0xd7a3)) return `${withFinal}(${noFinal})`;
  return (code - 0xac00) % 28 ? withFinal : noFinal;
}
(() => {
  SRC.recommend = "추천";
  let MODE = null, readText = "";
  const baseApi = api;
  const plusApi = (path, opt) => baseApi(`/api/plus${path}`, opt);

  // 캘린더에 넣은 직후, 같은 통신문 글로 금지·조건을 뽑아 붙인다(글은 서버에 저장하지 않는다)
  api = async function (path, opt = {}) {
    // 금지·조건은 방금 읽힌 그 통신문 글로만 찾는다(다른 탭에 남아 있던 예전 글을 쓰지 않는다).
    // 글이 없으면(사진 통신문) 추출 결과의 메모를 쓴다. 추출 지시가 금지 문장을 메모에 옮기게 돼 있다
    if (path === "/api/notice/extract") readText = opt.body instanceof FormData ? String(opt.body.get("text") || "") : "";
    const text = path === "/api/notice/commit" ? (readText || (opt.body?.events || []).map((e) => e.notes || "").join("\n")) : null;
    const r = await baseApi(path, opt);
    if (text !== null && MODE && r.created) {
      let failed = 0;
      for (const c of r.created) { try { await plusApi(`/events/${c.id}/analyze`, { method: "POST", body: { text } }); } catch { failed++; } }
      if (failed) setTimeout(() => toast("일정은 넣었지만 금지·조건 표시를 붙이지 못했어요.\n일정을 열어 '통신문 글로 다시 확인'을 눌러 주세요.", 6000), 2800);
    }
    return r;
  };

  const baseSheet = renderSheet;
  renderSheet = function (ev) {
    baseSheet(ev);
    if (MODE) plusSheet(ev.id);
  };

  async function plusSheet(id) {
    let v;
    try { v = await plusApi(`/events/${id}`); } catch { return; }
    if (sheetId !== id) return;                              // 그 사이 다른 일정을 열었으면 그리지 않는다
    const p = v.plus, s = p.summary;
    // 체크리스트 줄에 근거·조건·선택 표시
    for (const it of v.items) {
      const box = $(`#sheet input[data-iid="${it.id}"]`);
      if (!box) continue;
      const nm = box.nextElementSibling, m = it.meta || {};
      const notes = [];
      if (m.condition) notes.push(`조건: ${m.condition}`);
      if (m.not_accepted?.length) notes.push(`${m.not_accepted.join(", ")}${josa(m.not_accepted[m.not_accepted.length - 1], "은", "는")} 안 돼요`);
      if (it.guardian) notes.push("필요한 아이만 · 보호자가 정해요(우리 미션에는 안 나와요)");
      else if (m.conditional === "rain") notes.push(it.optional ? "비 올 때만(지금은 비 소식 없음)" : "비 소식이 있어 챙겨요");
      else if (m.optional_by_notice) notes.push("통신문에 '선택'이라고 적혀 있어요");
      if (m.kind === "wear") notes.push("입고 가는 것");
      if (m.quantity) notes.push(`수량: ${m.quantity}`);
      if (it.blocked) notes.push("통신문이 가져오지 말라고 한 것과 겹쳐 아이 화면에는 안 나와요");
      if (it.conflict) notes.push("⚠️ 통신문의 '가져오지 않는 것'과 겹쳐요. 확인해 주세요");
      if (it.skipped) notes.push("이번엔 안 가져가요(아이 화면에 회색으로 알려 줘요)");
      nm.insertAdjacentHTML("beforeend", notes.map((n) => `<span class="why">${esc(n)}</span>`).join(""));
      if (it.skipped) { nm.classList.add("skipped"); box.disabled = true; }
      if (!it.guardian && !it.blocked && ["notice", "user", "recommend"].includes(it.source))   // 이번엔 빼기: 지우지 않고 이번만 뺀다
        nm.insertAdjacentHTML("afterend", `<button class="ghost small skipbtn" data-skip="${it.id}" data-on="${it.skipped ? 1 : 0}">${it.skipped ? "다시 챙기기" : "이번엔 빼기"}</button>`);
    }
    // 근거 줄은 한 번만(같은 줄이 항목마다 되풀이되지 않게)
    const ev = [...new Set(v.items.filter((i) => i.source === "notice" && i.meta?.evidence).map((i) => i.meta.evidence))];
    const list = $("#sheet .checklist");
    if (ev.length && list && !$("#sheet .evi")) list.insertAdjacentHTML("beforebegin", `<p class="hint evi">통신문에서 가져온 줄: ${ev.slice(0, 2).map((e) => `“${esc(e)}”`).join(" / ")}</p>`);
    const ban = p.forbidden.length ? `<div class="card plus"><strong>가져오지 않는 것</strong>
      <ul class="banlist">${p.forbidden.map((f) => `<li><b>🙅 ${esc(f.name)}</b>${f.removed ? ' <span class="badge">아이가 뺐다고 함</span>' : ""}<span class="why">통신문: “${esc(f.evidence)}”</span></li>`).join("")}</ul>
      ${p.not_needed.length ? `<p class="hint">안 가져가도 되는 것: ${p.not_needed.map((f) => esc(f.name)).join(", ")}</p>` : ""}</div>`
      : !p.analyzed ? "" : p.often_forbidden.length ? `<div class="card plus"><p class="hint">이 통신문에서는 금지 문구를 못 찾았어요. 비슷한 행사에서는 <b>${p.often_forbidden.map(esc).join(", ")}</b>을(를) 막는 학교가 있었어요. 통신문을 한 번 더 확인해 주세요.</p></div>` : "";
    const recs = (p.recs.length || p.guardian_recs.length) ? `<div class="card plus"><strong>추천 준비물</strong>
      <p class="hint">${p.list_open ? "통신문 목록이 '등'으로 끝나요. " : ""}통신문에 없는 것은 추천으로 따로 보여 드려요${p.scenario ? ` · 상황: ${esc(p.scenario.name)}` : ""}. 받아들인 것만 준비물 수에 들어가요.</p>
      <div class="chips">${p.recs.map((r) => `<span class="chip rec" title="${esc(r.why)}">${esc(r.emoji)} ${esc(r.name)} <small>${esc(r.basis)}</small>
        <button data-acc="${esc(r.name)}" aria-label="${esc(r.name)} 넣기">＋</button><button data-dec="${esc(r.name)}" aria-label="${esc(r.name)} 빼기">✕</button></span>`).join("")}</div>
      ${p.guardian_recs.length ? `<p class="hint"><b>보호자가 정해요:</b> ${p.guardian_recs.map((r) => `${esc(r.emoji)} ${esc(r.name)} <button class="ghost small" data-acc="${esc(r.name)}">넣기</button>`).join(" ")}<br>약은 넣어도 아이 화면에는 나오지 않아요.</p>` : ""}</div>` : "";
    const stickerRow = MODE.stickers.map((x) => `<button data-stk="${esc(x)}" aria-label="칭찬 스티커 ${esc(x)}">${esc(x)}</button>`).join("");
    const result = v.kind !== "deadline" && v.items.length ? `<div class="card plus"><strong>우리 미션</strong>
      <p class="sum">준비물 ${s.counted}${s.skipped?.length ? ` (이번엔 뺀 것 ${s.skipped.length})` : ""} · 넣음 ${s.packed} · 아직 ${s.left.length}${s.left.length ? ` (${s.left.map(esc).join(", ")})` : ""}${s.optional ? ` · 추천 ${s.optional} 중 ${s.optional_packed}` : ""}${s.open_alerts.length ? ` · 빼야 할 것 ${s.open_alerts.map(esc).join(", ")}` : ""}</p>
      <div class="stk-row">${stickerRow}</div>
      <div class="chip-add"><input id="stkMsg" maxlength="40" placeholder="한마디(안 써도 돼요). 예: 스스로 챙겨서 멋져"></div>
      <p class="hint" id="stkGiven">${p.stickers.length ? `준 스티커: ${p.stickers.map((x) => esc(x.sticker)).join(" ")}` : "스티커를 누르면 아이 스티커판에 붙어요"}</p>
      <div class="actions"><a class="ghost small" href="/kid?e=${v.id}&mode=home">🏠 집에 와서 가방 확인(돌아오기)</a>
        <button class="ghost small" id="toneBtn">📅 내 캘린더에 넣기(말투 고르기)</button></div>
      <div id="toneBox"></div></div>` : "";
    const redo = v.kind !== "deadline" && !p.analyzed && v.items.some((i) => i.source === "notice") ? `<div class="card plus"><strong>금지·조건을 아직 확인하지 못했어요</strong>
      <p class="hint">통신문 글을 붙여 넣으면 가져오지 않는 것과 조건을 다시 찾아요. 글은 저장하지 않아요.</p>
      <textarea id="redoText" rows="4" placeholder="통신문 글"></textarea><button class="ghost small" id="redoBtn">통신문 글로 다시 확인</button></div>` : "";
    const wxNote = v.weather?.status === "ok" ? `<p class="hint plus">날씨·미세먼지는 정해 둔 동네의 예보(${esc(v.weather.provider || "Open-Meteo")}${v.weather.fetched_at ? `, ${esc(v.weather.fetched_at.slice(11))} 기준` : ""})라 실제와 다를 수 있어요. 아이의 위치는 쓰지 않아요.</p>` : "";
    const anchor = $("#sheet .kid-cta") || $("#sheet .actions:last-of-type");
    $("#sheet").querySelectorAll(".plus").forEach((x) => x.remove());
    anchor.insertAdjacentHTML("beforebegin", redo + ban + recs + wxNote + result);
    $("#redoBtn")?.addEventListener("click", async () => {
      const text = $("#redoText").value.trim();
      if (!text) return toast("통신문 글을 붙여 넣어 주세요");
      try { await plusApi(`/events/${id}/analyze`, { method: "POST", body: { text } }); openSheet(id); } catch (e) { toast("⚠️ " + e.message); }
    });
    $$("#sheet [data-skip]").forEach((b) => b.addEventListener("click", async () => {
      try { await plusApi(`/events/${id}/items/${b.dataset.skip}/skip`, { method: "POST", body: { skipped: b.dataset.on !== "1" } }); openSheet(id); } catch (e) { toast("⚠️ " + e.message); }
    }));
    $$("#sheet [data-acc]").forEach((b) => b.addEventListener("click", async () => { await plusApi(`/events/${id}/recs/accept`, { method: "POST", body: { name: b.dataset.acc } }); openSheet(id); }));
    $$("#sheet [data-dec]").forEach((b) => b.addEventListener("click", async () => { await plusApi(`/events/${id}/recs/decline`, { method: "POST", body: { name: b.dataset.dec } }); openSheet(id); }));
    $$("#sheet [data-stk]").forEach((b) => b.addEventListener("click", async () => {
      const r = await plusApi(`/events/${id}/stickers`, { method: "POST", body: { sticker: b.dataset.stk, message: $("#stkMsg").value.trim() } });
      $("#stkGiven").textContent = `준 스티커: ${r.stickers.map((x) => x.sticker).join(" ")}`;
      $("#stkMsg").value = ""; toast(`${b.dataset.stk} 스티커를 붙였어요`);
    }));
    $("#toneBtn")?.addEventListener("click", async () => {
      const t = await plusApi(`/events/${id}/tones`);
      $("#toneBox").innerHTML = Object.entries(t).map(([k, x]) => `<div class="tone"><b>${esc(x.label)}</b> ${esc(x.title)}<pre>${esc(x.body)}</pre>
          <div class="calout"><a class="ghost small" href="${esc(x.google_url)}" target="_blank" rel="noopener">구글 캘린더에 넣기</a>
          <button class="ghost small" data-ics="${esc(k)}">캘린더 파일 받기(.ics)</button></div></div>`).join("") +
        `<p class="hint">같은 준비물을 말투만 바꿔 적어요. 숫자와 목록은 코드가 채워요. 구글 캘린더는 채워진 화면이 열리고 저장은 직접 눌러요. 캘린더 파일은 애플·삼성 캘린더 등에서 열 수 있고 전날 저녁·당일 아침 알림이 들어 있어요(앱에 따라 알림은 그 앱의 기본값으로 바뀔 수 있어요).</p>`;
      $$("#toneBox [data-ics]").forEach((b) => b.addEventListener("click", () => {
        const x = t[b.dataset.ics], a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([x.ics], { type: "text/calendar;charset=utf-8" }));
        a.download = x.filename; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      }));
    });
  }

  /* ---------- 설정: 아이 정보 ---------- */
  function mountProfile() {
    const form = $("#settingsDlg form"), row = form.querySelector(".row2:last-of-type");
    row.insertAdjacentHTML("beforebegin", `<h3 style="margin-top:14px">아이 정보</h3>
      <p class="hint">추천에만 써요. 이름은 별명이면 돼요.</p>
      <div class="row2"><label class="lbl">이름(별명)<input id="pfName" maxlength="12"></label>
        <label class="lbl">학년<input id="pfGrade" inputmode="numeric" maxlength="1"></label></div>
      <div class="traits" id="pfTraits">${MODE.traits.map((t) => `<label><input type="checkbox" value="${esc(t.id)}"> ${esc(t.label)}</label>`).join("")}</div>
      <label class="lbl">항상 챙기는 것(꼬리표, 쉼표로)<input id="pfAlways" placeholder="예: 교통카드, 지갑"></label>
      <label class="lbl">알림 말투<select id="pfTone"><option value="basic">보통</option><option value="cute">귀엽게</option><option value="neat">또박또박</option></select></label>`);
    $("#settingsBtn").addEventListener("click", async () => {
      const p = await plusApi("/profile");
      $("#pfName").value = p.name || ""; $("#pfGrade").value = p.grade || ""; $("#pfAlways").value = (p.always || []).join(", "); $("#pfTone").value = p.tone || "basic";
      $$("#pfTraits input").forEach((c) => (c.checked = (p.traits || []).includes(c.value)));
    });
    $("#homeSave").addEventListener("click", () => plusApi("/profile", { method: "PUT", body: {
      name: $("#pfName").value.trim(), grade: $("#pfGrade").value.trim(), tone: $("#pfTone").value,
      traits: $$("#pfTraits input").filter((c) => c.checked).map((c) => c.value),
      always: $("#pfAlways").value.split(",").map((x) => x.trim()).filter(Boolean) } }).catch(() => toast("아이 정보를 저장하지 못했어요")));
  }

  /* ---------- 예시 판: 실제 통신문 문장으로 해 보기 ----------
     scenarios.json sources 에서 그대로 옮긴 인용(제목·문장·주소). 인용의 " / " 는 줄바꿈으로 넣는다. */
  const REAL_NOTICES = [{"label": "금빛초 체험", "school": "성남 금빛초", "title": "2026 5학년 현장체험학습 참가 희망 조사(한국잡월드 숙련기술체험관)", "quote": "3. 준비물: 개인 도시락, 간식, 물, 음료수, 멀미약, 비닐 봉투 (장난감 등 불가)", "url": "https://www.goesn.kr/geumbit-e/na/ntt/selectNttInfo.do?mi=11070&nttSn=1926110"}, {"label": "민백초 수영", "school": "안양 민백초", "title": "2026 초등생존수영 실기교육 실시 안내 및 학생 안전생활 수칙(3,4학년)", "quote": "5. 학생 준비물 : 수영복, 수영모자, 수영가방, 수건, 여분의 비닐 봉지, 등 (※ 입장제한: 래쉬가드, 아쿠아슈즈, 남성용 트렁크, 일반 티셔츠, , 스킨스쿠버 슈트, 수경 ) / ◦ 수영 실기교육 하는 날에는 분실 등의 문제로 휴대전화, 귀걸이, 목걸이, 시계, 용돈 등의 귀중품을 가지고 등교하지 않도록 합니다.", "url": "https://www.goeay.kr/minbaeg-e/na/ntt/selectNttInfo.do?bbsId=699&mi=2430&nttSn=1310717"}, {"label": "신능초 수영", "school": "고양 신능초", "title": "2025 초등생존수영 실기교육 실시 및 학부모자원봉사자 지원 안내", "quote": "4. 학생 준비물 수영복, 수영모자, 물안경, 수영가방, 수건, 여분 봉지, 샤워 도구(선택) 등 * 모든 물건에 자기 이름 쓰기 / ◦ 개인 귀중품은 수영장으로 가져오지 않도록 하며 개인 물건을 잘 관리합니다. 특히 시계, 귀걸이, 목걸이는 착용하지 않습니다.", "url": "https://www.goegy.kr/shinneung-e/na/ntt/selectNttInfo.do?bbsId=854&mi=2452&nttSn=1145358"}];
  function mountRealNotices() {
    $("#extractBtn").insertAdjacentHTML("beforebegin", `<div class="realrow" id="realRow">
      <span class="lbl">실제 통신문 문장으로 해 보기</span>
      <div class="realbtns">${REAL_NOTICES.map((r, i) => `<button class="ghost small" data-real="${i}">${esc(r.label)}</button>`).join("")}</div>
      <p class="hint">실제 초등학교 통신문의 준비물 주변 문장이에요(출처: ${REAL_NOTICES.map((r) => `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.school)}</a>`).join(", ")}). 날짜가 없어서 내일 일정으로 넣어요.</p></div>`);
    $$("#realRow [data-real]").forEach((b) => b.addEventListener("click", () => {
      const r = REAL_NOTICES[+b.dataset.real];
      $(".tab[data-src='text']")?.click();
      $("#textIn").value = r.title + "\n" + r.quote.replace(/ \/ /g, "\n");
      $("#textIn").focus();
      toast(`${r.school} 통신문 문장을 넣었어요. '일정·준비물 뽑기'를 눌러 보세요`);
    }));
  }

  /* ---------- 통신문 탭: 고지 + 알림장 없는 평소 일정 ---------- */
  async function mountAdd() {
    $("#extractStatus").insertAdjacentHTML("afterend", `<p class="hint">${MODE.demo
      ? "예시 모드예요. AI를 부르지 않고 규칙으로 읽어요. 링크·사진은 준비된 예시 통신문으로 대신해요."
      : "통신문 글과 사진은 일정을 뽑을 때 AI(Anthropic)로 보내요. 원문은 저장하지 않고, 준비물이 나온 줄만 근거로 남겨요. AI가 틀릴 수 있으니 넣기 전에 확인해 주세요."}</p>`);
    if (MODE.demo) mountRealNotices();
    const list = await plusApi("/scenarios");
    $("#preview").insertAdjacentHTML("beforebegin", `<div class="card" id="quickCard"><strong>알림장 없는 평소 일정</strong>
      <p class="hint">상황을 고르면 기본 준비물이 추천으로 들어가요. 빼거나 더할 수 있어요.</p>
      <div class="row2"><label class="lbl">상황<select id="qScenario">${list.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("")}</select></label>
        <label class="lbl">날짜<input type="date" id="qDate" value="${ymd(new Date(Date.now() + 86400000))}"></label></div>
      <button class="ghost" id="qAdd">추천 준비물로 일정 만들기</button></div>`);
    $("#qScenario").value = "swim_academy";
    $("#qAdd").addEventListener("click", async () => {
      try {
        const r = await plusApi("/quick-event", { method: "POST", body: { scenario: $("#qScenario").value, date: $("#qDate").value } });
        toast("일정을 만들었어요"); selDay = $("#qDate").value; calMonth = parse(selDay); calMonth.setDate(1); show("cal"); openSheet(r.id);
      } catch (e) { toast("⚠️ " + e.message); }
    });
  }

  (async () => {
    try { MODE = await baseApi("/api/plus/mode"); } catch { return; }     // 추가 기능이 없는 서버
    if (MODE.demo && $("#extractBtn")) $("#extractBtn").textContent = "일정·준비물 뽑기 (예시: 규칙으로 읽어요)";
    mountProfile();
    mountAdd();
    if (MODE.demo) $(".top .sub").insertAdjacentHTML("afterend", `<p class="sub demo">예시 모드 · AI를 부르지 않아요 · 지어낸 예시 일정</p>`);
  })();
})();
