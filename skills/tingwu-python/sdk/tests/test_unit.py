"""离线单元测试（不访问网络）。

运行： ``pytest tests/ -v``
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tingwu import (  # noqa: E402
    APIError,
    AuthError,
    HTTPError,
    PasswordLogin,
    Ticket,
    TingwuClient,
    extract_ticket_from_cookie_string,
    parse_transcript,
)
from tingwu.endpoints import ACTION_MODULE, endpoint_for_action  # noqa: E402

# --------------------------------------------------------------------------
# ticket 解析
# --------------------------------------------------------------------------


class TestTicketParsing:
    def test_full_cookie_header(self):
        raw = "Cookie: a=1; login_aliyunid_ticket=_wkpof_ABC123; b=2"
        assert extract_ticket_from_cookie_string(raw) == "_wkpof_ABC123"

    def test_plain_cookie_string(self):
        raw = "sca=x; login_aliyunid_ticket=_wkpof_XYZ; cna=y"
        assert extract_ticket_from_cookie_string(raw) == "_wkpof_XYZ"

    def test_bare_value(self):
        v = "_wkpof_" + "A" * 60
        assert extract_ticket_from_cookie_string(v) == v

    def test_missing_returns_none(self):
        assert extract_ticket_from_cookie_string("a=1; b=2") is None
        assert extract_ticket_from_cookie_string("") is None
        assert extract_ticket_from_cookie_string("short") is None

    def test_value_with_special_chars(self):
        # 真实 ticket 含 * $ . 等
        v = "_wkpof_AB*cd$ef.gh" + "X" * 40
        assert extract_ticket_from_cookie_string(f"login_aliyunid_ticket={v}") == v


class TestTicketObject:
    def test_cookie_header(self):
        t = Ticket(value="abc")
        assert t.cookie_header() == "login_aliyunid_ticket=abc"

    def test_extra_cookies(self):
        t = Ticket(value="abc", extra_cookies={"cna": "xyz"})
        assert "login_aliyunid_ticket=abc" in t.cookie_header()
        assert "cna=xyz" in t.cookie_header()

    def test_roundtrip_dict(self):
        t = Ticket(value="abc", obtained_at=123.0, source="cdp")
        t2 = Ticket.from_dict(t.to_dict())
        assert t2.value == t.value
        assert t2.obtained_at == t.obtained_at
        assert t2.source == t.source

    def test_save_load(self, tmp_path):
        p = tmp_path / "t.json"
        Ticket(value="abc", source="test").save(p)
        got = Ticket.load(p)
        assert got is not None and got.value == "abc"

    def test_load_missing(self, tmp_path):
        assert Ticket.load(tmp_path / "nope.json") is None

    def test_load_corrupt(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        assert Ticket.load(p) is None

    def test_age_none_when_issue_time_unknown(self):
        """从 cookie/CDP 拿到的 ticket 不知道签发时刻，age 应为 None。"""
        t = Ticket(value="abc", source="cdp")
        assert t.issued_at is None
        assert t.age is None
        # 三态：无法判断，而不是误报"有效"
        assert t.is_probably_valid is None

    def test_age_known_after_login(self):
        import time

        now = time.time()
        t = Ticket(value="abc", issued_at=now, obtained_at=now, source="login")
        assert t.age is not None and t.age < 5
        assert t.is_probably_valid is True

        old = Ticket(value="abc", issued_at=now - 999_999, source="login")
        assert old.is_probably_valid is False

    def test_since_obtained_is_not_age(self):
        """库持有的时长不等于 ticket 的真实寿命。"""
        import time

        t = Ticket(value="abc", source="cdp")  # issued_at 未知
        assert t.since_obtained < 5
        assert t.age is None  # 真实寿命未知

    def test_issued_at_roundtrip(self, tmp_path):
        import time

        p = tmp_path / "t.json"
        now = time.time()
        Ticket(value="abc", issued_at=now, source="login").save(p)
        got = Ticket.load(p)
        assert got is not None and got.issued_at is not None
        assert abs(got.issued_at - now) < 1


# --------------------------------------------------------------------------
# 客户端构造
# --------------------------------------------------------------------------


class TestClientConstruction:
    def test_from_cookie(self):
        c = TingwuClient.from_cookie("login_aliyunid_ticket=_wkpof_" + "A" * 50)
        assert c.ticket is not None
        assert c.ticket.value.startswith("_wkpof_")

    def test_from_ticket_object(self):
        c = TingwuClient(ticket=Ticket(value="xyz", source="t"))
        assert c.ticket.value == "xyz"

    def test_invalid_cookie_raises(self):
        with pytest.raises(ValueError):
            TingwuClient.from_cookie("nothing_useful=1")

    def test_no_ticket_ok(self):
        c = TingwuClient()
        assert c.ticket is None

    def test_repr(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        assert "ticket=yes" in repr(c)

    def test_cookie_header_sent(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        h = c._headers()
        assert h["Cookie"].startswith("login_aliyunid_ticket=")

    def test_env_client(self, monkeypatch):
        from tingwu import client_from_env

        monkeypatch.setenv("TINGWU_TICKET", "login_aliyunid_ticket=" + "A" * 50)
        assert client_from_env().ticket is not None

        monkeypatch.delenv("TINGWU_TICKET")
        with pytest.raises(AuthError):
            client_from_env()


# --------------------------------------------------------------------------
# endpoint 映射
# --------------------------------------------------------------------------


class TestEndpoints:
    def test_known_action(self):
        assert endpoint_for_action("getTransList") == "/trans/request?getTransList"
        assert endpoint_for_action("getDirList") == "/directory/request?getDirList"

    def test_path_override(self):
        # getTransResult 不在 /request 形式下
        assert endpoint_for_action("getTransResult") == "/trans/getTransResult"

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            endpoint_for_action("definitelyNotAnAction")

    def test_all_modules_valid(self):
        from tingwu.endpoints import MODULE_PATHS

        for action, mod in ACTION_MODULE.items():
            assert mod in MODULE_PATHS, f"{action} -> 未知模块 {mod}"

    def test_no_empty_actions(self):
        for a in ACTION_MODULE:
            assert a and a.isascii()


# --------------------------------------------------------------------------
# 转写解析
# --------------------------------------------------------------------------


def _make_payload():
    """构造一个与真实响应同构的 payload。"""
    result = {
        "pg": [
            {
                "pi": "111",
                "ui": "1",
                "sc": [
                    {"bt": 0, "et": 1000, "id": 10, "si": 1, "tc": "你好"},
                    {"bt": 1000, "et": 2000, "id": 20, "si": 2, "tc": "世界"},
                ],
            },
            {
                "pi": "222",
                "ui": "2",
                "sc": [{"bt": 2000, "et": 3000, "id": 30, "si": 3, "tc": "再见"}],
            },
        ]
    }
    return {
        "transId": "t123",
        "duration": 3,  # 秒
        "result": json.dumps(result),
        "tag": {"showName": "测试录音"},
        "playback": "https://example.com/a.m4a",
    }


class TestTranscript:
    def test_parse_basic(self):
        tr = parse_transcript(_make_payload())
        assert tr.trans_id == "t123"
        assert len(tr) == 3
        assert tr.text == "你好世界再见"

    def test_speakers(self):
        tr = parse_transcript(_make_payload())
        assert tr.speakers == ["1", "2"]

    def test_duration_seconds(self):
        tr = parse_transcript(_make_payload())
        # 服务端 duration 单位是秒
        assert tr.duration == 3.0
        assert tr.duration_ms == 3000

    def test_sentence_timing(self):
        tr = parse_transcript(_make_payload())
        s = tr.sentences[0]
        assert s.begin == 0.0 and s.end == 1.0
        assert s.begin_ms == 0 and s.end_ms == 1000

    def test_by_speaker(self):
        tr = parse_transcript(_make_payload())
        g = tr.by_speaker()
        assert len(g["1"]) == 2 and len(g["2"]) == 1

    def test_show_name_and_playback(self):
        tr = parse_transcript(_make_payload())
        assert tr.show_name == "测试录音"
        assert tr.playback_url == "https://example.com/a.m4a"

    def test_to_srt(self):
        tr = parse_transcript(_make_payload())
        srt = tr.to_srt()
        assert "00:00:00,000 --> 00:00:01,000" in srt
        assert "你好" in srt
        assert srt.splitlines()[0] == "1"

    def test_to_srt_with_speaker(self):
        tr = parse_transcript(_make_payload())
        assert "[1] 你好" in tr.to_srt(with_speaker=True)

    def test_to_vtt(self):
        tr = parse_transcript(_make_payload())
        vtt = tr.to_vtt()
        assert vtt.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:01.000" in vtt

    def test_to_text(self):
        tr = parse_transcript(_make_payload())
        assert "你好" in tr.to_text()
        assert "0.0s" in tr.to_text(with_timestamps=True)

    def test_to_markdown(self):
        tr = parse_transcript(_make_payload())
        md = tr.to_markdown()
        assert "# 测试录音" in md
        assert "说话人 1" in md

    def test_iter(self):
        tr = parse_transcript(_make_payload())
        assert [s.text for s in tr] == ["你好", "世界", "再见"]

    def test_empty_result(self):
        tr = parse_transcript({"transId": "x", "result": None})
        assert len(tr) == 0
        assert tr.text == ""

    def test_bad_json_result(self):
        tr = parse_transcript({"transId": "x", "result": "{{bad"})
        assert len(tr) == 0

    def test_result_already_dict(self):
        p = _make_payload()
        p["result"] = json.loads(p["result"])
        tr = parse_transcript(p)
        assert len(tr) == 3


# --------------------------------------------------------------------------
# 错误处理（用假 session）
# --------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    def __init__(self, resp):
        self.resp = resp
        self.headers = {}
        self.cookies = []
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(("GET", url))
        return self.resp

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw.get("json")))
        return self.resp


class TestErrorHandling:
    def test_not_login_raises_auth_error(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "message": "Not login.", "success": False})
        )
        with pytest.raises(AuthError):
            c.account.info()

    def test_api_error(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(
            FakeResponse(
                200,
                {"code": "TIG.InvalidRequest", "message": "bad", "success": False, "requestId": "r1"},
            )
        )
        with pytest.raises(APIError) as ei:
            c.trans.list()
        assert ei.value.code == "TIG.InvalidRequest"
        assert ei.value.request_id == "r1"

    def test_data_unwrapped(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(FakeResponse(200, {"code": "0", "success": True, "data": {"x": 1}}))
        assert c.account.info() == {"x": 1}

    def test_raw_returns_full_body(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(
            FakeResponse(200, {"code": "0", "success": True, "data": [1], "total": 9})
        )
        r = c.trans.list(raw=True)
        assert r["total"] == 9

    def test_non_json_with_login_marker(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(FakeResponse(200, None, text="<html>please login</html>"))
        with pytest.raises(AuthError):
            c.account.info()

    def test_auth_refresh_callback(self):
        calls = []

        def refresh():
            calls.append(1)
            return "login_aliyunid_ticket=" + "B" * 50

        c = TingwuClient(
            ticket="login_aliyunid_ticket=" + "A" * 50, on_auth_expired=refresh
        )
        c.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "success": False, "message": "x"})
        )
        # 首次触发刷新；刷新后 session 仍返回 NotLogin，故最终仍抛
        with pytest.raises(AuthError):
            c.account.info()
        assert calls, "on_auth_expired 应被调用"
        assert c.ticket.value == "B" * 50

    def test_url_has_c_web(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        s = FakeSession(FakeResponse(200, {"code": "0", "success": True, "data": {}}))
        c.session = s
        c.account.info()
        assert "c=web" in s.calls[0][1]


# --------------------------------------------------------------------------
# 登录态探测
# --------------------------------------------------------------------------


class TestCheck:
    def test_check_true_when_valid(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(
            FakeResponse(200, {"code": "0", "success": True, "data": {"userId": 1}})
        )
        assert c.check() is True

    def test_check_false_when_expired(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50, auto_refresh=False)
        c.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "success": False, "message": "x"})
        )
        assert c.check() is False

    def test_check_does_not_raise(self):
        """check() 的设计目标：失败返回 False，绝不抛 AuthError。"""
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50, auto_refresh=False)
        c.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "success": False, "message": "x"})
        )
        try:
            assert c.check() is False
        except AuthError:
            pytest.fail("check() 不应抛 AuthError")

    def test_check_refreshes_and_recovers(self):
        """失效后自动刷新再试，应返回 True。"""
        state = {"n": 0}

        class SeqSession:
            def __init__(self):
                self.headers = {}
                self.cookies = []

            def get(self, url, **kw):
                state["n"] += 1
                if state["n"] == 1:
                    return FakeResponse(
                        200, {"code": "CMN.NotLogin", "success": False, "message": "x"}
                    )
                return FakeResponse(
                    200, {"code": "0", "success": True, "data": {"userId": 1}}
                )

            post = get

        c = TingwuClient(
            ticket="login_aliyunid_ticket=" + "A" * 50,
            on_auth_expired=lambda: "login_aliyunid_ticket=" + "B" * 50,
        )
        c.session = SeqSession()
        assert c.check() is True
        assert c.ticket.value == "B" * 50

    def test_check_no_refresh_when_disabled(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "success": False, "message": "x"})
        )
        assert c.check(refresh=False) is False

    def test_ensure_login_raises_when_invalid(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50, auto_refresh=False)
        c.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "success": False, "message": "x"})
        )
        with pytest.raises(AuthError):
            c.ensure_login()

    def test_ensure_login_passes_when_valid(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(FakeResponse(200, {"code": "0", "success": True, "data": {}}))
        c.ensure_login()  # 不抛即通过

    def test_check_or_raise_returns_account(self):
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50)
        c.session = FakeSession(
            FakeResponse(200, {"code": "0", "success": True, "data": {"userId": 10001}})
        )
        assert c.check_or_raise() == {"userId": 10001}

    def test_check_propagates_network_errors(self):
        """网络故障不等于登录失效，应向上抛而不是返回 False。"""
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50, retries=0)
        c.session = FakeSession(FakeResponse(500, None, text="server down"))
        with pytest.raises(HTTPError):
            c.check()

    def test_check_restores_auto_refresh_flag(self):
        """check() 内部临时关掉 auto_refresh，结束后必须还原。"""
        c = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50, auto_refresh=True)
        c.session = FakeSession(FakeResponse(200, {"code": "0", "success": True, "data": {}}))
        c.check()
        assert c.auto_refresh is True

        c2 = TingwuClient(ticket="login_aliyunid_ticket=" + "A" * 50, auto_refresh=False)
        c2.session = FakeSession(
            FakeResponse(200, {"code": "CMN.NotLogin", "success": False, "message": "x"})
        )
        c2.check()
        assert c2.auto_refresh is False


# --------------------------------------------------------------------------
# 登录（不实际发请求）
# --------------------------------------------------------------------------


class TestPasswordLogin:
    def test_rsa_encrypt_shape(self):
        """用真实公钥验证加密输出是 512 位小写 hex。"""
        pytest.importorskip("cryptography")
        login = PasswordLogin("13800000000", "pw")
        login._modulus = "b5e9d2031eb1c31e39440bb63de4527c1c437fb2d453bc36f4ba8f317f5ca31a" \
                         "160ede372fe62beb7a239e1326f0e7824b21a04ce5f83dbbad5324ba657539ef" \
                         "0a721f3293f2e8e46543d503e7a1fc9e6ad4a4487feecef11b2bd0537dc02b23" \
                         "c0c349a169d7ad4469577795240a1e1f279d0ca2028074a371f4630cce31d1f0f" \
                         "133605ef26980b42dad7716ec4ea5253bbd8fe1e5d35573a00841b71a28c01d1" \
                         "aa3e04d665dcf10e1b1e6377a230e447e1e3f85e6b2ad51b83b049374a54a8e8" \
                         "64ddf91ab93f05e7049573ca60892ef275ae378577a6d7ea48ae2c39b1487db9e" \
                         "c11ca3ae938ee2a69cada5905fa115b2e86e262e553d234b092f21dcf048db"
        login._exponent = "10001"
        out = login._encrypt_password("hello")
        assert len(out) == 512
        assert out == out.lower()
        int(out, 16)  # 合法 hex

    def test_encrypt_is_randomized(self):
        """PKCS#1 v1.5 有随机填充，两次结果应不同。"""
        pytest.importorskip("cryptography")
        login = PasswordLogin("13800000000", "pw")
        login._modulus = "b5e9d2031eb1c31e39440bb63de4527c1c437fb2d453bc36f4ba8f317f5ca31a" \
                         "160ede372fe62beb7a239e1326f0e7824b21a04ce5f83dbbad5324ba657539ef" \
                         "0a721f3293f2e8e46543d503e7a1fc9e6ad4a4487feecef11b2bd0537dc02b23" \
                         "c0c349a169d7ad4469577795240a1e1f279d0ca2028074a371f4630cce31d1f0f" \
                         "133605ef26980b42dad7716ec4ea5253bbd8fe1e5d35573a00841b71a28c01d1" \
                         "aa3e04d665dcf10e1b1e6377a230e447e1e3f85e6b2ad51b83b049374a54a8e8" \
                         "64ddf91ab93f05e7049573ca60892ef275ae378577a6d7ea48ae2c39b1487db9e" \
                         "c11ca3ae938ee2a69cada5905fa115b2e86e262e553d234b092f21dcf048db"
        login._exponent = "10001"
        assert login._encrypt_password("hello") != login._encrypt_password("hello")

    def test_encrypt_without_config_raises(self):
        login = PasswordLogin("13800000000", "pw")
        with pytest.raises(Exception):
            login._encrypt_password("x")


