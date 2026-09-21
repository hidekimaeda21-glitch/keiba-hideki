# KEIBA AI PRO - iPhone 17 Mobile Server with Zero-Password HTTPS Tunnel

$port = 8080
$rootDir = (Get-Location).Path

# Local IPv4
$ipList = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet' -and $_.IPAddress -notmatch '^169\.254\.' -and $_.IPAddress -notmatch '^127\.' }
if ($ipList) {
    $localIp = $ipList[0].IPAddress
} else {
    $localIp = "127.0.0.1"
}
$localUrl = "http://localhost:$($port)/"
$lanUrl = "http://$($localIp):$($port)/"

# Start HTTP Listener
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$($port)/")
try {
    $listener.Prefixes.Add("http://*:$($port)/")
} catch {}
try {
    $listener.Start()
} catch {
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add("http://localhost:$($port)/")
    $listener.Start()
}

# Start Cloudflare Tunnel with --http-host-header localhost (No-Password, No-Login, 100% Free HTTPS)
$tunnelUrl = ""
$cloudflaredPath = Join-Path $rootDir "cloudflared.exe"
$tunnelProc = $null

if (Test-Path $cloudflaredPath) {
    $logFile = Join-Path $rootDir "tunnel.log"
    Remove-Item $logFile -ErrorAction SilentlyContinue
    # CRITICAL: --http-host-header localhost prevents Windows HttpListener 400 Bad Request
    $tunnelProc = Start-Process $cloudflaredPath -ArgumentList "tunnel", "--url", "http://localhost:$port", "--http-host-header", "localhost", "--logfile", $logFile -PassThru
    
    # Wait for tunnel URL
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $logFile) {
            $lines = Get-Content $logFile -ErrorAction SilentlyContinue
            foreach ($line in $lines) {
                if ($line -match 'https://[a-zA-Z0-9-]+\.trycloudflare\.com') {
                    $tunnelUrl = $matches[0]
                    break
                }
            }
            if ($tunnelUrl) { break }
        }
    }
}

$bestUrl = if ($tunnelUrl) { $tunnelUrl } else { $lanUrl }

# Save server_info.json for front-end synchronization
$infoJson = "{`"tunnelUrl`":`"$tunnelUrl`",`"lanUrl`":`"$lanUrl`",`"bestUrl`":`"$bestUrl`"}"
[System.IO.File]::WriteAllText((Join-Path $rootDir "server_info.json"), $infoJson, [System.Text.Encoding]::UTF8)

# Generate high-resolution QR code image for iPhone
try {
    $qrApi = "https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=" + [System.Uri]::EscapeDataString($bestUrl)
    $qrFile = Join-Path $rootDir "iphone_qr.png"
    Invoke-WebRequest -Uri $qrApi -OutFile $qrFile -UseBasicParsing
    
    # Also copy to artifact dir if exists
    $artifactDir = Join-Path $env:USERPROFILE ".gemini\antigravity-ide\brain\7567da90-e8b5-4503-bd6c-15a9c0e921ef"
    if (Test-Path $artifactDir) {
        Copy-Item $qrFile (Join-Path $artifactDir "iphone_qr.png") -Force -ErrorAction SilentlyContinue
    }
    
    # Auto popup QR code image on PC screen
    Start-Process $qrFile
} catch {}

# Copy best URL to clipboard automatically so user can easily paste it
try {
    Set-Clipboard -Value $bestUrl
} catch {}

# Open browser on PC
Start-Process $localUrl

Clear-Host
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  KEIBA AI PRO - NO-PASSWORD FREE HTTPS URL READY" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  [iPhone 17 ACCESS URL - PASSWORD FREE & 100% UNBLOCKED]" -ForegroundColor Cyan
Write-Host "  ==> $bestUrl" -ForegroundColor Green
Write-Host ""
Write-Host "  * Scan the QR Code image on your screen with iPhone 17 camera!" -ForegroundColor White
Write-Host "  * NO PASSWORD, NO ACCOUNT, NO LOGIN REQUIRED!" -ForegroundColor Yellow
Write-Host "  * URL has been copied to your clipboard automatically." -ForegroundColor White
Write-Host "  * Works on both Wi-Fi and 4G/5G mobile data!" -ForegroundColor White
Write-Host "  * In Safari: Tap 'Share' icon -> 'Add to Home Screen'!" -ForegroundColor White
Write-Host ""
Write-Host "  [LAN Backup URL] $lanUrl" -ForegroundColor Gray
Write-Host "  [PC URL]         $localUrl" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Press Ctrl + C or close this window to stop server." -ForegroundColor Gray
Write-Host ""

$mimeTypes = @{
    ".html" = "text/html; charset=utf-8"
    ".css"  = "text/css; charset=utf-8"
    ".js"   = "application/javascript; charset=utf-8"
    ".json" = "application/json; charset=utf-8"
    ".png"  = "image/png"
    ".jpg"  = "image/jpeg"
    ".jpeg" = "image/jpeg"
    ".svg"  = "image/svg+xml"
    ".ico"  = "image/x-icon"
}

try {
    while ($listener.IsListening) {
        try {
            $context = $listener.GetContext()
            $request = $context.Request
            $response = $context.Response

            $relPath = $request.Url.LocalPath.TrimStart('/')
            if ([string]::IsNullOrWhiteSpace($relPath) -or $relPath -eq '/') {
                $relPath = "index.html"
            }

            $relPath = [System.Uri]::UnescapeDataString($relPath)
            $filePath = Join-Path $rootDir $relPath

            if (Test-Path $filePath -PathType Leaf) {
                $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
                $contentType = if ($mimeTypes.ContainsKey($ext)) { $mimeTypes[$ext] } else { "application/octet-stream" }
                
                $bytes = [System.IO.File]::ReadAllBytes($filePath)
                $response.ContentType = $contentType
                $response.ContentLength64 = $bytes.Length
                $response.AddHeader("Access-Control-Allow-Origin", "*")
                $response.AddHeader("Cache-Control", "no-cache")
                $response.OutputStream.Write($bytes, 0, $bytes.Length)
            } else {
                $response.StatusCode = 404
                $notFound = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found")
                $response.OutputStream.Write($notFound, 0, $notFound.Length)
            }
            $response.OutputStream.Close()
        } catch {}
    }
} finally {
    if ($tunnelProc -and -not $tunnelProc.HasExited) {
        Stop-Process -Id $tunnelProc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item (Join-Path $rootDir "tunnel.log") -Force -ErrorAction SilentlyContinue
}
