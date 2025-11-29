# YouTube to H5P Moodle Pipeline Workflow

## Workflow Details

- **Workflow ID**: `ceuN24aWjZ9ncUk2`
- **Name**: YouTube to H5P Moodle Pipeline
- **Status**: Active
- **Webhook URL**: https://srv947487.hstgr.cloud/webhook/youtube-to-h5p

## Workflow Structure

```
┌─────────────────────┐
│  Webhook - Start    │
│  (POST)             │
│  /youtube-to-h5p    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Get YouTube URL Row │
│ (Supabase)          │
│ Table: youtube_urls │
│ Filter: id = $json  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Check Subtitles    │
│  (Switch Node)      │
│  Has Subtitles?     │
└─────┬──────────┬────┘
      │          │
      │ Yes      │ No
      ▼          ▼
┌──────────┐  ┌─────────────────┐
│Generate  │  │ No Subtitles    │
│H5P Course│  │ Error Response  │
│(SSH Node)│  └─────────────────┘
└─────┬────┘
      │
      ▼
┌─────────────────────┐
│ Parse SSH Output    │
│ (Code Node)         │
│ JSON.parse(stdout)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Update YouTube URL  │
│ (Supabase)          │
│ Set moodle_course_id│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Respond to Webhook  │
│ Return course URL   │
└─────────────────────┘
```

## Nodes Overview

### 1. Webhook - Start
- **Type**: `n8n-nodes-base.webhook`
- **Method**: POST
- **Path**: `youtube-to-h5p`
- **Expected Input**:
  ```json
  {
    "youtube_url_id": 123
  }
  ```

### 2. Get YouTube URL Row
- **Type**: `n8n-nodes-base.supabase`
- **Operation**: Get Row
- **Table**: `youtube_urls`
- **Filter**: `id = {{ $json.youtube_url_id }}`
- **Output**: YouTube URL record with title, subtitles, etc.

### 3. Check Subtitles
- **Type**: `n8n-nodes-base.switch`
- **Condition**: Check if `subtitles` field is not empty
- **Outputs**:
  - `has_subtitles` (Output 0): If subtitles exist → Continue to H5P generation
  - `extra` (Output 2): If no subtitles → Return error

### 4. Generate H5P Course
- **Type**: `n8n-nodes-base.ssh`
- **Authentication**: SSH Password (Credential ID: 28)
- **Command**:
  ```bash
  cd /home/claude/python-modules/src/services/h5p && \
  python3 cli_youtube_to_h5p.py \
    --subtitle-text "={{ $json.subtitles }}" \
    --title "={{ $json.title }}" \
    --createcourse \
    --coursename "={{ $json.title }} - Kurs"
  ```
- **Output**: JSON on stdout with `moodle_course_id`

### 5. Parse SSH Output
- **Type**: `n8n-nodes-base.code`
- **Code**:
  ```javascript
  return JSON.parse($input.item.json.stdout);
  ```
- **Purpose**: Convert SSH command stdout (JSON string) to object

### 6. Update YouTube URL
- **Type**: `n8n-nodes-base.supabase`
- **Operation**: Update Row
- **Table**: `youtube_urls`
- **ID**: `{{ $node["Get YouTube URL Row"].json.id }}`
- **Fields**:
  - `moodle_course_id`: `{{ $json.moodle_course_id }}`

### 7. Respond to Webhook
- **Type**: `n8n-nodes-base.respondToWebhook`
- **Response**:
  ```json
  {
    "success": true,
    "course_id": "<moodle_course_id>",
    "course_url": "https://moodle.example.com/course/view.php?id=<course_id>"
  }
  ```

### 8. No Subtitles Error
- **Type**: `n8n-nodes-base.respondToWebhook`
- **Response**:
  ```json
  {
    "error": "No subtitles available",
    "youtube_url_id": "<youtube_url_id>"
  }
  ```

## Node Connections

| From | To | Condition |
|------|-----|-----------|
| Webhook - Start | Get YouTube URL Row | Always |
| Get YouTube URL Row | Check Subtitles | Always |
| Check Subtitles | Generate H5P Course | Has subtitles (Output 0) |
| Check Subtitles | No Subtitles Error | No subtitles (Output 2) |
| Generate H5P Course | Parse SSH Output | Always |
| Parse SSH Output | Update YouTube URL | Always |
| Update YouTube URL | Respond to Webhook | Always |

## Testing

### Test Command
```bash
curl -X POST "https://srv947487.hstgr.cloud/webhook/youtube-to-h5p" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url_id": 123}'
```

### Expected Success Response
```json
{
  "success": true,
  "course_id": 42,
  "course_url": "https://moodle.example.com/course/view.php?id=42"
}
```

### Expected Error Response (No Subtitles)
```json
{
  "error": "No subtitles available",
  "youtube_url_id": 123
}
```

## Prerequisites

1. **Database**: Supabase `youtube_urls` table must have:
   - `id` (primary key)
   - `title` (text)
   - `subtitles` (text)
   - `moodle_course_id` (integer, nullable)

2. **VPS Setup**:
   - SSH access configured (user: `claude`)
   - Python environment at `/home/claude/python-modules`
   - H5P CLI tool at `src/services/h5p/cli_youtube_to_h5p.py`

3. **n8n Credentials**:
   - Supabase connection configured
   - SSH Password account (ID: 28) configured

## Notes

- The workflow is **transactional**: If H5P generation fails, the database is not updated
- The SSH node executes on the VPS host (not in Docker)
- The Python CLI must output valid JSON to stdout for parsing
- The workflow responds immediately after database update (fire-and-forget for Moodle)
