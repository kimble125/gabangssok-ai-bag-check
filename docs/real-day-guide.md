# 가방쏙 하루 실습: 박물관에 가져간 물통, 집에 돌아왔을까?

가상의 통신문 한 장을 넣고 **보호자가 읽은 근거, 아이가 넣은 물건, 집에 가져온 물건**을 같은 일정 번호로 따라갑니다. 화면만 보려면 **1절**, 키 없이 실제 HTTP API와 MCP(비서가 앱의 도구를 부르는 규약)를 써 보려면 **2–4절**이면 됩니다. 여기까지는 Docker나 Claude 계정이 필요 없습니다.

**어디서 시작할까요?** [설치 없이 공개 체험판 열기](https://kimble125.github.io/gabangssok-ai-bag-check/demo/) · [실제판을 내 컴퓨터에서 켜기](#real-server). 실제판이 켜지면 같은 1절의 통신문과 버튼을 그대로 쓰세요. 2–4절의 터미널 검산은 선택입니다.

| 어느 판을 열까? | 할 수 있는 일 | 예시이거나 빠진 것 |
|---|---|---|
| **공개 체험판** · 브라우저 | 부모·아이 두 화면에서 가상 통신문 붙여넣기, 규칙 분석, 체크·스티커·귀가 확인 | Claude API 없음. 사진과 링크는 준비된 예시. 탭 안 SQLite라 새로 고치면 초기화됩니다. 외부 비서가 붙을 `/mcp/` 주소는 없습니다. |
| **로컬 예시 서버** · Python 3.10+ · 기본 `127.0.0.1:6111` | 같은 규칙과 UI, 실제 SQLite 쓰기, HTTP API, 조회·분석용 MCP 도구 4개 | 글은 규칙으로, 사진은 예시로 처리. 일정 등록은 MCP를 거치지 않고 DB에 직접 저장합니다. |
| **실제 서버** · Docker · 호스트 `6110` → 컨테이너 `8000` | FastAPI, 실제 캘린더 MCP, 키가 있으면 Claude로 글·통신문 사진 추출 및 준비물 사진 분석 | 로그인·가족별 접근 통제 없음. 외부망에 공개하지 마세요. 실제 모델 호출은 유료일 수 있으며 아래 실측에 포함하지 않았습니다. |

## 1. 화면으로 보는 하루

GitHub Pages의 **프로토타입 눌러 보기**를 선택하세요([소개 소스](index.html) · [체험판 소스](demo/index.html)). GitHub에서 HTML 코드만 보인다면 저장소 루트에서 `python3 -m http.server 8765 --bind 127.0.0.1 --directory docs` 후 `http://127.0.0.1:8765/demo/`를 엽니다. 이 포트는 정적 파일 전용입니다. 실행 도구(Pyodide)·글꼴 다운로드와 날씨 조회에는 네트워크를 씁니다. CDN이 막히면 [화면 사진 모음](assets/shots/) 또는 2절로 이동하세요.

화면 명칭은 부모·아이 화면 코드 기준입니다. 화면 문구가 다르면 실제 표시를 따르세요.

**전날 저녁, 보호자.** `＋ 통신문` → `붙여넣기`에 아래 글을 넣습니다. 실제 학교·아동 정보는 필요 없습니다.

```text
박물관 견학 안내
내일은 박물관 견학입니다.
장소: 가상박물관
준비물: 물통, 수건, 비닐봉지 2장, 개인 약품(멀미약 등 필요한 학생)
장난감은 가져오지 않습니다.
```

1. `일정·준비물 뽑기` → 미리보기에서 내일 날짜와 장소를 확인 → `캘린더에 넣기`. 날짜가 없으면 규칙이 내일로 대신 넣기도 하므로 **등록 전 원문과 대조**하세요.
2. 일정 상세에서 물통·수건·비닐봉지 **2장**의 근거 줄과 금지 근거 **“장난감은 가져오지 않습니다.”**를 읽습니다. 개인 약품은 보호자가 정하고 아이 필수 수에서 뺍니다. `필기도구` 같은 추천에는 이유가 있지만 원문 필수품이 아닙니다. 같은 결과를 보려면 추천을 추가하지 마세요.
3. **등교 전, 아이.** `아이랑 가방 싸기` → `사진 없이 하나씩 할래`. 물통만 `넣었어!`, 나머지는 `아직 못 찾았어` → `엄마에게 보여 주기`. 예시 사진을 보고 싶으면 대신 `몇 개 안 보임`을 누르세요. 실물 촬영·판독이 아니라 미리 정해진 표시입니다. 실제판에서는 `다 펼쳤어!`로 물건 사진을 보내고, 안 보인 물건은 직접 확인합니다. 사진에 안 보인다고 집에 없다는 뜻은 아닙니다. 수량·조건 항목은 아이가 확인합니다.
4. **하교 후.** 보호자 일정 상세 → `집에 와서 가방 확인(돌아오기)` → 아이가 물통을 눌러 `가져왔어`로 바꾸고 `엄마에게 알려 주기`. 아침에 **체크했고 다시 가져올 물건만** 나옵니다. 보호자 `알림`에서 등교·귀가 결과를 따로 읽고, 일정 상세에서 스티커를 주면 아이의 `내 스티커판`에 남습니다. 다른 가족 휴대폰으로 전송하는 푸시가 아닙니다.

[등교 확인 화면](assets/shots/6_kid_one.webp) · [보호자 스티커](assets/shots/8_parent_sticker.webp) · [귀가 확인 화면](assets/shots/10_kid_home.webp). 사진들은 화면 구조를 보여 주는 **다른 예시 일정**이며, 아래 실측의 사진 판독 증거가 아닙니다.

## 2. 전날: 키 없이 서버를 켜고 일정 저장하기

준비: 저장소 사본, 터미널 두 개, Python 3.10 이상. 아래 API 예제에는 `curl`, `jq`, Bash가 필요합니다. `jq`가 없다면 설치 없이 1절 또는 로컬 서버의 브라우저 화면을 쓰세요.

**터미널 A, 저장소 루트에서:** 기존 서버나 가족 DB를 건드리지 않도록 전용 포트와 새 임시 DB를 씁니다. 날씨 요청도 사용하지 않는 로컬 프록시로 보내서 예보 없이 재현합니다. 같은 네트워크의 다른 기기로는 접속할 수 없습니다.

```bash
D=$(mktemp -d)
env -i PATH="$PATH" TZ=Asia/Seoul PYTHONUTF8=1 DB_PATH="$D/demo.db" PORT=47163 \
  https_proxy=http://127.0.0.1:1 http_proxy=http://127.0.0.1:1 no_proxy=127.0.0.1,localhost \
  python3 -B poc/donghyun/demo_server.py
```

**터미널 B:** 이후 2–4절 블록은 같은 셸에서 순서대로 실행합니다. 화면 실습을 먼저 했다면 새로운 DB로 시작하세요. 포트를 이미 쓰고 있다면 기존 서버를 끄지 말고 A의 `PORT`와 B의 `BASE`를 같은 빈 포트로 바꾸세요.

```bash
BASE=http://127.0.0.1:47163
curl -fsS "$BASE/healthz" | jq -c .  # {"ok":true,"mode":"demo"}
TEXT='박물관 견학 안내
내일은 박물관 견학입니다.
장소: 가상박물관
준비물: 물통, 수건, 비닐봉지 2장, 개인 약품(멀미약 등 필요한 학생)
장난감은 가져오지 않습니다.'
EX=$(curl -fsS --form-string "text=$TEXT" "$BASE/api/notice/extract")
printf '%s' "$EX" | jq '.events[] | {title,date,location,items}'
```

**여기서 확인:** `title`은 `박물관 견학`, `location`은 `가상박물관`, `items`는 원문의 네 항목입니다. 읽기만 했으므로 아직 일정 번호는 없습니다. 기대한 결과라면 다음을 실행하세요. `post_json`은 표준입력으로 JSON을 보내는 작은 함수입니다.

```bash
post_json() { curl -fsS -H 'Content-Type: application/json' --data-binary @- "$1"; }
C=$(printf '%s' "$EX" | jq '{events,source_title:"가상 통신문"}' | post_json "$BASE/api/notice/commit")
printf '%s' "$C" | jq .
E=$(printf '%s' "$C" | jq -er '.created[0].id')
P="$BASE/api/plus/events/$E"
jq -nc --arg t "$TEXT" '{text:$t}' | post_json "$P/analyze" | jq '{forbidden:.plus.forbidden,summary:.plus.summary}'
```

11월 22일 실행에서는 `created[0]`이 `{"id":4,"title":"박물관 견학","date":"2026-11-23"}`, `via`는 `예시 서버(직접 저장)`이었습니다. 번호·날짜는 달라집니다. **저장과 근거 분석은 별도 호출**입니다. 웹 화면은 등록 직후 자동으로 `analyze`를 부릅니다. API에서 생략하면 준비물이 저장돼도 금지·조건 근거가 붙지 않습니다.

## 3. 밤: AI 비서에게 물을 질문을 MCP로 검산하기

비서 앱 없이도 다음은 `/mcp/`에 보내는 **실제 JSON-RPC 요청**입니다. 연결 → 도구 목록 → 원문 읽기 → 저장된 일정 찾기 → 준비물 판단 → 캘린더 내보내기 순입니다. `initialize`에 고른 규약은 예시 서버가 지원하는 `2025-06-18`입니다.

```bash
rpc() { curl -fsS "$BASE/mcp/" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-06-18' --data-binary @-; }
tool() { jq -nc --arg n "$1" --argjson a "$2" \
  '{jsonrpc:"2.0",id:3,method:"tools/call",params:{name:$n,arguments:$a}}' | rpc; }
printf '%s' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"judge","version":"1"}}}' | rpc | jq '.result.serverInfo'
printf '%s' '{"jsonrpc":"2.0","method":"notifications/initialized"}' | rpc
printf '%s' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | rpc | jq '[.result.tools[].name]'
A=$(jq -nc --argjson e "$E" '{event_id:$e}')
tool read_notice "$(jq -nc --arg t "$TEXT" '{text:$t}')" | jq '.result.structuredContent | {items:.events[0].items,forbidden}'
tool list_events '{}' | jq '.result.content[0].text | fromjson | map(select(.title=="박물관 견학"))'
tool packing_plan "$A" | jq '.result.structuredContent | {summary,parent_decides,forbidden,recommendations}'
tool calendar_entry "$A" | jq '.result.structuredContent | {title,reminders,filename,ics:(.ics|startswith("BEGIN:VCALENDAR"))}'
```

서버 이름은 `gabangssok`, 목록은 `list_events`, `read_notice`, `packing_plan`, `calendar_entry`입니다. `read_notice`는 저장하지 않고, `packing_plan`과 `calendar_entry`는 저장된 `event_id`를 받습니다. 일정 목록은 이 예시 서버에서 `content[0].text` 안의 JSON 배열이고, 나머지 세 도구는 `structuredContent`도 제공합니다.

| AI 비서에 그대로 물을 질문 | 어떤 값과 대조할까? (로컬 규칙 결과 기준 정답) |
|---|---|
| “내일 박물관에 필수로 몇 가지 가져가? 비닐봉지와 약은 어떻게 해?” | `list_events`로 번호 확인 → `packing_plan.summary.count=3`. 물통·수건·비닐봉지이고 봉지는 **2장**입니다. 개인 약품은 필요한 학생만 보호자가 결정하며 아이 필수 수에서 제외합니다. |
| “장난감도 챙겨? 통신문에서 이유를 찾아줘.” | `read_notice.forbidden` 또는 `packing_plan.forbidden`: **아니요. “장난감은 가져오지 않습니다.”** 추천을 통신문 지시로 바꾸지 않습니다. |
| “달력에 넣으면 언제 알려 줘? 지금 저장된 거야?” | `calendar_entry.reminders`: 전날 19:00·행사 당일 07:30, 한국 시간. `google_url`은 일정 작성 화면, `ics`는 가져올 파일 내용입니다. **외부 달력에 자동 저장하지 않습니다.** |

실제 비서로 대화하려면 같은 컴퓨터의 Streamable HTTP 지원 클라이언트에 `http://127.0.0.1:47163/mcp/`를 등록합니다. Claude Code가 이미 설치돼 있다면 `claude mcp add --transport http gabangssok-demo http://127.0.0.1:47163/mcp/`가 등록 예입니다. **비서의 로그인·모델 사용료와 로컬 도구는 별개**입니다. 비서 대화를 하지 않아도 위 명령으로 정답을 검산할 수 있습니다. 원격 서비스에서는 그 서비스의 `127.0.0.1`이 내 컴퓨터가 아닙니다. 터널로 가족 데이터를 노출하지 마세요.

## 4. 아침과 하교: 물통 하나만 확인해 결과의 차이 보기

아래 사진 요청은 **예시 서버에서만**, 사진 파일 없이 `case=miss`를 선택합니다. 모델 호출이나 이미지 판독이 아닙니다. 응답은 체크 후보이며 이 HTTP 호출만으로 `seen`이 저장되지는 않습니다. 화면에서는 아이 화면 코드가 보인 항목을 체크합니다. 여기서는 **직접 보고 물통만** 체크합니다.

```bash
curl -fsS -X POST "$P/photo-check?case=miss" | jq '{mode,seen,not_seen,forbidden_seen}'
I=$(curl -fsS "$P" | jq -er '.items[] | select(.name=="물통") | .id')
curl -fsS -X PATCH -H 'Content-Type: application/json' -d '{"checked":true}' "$BASE/api/items/$I" | jq .
curl -fsS -X POST "$P/kid-report" | jq '{body,summary:.summary.left}'
curl -fsS "$P/return" | jq '.summary'
jq -nc --argjson i "$I" '{item_id:$i,returned:true}' | post_json "$P/return" | jq '.summary'
curl -fsS -X POST "$P/return/report" | jq '.summary'
curl -fsS "$BASE/api/notifications" | jq --argjson e "$E" '[.[]|select(.event_id==$e and (.kind=="kid" or .kind=="home"))|{kind,message}]'
S=$(curl -fsS "$BASE/api/plus/mode" | jq -r '.stickers[0]')
jq -nc --arg s "$S" '{sticker:$s,message:"물통 잘 가져왔네!"}' | post_json "$P/stickers" | jq '.stickers[0]|{sticker,message}'
printf '보호자 %s/\n등교 %s/kid?e=%s\n귀가 %s/kid?e=%s&mode=home\n' "$BASE" "$BASE" "$E" "$BASE" "$E"
```

| 언제 | 이번 시험에서 받은 값 |
|---|---|
| 등교 전 사진 예시 | `mode:"example"`, 보임 1개·안 보임 2개. 항목 ID는 DB마다 달라집니다. |
| 물통만 넣었다고 보고 | `준비물 3 · 넣음 1 · 아직 2 (수건, 비닐봉지 2장)` |
| 귀가 전 → 후 | `{"counted":1,"returned":0,"left":["물통"]}` → `{"counted":1,"returned":1,"left":[]}` |
| 보호자 | 같은 일정의 알림 두 종류 `kid`·`home`와 스티커 메시지 `물통 잘 가져왔네!`를 확인했습니다. |

`귀가 1/1`은 **물통을 가져왔다는 뜻**이지 아침 준비물 3개가 모두 있었다는 뜻이 아닙니다. 여기까지가 무과금 연동 시험입니다. 화면을 다 봤다면 **터미널 A에서 Ctrl+C**로 이 서버만 종료하세요. DB는 A의 `$D/demo.db`에만 있습니다.

<a id="real-server"></a>

## 5. 선택: 실제 Docker 서버와 Claude는 어디에서 쓰나?

**이 절은 코드로 확인한 실행 경로입니다. 이 가이드를 만들 때 Docker 빌드, Claude API 및 비서의 자연어 답변은 시험하지 않았습니다.** [Compose 설정](../poc/donghyun/docker-compose.yml)의 원래 명령은 `poc/donghyun`에서 `docker compose up --build`이며, 기본 게시가 `6110:8000`이라 외부 인터페이스에도 열릴 수 있습니다. 아래는 같은 [Dockerfile](../poc/donghyun/Dockerfile)을 **로컬에만 바인딩**하는 대안입니다. Docker 엔진·Git이 필요하며 최초 빌드 때 베이스 이미지와 의존성을 내려받습니다.

```bash
# 저장소 루트. 추적된 빌드 입력만 보내고 개인 설정 파일은 포함하지 않습니다.
git archive --format=tar HEAD:poc/donghyun Dockerfile requirements.txt app | docker build -t gabangssok-local -
# 실제판을 선택하고 본인이 환경변수로 키를 준비한 경우에만 실행합니다.
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  docker run --rm -it -p 127.0.0.1:6110:8000 --tmpfs /data \
    -e TZ=Asia/Seoul -e ANTHROPIC_API_KEY -e CLAUDE_MODEL gabangssok-local
else
  printf '%s\n' '키 없는 심사는 2절 예시 서버를 사용하세요.'
fi
```

**화면으로 체험하려면** 서버를 켠 뒤 브라우저에서 `http://127.0.0.1:6110/`를 열고 1절의 박물관 통신문을 넣으세요. 등교 전에는 준비된 그림 대신 개인정보 없는 실제 물건 사진을 사용합니다. MCP를 보려면 아래의 같은 일정 번호로 확인하세요.

다른 터미널에서 `curl -fsS http://127.0.0.1:6110/healthz`의 기대값은 `{"ok":true}`. `GET /api/plus/mode`는 실제판이면 `demo:false`이며, `ai:true`는 **키가 설정됐다는 뜻**이지 결제·모델 접근·호출 성공 증거는 아닙니다. `--tmpfs /data`는 시험 컨테이너를 끄면 데이터가 사라집니다. 기본 Compose는 대신 `./data`를 `/data`에 연결해 SQLite를 유지합니다.

- **일정 등록·비서 조회:** 실제 `POST /api/notice/commit`은 앱 내부 MCP `add_event`로 저장합니다(기대 `via:"mcp:add_event"`). URL은 호스트에서 `http://127.0.0.1:6110/mcp/`, 컨테이너 내부 기본값은 `http://127.0.0.1:8000/mcp/`입니다. 실제판에는 `add_event`·`list_events`·`get_checklist`·`check_item`·`delete_event`와 규칙 도구 3개가 있습니다. 키 없는 `read_notice`는 실제판에서도 **규칙** 도구입니다. 비서는 예시판 주소 대신 `6110/mcp/`를 등록하세요. [HTTP API](../poc/donghyun/app/main.py) · [캘린더 MCP](../poc/donghyun/app/calendar_mcp.py) · [규칙 MCP](../poc/donghyun/app/chaeng/mcp_tools.py)
- **실제 글·사진 분석:** 본인이 Anthropic 전송·비용을 허용할 때만 서버 프로세스에 `ANTHROPIC_API_KEY`를 주입합니다. 위 `docker run`은 키 값을 명령에 쓰지 않고 이미 준비된 환경변수를 컨테이너에 전달합니다. 서버는 `extract.py`를 불러올 때 SDK 클라이언트를 생성하므로, 키 없이 본체가 뜬다고 전제하지 마세요. `CLAUDE_MODEL`로 계정이 지원하는 모델을 지정할 수 있습니다(코드 기본 `claude-opus-5-5`). 키를 통신문·브라우저·Git·채팅에 붙이지 마세요. 실제판의 `/api/notice/extract`는 키가 없어도 규칙으로 자동 대체되지 않습니다. [추출 코드](../poc/donghyun/app/extract.py) · [사진 분석 코드](../poc/donghyun/app/chaeng/vision.py)
- **요청 형식:** 2절의 `--form-string "text=$TEXT"`는 실제판에서도 같은 multipart 형식이지만, `BASE`를 `6110`으로 바꾸어 추출하면 **Claude API 호출**입니다. 사진 분석은 실제판에 등록한 일정의 `$P`로 `curl -F 'image=@objects.jpg;type=image/jpeg' "$P/photo-check"`입니다. `objects.jpg`는 본인 확인을 마친 물건 사진이어야 합니다. 코드상 성공 응답은 `mode:"ai"`, `seen`·`not_seen`(항목 ID), `forbidden_seen`, `people_or_names`입니다. 모델 응답이어서 위 예시 사진의 값과 일치할 이유가 없습니다. [추가 API·제한](../poc/donghyun/app/chaeng/router.py)
- **개인정보:** 실제 추출은 통신문 글·사진, 사진 확인은 물건 목록·사진을 Anthropic으로 보냅니다. 얼굴·이름표·학교·연락처를 제외하세요. 앱 DB에는 일정·준비물·근거 줄·체크·알림 등이 남습니다. 앱이 사진 원본을 저장하지 않는 것과 외부 서비스에 전송하지 않는 것은 다릅니다. 날씨를 켜면 위치 좌표가 예보 서비스로, 외부 달력 링크를 열면 일정 정보가 해당 서비스로 갑니다. [저장·집계 코드](../poc/donghyun/app/chaeng/service.py)

**막히면:** `/mcp/`를 주소창에서 여는 GET 대신 3절의 POST를 쓰세요. 예시판에서 401이면 별도로 설정된 `MCP_ACCESS_TOKEN`이 필요한 인스턴스입니다. 토큰을 공유하지 말고 2절의 격리 서버로 돌아가세요. 404나 도구 `isError:true`면 현재 서버의 `list_events`에서 번호를 다시 찾습니다. 사진 413(8MB 초과)·429(하루 횟수 제한)·502(모델 실패)면 `사진 없이 하나씩 할래`로 전환하세요. 날씨가 없으면 통신문을 기준으로 진행하고 `시연용 가정`을 실예보로 해석하지 마세요.

**검증 범위:** 2026-11-22, `127.0.0.1` 전용 예시 서버·새 SQLite·예보 없는 조건에서 통신문 1건으로 HTTP 요청, MCP 도구 4개, 등교·귀가 보고와 스티커를 확인했습니다. 유료 호출·실물 사진 인식 정확도·실제 가족 사용성을 검증한 것이 아닙니다. 화면 안내는 [부모](../poc/donghyun/app/static/plus.js)·[아이](../poc/donghyun/app/static/kid.js) 코드 기준입니다. 닫힌 브라우저로 보내는 원격 푸시, 로그인·가족 공유, 수납 사진으로 물건 찾기, 두고 온 물건의 다음 날 자동 이월은 이 하루 경로의 구현에 포함되지 않습니다.
