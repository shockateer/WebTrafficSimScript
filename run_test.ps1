<#
.SYNOPSIS
PowerShell wrapper to run the Python Bandwidth Stress Tester.
#>

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# The name of your python script file
$ScriptName = "bandwidth_test.py"

# Input Text Files
$WebsiteList = "websites.txt"
$FileList = "files.txt"

# TIMING SETTINGS
# Total time to run the script (in minutes)
$RunTimeMinutes = 10

# Time to pause between the end of one loop and the start of the next (in seconds)
$LoopDelay = 30

# Time to pause after every single download request (in seconds)
$RequestDelay = 2

# TOGGLE TESTS
# Set these to $true to DISABLE a specific test, or $false to RUN it.
$DisableWebTest = $false
$DisableFileTest = $false

# ============================================================================
# EXECUTION LOGIC
# ============================================================================

Clear-Host
$ErrorActionPreference = "Stop"

# 1. Check if Python is installed/accessible
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not found in your PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.8+ and add it to your PATH."
    Read-Host "Press Enter to exit"
    exit
}

# 2. Check if the script file exists
if (-not (Test-Path $ScriptName)) {
    Write-Host "Error: Could not find '$ScriptName' in this directory." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

# 3. Build the argument list array
$PyArgs = @(
    $ScriptName,
    "-w", $WebsiteList,
    "-f", $FileList,
    "-t", $RunTimeMinutes,
    "-l", $LoopDelay,
    "-r", $RequestDelay
)

# Append flags if user disabled specific tests
if ($DisableWebTest) { $PyArgs += "--no-web" }
if ($DisableFileTest) { $PyArgs += "--no-files" }

# 4. Display Status
Write-Host "Starting Bandwidth Stress Test..." -ForegroundColor Cyan
Write-Host "------------------------------------------" -ForegroundColor DarkGray
Write-Host "Script:    $ScriptName"
Write-Host "Duration:  $RunTimeMinutes Minutes"
Write-Host "Loop Wait: $LoopDelay Seconds"
Write-Host "Req Wait:  $RequestDelay Seconds"
Write-Host "------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# 5. Run the Python Script
# We use the call operator '&' to execute the command constructed from variables
try {
    & python $PyArgs
}
catch {
    Write-Host "An unexpected error occurred: $_" -ForegroundColor Red
}

# 6. Pause at end so window doesn't close immediately
Write-Host ""
Write-Host "Script finished or stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"