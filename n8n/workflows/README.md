# n8n Automation Workflows

This directory contains the n8n workflows used by the **AI-Powered Operating Intelligence Platform / AI Chief of Staff** to automate business notifications and workflow follow-up actions.

The workflows are designed to work with the FastAPI backend and PostgreSQL `automation_logs` table. They do not make business decisions independently. Business issues, task state, priority, and eligibility are determined by the backend first; n8n is used only to execute controlled automation actions such as sending notifications and reporting execution results back to FastAPI.

---

## 1. Included Workflows

| Workflow | File | Webhook Path | Purpose |
|---|---|---|---|
| High Priority Alert | `high_priority_alert.json` | `/webhook/high-priority-alert` | Sends a notification when an active High-priority business issue is triggered by the backend. |
| Task Reminder | `task_reminder.json` | `/webhook/task-reminder` | Sends a reminder for an incomplete task. |
| Overdue Task Escalation | `overdue_task_escalation.json` | `/webhook/overdue-escalation` | Sends an escalation when an incomplete task is past its due date. |

---

## 2. Architecture

```text
FastAPI
   ↓
Validate business state
   ↓
Generate idempotency key
   ↓
Create / reuse automation log
   ↓
Authenticated request to n8n
   ↓
n8n workflow
   ↓
Send notification email
   ↓
Success / Failure callback
   ↓
FastAPI
   ↓
Update automation_logs
```

The backend remains the source of truth for issue priority, task status, due dates, workflow eligibility, duplicate prevention, and automation execution history.

n8n does not directly create tasks, change task status, modify recommendations, or make autonomous business decisions.

---

## 3. Workflow Structure

Each workflow follows the same controlled pattern:

```text
Authenticated Webhook
        ↓
Send Email
       ↙ ↘
 Success   Failure
   ↓         ↓
Success    Failure
Callback   Callback
   ↓         ↓
200        Error
Response   Response
```

### Success path

1. The email is sent.
2. n8n calls the FastAPI callback endpoint.
3. The callback sends `execution_status = Succeeded`.
4. The n8n execution ID is included.
5. FastAPI updates the matching `automation_logs` row.
6. n8n returns a successful webhook response.

### Failure path

1. Email delivery fails.
2. The email node routes through its error output.
3. n8n calls the FastAPI callback endpoint.
4. The callback sends `execution_status = Failed`.
5. Error metadata is recorded.
6. FastAPI updates the corresponding automation log.

---

## 4. FastAPI Endpoints Used

### Trigger endpoints

```text
POST /api/automations/high-priority-alert
POST /api/automations/task-reminder
POST /api/automations/overdue-escalation
```

Trigger requests are protected by:

```text
X-Automation-API-Secret
```

### Callback endpoint

```text
POST /api/automations/log
```

The callback is protected by:

```text
X-N8N-Callback-Secret
```

### Automation log endpoints

```text
GET /api/automation-logs
GET /api/automation-logs/{automation_log_id}
```

---

## 5. Authentication Model

### FastAPI → n8n

The Webhook node uses Header Authentication:

```text
Header Name:
Authorization

Header Value:
Bearer <N8N_OUTBOUND_AUTH_TOKEN>
```

There must be one space between `Bearer` and the token.

### n8n → FastAPI

Callback nodes use:

```text
Header Name:
X-N8N-Callback-Secret

Header Value:
<N8N_CALLBACK_SECRET>
```

### External trigger protection

Requests that trigger an automation through FastAPI use:

```text
X-Automation-API-Secret
```

The three secrets should be different.

---

## 6. Required Environment Configuration

```env
AUTOMATION_ENABLED=true

AUTOMATION_API_SECRET=
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
N8N_OUTBOUND_AUTH_TOKEN=
N8N_CALLBACK_SECRET=

N8N_TIMEOUT_SECONDS=10
N8N_MAX_RETRIES=2
N8N_RETRY_BACKOFF_SECONDS=0.5

N8N_HIGH_PRIORITY_ALERT_PATH=high-priority-alert
N8N_TASK_REMINDER_PATH=task-reminder
N8N_OVERDUE_ESCALATION_PATH=overdue-escalation
```

