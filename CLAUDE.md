# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

### Environment Setup
```bash
# Set Java 17 environment (required for builds)
export JAVA_HOME=/Applications/Android\ Studio.app/Contents/jbr/Contents/Home

# Build debug APK
./gradlew assembleDebug

# Build release APK  
./gradlew assembleRelease

# Run tests
./gradlew test

# Clean build
./gradlew clean
```

### Debugging
- Use `EasyLog.log()` for logging throughout the application
- Debug APKs are signed with the development certificate in `sign/key.jks`
- Build outputs are in `app/build/outputs/apk/`

## Architecture Overview

### Technology Stack
- **Language**: Kotlin with Jetpack Compose UI
- **Architecture**: MVVM (Model-View-ViewModel) 
- **Routing**: TheRouter for navigation between activities
- **Networking**: Retrofit + OkHttp with custom HttpResult wrapper
- **State Management**: MMKV for persistent storage, StateFlow for reactive state
- **Image Loading**: Coil3 for async image loading
- **Dependency Injection**: KSP with TheRouter's @Singleton and @Autowired
- **Push Notifications**: Firebase Messaging
- **Billing**: Google Play Billing

### Module Structure
- `app/` - Main application module with activities, UI components, and business logic
- `network/` - Shared networking layer with HTTP result handling and interceptors  
- `utils/` - Shared utilities including logging (EasyLog) and storage (IntySetting)

### Key Application Components

#### Route Management
- All routes defined in `Constant.kt` using URL-style paths (e.g., `"http://inty.ai/main"`)
- Activities annotated with `@Route(path = Constant.ROUTE_*)` 
- Parameter injection via `@Autowired` annotations
- Navigation via `TheRouter.build(Constant.ROUTE_*).navigation(context)`

#### State Management
- `IntySetting` (MMKV-based) manages user preferences, conversation tracking, and character-specific settings
- Three-state setting system for keep-talking functionality (true/false/null for "follow global")
- User session management with guest mode support
- Conversation filtering to show only user-initiated chats

#### Networking Architecture
- API interfaces in `net/` package using Retrofit with suspend functions
- Custom `HttpResult<T>` wrapper for Success/Failure handling
- Business logic in ViewModels using `viewModelScope.launch(Dispatchers.IO)`
- API services injected via TheRouter: `TheRouter.get(IAgentApi::class.java)`

#### UI Architecture  
- Jetpack Compose with Material3 design system
- ViewModels extend `BaseActivityViewModel` and use `StateFlow` for reactive UI
- Custom base components in `base/` package (e.g., `IntyImage`, `IntyCircleImage`)
- Global theme and colors defined in `ui/theme/`

### Core Business Logic

#### Chat System
- `ChatViewModel` manages conversation state and message flow
- Real-time message updates via StateFlow
- Keep-talking functionality with character-specific overrides
- Background image handling with proper keyboard layout management

#### Agent Management  
- `MainViewModel` handles agent discovery, following, and creation
- Agent states synchronized across activities via LocalBroadcastManager
- Follow state changes broadcast with "FOLLOW_STATE_CHANGED" intent
- Avatar generation and management through `AvatarManager` singleton

#### User Management
- Google OAuth integration with guest mode fallback
- User profile management via `UserProfileManager` 
- Logout without app restart by switching to guest mode
- FCM token registration for push notifications

### Important Implementation Details

#### Avatar Generation Flow
- `AvatarGenerateActivity` for AI-powered avatar creation
- `AvatarManager` handles URL transfer between activities
- Generated avatars integrated into character creation workflow
- API field mapping: server returns `url` field, not `imageUrl`

#### Settings System
- Global settings in main settings screen
- Character-specific settings with priority over global
- Real-time UI updates when settings change
- Three-state toggle system for keep-talking preferences

#### Navigation and Lifecycle
- Custom lifecycle handling for avatar URL management
- Activity result patterns for OAuth and permissions
- Proper broadcast receiver management for state synchronization
- Background image positioning that doesn't interfere with keyboard

### Development Patterns

#### Error Handling
- Network calls wrapped in try-catch with user-friendly messages
- `HttpResult.Success`/`HttpResult.Failure` pattern for API responses
- Toast messages for user feedback on actions
- Comprehensive logging with `EasyLog` at key operation points

#### State Updates
- Immediate UI feedback with optimistic updates
- Background sync with server API calls
- Broadcast mechanism for cross-activity state updates
- StateFlow collectors for reactive UI updates

#### Testing and Debugging
- Extensive logging throughout the application
- Debug builds include network inspection tools (Chucker)
- Clear separation of concerns for easier unit testing
- Preview functions for Compose components

## Key Files and Their Purposes

- `Constant.kt` - All route definitions and global constants
- `IntySetting.kt` - User preferences and conversation tracking
- `MainViewModel.kt` - Core app state management and agent operations
- `ChatViewModel.kt` - Chat functionality and message management  
- `IAgentApi.kt`/`IChatApi.kt` - API interface definitions
- `AvatarManager.kt` - Avatar URL management between activities
- `UserProfileManager.kt` - User session and profile management

## Development Workflow Rules

### Important Guidelines
1. **Do not commit or push code unless explicitly requested** - Only perform git operations when the user specifically asks for it
2. **Always ensure successful build after completing requirements** - Run build command to verify compilation after any development task

## Development Notes

### Common Pitfalls
- Always use `viewModelScope.launch(Dispatchers.IO)` for network calls
- Remember to call `IntySetting.setUserInitiatedConversation()` when users start chats
- Avatar URL field mapping: API returns `url`, not `imageUrl` 
- Broadcast receivers must be registered/unregistered in activity lifecycle
- Java 17 is required - set JAVA_HOME before building

### Code Style
- Follow existing patterns in `.cursorrules` file
- Use Material3 components and theme system
- Prefer StateFlow over LiveData for reactive state
- Use `@Composable` functions for UI components
- Network calls in ViewModels, UI logic in Composables