# Inty SDK Migration TODOs

## API Endpoints Not Using Generated SDK

The following API endpoints are currently implemented using Retrofit/Moshi but are **not available in the generated SDK**. These endpoints should be migrated to use the generated SDK when possible.

### 1. Agent API (IAgentApi.kt)
- `POST /api/v1/ai/agents/text-to-image` - Generate background images for agents
- `POST /api/v1/images` - Upload avatar images

### 2. Chat API (IChatApi.kt)
- `POST /api/v1/chat/completions/{agent_id}` - Send messages to agents
- `GET /api/v1/chats/agents/{agent_id}/messages` - Get chat messages by agent ID
- `GET /api/v1/chats/` - Get user's chat conversations list
- `GET /api/v1/ai/agents/{agent_id}` - Get agent information (duplicate from IAgentApi)
- `GET /api/v1/chats/agents/{agent_id}/settings` - Get chat settings by agent ID
- `PUT /api/v1/chats/agents/{agent_id}/settings` - Update chat settings by agent ID
- `POST /api/v1/chats/agents/{agent_id}/messages/{message_id}/voice` - Generate voice for messages

### 3. User API (IUserApi.kt)
- `POST /api/v1/auth/google/login` - Google authentication login
- `POST /api/v1/images` - Upload avatar images (duplicate from IAgentApi)
- `GET /api/v1/users/deletion/check` - Check user deletion status
- `POST /api/v1/users/delete-account` - Delete user account

### 4. Subscription API (ISubscriptionApi.kt)
- `GET /api/v1/subscription/plans` - Get subscription plans
- `POST /api/v1/subscription/verify` - Verify subscription

### 5. Common API (ICommonApi.kt)
- `POST /api/v1/version/check` - Check app version updates

## Migration Tasks

### High Priority
1. **Image Upload Endpoints** - `POST /api/v1/images` appears in both IAgentApi and IUserApi, should be consolidated
2. **Agent Information** - `GET /api/v1/ai/agents/{agent_id}` is duplicated between IAgentApi and IChatApi
3. **Chat Functionality** - Core chat endpoints should be migrated to use generated SDK when available

### Medium Priority
1. **Authentication** - Google login endpoint should use generated SDK
2. **Subscription Management** - Subscription endpoints should use generated SDK
3. **Version Checking** - Version check endpoint should use generated SDK

### Low Priority
1. **User Management** - User deletion endpoints may be app-specific
2. **Voice Generation** - Voice generation endpoints may be app-specific

## Notes

- The generated SDK appears to be more focused on core agent management, authentication, and basic subscription functionality
- The Retrofit implementation includes additional features like chat messaging, image generation, voice synthesis, and more comprehensive user management capabilities
- Consider whether these additional endpoints should be added to the generated SDK or remain as custom implementations
- Some endpoints may be duplicates that should be consolidated regardless of SDK usage

## Total Count
**13 unique API endpoints** are currently not using the generated SDK.