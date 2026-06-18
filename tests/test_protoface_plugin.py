from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest

from livekit.agents import APIStatusError, Plugin
from livekit.agents.voice.avatar import AvatarSession as BaseAvatarSession
from livekit.agents.voice.room_io import ATTRIBUTE_PUBLISH_ON_BEHALF
from livekit.plugins import protoface

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    async def text(self) -> str:
        return json.dumps(self._payload)

    async def json(self, *, content_type: str | None = None) -> object:
        del content_type
        return self._payload

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb


class _FakeSession:
    def __init__(self, *responses: _FakeResponse) -> None:
        self.requests: list[dict[str, Any]] = []
        self._responses = list(responses)

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self._responses.pop(0)


def test_subclasses_avatar_session() -> None:
    assert issubclass(protoface.AvatarSession, BaseAvatarSession)


def test_provider_and_default_identity() -> None:
    session = protoface.AvatarSession(api_key="sk_live_test")

    assert session.provider == "protoface"
    assert session.avatar_identity == "protoface-avatar-agent"
    assert session.session_id is None


def test_plugin_registered_on_import() -> None:
    packages = {plugin.package for plugin in Plugin.registered_plugins}

    assert "livekit.plugins.protoface" in packages


@pytest.mark.asyncio
async def test_start_twice_raises_before_network_call() -> None:
    session = protoface.AvatarSession(api_key="sk_live_test")
    session._session_id = "ses_already"

    with pytest.raises(RuntimeError, match="called twice"):
        await session.start(agent_session=None, room=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_start_session_sends_auth_and_body() -> None:
    http_session = _FakeSession(
        _FakeResponse(200, {"id": "ses_abc", "avatar_id": "av_stock_001", "status": "queued"})
    )
    client = protoface.ProtofaceAPI(
        api_key="sk_live_test",
        api_url="https://api.protoface.com/",
        session=http_session,  # type: ignore[arg-type]
    )

    out = await client.start_session(
        avatar_id="av_stock_001",
        transport={
            "type": "livekit",
            "url": "wss://x.livekit.cloud",
            "room_name": "demo",
            "worker_token": "tok",
            "worker_identity": "protoface-avatar-agent",
            "audio_source": "data_stream",
        },
        max_duration_seconds=120,
    )

    request = http_session.requests[0]
    assert out["id"] == "ses_abc"
    assert request["method"] == "POST"
    assert request["url"] == "https://api.protoface.com/v1/sessions"
    assert request["headers"]["Authorization"] == "Bearer sk_live_test"
    assert request["headers"]["User-Agent"].startswith("livekit-plugins-protoface/")
    assert request["json"]["avatar_id"] == "av_stock_001"
    assert request["json"]["transport"]["worker_identity"] == "protoface-avatar-agent"
    assert request["json"]["transport"]["audio_source"] == "data_stream"
    assert request["json"]["max_duration_seconds"] == 120


@pytest.mark.asyncio
async def test_error_response_raises_api_status_error() -> None:
    http_session = _FakeSession(
        _FakeResponse(
            400,
            {
                "error": {
                    "type": "invalid_request",
                    "code": "transport.unsupported",
                    "message": "transport.type='websocket' is not supported",
                }
            },
        )
    )
    client = protoface.ProtofaceAPI(
        api_key="sk_live_test",
        api_url="https://api.protoface.com",
        session=http_session,  # type: ignore[arg-type]
    )

    with pytest.raises(APIStatusError) as exc_info:
        await client.start_session(
            avatar_id="av_stock_001",
            transport={
                "type": "websocket",
                "url": "wss://x",
                "room_name": "r",
                "worker_token": "t",
            },
        )

    assert exc_info.value.status_code == 400
    assert isinstance(exc_info.value.body, dict)
    assert exc_info.value.body["error"]["code"] == "transport.unsupported"


@pytest.mark.asyncio
async def test_end_session_hits_expected_path() -> None:
    http_session = _FakeSession(_FakeResponse(200, {"id": "ses_x", "status": "ended"}))
    client = protoface.ProtofaceAPI(
        api_key="sk_live_test",
        api_url="https://api.protoface.com",
        session=http_session,  # type: ignore[arg-type]
    )

    await client.end_session("ses_x")

    assert http_session.requests[0]["method"] == "POST"
    assert http_session.requests[0]["url"] == "https://api.protoface.com/v1/sessions/ses_x/end"


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROTOFACE_API_KEY", raising=False)

    with pytest.raises(protoface.ProtofaceException, match="PROTOFACE_API_KEY"):
        protoface.ProtofaceAPI(api_key=None)


_TEST_API_KEY = "APIxxxxxxxxxxxx"
_TEST_API_SECRET = "secret-bytes-at-least-32-chars-long"


def _mint(
    monkeypatch: pytest.MonkeyPatch,
    *,
    local_identity: str = "agent-local",
    room_name: str = "demo-room",
    avatar_identity: str | None = None,
) -> str:
    fake_ctx = MagicMock()
    fake_ctx.local_participant_identity = local_identity

    def _get_job_context(*, required: bool = True) -> MagicMock:
        del required
        return fake_ctx

    monkeypatch.setattr(
        "livekit.plugins.protoface.avatar.get_job_context",
        _get_job_context,
    )
    avatar = protoface.AvatarSession(
        api_key="sk_live_test",
        avatar_participant_identity=avatar_identity,
    )
    fake_room = MagicMock()
    fake_room.name = room_name

    return avatar._mint_worker_token(
        room=fake_room,
        livekit_api_key=_TEST_API_KEY,
        livekit_api_secret=_TEST_API_SECRET,
    )


def _decode(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _TEST_API_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def test_worker_token_subject_and_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = _decode(_mint(monkeypatch))

    assert claims["sub"] == "protoface-avatar-agent"
    assert claims["name"] == "protoface-avatar-agent"
    assert claims["kind"] == "agent"


def test_worker_token_room_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = _decode(_mint(monkeypatch, room_name="customer-room-42"))
    video = claims["video"]

    assert isinstance(video, dict)
    assert video["room"] == "customer-room-42"
    assert video["roomJoin"] is True
    assert video["canPublish"] is True
    assert video["canSubscribe"] is True
    assert video["canPublishData"] is True


def test_worker_token_publish_on_behalf_of_local_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claims = _decode(_mint(monkeypatch, local_identity="agent-local-7"))
    attributes = claims["attributes"]

    assert isinstance(attributes, dict)
    assert attributes[ATTRIBUTE_PUBLISH_ON_BEHALF] == "agent-local-7"


def test_worker_token_custom_identity_override(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = _decode(_mint(monkeypatch, avatar_identity="custom-protoface"))

    assert claims["sub"] == "custom-protoface"
    assert claims["name"] == "protoface-avatar-agent"
