# Complete API testing script

$baseUrl = "http://localhost:8000"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  API Complete Test Suite" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "TEST 1: Health Check" -ForegroundColor Yellow
Write-Host "--------------------" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health"
    Write-Host "✅ Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Redis: $($health.redis)" -ForegroundColor White
    Write-Host "   Time: $($health.timestamp)" -ForegroundColor White
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nMake sure API is running: python api.py" -ForegroundColor Yellow
    exit 1
}

# Test 2: Submit Toxic Content
Write-Host "`nTEST 2: Submit Toxic Content" -ForegroundColor Yellow
Write-Host "-----------------------------" -ForegroundColor Yellow
try {
    $content1 = @{
        content = "I hate you, you're stupid and should die"
        content_type = "text"
        user_id = "test-user-toxic"
    } | ConvertTo-Json

    $submit1 = Invoke-RestMethod -Uri "$baseUrl/moderate" -Method POST -ContentType "application/json" -Body $content1
    $contentId1 = $submit1.content_id
    Write-Host "✅ Submitted: $contentId1" -ForegroundColor Green
    
    # Wait for processing
    Write-Host "   Waiting 3 seconds for processing..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
    
    # Check status
    try {
        $status1 = Invoke-RestMethod -Uri "$baseUrl/status/$contentId1"
        Write-Host "   Severity: $($status1.severity)" -ForegroundColor White
        Write-Host "   Action: $($status1.action)" -ForegroundColor White
        Write-Host "   Issues: $($status1.detected_issues -join ', ')" -ForegroundColor White
        
        if ($status1.severity -gt 0.3) {
            Write-Host "✅ Toxic content detected correctly!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Severity lower than expected" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Status check failed (worker may not be running)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Submit Spam Content
Write-Host "`nTEST 3: Submit Spam Content" -ForegroundColor Yellow
Write-Host "---------------------------" -ForegroundColor Yellow
try {
    # Submit multiple posts quickly (spam burst)
    $spamUserId = "test-user-spam"
    $contentIds = @()
    
    for ($i = 1; $i -le 6; $i++) {
        $spamContent = @{
            content = "Buy now! Click here! Free money! Post $i"
            content_type = "text"
            user_id = $spamUserId
        } | ConvertTo-Json
        
        $spamSubmit = Invoke-RestMethod -Uri "$baseUrl/moderate" -Method POST -ContentType "application/json" -Body $spamContent
        $contentIds += $spamSubmit.content_id
        Start-Sleep -Milliseconds 500
    }
    
    Write-Host "✅ Submitted 6 spam posts" -ForegroundColor Green
    
    # Check last post
    Start-Sleep -Seconds 3
    $lastId = $contentIds[-1]
    
    try {
        $spamStatus = Invoke-RestMethod -Uri "$baseUrl/status/$lastId"
        
        Write-Host "   Last Post ID: $lastId" -ForegroundColor White
        Write-Host "   Severity: $($spamStatus.severity)" -ForegroundColor White
        Write-Host "   Action: $($spamStatus.action)" -ForegroundColor White
        Write-Host "   Issues: $($spamStatus.detected_issues -join ', ')" -ForegroundColor White
        
        if ($spamStatus.detected_issues -match "spam") {
            Write-Host "✅ Spam detected correctly!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Spam not detected" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Status check failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Submit Clean Content
Write-Host "`nTEST 4: Submit Clean Content" -ForegroundColor Yellow
Write-Host "----------------------------" -ForegroundColor Yellow
try {
    $cleanContent = @{
        content = "This is a nice day. I enjoy spending time with friends."
        content_type = "text"
        user_id = "test-user-clean"
    } | ConvertTo-Json

    $cleanSubmit = Invoke-RestMethod -Uri "$baseUrl/moderate" -Method POST -ContentType "application/json" -Body $cleanContent
    $cleanId = $cleanSubmit.content_id
    Write-Host "✅ Submitted: $cleanId" -ForegroundColor Green
    
    Start-Sleep -Seconds 3
    
    try {
        $cleanStatus = Invoke-RestMethod -Uri "$baseUrl/status/$cleanId"
        
        Write-Host "   Severity: $($cleanStatus.severity)" -ForegroundColor White
        Write-Host "   Action: $($cleanStatus.action)" -ForegroundColor White
        
        if ($cleanStatus.action -eq "approve") {
            Write-Host "✅ Clean content approved correctly!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Expected approval, got $($cleanStatus.action)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Status check failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Submit Appeal
Write-Host "`nTEST 5: Submit Appeal" -ForegroundColor Yellow
Write-Host "---------------------" -ForegroundColor Yellow
try {
    if ($contentId1) {
        $appeal = @{
            content_id = $contentId1
            user_id = "test-user-toxic"
            appeal_reason = "This was taken out of context"
            additional_context = "I was quoting someone else"
        } | ConvertTo-Json

        $appealResult = Invoke-RestMethod -Uri "$baseUrl/appeal" -Method POST -ContentType "application/json" -Body $appeal
        Write-Host "✅ Appeal submitted" -ForegroundColor Green
        Write-Host "   Appeal Granted: $($appealResult.appeal_granted)" -ForegroundColor White
        Write-Host "   New Action: $($appealResult.new_action)" -ForegroundColor White
    } else {
        Write-Host "⚠️  Skipped (no content ID from Test 2)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: User Statistics
Write-Host "`nTEST 6: User Statistics" -ForegroundColor Yellow
Write-Host "-----------------------" -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$baseUrl/stats/user/$spamUserId"
    Write-Host "✅ Stats retrieved" -ForegroundColor Green
    Write-Host "   User: $($stats.user_id)" -ForegroundColor White
    Write-Host "   Recent Posts: $($stats.recent_post_count)" -ForegroundColor White
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  All Tests Completed!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "View interactive docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
