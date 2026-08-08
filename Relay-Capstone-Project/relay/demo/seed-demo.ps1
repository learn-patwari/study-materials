# Relay Demo Seed Script
# Seeds the running Relay app with sample workflows and runs so the console
# at http://localhost:8080 has data to display.
#
# Prerequisites: Relay app running on localhost:8080
# Run from any directory: .\demo\seed-demo.ps1

$BASE = "http://localhost:8080"
$ErrorActionPreference = "Stop"

function Say($msg) { Write-Host "`n== $msg ==" -ForegroundColor Cyan }
function Post($url, $body) {
    try {
        Invoke-RestMethod -Uri "$BASE$url" -Method POST `
            -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 10)
    } catch {
        Write-Host "  ERROR POST $url : $_" -ForegroundColor Red
        throw
    }
}
function Get($url) {
    try {
        Invoke-RestMethod -Uri "$BASE$url" -Method GET
    } catch {
        Write-Host "  ERROR GET $url : $_" -ForegroundColor Red
        throw
    }
}

# ── 1. Health check ────────────────────────────────────────────────────────────
Say "Checking app health"
try { $h = Get "/actuator/health"; Write-Host "Status: $($h.status)" -ForegroundColor Green }
catch { Write-Host "App not reachable at $BASE - is it running?" -ForegroundColor Red; exit 1 }

# ── 2. Workflow A: simple order pipeline (no approval) ────────────────────────
Say "Creating workflow: simple-order"
$wfA = Post "/api/workflows" @{ name = "simple-order" }
$widA = $wfA.id
Write-Host "workflow id: $widA"

Post "/api/workflows/$widA/versions" @{
    start = "validate"
    nodes = @{
        validate = @{ type = "condition"; config = @{ expr = "{{input.amount}} > 0" }; onTrue = "charge"; onFalse = "reject" }
        charge   = @{ type = "http_request"; next = "notify"; config = @{ method = "POST"; url = "https://api.mock/charge" } }
        notify   = @{ type = "notify"; next = $null; config = @{ to = "ops"; template = "Order charged: {{input.amount}}" } }
        reject   = @{ type = "notify"; next = $null; config = @{ to = "ops"; template = "Order rejected: {{input.amount}}" } }
    }
} | Out-Null

Invoke-RestMethod -Uri "$BASE/api/workflows/$widA/versions/1/publish" -Method POST | Out-Null
Write-Host "Published v1"

# Trigger 3 runs
Say "Triggering 3 runs for simple-order"
foreach ($amount in @(500, 1200, 0)) {
    $run = Post "/api/triggers/$widA/manual" @{ amount = $amount }
    Write-Host "  run $($run.runId) - amount=$amount"
    Start-Sleep -Milliseconds 500
}

# ── 3. Workflow B: approval-gated payment ─────────────────────────────────────
Say "Creating workflow: approval-payment"
$wfB = Post "/api/workflows" @{ name = "approval-payment" }
$widB = $wfB.id
Write-Host "workflow id: $widB"

Post "/api/workflows/$widB/versions" @{
    start = "charge"
    nodes = @{
        charge = @{ type = "http_request"; sensitive = $true; next = "done"; config = @{ method = "POST"; url = "https://api.mock/orders" } }
        done   = @{ type = "notify"; next = $null; config = @{ to = "ops"; template = "Payment complete" } }
    }
} | Out-Null

Invoke-RestMethod -Uri "$BASE/api/workflows/$widB/versions/1/publish" -Method POST | Out-Null
Write-Host "Published v1"

# Trigger 2 runs - they will park at WAITING_APPROVAL
Say "Triggering 2 runs for approval-payment (will park at approval gate)"
foreach ($ref in @("TXN-001", "TXN-002")) {
    $run = Post "/api/triggers/$widB/manual" @{ ref = $ref; amount = 2499 }
    Write-Host "  run $($run.runId) - ref=$ref"
    Start-Sleep -Milliseconds 500
}

# ── 4. Workflow C: AI node pipeline ───────────────────────────────────────────
Say "Creating workflow: ai-summary"
$wfC = Post "/api/workflows" @{ name = "ai-summary" }
$widC = $wfC.id
Write-Host "workflow id: $widC"

Post "/api/workflows/$widC/versions" @{
    start = "summarise"
    nodes = @{
        summarise = @{
            type   = "ai"
            next   = "notify"
            config = @{
                prompt         = "Summarise this ticket in one sentence: {{input.text}}"
                outputSchema   = @{
                    type       = "object"
                    required   = @("summary")
                    properties = @{ summary = @{ type = "string" } }
                }
            }
        }
        notify = @{ type = "notify"; next = $null; config = @{ to = "team"; template = "{{steps.summarise.summary}}" } }
    }
} | Out-Null

Invoke-RestMethod -Uri "$BASE/api/workflows/$widC/versions/1/publish" -Method POST | Out-Null
Write-Host "Published v1"

# Trigger 2 runs
Say "Triggering 2 runs for ai-summary"
foreach ($text in @("Login button broken on Safari mobile", "Dashboard loads slowly for enterprise accounts")) {
    $run = Post "/api/triggers/$widC/manual" @{ text = $text }
    Write-Host "  run $($run.runId)"
    Start-Sleep -Milliseconds 500
}

# ── 5. Summary ────────────────────────────────────────────────────────────────
Start-Sleep -Seconds 2
Say "Done - fetching run summary"
$runs = Get "/api/runs"
Write-Host "Total runs: $($runs.Count)"
foreach ($r in $runs) {
    Write-Host "  $($r.id.Substring(0,8))  $($r.status.PadRight(20)) node=$($r.currentNode)"
}

Write-Host "`nOpen http://localhost:8080 to see the console." -ForegroundColor Green
$pending = Get "/api/approvals?status=PENDING"
if ($pending.Count -gt 0) {
    Write-Host "Pending approvals: $($pending.Count) - approve them in the console or via:" -ForegroundColor Yellow
    foreach ($a in $pending) {
        Write-Host "  Invoke-RestMethod -Uri '$BASE/api/approvals/$($a.id)/grant' -Method POST -ContentType 'application/json' -Body '{}'"
    }
}
