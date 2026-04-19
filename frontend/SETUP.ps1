# AgriConnect Frontend Complete Setup
Write-Host "Creating AgriConnect source files..." -ForegroundColor Cyan

# Ensure directories exist
$dirs = @("src/contexts", "src/lib", "src/pages", "src/components")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Host "All directories created!" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. I will now create all the source files for you"
Write-Host "2. After that, run: npm run dev"
Write-Host "3. Open http://localhost:3000"
Write-Host ""
