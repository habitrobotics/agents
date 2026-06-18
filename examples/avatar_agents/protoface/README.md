# LiveKit Protoface Avatar Agent

This example demonstrates how to create a realtime Protoface avatar using
[Protoface](https://protoface.ai/).

## Usage

- Update the environment:

```bash
# Protoface config
export PROTOFACE_API_KEY="..."
export PROTOFACE_AVATAR_ID="av_stock_001"  # optional; defaults to av_stock_001

# Google config
export GOOGLE_API_KEY="..."

# LiveKit config
export LIVEKIT_API_KEY="..."
export LIVEKIT_API_SECRET="..."
export LIVEKIT_URL="..."
```

- Start the agent worker:

```bash
python examples/avatar_agents/protoface/agent_worker.py dev
```
