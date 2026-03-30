# TV-Cast x WatchThis: Group Movie Night — PRD

## What This Is

A multiplayer layer on top of WatchThis. A group of friends opens the app — one person casts a room to the TV, everyone else joins on their phones, each person votes their mood, the AI synthesizes all votes into a single recommendation, and it appears on the big screen. One question in, one answer out. Decision done.

**This is integration work, not a rewrite.** The existing WatchThis pipeline (mood interpreter, TMDB candidates, Reddit enrichment, curation, Sonnet ranking, streaming lookup) stays untouched. We're adding a WebSocket room layer on top and a new "group mood synthesis" step before the existing orchestrator.

---

## What Already Exists (Don't Rebuild)

| Piece | Location | Status |
|---|---|---|
| Mood interpreter (Haiku) | `core/mood_interpreter.py` | Working |
| Candidate retrieval (TMDB) | `core/candidate_retrieval.py` | Working |
| Signal enrichment (Reddit + OMDb) | `core/signal_enrichment.py` | Working |
| Candidate curation + scoring | `core/candidate_curation.py` | Working |
| Ranker + pitch gen (Sonnet) | `core/ranker.py` | Working |
| Streaming lookup (Watchmode) | `core/streaming_lookup.py` | Working |
| Orchestrator (full pipeline) | `core/orchestrator.py` | Working |
| FastAPI server + routes | `api/server.py`, `api/routes.py` | Working |
| React web frontend | `web/` | Working |
| iOS app | `ios/` | Working |
| CLI | `cli/main.py` | Working |

---

## What We're Building (Net-New)

### 1. WebSocket Room Server

A room system where one host creates a session and guests join by code.

**Room lifecycle:**
```
Host opens TV display  →  Room created, 4-digit code generated
                          Room state: WAITING
                               │
Guests join via phone  →  Each guest registers in room
                          Room state: WAITING (guests accumulating)
                               │
Host starts voting     →  All controllers show mood picker
                          Room state: VOTING
                               │
All guests submit      →  Votes collected
                          Room state: PROCESSING
                               │
AI synthesizes + picks →  Recommendation generated
                          Room state: RESULT
                               │
"Spin Again"           →  Back to PROCESSING (same votes, re-roll)
"New Round"            →  Back to VOTING (fresh votes)
```

**Room data model:**
```python
class Room:
    code: str              # 4-digit alphanumeric (e.g., "A7K2")
    host_id: str           # WebSocket connection ID
    state: RoomState       # WAITING | VOTING | PROCESSING | RESULT
    guests: list[Guest]    # Connected guests
    votes: dict[str, Vote] # guest_id -> their vote
    current_result: RecommendationResponse | None
    excluded_tmdb_ids: list[int]  # For re-rolls
    created_at: datetime

class Guest:
    id: str                # WebSocket connection ID
    name: str              # Display name (entered on join)
    connected: bool        # Still connected?

class Vote:
    mood: list[str]        # Selected mood tags (e.g., ["funny", "low-effort"])
    format: FormatFilter   # Movie / TV / Any
    length: LengthFilter   # Quick / Standard / Long / Epic / Any
```

**WebSocket messages (server ↔ clients):**

| Direction | Event | Payload | When |
|---|---|---|---|
| Host → Server | `create_room` | `{ host_name }` | Host opens TV display |
| Server → Host | `room_created` | `{ code, room }` | Room ready |
| Guest → Server | `join_room` | `{ code, guest_name }` | Guest enters code |
| Server → All | `guest_joined` | `{ guest }` | New guest connected |
| Server → All | `guest_left` | `{ guest_id }` | Guest disconnected |
| Host → Server | `start_voting` | `{}` | Host triggers vote phase |
| Server → All | `voting_started` | `{}` | Controllers show mood picker |
| Guest → Server | `submit_vote` | `{ mood, format, length }` | Guest submits mood |
| Server → All | `vote_received` | `{ guest_id, guest_name }` | Progress update (not the vote itself) |
| Server → All | `all_votes_in` | `{ count }` | Everyone voted |
| Server → All | `processing` | `{}` | AI is working |
| Server → All | `result` | `{ recommendation }` | Show on TV + phones |
| Host → Server | `spin_again` | `{}` | Re-roll with same votes |
| Host → Server | `new_round` | `{}` | Fresh voting round |

**Implementation notes:**
- Use FastAPI's built-in WebSocket support (`@app.websocket`)
- Rooms are in-memory only — no persistence needed, ephemeral by design
- Room auto-expires after 2 hours of inactivity
- Room code collision: retry generation (4-char alphanumeric = 1.6M combinations, fine for concurrent rooms)
- Max guests per room: 8 (UI constraint, not technical)
- Handle disconnects gracefully: guest can rejoin same room by code + name

