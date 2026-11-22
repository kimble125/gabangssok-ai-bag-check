"""챙겼지 추가 기능 시험. 실행: poc/donghyun 에서  python3 -m unittest discover -s tests -v
모델 호출과 네트워크가 없다. 알림장은 전부 지어낸 것이다(실제 학교 문서 아님).
"""
import urllib.parse
import os
import tempfile
import unittest

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="chaeng-test-"), "app.db")

from app import db  # noqa: E402
from datetime import date as Date  # noqa: E402

from app.chaeng import guard, recommend, service, simple_extract, tone  # noqa: E402

NOTICE_A = """2학년 가을 현장체험학습 안내
1. 일시 : 11월 20일(금) 09:00–14:30
2. 장소 : ○○숲체험원
3. 준비물 : 도시락, 마실 물(플라스틱 물통), 개인용 돗자리, 모자, 간식, 물티슈, 개인 약품(멀미약 등 필요한 학생), 우천 시 우산 또는 우의 등
4. 유의 사항 : 유리병·탄산음료와 장난감, 귀중품은 가져오지 않습니다. 간편한 복장과 운동화를 착용합니다."""
ITEMS_A = ["도시락", "마실 물(플라스틱 물통)", "개인용 돗자리", "모자", "간식", "물티슈",
           "개인 약품(멀미약 등 필요한 학생)", "우천 시 우산 또는 우의"]
NOTICE_B = """4학년 현장체험학습(역사박물관) 안내
2. 준비물 : 필기도구(연필 2자루, 지우개), 체험학습 활동지, 물통, 작은 가방(백팩) 등
 ※ 체험비에 점심 식사 포함(도시락 지참하지 않음)
5. 교통카드는 필요 없습니다(전세버스 이용)."""
NOTICE_C = """[1학년 3반 알림장]
1. 내일은 가을 소풍입니다. 체육복 입고 오기
2. 준비물: 도시락, 물, 돗자리, 물티슈, 비닐봉지 2장
3. 과자는 한 봉지만! 탄산음료 X"""


def fresh_event(items, title="2학년 가을 현장체험학습", **kw):
    data = {"title": title, "kind": "event", "date": "2026-11-20", "outdoor": True} | kw
    return db.insert_event(data, [{"name": n, "source": "notice"} for n in items])


class GuardTest(unittest.TestCase):
    def test_forbidden_sentence(self):
        names = [f["name"] for f in guard.find_forbidden(NOTICE_A)]
        for n in ("유리병", "탄산음료", "장난감", "귀중품"):
            self.assertIn(n, names)
        self.assertNotIn("간편한 복장", names)

    def test_forbidden_marks(self):
        self.assertIn("탄산음료", [f["name"] for f in guard.find_forbidden(NOTICE_C)])
        self.assertIn("도시락", [f["name"] for f in guard.find_forbidden(NOTICE_B)])
        self.assertIn("교통카드", [f["name"] for f in guard.find_not_needed(NOTICE_B)])

    def test_allowed_sentence_is_not_forbidden(self):
        t = "우산은 가져오지 않아도 됩니다. 장난감은 가져오지 않습니다."
        self.assertEqual([f["name"] for f in guard.find_forbidden(t)], ["장난감"])
        self.assertEqual([f["name"] for f in guard.find_not_needed(t)], ["우산"])

    def test_ban_sentence_with_object_particle(self):
        self.assertEqual([f["name"] for f in guard.find_forbidden("장난감을 가져오면 안 됩니다.")], ["장난감"])
        self.assertEqual([f["name"] for f in guard.find_forbidden("유리병과 캔은 가지고 오면 안 돼요")], ["유리병", "캔"])
        self.assertEqual([f["name"] for f in guard.find_forbidden("휴대폰을 사용 금지")], ["휴대폰"])
        eid = fresh_event(["장난감", "도시락"])
        v = service.analyze(eid, "준비물: 장난감, 도시락\n장난감을 가져오면 안 됩니다.")
        self.assertEqual([f["name"] for f in v["plus"]["forbidden"]], ["장난감"])
        self.assertTrue(next(i for i in v["items"] if i["name"] == "장난감").get("conflict"))   # 통신문 준비물과 금지가 겹치면 보호자에게 알린다

    def test_limits_written_only_in_the_notice(self):
        self.assertEqual(guard.annotate("과자", "과자는 한 봉지만! 탄산음료 X")["quantity"], "한 봉지만")
        self.assertEqual(guard.annotate("우산", "우산은 필요한 학생만 준비하세요.")["conditional"], "needed")
        other = guard.annotate("도시락", "3. 준비물 : 도시락, 비닐봉지 2장\n과자는 한 봉지만")
        self.assertNotIn("quantity", other)                  # 같은 글의 다른 물건 수량을 끌어오지 않는다

    def test_nested_parentheses(self):
        self.assertEqual(guard.split_name("물통(플라스틱(500ml))"), ("물통", "플라스틱(500ml)"))
        self.assertEqual(guard.annotate("비닐봉지 2장")["base"], "비닐봉지")

    def test_forbidden_hidden_in_item_parentheses(self):
        r = guard.analyze("3. 준비물 : 도시락, 물, 비닐 봉투 ( 장난감 등 불가 )", ["도시락", "물", "비닐 봉투 ( 장난감 등 불가 )"])
        self.assertIn("장난감", [f["name"] for f in r["forbidden"]])
        self.assertNotIn("condition", r["items"]["비닐 봉투 ( 장난감 등 불가 )"])

    def test_condition_and_substitute(self):
        r = guard.analyze(NOTICE_A, ITEMS_A)
        water = r["items"]["마실 물(플라스틱 물통)"]
        self.assertEqual(water["condition"], "플라스틱 물통")
        self.assertIn("유리병", water["not_accepted"])
        self.assertIn("마실 물(플라스틱 물통)", water["evidence"])

    def test_substitute_only_for_drinks(self):
        r = guard.analyze(NOTICE_A, ITEMS_A)
        self.assertNotIn("not_accepted", r["items"]["물티슈"])
        self.assertTrue(guard.annotate("손수건(선택)")["optional_by_notice"])

    def test_conditional_and_alternatives(self):
        r = guard.analyze(NOTICE_A, ITEMS_A)
        self.assertEqual(r["items"]["개인 약품(멀미약 등 필요한 학생)"]["conditional"], "needed")
        rain = r["items"]["우천 시 우산 또는 우의"]
        self.assertEqual(rain["conditional"], "rain")
        self.assertEqual(rain["any_of"], ["우산", "우의"])

    def test_list_open(self):
        self.assertTrue(guard.list_open(NOTICE_A))
        self.assertTrue(guard.list_open(NOTICE_B))
        self.assertFalse(guard.list_open(NOTICE_C))

    def test_quantity_wear_and_bring_back(self):
        self.assertEqual(guard.annotate("비닐봉지 2장")["quantity"], "2장")
        self.assertEqual(guard.annotate("체육복 입고 오기")["kind"], "wear")
        self.assertEqual(guard.annotate("참가 신청서")["kind"], "submit")
        self.assertFalse(guard.annotate("간식")["bring_back"])
        self.assertTrue(guard.annotate("개인용 돗자리")["bring_back"])
        self.assertTrue(guard.annotate("물통")["bring_back"])


