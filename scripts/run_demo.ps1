#!/usr/bin/env pwsh
# RecoverAI Full Demo Workflow
# Demonstrates the complete detection-to-recovery lifecycle

$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"

Write-Host "=== RecoverAI Demo Workflow ===" -ForegroundColor Cyan
Write-Host "Backend: $base`n"

function Api($method, $path, $body = $null) {
    $uri = "$base$path"
    $headers = @{ "Content-Type" = "application/json" }
    if ($body) {
        $json = $body | ConvertTo-Json -Depth 5
        return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers -Body $json
    }
    return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers
}

# Step 1: Health check
Write-Host "STEP 1: Checking API health..." -ForegroundColor Yellow
$health = Api "GET" "/health"
Write-Host "  Status: $($health.status), AI: $($health.ai_provider), Payment: $($health.payment_provider)"

# Step 2: Generate synthetic dataset
Write-Host "`nSTEP 2: Generating 100-record synthetic dataset (seed=42)..." -ForegroundColor Yellow
$gen = Api "POST" "/api/v1/imports/generate-synthetic?count=100&seed=42"
Write-Host "  Batch ID: $($gen.batch_id)"
Write-Host "  Imported: $($gen.imported_rows) transactions"
Write-Host "  Scenarios: $($gen.metadata.label_distribution | ConvertTo-Json -Compress)"
$batchId = $gen.batch_id

# Step 3: Check dashboard
Write-Host "`nSTEP 3: Dashboard metrics..." -ForegroundColor Yellow
$dash = Api "GET" "/api/v1/dashboard"
Write-Host "  Total transactions: $($dash.total_transactions)"
Write-Host "  Revenue at risk: INR $($dash.total_revenue_at_risk)"
Write-Host "  Failed payments: $($dash.failed_payment_count)"
Write-Host "  Abandoned checkouts: $($dash.abandoned_checkout_count)"

# Step 4: Run recovery agent on batch
Write-Host "`nSTEP 4: Running recovery agent on batch..." -ForegroundColor Yellow
$process = Api "POST" "/api/v1/recovery/process-batch?batch_id=$batchId&auto_execute=true"
Write-Host "  Processed: $($process.processed) transactions"
Write-Host "  Outcomes: $($process.outcomes | ConvertTo-Json -Compress)"
Write-Host "  Batch action count: $($process.batch_action_count)"

# Step 5: Recovery queue
Write-Host "`nSTEP 5: Recovery queue status..." -ForegroundColor Yellow
$queue = Api "GET" "/api/v1/recovery/queue"
Write-Host "  Total cases: $($queue.total)"

# Step 6: Audit trail
Write-Host "`nSTEP 6: Audit trail..." -ForegroundColor Yellow
$audit = Api "GET" "/api/v1/audit?page_size=5"
Write-Host "  Total audit events: $($audit.total)"
Write-Host "  Recent events:"
foreach ($e in $audit.items) {
    Write-Host "    [$($e.event_type)] txn=$($e.transaction_id?.Substring(0,8))... actor=$($e.actor)"
}

# Step 7: Run evaluation (all 3 strategies)
Write-Host "`nSTEP 7: Running strategy evaluation..." -ForegroundColor Yellow
$eval = Api "POST" "/api/v1/evaluation/run?batch_id=$batchId&seed=42"
$runs = $eval.evaluation_runs
Write-Host "  Strategies evaluated:"
foreach ($strategy in @("baseline", "fixed_rule", "ai_assisted")) {
    $r = $runs.$strategy
    $rate = if ($r.recovery_rate_by_count) { "{0:P1}" -f [double]$r.recovery_rate_by_count } else { "0.0%" }
    $rec = [Math]::Round([double]$r.simulated_recovered_value, 0)
    Write-Host "    $strategy : rate=$rate, recovered=INR $rec (simulated)"
}

# Step 8: Final dashboard
Write-Host "`nSTEP 8: Updated dashboard after recovery..." -ForegroundColor Yellow
$dash2 = Api "GET" "/api/v1/dashboard"
Write-Host "  Actions executed: $($dash2.recovery_actions_executed)"
Write-Host "  Blocked actions: $($dash2.blocked_actions)"
Write-Host "  Human review: $($dash2.human_review_count)"
Write-Host "  Simulated recovered: INR $($dash2.actual_recovered_value)"

Write-Host "`n=== Demo Complete ===" -ForegroundColor Green
Write-Host "Open http://localhost:5173 to view the dashboard"
Write-Host "API docs: http://localhost:8000/api/docs"
Write-Host ""
Write-Host "IMPORTANT: All recovery values are simulated outcomes."
Write-Host "           No real financial transactions were processed."
