---
type: idea
status: planning
created: 2026-03-29
tags: [multiplayer, websocket, watchthis, product]
---

# TV-Cast × WatchThis: Group Movie Night App

## The Problem
A group of people wants to watch something together. Nobody can agree. Someone spends 20 minutes scrolling Netflix while everyone stares at their phone. The vibe dies.

## The Idea
Friends open the app on their phones. Each person votes on their mood (e.g. "something funny", "thriller", "low effort"). The AI picks one recommendation for the group. The result shows up on the TV.

One question in, one answer out. Decision done.

## How It Works (High Level)

1. **Room creation** — host opens TV display on the big screen, gets a room code
2. **Phone controllers** — guests open controller URL on their phones, enter room code
3. **Mood voting** — each person picks their mood/vibe (could be sliders, taps, quick options)
4. **AI synthesis** — WatchThis's recommendation engine reads all votes, picks one title that fits the group
5. **Display** — recommendation appears on the TV with title, poster, one-line reason

## Building Blocks (Both Already Exist)

| Piece | Source | Status |
|---|---|---|
| WebSocket server (room/broadcast) | TV-Cast | Working proof-of-concept |
| Controller → TV state sync | TV-Cast | Working |
| Mood-based recommendation engine | WatchThis | Working (API + CLI + iOS) |
| Multi-agent AI pipeline (Haiku → Sonnet) | WatchThis | Working |

This is mostly integration work, not net-new engineering.

## Tech Stack
- **Backend:** Python FastAPI + WebSockets (merge TV-Cast's AsyncIO server with WatchThis's API)
- **TV display:** HTML5 / React — fullscreen, shows recommendation
- **Phone controller:** Mobile-optimized HTML5 — mood input UI
- **AI:** WatchThis pipeline (mood interpreter → ranker)

## Open Questions
- How do you reconcile conflicting moods? (Average? Weight by enthusiasm? Let the AI decide?)
- Does it pull from a specific service (Netflix, etc.) or stay service-agnostic?
- Authentication? Or just ephemeral room codes?
- Do you show runners-up, or just the one pick?
- What's the minimum viable mood input? (Free text vs. preset options vs. sliders)

## MVP Scope
- Room code flow (host + guests join)
- Simple mood picker (5–6 preset options, multi-select)
- Single AI recommendation with title + reason displayed on TV
- No accounts, no persistence — ephemeral session

## Related
- [[Projects/TV-Cast]] — WebSocket backbone
- [[Projects/WatchThis]] — recommendation engine
- [[Learning/WebSockets]]
- [[Learning/SwiftUI]] (optional: native iOS controller later)
- [[Atoms/2026-03-24 TV-Cast x WatchThis mashup potential]]