class RecommendTest(unittest.TestCase):
    def setUp(self):
        self.data = recommend.load()

    def ev(self, items, **kw):
        return {"title": "2학년 가을 현장체험학습", "outdoor": True, "items": [{"name": n, "source": "notice"} for n in items]} | kw

    def test_same(self):
        self.assertTrue(recommend.same("마실 물(플라스틱 물통)", "물"))
        self.assertTrue(recommend.same("우천 시 우산 또는 우의", "우산 또는 우비"))
        self.assertFalse(recommend.same("모자", "돗자리"))
        self.assertFalse(recommend.same("안경", "안경집"))               # 품는다고 같은 물건이 아니다
        self.assertFalse(recommend.same("실내화", "실내화가방"))
        self.assertTrue(recommend.same("개인 물통", "물"))
        self.assertTrue(recommend.same("비닐봉지 2장", "비닐봉지"))
        self.assertTrue(recommend.is_medicine("개인 약품(멀미약 등 필요한 학생)"))
        self.assertFalse(recommend.is_medicine("세면도구(칫솔·치약·비누)"))

    def test_scenario_fills_only_missing(self):
        r = recommend.recommend(self.ev(["도시락", "마실 물(플라스틱 물통)", "모자"]), data=self.data)
        names = [x["name"] for x in r["recs"]]
        self.assertEqual(r["scenario"]["id"], "field_trip_outdoor")
        self.assertIn("돗자리", names)
        self.assertNotIn("도시락", names)
        self.assertNotIn("물", names)
        self.assertNotIn("모자", names)

    def test_weather_flags(self):
        w = {"status": "ok", "rain_prob": 70, "rain_mm": 3, "pm10_grade": "나쁨", "pm25_grade": "보통", "t_max": 12, "t_min": 3}
        r = recommend.recommend(self.ev(["도시락"], weather=w), data=self.data)
        self.assertTrue({"rain", "dust_bad", "cold"} <= set(r["flags"]))
        names = [x["name"] for x in r["recs"]]
        self.assertIn("우산 또는 우비", names)
        self.assertIn("마스크", names)

    def test_no_duplicate_with_weather_items(self):
        ev = self.ev(["도시락"], weather={"status": "ok", "rain_prob": 80, "rain_mm": 5})
        ev["items"].append({"name": "우산", "source": "weather"})
        self.assertNotIn("우산 또는 우비", [x["name"] for x in recommend.recommend(ev, data=self.data)["recs"]])

    def test_personal_and_guardian(self):
        prof = {"traits": ["motion_sickness", "glasses"], "always": ["지갑"]}
        r = recommend.recommend(self.ev(["도시락"]), prof, data=self.data)
        by = {x["name"]: x for x in r["recs"]}
        self.assertTrue(by["멀미약"]["guardian_decides"])
        self.assertTrue(by["개인 상비약"]["guardian_decides"])       # 기본 준비물 속의 약도 보호자 몫
        self.assertEqual(by["지갑"]["group"], "tag")
        self.assertIn("안경집", by)

    def test_declined_and_watch(self):
        r = recommend.recommend(self.ev(["도시락", "물티슈"]), forgot={"물티슈": 2}, declined=["돗자리"], data=self.data)
        self.assertNotIn("돗자리", [x["name"] for x in r["recs"]])
        self.assertEqual(r["watch"], ["물티슈"])

    def test_specific_scenario_beats_generic(self):
        ev = {"title": "4학년 현장체험학습(역사박물관)", "items": [{"name": "물통", "source": "notice"}]}
        r = recommend.recommend(ev, data=self.data, exclude=["도시락"])
        self.assertEqual(r["scenario"]["id"], "indoor_museum_show")
        self.assertNotIn("도시락", [x["name"] for x in r["recs"]])

    def test_fields_are_not_glued(self):
        ev = {"title": "2학년 가을 현장체험학습", "notes": "준비물 : 도시락", "items": []}
        self.assertEqual(recommend.recommend(ev, data=self.data)["scenario"]["id"], "field_trip_outdoor")

    def test_no_scenario(self):
        r = recommend.recommend({"title": "학부모 상담 주간 안내", "items": []}, data=self.data)
        self.assertIsNone(r["scenario"])
        self.assertEqual(r["recs"], [])

    def test_data_shape(self):
        ids = [s["id"] for s in self.data["scenarios"]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in self.data["scenarios"]:
            self.assertTrue(s["match"] and s["defaults"], s["id"])
        for c in self.data["conditional"]:
            self.assertIn(c["when"], {"rain", "dust_bad", "hot", "cold", "wet_activity", "bus"})


class ServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init()
        service.init()

    def setUp(self):
        service.set_profile({"name": "", "traits": [], "always": [], "tone": "basic"})

    def test_analyze_view_and_summary(self):
        eid = fresh_event(ITEMS_A)
        v = service.analyze(eid, NOTICE_A)
        p = v["plus"]
        self.assertTrue(p["list_open"])
        self.assertEqual([f["name"] for f in p["forbidden"]], ["유리병", "탄산음료", "장난감", "귀중품"])
        self.assertFalse(p["summary"]["all_packed"])
        self.assertEqual(p["summary"]["counted"], len(ITEMS_A) - 2)   # 약(필요한 학생만)과 우천 시 준비물은 세지 않는다
        self.assertTrue(next(i for i in v["items"] if "약품" in i["name"])["guardian"])
        for it in v["items"]:
            db.set_item_checked(it["id"], True)
        s = service.view(eid)["plus"]["summary"]
        self.assertTrue(s["all_packed"])
        self.assertEqual(s["open_alerts"], [])              # 금지 목록은 알려 주기만 한다. 사진에 보인 것만 막는다

    def test_optional_items_do_not_block(self):
        eid = fresh_event(["도시락"])
        db.add_item(eid, "우산", source="weather", reason="비 80%")
        v = service.view(eid)
        db.set_item_checked(v["items"][0]["id"], True)
        s = service.view(eid)["plus"]["summary"]
        self.assertTrue(s["all_packed"])
        self.assertEqual(s["optional_left"], ["우산"])

    def test_forbidden_is_never_recommended(self):
        eid = fresh_event(["물통", "필기도구"], title="4학년 현장체험학습(역사박물관)", outdoor=False)
        v = service.analyze(eid, NOTICE_B)
        self.assertIn("도시락", [f["name"] for f in v["plus"]["forbidden"]])
        self.assertNotIn("도시락", [r["name"] for r in v["plus"]["recs"]])

    def test_empty_list_is_not_done(self):
        eid = fresh_event([])
        self.assertFalse(service.view(eid)["plus"]["summary"]["all_packed"])

    def test_accept_and_decline_rec(self):
        eid = fresh_event(["도시락", "물"])
        recs = [r["name"] for r in service.view(eid)["plus"]["recs"]]
        self.assertIn("돗자리", recs)
        v = service.accept_rec(eid, "돗자리")
        added = next(i for i in v["items"] if i["name"] == "돗자리")
        self.assertEqual(added["source"], "recommend")
        self.assertFalse(added["optional"])
        self.assertNotIn("돗자리", [r["name"] for r in v["plus"]["recs"]])
        v = service.decline_rec(eid, "간식")
        self.assertNotIn("간식", [r["name"] for r in v["plus"]["recs"]])

    def test_guardian_recs_are_separate(self):
        service.set_profile({"traits": ["motion_sickness"]})
        eid = fresh_event(["도시락"])
        p = service.view(eid)["plus"]
        self.assertNotIn("멀미약", [r["name"] for r in p["recs"]])
        self.assertIn("멀미약", [r["name"] for r in p["guardian_recs"]])

    def test_accepted_medicine_stays_with_guardian(self):
        service.set_profile({"traits": ["motion_sickness"]})
        eid = fresh_event(["도시락"])
        v = service.accept_rec(eid, "멀미약")
        med = next(i for i in v["items"] if i["name"] == "멀미약")
        self.assertTrue(med["guardian"] and med["optional"])     # 받아들여도 아이 미션에는 안 나온다
        eid2 = fresh_event(["도시락", "멀미약"])
        self.assertTrue(next(i for i in service.view(eid2)["items"] if i["name"] == "멀미약")["guardian"])

    def test_auto_items_that_clash_with_a_ban_are_hidden(self):
        eid = fresh_event(["우비"])
        service.analyze(eid, "우산은 가져오지 않습니다. 우비를 입고 오세요.")
        db.replace_weather(eid, {"status": "ok", "rain_prob": 80, "rain_mm": 6, "weather": "비"},
                           [{"name": "우산", "reason": "비 80%"}], "2026-11-19 21:00")
        v = service.view(eid)
        umbrella = next(i for i in v["items"] if i["name"] == "우산")
        self.assertTrue(umbrella["blocked"])
        self.assertEqual(v["plus"]["summary"]["optional"], 0)
        self.assertNotIn("우산 또는 우비", [r["name"] for r in v["plus"]["recs"]])

    def test_finish_needs_flagged_ban_removed(self):
        eid = fresh_event(["도시락"])
        service.analyze(eid, "장난감은 가져오지 않습니다.")
        db.set_item_checked(service.view(eid)["items"][0]["id"], True)
        service.flag_forbidden(eid, ["장난감"])
        s = service.view(eid)["plus"]["summary"]
        self.assertTrue(s["all_packed"])
        self.assertFalse(s["can_finish"])
        self.assertTrue(service.alert_removed(eid, "장난감")["plus"]["summary"]["can_finish"])

    def test_analyze_without_text_is_not_marked_done(self):
        eid = fresh_event(["도시락"])
        self.assertFalse(service.analyze(eid, "")["plus"]["analyzed"])
        self.assertTrue(service.analyze(eid, "준비물: 도시락")["plus"]["analyzed"])

    def test_delete_event_sweeps_plus_tables(self):
        eid = fresh_event(ITEMS_A)
        service.analyze(eid, NOTICE_A)
        service.give_sticker(eid, "⭐")
        db.delete_event(eid)
        service.sweep(eid)
        with db.tx() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) c FROM plus_event WHERE event_id=?", (eid,)).fetchone()["c"], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) c FROM plus_sticker WHERE event_id=?", (eid,)).fetchone()["c"], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) c FROM plus_item WHERE item_id NOT IN (SELECT id FROM items)").fetchone()["c"], 0)

    def test_weather_refresh_keeps_item_ids(self):
        eid = fresh_event(["도시락"])
        w = {"status": "ok", "rain_prob": 80, "rain_mm": 6, "weather": "비"}
        db.replace_weather(eid, w, [{"name": "우산", "reason": "a"}], "2026-11-19 21:00")
        first = next(i for i in db.get_event(eid)["items"] if i["name"] == "우산")
        db.set_item_checked(first["id"], True)
        db.replace_weather(eid, w, [{"name": "우산", "reason": "b"}, {"name": "장갑", "reason": "c"}], "2026-11-19 22:00")
        again = next(i for i in db.get_event(eid)["items"] if i["name"] == "우산")
        self.assertEqual((again["id"], again["checked"], again["reason"]), (first["id"], True, "b"))

    def test_skip_this_time_is_not_a_ban(self):
        eid = fresh_event(["도시락", "물통"])
        service.analyze(eid, "준비물: 도시락, 물통")
        v = service.view(eid)
        bottle = next(i for i in v["items"] if i["name"] == "물통")
        db.set_item_checked(bottle["id"], True)
        v = service.set_skipped(eid, bottle["id"], True)
        b2 = next(i for i in v["items"] if i["name"] == "물통")
        self.assertTrue(b2["skipped"] and b2["optional"] and not b2["checked"])
        self.assertEqual((v["plus"]["summary"]["counted"], v["plus"]["summary"]["skipped"], v["plus"]["forbidden"]), (1, ["물통"], []))
        db.set_item_checked(next(i for i in v["items"] if i["name"] == "도시락")["id"], True)
        self.assertTrue(service.view(eid)["plus"]["summary"]["can_finish"])          # 뺀 것은 끝을 막지 않는다
        v = service.set_skipped(eid, bottle["id"], False)
        self.assertEqual(v["plus"]["summary"]["counted"], 2)                        # 다시 챙기기
        self.assertIsNone(service.set_skipped(eid, 999999, True))

    def test_alert_removed(self):
        eid = fresh_event(ITEMS_A)
        service.analyze(eid, NOTICE_A)
        service.flag_forbidden(eid, ["유리병"])
        self.assertEqual(service.view(eid)["plus"]["summary"]["open_alerts"], ["유리병"])   # 사진에 보였으면 뺄 때까지 남는다
        v = service.alert_removed(eid, "유리병")
        self.assertEqual(v["plus"]["summary"]["open_alerts"], [])
        self.assertTrue(next(f for f in v["plus"]["forbidden"] if f["name"] == "유리병")["removed"])

    def test_kid_report_counts_and_forgot(self):
        eid = fresh_event(["도시락", "물티슈"])
        v = service.view(eid)
        db.set_item_checked(v["items"][0]["id"], True)
        r = service.kid_report(eid)
        self.assertIn("넣음 1", r["body"])
        self.assertIn("물티슈", r["body"])
        service.kid_report(eid)                               # 같은 일정을 다시 보내도 한 번만 센다
        self.assertEqual(service._kv_get("forgot", {}).get("물티슈"), 1)
        eid2 = fresh_event(["도시락", "물티슈"])
        self.assertEqual(service.view(eid2)["plus"]["watch"], ["물티슈"])

    def test_stickers(self):
        eid = fresh_event(["도시락"])
        self.assertIsNone(service.give_sticker(eid, "❌"))
        r = service.give_sticker(eid, "⭐", "스스로 챙겨서 멋져")
        self.assertEqual(r["stickers"][0]["sticker"], "⭐")
        self.assertGreaterEqual(len(service.stickers()), 1)

    def test_return_check_skips_consumed(self):
        eid = fresh_event(["도시락", "간식", "개인용 돗자리", "물통", "참가 신청서"])
        for it in service.view(eid)["items"]:
            db.set_item_checked(it["id"], True)
        r = service.return_view(eid)
        names = [i["name"] for i in r["items"]]
        self.assertEqual(names, ["개인용 돗자리", "물통"])
        self.assertIsNone(service.set_returned(eid, 999999, True))     # 이 일정의 물건이 아니면 받지 않는다
        eid_w = fresh_event(["도시락통", "운동화"])
        for i in service.view(eid_w)["items"]:
            db.set_item_checked(i["id"], True)
        self.assertEqual([i["name"] for i in service.return_view(eid_w)["items"]], ["도시락통"])   # 입고 간 것은 묻지 않는다
        r = service.set_returned(eid, r["items"][0]["id"], True)
        self.assertEqual(r["summary"]["left"], ["물통"])
        self.assertIn("아직 1", service.return_report(eid)["body"])

    def test_quick_event(self):
        eid = service.quick_event("swim_academy", "2026-11-21")
        v = service.view(eid)
        self.assertTrue(all(i["source"] == "recommend" for i in v["items"]))
        self.assertIn("수영복", [i["name"] for i in v["items"]])
        self.assertIsNone(service.quick_event("no_such", "2026-11-21"))
        self.assertEqual(db.get_event(service.quick_event("swim_academy", "2026-1-2"))["date"], "2026-01-02")
        with self.assertRaises(ValueError):
            service.quick_event("swim_academy", "2026-02-31")

    def test_rain_item_counts_only_when_rain(self):
        eid = fresh_event(["도시락", "우천 시 우산 또는 우의"])
        service.analyze(eid, NOTICE_A)
        self.assertEqual(service.view(eid)["plus"]["summary"]["counted"], 1)
        db.replace_weather(eid, {"status": "ok", "rain_prob": 80, "rain_mm": 6, "weather": "비"}, [], "2026-11-19 21:00")
        self.assertEqual(service.view(eid)["plus"]["summary"]["counted"], 2)

    def test_subject_particle(self):
        self.assertEqual(tone.subject("하늘"), "하늘이가")
        self.assertEqual(tone.subject("지우"), "지우가")
        self.assertEqual(tone.subject(""), "아이가")

    def test_tone_previews(self):
        eid = fresh_event(ITEMS_A)
        service.analyze(eid, NOTICE_A)
        t = service.tone_previews(eid)
        self.assertEqual(set(t), set(tone.TONES))
        self.assertIn("유리병", t["neat"]["body"])
        self.assertIn("🙅", t["cute"]["body"])


