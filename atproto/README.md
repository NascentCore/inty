# ATProto (Account Portability Protocol)

## AT Protocol example

See https://stackoverflow.com/a/77633012, AT Protocol's SDK uses a pydantic model
that is unversioned? So it needs to install newest version, otherwise importing
at protocol's pydantic model fails.

```bash
# Put your https://bsky.app/ username and password as env vars to .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bluesky_example.py
```

## What is AT Protocol?

AT Protocol (Authenticated Transfer Protocol) is an open social networking protocol developed by Bluesky. It's designed to create a decentralized social web where users have control over their data and can move between different services while maintaining their social connections.

### Key Features

1. Account Portability

- Users can move their accounts between different services
- Maintain your identity and social graph across platforms
- No vendor lock-in

2. Algorithmic Choice

- Users can choose their own algorithms for content discovery
- Different services can implement different recommendation systems
- Freedom to switch between different algorithms

3. Interoperable Data

- Standardized data formats for social content
- Easy sharing and interaction between different services
- Common protocol for social features

### Core Concepts

1. **DID**: Your unique identifier in the network
2. **Handle**: Your human-readable username
3. **Repository**: Your personal data store
4. **Records**: Individual pieces of content

## Resources

- [AT Protocol Documentation](https://atproto.com/docs)
- [Bluesky GitHub](https://github.com/bluesky-social)
- [Protocol Specification](https://atproto.com/specs)