Do not commit real secret values. `.env` and `.env.test` should remain local and ignored by Git.

---

## 7. n8n Credentials Required

### A. Webhook Header Auth

Credential type:

```text
Header Auth
```

Configuration:

```text
Header Name:
Authorization

Header Value:
Bearer <N8N_OUTBOUND_AUTH_TOKEN>
```

Use this credential in each Webhook node.

### B. Callback Header Auth

Credential type:

```text
Header Auth
```

Configuration:

```text
Header Name:
X-N8N-Callback-Secret

Header Value:
<N8N_CALLBACK_SECRET>
```

Use this credential in both `Record Success Callback` and `Record Failure Callback`.

### C. SMTP Credential

The Send Email node requires a valid SMTP credential. Typical fields include:

```text
SMTP host
SMTP port
Username
Password / App Password
TLS or SSL setting
```

Credentials should be stored inside n8n's credential system and must not be embedded directly inside workflow JSON files.

---

## 8. Email Configuration

Each workflow contains a Send Email node.

Configure:

```text
From Email
To Email
SMTP Credential
```

For initial validation, use a controlled mailbox.

For production deployment, the recipient can later be made dynamic based on manager, owner, role, or escalation policy.

The current workflows generate notification content from deterministic backend data received in the webhook payload. No LLM is used to invent the email content.

---

## 9. Workflow-Specific Behavior

### High Priority Alert

Webhook path:

```text
/webhook/high-priority-alert
```

Purpose: send an immediate notification for an active High-priority issue.

Typical email content includes issue ID, title, business area, priority, priority score, store, product, vendor, summary, and priority reason.

### Task Reminder

Webhook path:

```text
/webhook/task-reminder
```

Purpose: send a reminder for an incomplete task.

The backend prevents reminders for completed tasks and generates a daily idempotency key so the same task reminder is not repeatedly sent on the same day.

Typical email content includes task ID, title, assignee, assigned role, priority, status, due date, business area, and description.

### Overdue Task Escalation

Webhook path:

```text
/webhook/overdue-escalation
```

Purpose: escalate an incomplete task whose due date has passed.

The backend verifies that the task exists, is incomplete, has a due date, and is actually overdue.

Typical email content includes task ID, title, assignee, role, priority, status, due date, related issue, business area, escalation reason, and description.

---

## 10. Idempotency and Duplicate Prevention

FastAPI generates an idempotency key before sending a workflow request to n8n.

If the same automation event is triggered again with the same key:

```text
FastAPI
   ↓
Existing automation log found
   ↓
duplicate = true
   ↓
No second n8n workflow is sent
```

This protects against duplicate reminders, alerts, and escalations.

---

## 11. Automation Logging

Each execution is represented in PostgreSQL `automation_logs`.

Important fields include:

```text
automation_log_id
task_id
issue_id
workflow_name
action_type
execution_status
idempotency_key
n8n_execution_id
attempt_count
http_status_code
message
error_type
error_message
request_metadata
executed_at
```

Typical status progression:

```text
Pending
   ↓
Triggered
   ↓
Succeeded
```

or:

```text
Pending
   ↓
Triggered
   ↓
Failed
```

The final n8n execution ID is stored so an automation log can be traced back to the corresponding n8n execution.

---

## 12. Expression Handling

Runtime values must be configured in **Expression** mode.

### Idempotency key

```text
{{ $('Webhook').item.json.body.idempotency_key }}
```

### n8n execution ID

```text
{{ $execution.id }}
```

The stored value must be the evaluated execution ID, not the literal expression text.

Correct:

```text
105
```

Incorrect:

```text
={{ $execution.id }}
```

Always verify expression mode before publishing a workflow.

---

## 13. Import Procedure

