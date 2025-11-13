# Version Check API Usage

The version check API allows clients to verify if they need to update to the latest version available on Google Play Store.

## Endpoints

### POST /api/v1/version/check

Check if the client app needs to update.

**Request Body:**

```json
{
  "version": "1.2.3",
  "platform": "android"
}
```

**Response:**

```json
{
  "code": 200,
  "success": true,
  "message": "Success",
  "data": {
    "current_version": "1.2.3",
    "latest_version": "1.3.0",
    "latest_version_code": 130,
    "update_required": true,
    "force_update": false,
    "minimum_version": "1.0.0",
    "changelog": "Bug fixes and performance improvements",
    "download_url": "https://play.google.com/store/apps/details?id=com.ai.inty",
    "message": "Update available"
  }
}
```

### GET /api/v1/version/latest

Get latest version information (Admin only).

**Response:**

```json
{
  "code": 200,
  "success": true,
  "message": "Success",
  "data": {
    "version_code": 130,
    "version_name": "1.3.0",
    "status": "completed",
    "release_notes": "Bug fixes and performance improvements",
    "user_fraction": null
  }
}
```

## Configuration

Add the following settings to `config.yaml`:

```yaml
google_play:
  package_name: com.ai.intellimate
  service_account_key: inty-backend-key.json
  enable_version_check: true
  android_app_version_code_diff_limit: 10
  force_update_versions: ["1.0.5", "1.1.2"] # Versions that require force update
  release_track: internal # Track to query: internal/closed/open/production
  fallback_tracks: [production, internal] # Fallback tracks if primary fails
```

### Track Configuration

- **release_track**: Primary track to query for version information
  - `internal`: Internal testing track (up to 100 testers)
  - `closed`: Closed testing track (invite-only groups)
  - `open`: Open testing track (public beta)
  - `production`: Production track (live for all users)

- **fallback_tracks**: Array of tracks to try if primary track has no releases
  - Useful when transitioning between tracks
  - System will try tracks in order until it finds version information

### Version Name Parsing

The system automatically handles complex version name formats from Google Play:

- `"217 (1.0.1 (507a57a))"` → extracts `"1.0.1"`
- `"(1.0.1)"` → extracts `"1.0.1"`
- `"1.0.1"` → uses as is
- `"v1.2.3"` → uses as is

This ensures accurate version comparison regardless of Google Play's internal naming conventions.

## Response Fields

- `update_required`: Whether an update is available
- `force_update`: Whether the update is mandatory
- `minimum_version`: Minimum supported version (below this requires force update)
- `changelog`: Release notes from Google Play Console
- `download_url`: Direct link to app on Play Store

## Error Handling

If the Google Play API is unavailable, the service will return a safe response allowing the app to continue functioning:

```json
{
  "current_version": "1.2.3",
  "latest_version": "unknown",
  "update_required": false,
  "force_update": false,
  "message": "Version check failed but app can continue",
  "error": "API connection failed"
}
```

## Client Implementation Example

```typescript
async function checkForUpdates() {
  try {
    const response = await fetch("/api/v1/version/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        version: "1.2.3",
        platform: "android",
      }),
    });

    const result = await response.json();
    const versionData = result.data;

    if (versionData.force_update) {
      // Show mandatory update dialog
      showForceUpdateDialog(versionData);
    } else if (versionData.update_required) {
      // Show optional update prompt
      showUpdatePrompt(versionData);
    }
  } catch (error) {
    console.log("Version check failed, continuing normally");
  }
}
```
