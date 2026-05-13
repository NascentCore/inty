# Ops specific APIs

### 评测（`backend/ops/api/v1/evaluation.py`）

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/evaluation/sessions` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/start` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/results` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/cancel` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/monitor` | WS | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/questions/parse` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/models` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/scoring-criteria/validate` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | PUT | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | DELETE | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/check-background-aspect-ratio` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/upload-cropped-background` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/deploy` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/generated-images` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/generated-images/counts` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/templates` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/templates` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/batch` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/results/export` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/compare` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/new-users` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-activity` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversation-rounds` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-rounds-distribution` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/popular-agents` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/users-hitting-limit` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/agent-analytics` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions-detail` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversations-detail` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversations-detail/user-agent-paginated` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/reports` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/image-generation-failures` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/image-generation-latency` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-daily-messages` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-today-stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/session-messages` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/daily-voice-audios` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/live-chat-stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/live-chat-latency` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/llm-latency` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-generated-images` | GET | `backend/ops/api/v1/evaluation.py` |