class SimpleExtractTest(unittest.TestCase):
    TODAY = Date(2026, 11, 19)

    def test_samples(self):
        for key, n_items in (("a", 10), ("b", 6), ("c", 6)):
            s = simple_extract.sample(key, self.TODAY)
            ev = simple_extract.extract(s["text"], s["title"], s["posted"], self.TODAY)["events"][0]
            self.assertEqual((ev["date"], len(ev["items"])), ("2026-11-20", n_items), key)
        self.assertEqual(simple_extract.extract("", today=self.TODAY)["events"], [])

    def test_written_year_and_bad_dates(self):
        ex = simple_extract.extract("체험학습\n일시: 2025년 11월 20일", today=self.TODAY)
        self.assertEqual(ex["events"][0]["date"], "2025-11-20")
        ex = simple_extract.extract("체험학습\n일시: 2월 29일", today=Date(2027, 12, 30))
        self.assertEqual(ex["events"][0]["date"], "2028-02-29")
        ex = simple_extract.extract("체험학습\n일시: 2월 30일", today=self.TODAY)
        self.assertIn("확인해 주세요", ex["events"][0]["notes"])
        ex = simple_extract.extract("체험학습\n일시: 1월 8일", today=Date(2026, 12, 28))
        self.assertEqual(ex["events"][0]["date"], "2027-01-08")

    def test_worn_things_and_relative_deadline(self):
        a = simple_extract.sample("a", self.TODAY)
        ev = simple_extract.extract(a["text"], a["title"], a["posted"], self.TODAY)["events"][0]
        self.assertIn("간편한 복장", ev["items"])                 # 입고 가는 것도 챙길 것에 넣는다
        self.assertIn("운동화", ev["items"])
        self.assertEqual(guard.annotate("운동화")["kind"], "wear")
        ex = simple_extract.extract("체험학습 안내\n일시: 11월 20일\n준비물: 물\n슬리퍼는 신고 오지 않습니다. 실내화를 신고 옵니다.", today=self.TODAY)
        self.assertEqual(ex["events"][0]["items"], ["물", "실내화"])
        c = simple_extract.sample("c", self.TODAY)
        evs = simple_extract.extract(c["text"], c["title"], c["posted"], self.TODAY)["events"]
        self.assertEqual([(e["kind"], e["date"], e["items"][:1]) for e in evs][1], ("deadline", "2026-11-20", ["회신서"]))

    def test_split_items_keeps_parentheses(self):
        self.assertEqual(simple_extract.split_items("필기도구(연필 2자루, 지우개), 물통 등"), ["필기도구(연필 2자루, 지우개)", "물통"])


