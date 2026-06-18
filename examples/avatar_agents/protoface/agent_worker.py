import logging
import os

from dotenv import load_dotenv

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, RoomOutputOptions, cli
from livekit.plugins import google, protoface

logger = logging.getLogger("protoface-avatar-example")
logger.setLevel(logging.INFO)

load_dotenv()

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice="Puck",
        ),
        resume_false_interruption=False,
    )

    avatar = protoface.AvatarSession(
        avatar_id=os.getenv("PROTOFACE_AVATAR_ID", protoface.DEFAULT_STOCK_AVATAR_ID),
    )
    await avatar.start(session, room=ctx.room)

    await session.start(
        agent=Agent(instructions="You are a helpful realtime voice assistant."),
        room=ctx.room,
        room_output_options=RoomOutputOptions(audio_enabled=False),
    )


if __name__ == "__main__":
    cli.run_app(server)
