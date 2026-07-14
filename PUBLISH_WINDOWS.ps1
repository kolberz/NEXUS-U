$ErrorActionPreference = 'Stop'

$Repository = 'https://github.com/kolberz/NEXUS-U.git'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required. Install it with: winget install --id Git.Git -e --source winget'
}

Set-Location $PSScriptRoot

if (-not (Test-Path '.git')) {
    git init
    git config user.name 'Zach Kolber'
    git config user.email 'kolberzach@gmail.com'
    git add .
    git commit -m 'Publish NEXUS-U v2.6 Native Kernel recovery'
}

git branch -M main

$origin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $origin) {
    git remote set-url origin $Repository
} else {
    git remote add origin $Repository
}

git push -u origin main

git status
git log --oneline -1
