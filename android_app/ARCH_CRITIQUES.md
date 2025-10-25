## Architecture overview and critique

### Scope
- **Goal**: Summarize functionality, describe current architecture, assess fitness, and list major architectural problems with details. No fix plan included.

### Functionality overview
- **AI chat**: Conversations with agents, chat history, "keep talking", TTS audio playback.
- **Agents**: Discover, follow, create, edit, report.
- **Auth**: Guest creation and Google Sign-In.
- **Subscription**: Google Play Billing for plans and status monitoring.
- **Profile & settings**: User info, app update checks, preferences.
- **Media**: Image loading (Coil), audio playback (Media3/ExoPlayer).

### Architecture summary
- **Modules**:
  - `app`: Compose UI, Activities, startup orchestration.
  - `core/data`: Networking (two stacks), SDK facades, billing repository, chat domain (repository/use cases), settings (MMKV).
  - `core/common`, `core/design`, `core/firebase`, `library/network`, `library/utils` provide shared utilities, UI, analytics, and network helpers.
- **UI**: Compose with MVVM (`BaseVM` + StateFlow). Multi-Activity navigation with a custom bottom bar; limited Navigation Compose usage.
- **Data**:
  - Retrofit/Moshi stack via `NetServiceMgr` + `I*Api` interfaces.
  - Stainless-generated SDK via `IntyNetworkManager` and `*Service` facades returning `ApiResult`.
  - Local storage with MMKV; no Room; chat persistence currently disabled.
- **Orchestration**: `IntelliMateApp` initializes networking/startup; `UnifiedStartupManager` coordinates login/guest, preload, cache, and network sync; `BillingRepository` singleton manages purchases and state.
- **Media**: Media3 player with custom `AudioPlaybackManager`; image loading configured in design module.

### Fitness assessment
- The Compose + MVVM modular structure fits the product’s chat-first, media-rich use case.
- Reliability, consistency, and testability are hampered by parallel networking stacks, manual DI patterns, singleton-heavy orchestration, and disabled persistence—risky for a long-term companion app that needs stable auth flows, uniform error handling, and offline continuity.

## Major architectural problems

### 1) Dual networking stacks in active use
- **What**: Both Retrofit/Moshi (`NetServiceMgr` + `I*Api`) and the generated SDK (`IntyNetworkManager` + `*Service`) are used across features (e.g., `UnifiedStartupManager` mixes `AuthService` with `NetServiceMgr.getAgentApi()`).
- **Impact**: Inconsistent error handling/logging, duplicated env config, diverging auth flows, higher maintenance burden, more complex testing and observability.

### 2) No standardized DI; globals and manual wiring
- **What**: Global object `ChatModule` hand-wires repository/use cases; `@Inject` annotations exist but no DI runtime (Hilt/Koin) actually wires dependencies; view models pull dependencies lazily.
- **Impact**: Hard to substitute fakes in tests, unclear lifecycles, hidden wiring inside singletons, inconsistent scoping.

### 3) Lifecycle-detached background work in `BaseVM`
- **What**: `BaseVM` creates its own `backgroundScope` and "persistent" coroutines independent of `viewModelScope`.
- **Impact**: Work can outlive screens, risking leaks, race conditions, and state updates after disposal.

### 4) Fragile 401 handling in `AuthInterceptor`
- **What**: On HTTP 401, logs and forcibly logs out and relaunches the app.
- **Impact**: Potential relaunch loops, poor UX, and brittle recovery for token expiry or transient auth issues; mismatched with SDK-based auth paths.

### 5) Billing initialization relies on timed delays and Activity coupling
- **What**: `MainActivity` uses ad-hoc `delay(500)` timing before init and plan fetching; billing monitoring started from the Activity.
- **Impact**: Flaky startup, race conditions across devices, tight coupling to a single screen lifecycle.

### 6) Chat persistence disabled; no offline continuity
- **What**: Chat persistence methods are intentionally no-op; only pagination flags stored.
- **Impact**: Cold starts lose context, reduced resilience offline/poor networks, higher repeated network load.

### 7) Hybrid navigation: multi-Activity + Compose, limited Navigation Compose
- **What**: Many flows launch Activities directly; bottom navigation is custom; minimal `NavHost` usage.
- **Impact**: Back stack complexity, harder deep links/state restoration, more manual transition and state handling, reduced testability of navigation.

### 8) Duplicated and inconsistent OkHttp clients
- **What**: Separate clients built in `NetServiceMgr`, Media3 audio, and Coil image config with differing interceptors/timeouts.
- **Impact**: Inconsistent headers, TLS, retries, logging, and caching; cross-cutting concerns harder to apply uniformly.

### 9) Retry interceptor uses blocking sleeps (and is commented out)
- **What**: `RetryInterceptor` uses `Thread.sleep` in an OkHttp interceptor; currently disabled.
- **Impact**: If enabled, blocks OkHttp threads; regardless, it’s confusing dead code and a risky approach for retries.

### 10) Security and logging concerns
- **What**: Access token stored in MMKV without visible encryption key management; interceptor logs request URLs and auth context.
- **Impact**: Elevated data exposure risk and log leakage; not ideal for a sensitive, account-based product.

### 11) Layering leaks from view models to data sources
- **What**: Example: `ChatViewModel` uses domain use cases for messages but also calls APIs directly for settings, bypassing repository/domain in places.
- **Impact**: Mixed responsibilities, reduced flexibility to change data sources, inconsistent error handling.

### 12) Heavy reliance on global singletons with internal state
- **What**: `UnifiedStartupManager`, `BillingRepository`, `ChatSessionManager`, `AgentCacheManager` hold global state and executors.
- **Impact**: Hidden dependencies, state coupling across screens, complex test setup, subtle timing interactions with UI.

### 13) Over-instrumentation on hot network paths
- **What**: Interceptors emit analytics/crash events per request and error.
- **Impact**: Performance overhead, noisy telemetry (e.g., treating expected states as errors), potential privacy implications.

### 14) MMKV JSON caches for large lists without size/eviction policies
- **What**: Agent lists stored as JSON strings with TTL, no size caps.
- **Impact**: Potential storage bloat, slower reads/writes as payloads grow, fragile manual serialization.

### 15) Activity-centric custom back/gesture handling
- **What**: Manual edge-swipe/back handling in `MainActivity`.
- **Impact**: Behavior variance across devices and OS versions; potential conflicts with system gestures; extra maintenance.

## Notable strengths
- **Compose + StateFlow**: Reactive, modern UI patterns used consistently in view models.
- **Modularization**: Separation for design, utils, firebase, data, and app layers.
- **Media**: Media3-based audio manager with audio focus; proactive image/audio preloading.
- **Billing repository**: Centralized subscription state/events, despite lifecycle coupling noted above.