### 2. Group Mood Synthesis

The bridge between "N individual votes" and "1 mood input for the existing pipeline."

**Where it fits:**
```
Individual votes (N guests)
         ↓
[Group Mood Synthesizer]  ← NEW (Claude Haiku)
         ↓
Single MoodInterpretation
         ↓
[Existing Orchestrator]   ← UNCHANGED (candidates → enrich → curate → rank → stream)
         ↓
RecommendationResponse
```

**Synthesis strategy — let the AI decide:**

Feed all votes to Haiku and ask it to produce a single `MoodInterpretation` that best satisfies the group. The prompt should:
- Find the common ground (if 3/4 want comedy, lean comedy)
- Handle conflicts intelligently (if one person wants horror and three don't, skip horror)
- Weight enthusiasm — if someone picked 4 mood tags vs. someone who picked 1, they care more
- Account for format/length consensus (majority rules, ties → "any")
- Output the same `MoodInterpretation` schema the existing pipeline expects

**Input to synthesizer:**
```json
{
  "votes": [
    { "name": "Bryan", "mood": ["funny", "low-effort"], "format": "movie", "length": "standard" },
    { "name": "Alex", "mood": ["thriller", "dark"], "format": "movie", "length": "long" },
    { "name": "Sam", "mood": ["funny", "feel-good"], "format": "any", "length": "any" },
    { "name": "Jordan", "mood": ["action", "funny"], "format": "movie", "length": "standard" }
  ]
}
```

**Output:** Standard `MoodInterpretation` (same as `mood_interpreter.py` produces for solo mode). The rest of the pipeline doesn't know or care that it came from a group.

**Why Haiku, not heuristics:** Mood reconciliation is a judgment call ("funny + thriller = dark comedy? or action-comedy?"). Heuristics would be brittle. Haiku is fast, cheap (~$0.0003), and good at structured extraction. Already proven in the solo mood interpreter.

**File:** `core/group_synthesizer.py` — new file, single function: `synthesize_group_mood(votes: list[Vote]) -> MoodInterpretation`

### 3. TV Display (Host View)

A fullscreen React page optimized for a TV/large screen. Separate route from the existing web app.

**Route:** `/tv`

**Screens:**

1. **Lobby** — Shows room code (large, readable from across the room), list of connected guests, "Start Voting" button
2. **Voting in progress** — Shows who has voted (checkmarks), who hasn't yet, waiting animation
3. **Processing** — "Finding something everyone will love..." with animation
4. **Result** — Full recommendation card (poster, title, pitch, streaming sources, ratings). "Spin Again" and "New Round" buttons

**Design constraints:**
- Text must be readable from 10+ feet away (minimum 32px body, 64px+ for room code/title)
- Dark background (TV in dim room)
- No scrolling — everything fits on one screen per state
- Minimal UI — no nav, no settings, no clutter
- Poster image should be large and prominent on result screen

**Tech:** Same React + Vite + Tailwind stack. New route in the existing web app, not a separate project. Uses WebSocket connection (not HTTP polling).

### 4. Phone Controller (Guest View)

A mobile-optimized web page guests open on their phones. No app install required.

**Route:** `/join`

**Screens:**

1. **Join** — Enter room code + display name. Large input fields, thumb-friendly.
2. **Waiting** — "Waiting for host to start..." Shows who else is in the room.
3. **Vote** — Mood picker UI:
   - 6-8 preset mood tags (multi-select, tap to toggle):
     - Funny, Feel-Good, Thriller, Action, Scary, Mind-Bending, Romantic, Low-Effort
   - Optional format toggle: Movie / TV / Don't Care
   - Optional length toggle: Quick / Standard / Long / Don't Care
   - "Lock In" button to submit
4. **Voted** — "Vote locked in! Waiting for others..." Shows progress (3/4 voted)
5. **Result** — Compact version of the recommendation (title, pitch, poster thumbnail). Full detail is on the TV.

**Design constraints:**
- Must work on any phone browser (Safari, Chrome) — no app install
- Touch targets minimum 44px
- One-handed operation
- Works in portrait only (phones held casually)
- Fast load — guests are joining mid-conversation, every second of friction kills the vibe

**Tech:** Same React + Vite + Tailwind stack. New route in the existing web app. Mobile-first responsive. Uses WebSocket connection to the room.

---

## Architecture Changes

### Files to Add

```
core/
  group_synthesizer.py        # Group mood synthesis (Haiku)

api/
  websocket_manager.py        # Room management, WebSocket handling
  ws_routes.py                # WebSocket endpoint registration

web/src/
  screens/
    TVLobby.jsx               # TV: room code + guest list
    TVVoting.jsx              # TV: voting progress
    TVProcessing.jsx          # TV: loading state
    TVResult.jsx              # TV: recommendation display
    JoinRoom.jsx              # Phone: enter code + name
    PhoneWaiting.jsx          # Phone: waiting for vote phase
    PhoneVote.jsx             # Phone: mood picker
    PhoneVoted.jsx            # Phone: waiting for others
    PhoneResult.jsx           # Phone: compact result
  hooks/
    useWebSocket.js           # WebSocket connection hook
  routes.jsx                  # Add /tv and /join routes
```

### Files to Modify

```
api/server.py                 # Mount WebSocket routes
web/src/App.jsx               # Add router with /tv and /join
web/vite.config.js            # Proxy WebSocket connections in dev
```

### Files NOT to Touch

Everything in `core/` except adding `group_synthesizer.py`. The orchestrator, mood interpreter, candidate pipeline, ranker — all stay exactly as they are. The group synthesizer's output is a `MoodInterpretation`, which is the orchestrator's existing input type. Clean seam.

---

## Build Order

### Phase 1: WebSocket Room Infrastructure
1. `api/websocket_manager.py` — Room class, in-memory room store, create/join/leave logic
2. `api/ws_routes.py` — WebSocket endpoint, message routing
3. Wire into `api/server.py`
4. **Test:** Two terminal WebSocket clients can create room, join, exchange messages

### Phase 2: Group Mood Synthesis
1. `core/group_synthesizer.py` — Haiku prompt, vote → MoodInterpretation
2. Connect synthesizer output to existing orchestrator
3. **Test:** Submit mock group votes via API, get valid recommendation back

### Phase 3: TV Display
1. Add React Router to web app
2. Build `/tv` route with lobby → voting → processing → result flow
3. Connect to WebSocket for real-time state updates
4. **Test:** Open `/tv` in browser, see room code, connect a second tab as guest

### Phase 4: Phone Controller
1. Build `/join` route with join → waiting → vote → voted → result flow
2. Mood picker UI with preset tags
3. Connect to WebSocket
4. **Test:** Full flow — TV on laptop, phones join, vote, see result

### Phase 5: Polish
1. Reconnection handling (guest refreshes phone)
2. Host disconnect handling (room cleanup)
3. Loading animations / transitions
4. Error states (room not found, room full, vote timeout)
5. Mobile Safari quirks

---

## Scope Decisions (MVP)

| Decision | Choice | Rationale |
|---|---|---|
| Mood input method | Preset tags (multi-select) | Free text on phone is slow and awkward in a group setting. Tapping tags is fast and fun. |
| Number of recommendations | 1 | That's the whole point — eliminate choice paralysis. |
| Show runners-up? | No | One pick. Commit to it. "Spin Again" if they hate it. |
| Accounts / auth | No | Ephemeral rooms. No sign-up friction. |
| Persistence | No | Room dies when everyone leaves. No history needed for group mode. |
| Service-specific filtering | No (v1) | Service-agnostic. Streaming sources shown after the pick. |
| Conflict resolution | AI decides | Haiku interprets the group's collective mood. No voting algorithms, no averaging. |
| Free text mood input | No (v1) | Tags only for group mode. Keep it fast. Solo mode still supports free text via existing flow. |

---

## Open Questions Resolved

From the original idea note:

> **How do you reconcile conflicting moods?**
Let the AI decide. Feed all votes to Haiku, ask it to find the common thread. This is a judgment call, not a math problem.

> **Does it pull from a specific service or stay service-agnostic?**
Service-agnostic. Watchmode lookup happens after the pick, same as solo mode.

> **Authentication?**
Ephemeral room codes. No accounts.

> **Show runners-up?**
No. One pick. "Spin Again" exists.

> **Minimum viable mood input?**
Preset tags, multi-select. 6-8 options covering the main vibes.

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| WebSocket complexity in production | High | Keep rooms in-memory for MVP. No Redis/pub-sub needed until multi-server. |
| Mobile Safari WebSocket quirks | Medium | Test early. Fallback: long-polling (ugly but works). |
| Group synthesis quality | Medium | Log all group votes + synthesized interpretation. Review and tune prompt. |
| Latency (AI synthesis + full pipeline) | Medium | Synthesis is one Haiku call (~200ms). Full pipeline is 3-5s. Show good loading state. |
| Room code guessing | Low | 4-char alphanumeric = 1.6M codes. Rooms are short-lived. Not a real attack surface. |

---

## Non-Goals (Explicitly Out of Scope)

- Native iOS group mode (web-only for MVP — everyone has a phone browser)
- Chat / reactions in room
- Persistent watch history for groups
- "I've already seen this" per-person filtering
- Streaming service filtering ("only show Netflix")
- More than 8 people per room
- Multiple TVs / multi-room sync
- Custom mood tag creation