# --------------------------------------------------------------------------
# 控制台编码（Windows gbk 乱码回归）
# --------------------------------------------------------------------------


class TestEncoding:
    def test_enable_utf8_output_switches_encoding(self):
        """默认 gbk 环境必须被切成 utf-8，否则中文输出乱码。"""
        import io

        from tingwu._encoding import enable_utf8_output

        buf = io.TextIOWrapper(io.BytesIO(), encoding="gbk")
        real = sys.stdout
        sys.stdout = buf
        try:
            assert buf.encoding.lower() == "gbk"
            enable_utf8_output()
            assert buf.encoding.lower().replace("-", "") == "utf8"
        finally:
            sys.stdout = real

    def test_respects_pythonioencoding(self, monkeypatch):
        """用户显式设了 PYTHONIOENCODING 就不越权覆盖。"""
        import io

        from tingwu._encoding import enable_utf8_output

        monkeypatch.setenv("PYTHONIOENCODING", "gbk")
        buf = io.TextIOWrapper(io.BytesIO(), encoding="gbk")
        real = sys.stdout
        sys.stdout = buf
        try:
            assert enable_utf8_output() is False
            assert buf.encoding.lower() == "gbk"
        finally:
            sys.stdout = real

    def test_force_overrides_env(self, monkeypatch):
        import io

        from tingwu._encoding import enable_utf8_output

        monkeypatch.setenv("PYTHONIOENCODING", "gbk")
        buf = io.TextIOWrapper(io.BytesIO(), encoding="gbk")
        real = sys.stdout
        sys.stdout = buf
        try:
            enable_utf8_output(force=True)
            assert buf.encoding.lower().replace("-", "") == "utf8"
        finally:
            sys.stdout = real

    def test_never_raises_on_exotic_stream(self):
        """流不支持 reconfigure（如旧式包装器）时必须静默跳过。"""
        from tingwu._encoding import enable_utf8_output

        class NoReconfigure:
            encoding = "gbk"

        real = sys.stdout
        sys.stdout = NoReconfigure()  # type: ignore[assignment]
        try:
            enable_utf8_output()  # 不抛即通过
        finally:
            sys.stdout = real