1. Start n8n.
2. Open the n8n editor.
3. Import the required JSON file.
4. Reconnect the Webhook Header Auth credential.
5. Reconnect the callback Header Auth credential.
6. Reconnect the SMTP credential.
7. Configure sender and recipient email addresses.
8. Confirm runtime expressions.
9. Save the workflow.
10. Test the workflow.
11. Publish only after the test succeeds.

---

## 14. Testing Procedure

Each workflow should first be tested using its n8n test webhook:

```text
/webhook-test/<workflow-path>
```

For example:

```text
http://localhost:5678/webhook-test/task-reminder
```

During validation confirm:

```text
Webhook                         Success
Send Email                      Success
Record Success Callback         Success
Respond Success                 Success
```

Also confirm:

- the email arrives;
- FastAPI receives `POST /api/automations/log`;
- FastAPI returns HTTP 200;
- `automation_logs` reaches `Succeeded`;
- a real n8n execution ID is stored.

After successful test-mode validation, publish the workflow and validate the production webhook.

---

## 15. Production Webhook Paths

```text
http://localhost:5678/webhook/high-priority-alert
http://localhost:5678/webhook/task-reminder
http://localhost:5678/webhook/overdue-escalation
```

These endpoints are intended to be called by FastAPI, not normally by users directly.

---

## 16. Security Controls

The automation design includes:

- backend-controlled workflow eligibility;
- separate authentication for FastAPI → n8n and n8n → FastAPI;
- secrets stored outside workflow JSON;
- fixed webhook paths;
- duplicate prevention using idempotency keys;
- idempotent callback handling;
- protection against conflicting terminal status updates;
- retry and HTTP status logging;
- failure metadata logging;
- PostgreSQL execution history;
- no autonomous n8n modification of tasks, recommendations, or business state.

---

## 17. Repository Safety

Before committing exported workflow files:

1. Remove raw secret values.
2. Remove unnecessary instance-specific metadata such as local workflow IDs, version IDs, and instance IDs.
3. Keep credential references only where safe.
4. Confirm no SMTP password is present.
5. Confirm no callback secret is present.
6. Confirm no bearer token is present.
7. Keep `.env` and `.env.test` out of Git.

Useful checks:

```powershell
git diff -- n8n/workflows
git status
```

---

## 18. Local Development

Current local setup:

```text
FastAPI:
http://127.0.0.1:8000

n8n:
http://localhost:5678
```

n8n callback nodes use:

```text
http://127.0.0.1:8000/api/automations/log
```

This is correct while FastAPI and n8n run directly on the same Windows machine.

For containerized or remote deployment, callback and webhook URLs must be changed to addresses reachable between the deployed services.

---

## 19. Running Locally

Start n8n:

```text
n8n start
```

Start FastAPI:

```text
uvicorn backend.app.main:app --reload --env-file .env
```

n8n editor:

```text
http://localhost:5678
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 20. Current Validation Status

Validated successfully:

```text
FastAPI → n8n webhook delivery
n8n Webhook authentication
Email delivery
n8n → FastAPI callback
Callback authentication
PostgreSQL automation logging
Success status updates
Failure-path configuration
Idempotency protection
Duplicate suppression
Real n8n execution ID capture
Published production webhook registration
Invalid webhook credential rejection
```

All three workflows have been individually tested before publication.

---

## 21. Design Principle

n8n is an **execution and orchestration layer**, not the decision engine of the AI Chief of Staff.

```text
Deterministic analytics / AI agents
            ↓
Business decision support
            ↓
Human-approved / backend-controlled action
            ↓
FastAPI
            ↓
n8n
            ↓
Notification / workflow execution
            ↓
automation_logs
```

This keeps automated actions controlled, traceable, auditable, and separate from AI reasoning.

---

## 22. Workflow Files

```text
n8n/
└── workflows/
    ├── README.md
    ├── high_priority_alert.json
    ├── task_reminder.json
    └── overdue_task_escalation.json
```

These files form the automation workflow layer for the AI Chief of Staff platform.
