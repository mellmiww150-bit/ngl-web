$ErrorActionPreference = "Stop"
Write-Host "=== PROJ3CTX DEPLOY ===" -ForegroundColor Cyan

$repoUrl = Read-Host "GitHub repo URL (เช่น https://github.com/USERNAME/ngl-web.git)"
if (-not $repoUrl) { Write-Host "[!] กรอก URL ก่อน"; exit 1 }

Set-Location $PSScriptRoot
if (-not (Test-Path ".git")) { git init }
git add .
git commit -m "PROJ3CTX SPAM NGL - deploy ready"
git branch -M main
git remote remove origin 2>$null
git remote add origin $repoUrl
git push -u origin main

Write-Host "[+] เสร็จ! ไป Render.com -> New Web Service" -ForegroundColor Green
