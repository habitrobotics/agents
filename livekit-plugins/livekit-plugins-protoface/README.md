# Protoface plugin for LiveKit Agents

Support for [Protoface](https://protoface.ai/) virtual avatars.

Protoface hosts realtime talking faces for LiveKit rooms. Your LiveKit agent owns the
conversation pipeline; Protoface joins the room as an avatar participant, receives the
agent audio over LiveKit DataStream, and publishes synchronized avatar video.

## Installation

```bash
pip install livekit-plugins-protoface
```

## Pre-requisites

Create a Protoface API key and set it as an environment variable:

```bash
export PROTOFACE_API_KEY="..."
```

The avatar session also needs LiveKit credentials so it can mint a short-lived room token
for the Protoface worker:

```bash
export LIVEKIT_URL="wss://your-project.livekit.cloud"
export LIVEKIT_API_KEY="..."
export LIVEKIT_API_SECRET="..."
```

## Usage

```python
from livekit.agents import Agent, AgentSession, RoomOutputOptions
from livekit.plugins import protoface

session = AgentSession()

avatar = protoface.AvatarSession(
    avatar_id="av_stock_001",
)
await avatar.start(session, room=ctx.room)

await session.start(
    agent=Agent(instructions="Talk to me!"),
    room=ctx.room,
    room_output_options=RoomOutputOptions(audio_enabled=False),
)
```

`av_stock_001` is a stable Protoface stock avatar ID available to every account. You can
also pass a custom avatar ID from your Protoface dashboard.

## Configuration

| Parameter | Env var | Description |
|-----------|---------|-------------|
| `api_key` | `PROTOFACE_API_KEY` | Protoface API key |
| `api_url` | `PROTOFACE_API_URL` | API base URL (default: `https://api.protoface.com`) |
| `avatar_id` | - | Stable stock avatar ID or a custom Protoface avatar ID |
| `max_duration_seconds` | - | Optional maximum session duration in seconds |

LiveKit credentials (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`) are read
from environment variables or can be passed to `avatar.start()`.