class DemoDispatchTest(unittest.TestCase):
    """예시 서버의 주소표를 소켓 없이 부른다(브라우저 안에서 도는 판이 쓰는 길)."""

    @classmethod
    def setUpClass(cls):
        import demo_server
        cls.d = demo_server

        def no_network(url, params):
            raise OSError("시험에서는 네트워크를 쓰지 않는다")
        demo_server._get_json = no_network
        demo_server.boot()

    def call(self, method, path, **kw):
        return self.d.dispatch(method, path, **kw)

    def test_notice_to_calendar_to_kid_to_parent(self):
        code, s = self.call("POST", "/api/notice/fetch", json_body={"url": "sample:b"})
        self.assertEqual(code, 200)
        code, ex = self.call("POST", "/api/notice/extract", fields={"text": s["text"], "title": s["title"]})
        self.assertEqual((code, len(ex["events"])), (200, 1))
        code, c = self.call("POST", "/api/notice/commit", json_body={"events": ex["events"], "source_title": s["title"]})
        eid = c["created"][0]["id"]
        code, v = self.call("POST", f"/api/plus/events/{eid}/analyze", json_body={"text": s["text"]})
        self.assertIn("도시락", [f["name"] for f in v["plus"]["forbidden"]])
        code, r = self.call("POST", f"/api/plus/events/{eid}/photo-check", query={"case": "miss"}, files=[("image", "image/jpeg", b"")])
        self.assertEqual((code, r["mode"]), (200, "example"))
        self.assertTrue(r["seen"] and r["not_seen"])
        for iid in r["seen"] + r["not_seen"]:
            self.assertEqual(self.call("PATCH", f"/api/items/{iid}", json_body={"checked": True})[0], 200)
        code, rep = self.call("POST", f"/api/plus/events/{eid}/kid-report")
        self.assertEqual((code, rep["summary"]["left"]), (200, []))
        code, st = self.call("POST", f"/api/plus/events/{eid}/stickers", json_body={"sticker": "⭐", "message": "잘했어"})
        self.assertEqual(code, 200)
        self.assertTrue(self.call("GET", "/api/plus/stickers")[1])
        code, back = self.call("GET", f"/api/plus/events/{eid}/return")
        self.assertEqual(code, 200)
        self.assertTrue(back["items"])

    def test_errors_are_statuses_not_exceptions(self):
        self.assertEqual(self.call("GET", "/api/plus/events/999999")[0], 404)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)
        self.assertEqual(self.call("GET", "/static/kid.js")[0], 404)          # 화면 파일은 이 길로 열지 않는다
        self.assertEqual(self.call("POST", "/api/notice/extract", fields={})[0], 400)
        self.assertEqual(self.call("POST", "/api/plus/quick-event", json_body={"scenario": "swim_academy", "date": "2026-02-31"})[0], 400)
        self.assertEqual(self.call("POST", "/api/plus/events/1/items/999999/skip", json_body={"skipped": True})[0], 404)
        self.assertEqual(self.call("POST", "/api/plus/events/1/return", json_body={})[0], 400)

    def test_photo_only_notice_uses_example_and_says_so(self):
        code, ex = self.call("POST", "/api/notice/extract", fields={}, files=[("images", "image/jpeg", b"")])
        self.assertEqual(code, 200)
        self.assertIn("예시", ex["note"])

    def test_skipped_item_is_left_out_of_photo_check(self):
        eid = self.call("POST", "/api/plus/quick-event", json_body={"scenario": "swim_academy", "date": "2026-12-05"})[1]["id"]
        v = self.call("GET", f"/api/plus/events/{eid}")[1]
        first = next(i for i in v["items"] if not i["optional"])
        self.assertEqual(self.call("POST", f"/api/plus/events/{eid}/items/{first['id']}/skip", json_body={"skipped": True})[0], 200)
        r = self.call("POST", f"/api/plus/events/{eid}/photo-check", query={"case": "all"}, files=[("image", "image/jpeg", b"")])[1]
        self.assertNotIn(first["id"], r["seen"] + r["not_seen"])

    def test_real_notice_lines(self):
        """팀이 읽은 실제 통신문의 문장(조사 파일 26)으로: 금지 머리말, '등' 뒤 괄호, 준비물 줄 앞의 꾸밈말."""
        from app.chaeng import guard, simple_extract
        ban = lambda t: [f["name"] for f in guard.find_forbidden(t)]
        pool = "5. 학생 준비물 : 수영복, 수영모자, 수영가방, 수건, 여분의 비닐 봉지, 등 (※ 입장제한: 래쉬가드, 아쿠아슈즈, 남성용 트렁크, 일반 티셔츠, , 스킨스쿠버 슈트, 수경 )"
        self.assertEqual(ban(pool), ["래쉬가드", "아쿠아슈즈", "남성용 트렁크", "일반 티셔츠", "스킨스쿠버 슈트", "수경"])
        self.assertTrue(guard.list_open(pool))
        got = ban("※ 휴대지참 금지 품목: 고액의 현금(간식 살 곳 없음), 고가의 물건, 게임기, 폭죽, 화투, 카드, 술, 껌, 라이터, 화기, 칼 등")
        self.assertEqual((len(got), "휴대" in got, {"게임기", "폭죽", "칼", "고액의 현금"} <= set(got)), (11, False, True))
        self.assertEqual(ban("식중독 사고 예방을 위해 외부음식 반입은 금지합니다."), ["외부음식"])
        self.assertEqual(ban("휴대폰은 가져가지 않고 학교에 둡니다."), ["휴대폰"])
        self.assertEqual(ban("준비물: 도시락, 물. 우산은 가져오지 않아도 됩니다."), [])
        items = lambda line: simple_extract.extract("3학년 안내\n일시: 2026년 12월 3일\n" + line)["events"][0]["items"]
        self.assertEqual(items(pool), ["수영복", "수영모자", "수영가방", "수건", "여분의 비닐 봉지"])
        self.assertEqual(items("※ 복장 및 준비물 : 활동하기 편한 옷, 운동화 착용, 개인 상비약, 생수 등"), ["활동하기 편한 옷", "운동화", "개인 상비약", "생수"])
        self.assertEqual(items("5. 개인 준비물: 방한용품, 여벌 옷, 두꺼운 양말, 세면도구 등"), ["방한용품", "여벌 옷", "두꺼운 양말", "세면도구"])
        self.assertEqual(items("4. 학생 준비물 수영복, 수영모, 수경"), ["수영복", "수영모", "수경"])
        v = self.call("GET", "/api/plus/events/1")[1]                         # 숲체험 예시: 입는 추천은 '입는 것'으로, 갯벌 신발은 안 나온다
        recs = {r["name"]: r["kind"] for r in v["plus"]["recs"]}
        self.assertEqual((recs.get("긴 옷"), any("샌들" in n for n in recs)), ("wear", False))
        eid = self.call("POST", "/api/plus/quick-event", json_body={"scenario": "pe_day", "date": "2026-12-05"})[1]["id"]
        kinds = {i["meta"].get("kind") for i in self.call("GET", f"/api/plus/events/{eid}")[1]["items"]}
        self.assertIn("wear", kinds)

    def test_calendar_out_link_and_file(self):
        t = self.call("GET", "/api/plus/events/1/tones")[1]
        self.assertEqual(sorted(t), ["basic", "cute", "neat"])
        day = self.call("GET", "/api/plus/events/1")[1]["date"].replace("-", "")
        g = urllib.parse.parse_qs(urllib.parse.urlparse(t["cute"]["google_url"]).query)
        self.assertEqual((g["action"], g["ctz"], g["text"]), (["TEMPLATE"], ["Asia/Seoul"], [t["cute"]["title"]]))
        self.assertEqual(g["dates"], [f"{day}T000000Z/{day}T053000Z"])                 # 09:00–14:30 한국 시간
        ics = t["basic"]["ics"]
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n"))
        self.assertIn(f"DTSTART:{day}T000000Z", ics)
        self.assertEqual((ics.count("BEGIN:VALARM"), "TRIGGER:-PT14H" in ics, "TRIGGER:-PT1H30M" in ics), (2, True, True))   # 전날 19:00, 당일 07:30
        self.assertTrue(all(len(l.encode("utf-8")) <= 75 for l in ics.split("\r\n")))
        self.assertIn("유리병", ics.replace("\r\n ", ""))                              # 금지 항목이 메모에 들어간다
        all_day = self.call("GET", "/api/plus/events/2/tones")[1]["basic"]             # 회신 마감: 시간이 없으면 하루 종일
        self.assertIn("DTSTART;VALUE=DATE:", all_day["ics"])
        self.assertIn("TRIGGER:-PT5H", all_day["ics"])

    def test_mcp_tools(self):
        from app.chaeng import mcp_tools
        rpc = lambda method, params=None, mid=1: mcp_tools.handle_rpc({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}})
        init = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})["result"]
        self.assertEqual((init["protocolVersion"], init["serverInfo"]["name"], "tools" in init["capabilities"]), ("2025-03-26", "gabangssok", True))
        self.assertIsNone(mcp_tools.handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        names = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
        self.assertEqual(names, ["list_events", "read_notice", "packing_plan", "calendar_entry"])
        call = lambda name, **a: rpc("tools/call", {"name": name, "arguments": a})["result"]
        text = "2학년 현장체험학습 안내\n일시: 2026년 12월 3일(목) 9:00~14:00\n준비물: 도시락, 물(플라스틱 물통), 개인 약(필요한 학생) 등\n※ 장난감을 가져오면 안 됩니다."
        r = call("read_notice", text=text)["structuredContent"]
        self.assertEqual((r["events"][0]["date"], r["list_ends_with_etc"], [f["name"] for f in r["forbidden"]]), ("2026-12-03", True, ["장난감"]))
        items = {i["name"]: i for i in r["events"][0]["items"]}
        self.assertEqual((items["물"]["condition"], items["개인 약"].get("parent_decides")), ("플라스틱 물통", True))
        p = call("packing_plan", event_id=1)["structuredContent"]
        self.assertEqual((p["summary"]["count"], len(p["to_pack"]), [f["name"] for f in p["forbidden"]][:1]), (8, 8, ["유리병"]))
        self.assertTrue(any("약" in i["name"] for i in p["parent_decides"]) and all("약" not in i["name"] for i in p["to_pack"]))
        c = call("calendar_entry", event_id=1, tone="neat")["structuredContent"]
        self.assertTrue(c["title"].startswith("[준비물 8]") and c["google_url"].startswith("https://calendar.google.com/") and len(c["reminders"]) == 2)
        self.assertTrue(call("packing_plan", event_id=999999)["isError"])
        self.assertEqual(rpc("tools/call", {"name": "nope"})["error"]["code"], -32602)
        self.assertEqual(rpc("x/y")["error"]["code"], -32601)

    def test_reset_returns_to_seed(self):
        self.d.boot(reset=True)
        seeded = [e["title"] for e in self.call("GET", "/api/events")[1]]
        self.assertGreaterEqual(len(seeded), 2)
        self.call("POST", "/api/plus/quick-event", json_body={"scenario": "swim_academy", "date": "2026-12-01"})
        self.assertEqual(len(self.call("GET", "/api/events")[1]), len(seeded) + 1)
        self.d.boot(reset=True)
        self.assertEqual([e["title"] for e in self.call("GET", "/api/events")[1]], seeded)


class RealNoticeSentenceTest(unittest.TestCase):
    """실제 초등학교 통신문 문장(scenarios.json sources에서 그대로 옮김)으로 2026-11-22 실측에서 놓친 것을 다시 본다."""

    def forb(self, text):
        return [f["name"] for f in guard.find_forbidden(text)]

    def items(self, text):
        return simple_extract.extract("안내\n" + text)["events"][0]["items"]

    def test_valuables_not_brought_to_school(self):      # 9 안양 민백초
        t = "◦ 수영 실기교육 하는 날에는 분실 등의 문제로 휴대전화, 귀걸이, 목걸이, 시계, 용돈 등의 귀중품을 가지고 등교하지 않도록 합니다."
        names = self.forb(t)
        for n in ("휴대전화", "귀걸이", "목걸이", "시계", "용돈"):
            self.assertIn(n, names)
        self.assertNotIn("분실", " ".join(names))

    def test_not_worn(self):                               # 12 고양 신능초
        t = "◦ 개인 귀중품은 수영장으로 가져오지 않도록 하며 개인 물건을 잘 관리합니다. 특히 시계, 귀걸이, 목걸이는 착용하지 않습니다."
        self.assertEqual(self.forb(t), ["개인 귀중품", "시계", "귀걸이", "목걸이"])

    def test_wash_note_and_advice_are_not_forbidden(self):  # 18 청주 내수초, 2 김포 통진초
        self.assertEqual(self.forb("양말, 속옷(여벌, 세탁 불가), 개인용 물병 또는 텀블러"), [])
        t = "5. 준비물 : 간편한 복장, 운동화, 음료수와 물만 준비 (※ 이동차량 내 취식 자제/ 체험시설 내 외부 음식 반입 불가)"
        self.assertEqual(self.forb(t), ["외부 음식"])

    def test_ban_paren_leaves_item_name(self):             # 1 성남 금빛초
        t = "3. 준비물: 개인 도시락, 간식, 물, 음료수, 멀미약, 비닐 봉투 (장난감 등 불가)"
        items = self.items(t)
        self.assertEqual(items[-1], "비닐 봉투")
        self.assertIn("장난감", self.forb(t))
        self.assertIn("장난감", [f["name"] for f in guard.analyze(t, items)["forbidden"]])

    def test_note_after_mark_is_cut(self):                 # 11 부천 원종초, 13 대전오류초, 12 고양 신능초
        self.assertEqual(self.items("2. 학생 준비물: 수영복(실내용 권장), 수영모자, 수경, 수영복 담을 가방, 수건 등 (구명조끼는 준비하지 않음)")[-1], "수건")
        t = "5. 준비물: 실내 수영복, 수영모, 수경, 수건, 수영가방, 비닐봉지(지퍼백), 간편 복장 등 ※실내 수영장에서 입는 실내 수영복으로 준비 (반팔, 반바지 착용 안 됨)"
        self.assertEqual(self.items(t)[-2:], ["비닐봉지(지퍼백)", "간편 복장"])
        self.assertEqual(self.forb(t), ["반팔", "반바지"])
        t = "4. 학생 준비물 수영복, 수영모자, 물안경, 수영가방, 수건, 여분 봉지, 샤워 도구(선택) 등 * 모든 물건에 자기 이름 쓰기"
        self.assertEqual(self.items(t)[-1], "샤워 도구(선택)")

    def test_condition_paren_stays(self):                  # 조건 괄호는 이름에 남아 annotate가 읽는다
        items = self.items(NOTICE_A.split("\n")[3])
        self.assertIn("마실 물(플라스틱 물통)", items)
        self.assertIn("개인 약품(멀미약 등 필요한 학생)", items)
        self.assertEqual(guard.annotate("마실 물(플라스틱 물통)")["condition"], "플라스틱 물통")
        self.assertEqual(guard.annotate("개인 약품(멀미약 등 필요한 학생)")["conditional"], "needed")

    def test_grade_lists_are_left_alone(self):             # 21 과천초: 머리말 없는 학년별 목록은 아직 읽지 않는다(지어내지 않음)
        t = "(가정에서 직접 구매가 필요한 개인 학습준비물) 1학년: 풀, 가위, 색연필, 사인펜, 필기도구(연필, 지우개), 네임펜"
        self.assertEqual(self.items(t), [])


if __name__ == "__main__":
    unittest.main()
