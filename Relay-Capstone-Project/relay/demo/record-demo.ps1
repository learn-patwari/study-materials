# ============================================================
#  Relay - Recorded Demo Script
#  Run this while screen-recording. It walks through the full
#  Relay feature set with narrated pauses at each step.
#
#  Prerequisites: Relay app running on localhost:8080
#  Usage: .\demo\record-demo.ps1
# ============================================================

$BASE  = "http://localhost:8080"
$PAUSE = 2   # seconds between steps - increase if narrating live

# ── Helpers ──────────────────────────────────────────────────
function Banner($text) {
    $line = "=" * 60
    Write-Host ""
    Write-Host $line                        -ForegroundColor Magenta
    Write-Host "  $text"                    -ForegroundColor Magenta
    Write-Host $line                        -ForegroundColor Magenta
    Start-Sleep -Seconds $PAUSE
}

function Step($text) {
    Write-Host ""
    Write-Host ">>> $text" -ForegroundColor Cyan
    Start-Sleep -Seconds 1
}

function OK($text)   { Write-Host "    [OK] $text"   -ForegroundColor Green  }
function INFO($text) { Write-Host "    [--] $text"   -ForegroundColor Yellow }
function SHOW($text) { Write-Host "    $text"        -ForegroundColor White  }

function Post($url, $body) {
    Invoke-RestMethod -Uri "$BASE$url" -Method POST `
        -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 10)
}
function GET($url) { Invoke-RestMethod -Uri "$BASE$url" -Method GET }

# ── 0. Health check ──────────────────────────────────────────
Banner "RELAY - AI Workflow Orchestrator  |  Live Demo"

Step "Verifying Relay is running..."
try {
    $h = GET "/actuator/health"
    OK "App is UP  (status: $($h.status))"
} catch {
    Write-Host "ERROR: App not reachable at $BASE" -ForegroundColor Red
    exit 1
}
Start-Sleep -Seconds $PAUSE

# ── 1. Create workflow ────────────────────────────────────────
Banner "STEP 1 - Create & Publish a Workflow"

Step "Creating workflow: 'order-pipeline'"
$wf  = Post "/api/workflows" @{ name = "order-pipeline" }
$wid = $wf.id
OK "Created  id=$($wid.Substring(0,8))..."
Start-Sleep -Seconds $PAUSE

Step "Saving workflow definition (condition → http → notify)"
Post "/api/workflows/$wid/versions" @{
    start = "validate"
    nodes = @{
        validate = @{
            type   = "condition"
            config = @{ expr = "{{input.amount}} > 100" }
            onTrue = "charge"; onFalse = "reject"
        }
        charge = @{
            type      = "http_request"
            sensitive = $true
            next      = "notify"
            config    = @{ method = "POST"; url = "https://api.mock/charge" }
        }
        notify = @{
            type   = "notify"; next = $null
            config = @{ to = "ops"; template = "Charged {{input.amount}}" }
        }
        reject = @{
            type   = "notify"; next = $null
            config = @{ to = "ops"; template = "Rejected - too small" }
        }
    }
} | Out-Null
OK "Draft saved"

Step "Publishing v1..."
Invoke-RestMethod -Uri "$BASE/api/workflows/$wid/versions/1/publish" -Method POST | Out-Null
OK "Published - workflow is now triggerable"
Start-Sleep -Seconds $PAUSE

# ── 2. Trigger runs ───────────────────────────────────────────
Banner "STEP 2 - Trigger Runs"

Step "Triggering run #1  (amount=500  →  should hit approval gate)"
$r1 = Post "/api/triggers/$wid/manual" @{ amount = 500; customer = "Alice" }
OK "Run started  id=$($r1.runId.Substring(0,8))..."
Start-Sleep -Seconds 2

Step "Checking run #1 status..."
$s1 = GET "/api/runs/$($r1.runId)"
INFO "Status: $($s1.status)   current_node: $($s1.currentNode)"
Start-Sleep -Seconds $PAUSE

Step "Triggering run #2  (amount=50  →  should be rejected by condition)"
$r2 = Post "/api/triggers/$wid/manual" @{ amount = 50; customer = "Bob" }
OK "Run started  id=$($r2.runId.Substring(0,8))..."
Start-Sleep -Seconds 2

$s2 = GET "/api/runs/$($r2.runId)"
INFO "Status: $($s2.status)"
Start-Sleep -Seconds $PAUSE

# ── 3. Inspect trace ──────────────────────────────────────────
Banner "STEP 3 - Inspect the Execution Trace"

Step "Fetching trace for run #2 (the rejected run)..."
$trace = GET "/api/runs/$($r2.runId)/trace"
SHOW "Trace entries:"
foreach ($t in $trace) {
    $nodeLabel = if ($t.nodeId) { $t.nodeId } else { "-" }
    SHOW "  [$($t.kind.PadRight(20))]  node=$nodeLabel"
}
Start-Sleep -Seconds $PAUSE

# ── 4. Human approval gate ────────────────────────────────────
Banner "STEP 4 - Human Approval Gate"

Step "Listing pending approvals..."
$pending = GET "/api/approvals?status=PENDING"
if ($pending.Count -eq 0) {
    INFO "No pending approvals yet - waiting 3s..."
    Start-Sleep -Seconds 3
    $pending = GET "/api/approvals?status=PENDING"
}
OK "Pending approvals: $($pending.Count)"
foreach ($a in $pending) {
    SHOW "  approval id=$($a.id.Substring(0,8))...  run=$($a.runId.Substring(0,8))...  node=$($a.nodeId)"
}
Start-Sleep -Seconds $PAUSE

Step "Approving the gate for run #1..."
$apid = $pending[0].id
Post "/api/approvals/$apid/grant" @{ decidedBy = "demo-reviewer" } | Out-Null
OK "Approved by demo-reviewer"
Start-Sleep -Seconds 2

Step "Checking run #1 status after approval..."
for ($i = 0; $i -lt 10; $i++) {
    $s1 = GET "/api/runs/$($r1.runId)"
    if ($s1.status -eq "SUCCEEDED") { break }
    Start-Sleep -Seconds 1
}
OK "Run #1 final status: $($s1.status)"
Start-Sleep -Seconds $PAUSE

# ── 5. Exactly-once guarantee ─────────────────────────────────
Banner "STEP 5 - Exactly-Once Side Effects"

Step "Fetching trace for run #1 - verify charge fired once..."
$t1 = GET "/api/runs/$($r1.runId)/trace"
$chargeEvents = $t1 | Where-Object { $_.nodeId -eq "charge" }
OK "Trace entries for 'charge' node: $($chargeEvents.Count)  (expected: 1)"
Start-Sleep -Seconds $PAUSE

# ── 6. AI node workflow ───────────────────────────────────────
Banner "STEP 6 - AI Node with JSON-Schema Validation"

Step "Creating workflow: 'ai-triage'"
$wfAI  = Post "/api/workflows" @{ name = "ai-triage" }
$widAI = $wfAI.id
OK "Created  id=$($widAI.Substring(0,8))..."

Post "/api/workflows/$widAI/versions" @{
    start = "classify"
    nodes = @{
        classify = @{
            type   = "ai"
            next   = "route"
            config = @{
                prompt       = "Classify this support ticket as 'bug', 'feature', or 'question'. Ticket: {{input.ticket}}"
                outputSchema = @{
                    type       = "object"
                    required   = @("category")
                    properties = @{ category = @{ type = "string"; enum = @("bug","feature","question") } }
                }
            }
        }
        route = @{
            type   = "notify"; next = $null
            config = @{ to = "team"; template = "Ticket classified as: {{steps.classify.category}}" }
        }
    }
} | Out-Null
Invoke-RestMethod -Uri "$BASE/api/workflows/$widAI/versions/1/publish" -Method POST | Out-Null
OK "ai-triage workflow published"
Start-Sleep -Seconds $PAUSE

Step "Triggering AI triage run..."
$rAI = Post "/api/triggers/$widAI/manual" @{ ticket = "Login button is broken on Safari mobile" }
OK "Run started  id=$($rAI.runId.Substring(0,8))..."
Start-Sleep -Seconds 3

$sAI = GET "/api/runs/$($rAI.runId)"
OK "Status: $($sAI.status)"
Start-Sleep -Seconds $PAUSE

# ── 7. Console ────────────────────────────────────────────────
Banner "STEP 7 - Web Console"

Step "Opening Relay Console in browser..."
Start-Process "http://localhost:8080"
INFO "Console shows all runs, traces, and pending approvals"
INFO "Runs auto-refresh every 2 seconds"
Start-Sleep -Seconds $PAUSE

# ── 8. Summary ────────────────────────────────────────────────
Banner "DEMO COMPLETE"

$allRuns = GET "/api/runs"
SHOW ""
SHOW "  Total runs created : $($allRuns.Count)"
SHOW "  Run breakdown:"
foreach ($r in $allRuns) {
    SHOW "    $($r.id.Substring(0,8))...  $($r.status.PadRight(20))  steps=$($r.stepCount)"
}
SHOW ""
OK "Relay demonstrated:"
OK "  - Workflow authoring + versioning + publish"
OK "  - Condition branching"
OK "  - Human approval gates (pause / resume)"
OK "  - Exactly-once side effects"
OK "  - AI node with JSON-Schema validated output"
OK "  - Full execution trace"
OK "  - Live web console"
SHOW ""
