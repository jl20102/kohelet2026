# kohelet2026
Repo for collaboration on the Kohelet 2026 coding competition.

## Architecture & Logic

### System Overview
The application follows a client-server model. The frontend handles the prayer interface and biometric simulation (mouse/scroll tracking), while the Flask backend maintains state and connects to external APIs.

```mermaid
graph TD
    subgraph Client [Browser / Frontend]
        UI[User Interface]
        Tracker[Activity Tracker]
        Graph[Canvas Visualizer]
    end

    subgraph Server [Flask Backend]
        API[API Routes]
        State[State Deque]
        Analysis[Focus Logic]
    end

    subgraph External [External APIs]
        Sefaria[Sefaria Database]
    end

    UI -->|User Reads| Tracker
    Tracker -->|Pulse 2s| API
    API -->|Store Data| State
    State -->|Check Flatline| Analysis
    Analysis -->|Alert Status| API
    API -->|Update Graph| Graph
    
    UI -->|Request Prayer| API
    API -->|Fetch Text| Sefaria
```

### "Nudge" Logic Flow
The system monitors user engagement in 2-second intervals. If the user becomes idle (flatlines) for too long, the system triggers a check-in.

```mermaid
sequenceDiagram
    participant U as User
    participant C as Client (JS)
    participant S as Server (Python)

    loop Every 2 Seconds
        C->>C: Check Mouse/Scroll Activity
        C->>S: POST /stream_sample {active: 0 or 1}
        S->>S: Update Speed History
        S->>S: Check last 3 samples (6s)
        S-->>C: {flatline_alert: boolean}
    end

    opt If Flatline Alert is True
        C->>U: Show "Check In" Overlay
        U->>C: Input Anxiety/Focus Levels
        C->>S: POST /submit_checkin
    end
```