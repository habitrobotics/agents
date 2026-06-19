# Protoface plugin for LiveKit Agents

Support for [Protoface](https://protoface.com/) virtual avatars.

## Installation

```bash
pip install livekit-plugins-protoface
```

## Pre-requisites

You'll need an API key from Protoface. It can be set as an environment variable:
`PROTOFACE_API_KEY`.

The avatar session also needs LiveKit credentials to mint a short-lived room token for
the Protoface worker:

```bash
export LIVEKIT_URL="wss://your-project.livekit.cloud"
export LIVEKIT_API_KEY="..."
export LIVEKIT_API_SECRET="..."
```
