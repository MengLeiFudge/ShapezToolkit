[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$CleanTmp,
    [switch]$CleanTrash,
    [int]$TmpMaxAgeDays = 7,
    [int]$SourcesWarnMiB = 250,
    [int]$TotalWarnMiB = 512
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$codexRoot = Join-Path $repoRoot '.codex'

if (-not (Test-Path -LiteralPath $codexRoot)) {
    Write-Host "No .codex directory found at $codexRoot"
    exit 0
}

$whitelistDirs = @('drafts', 'tests', 'tmp', 'sources', 'trash')
$whitelistRoot = $whitelistDirs + @('README.md')

function Get-ItemSizeBytes {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return 0L }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) { return [int64]$item.Length }
    $sum = (Get-ChildItem -LiteralPath $Path -Force -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    if ($null -eq $sum) { return 0L }
    return [int64]$sum
}

function Format-Size {
    param([int64]$Bytes)
    if ($Bytes -ge 1GB) { return ('{0:N2} GiB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N2} MiB' -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ('{0:N1} KiB' -f ($Bytes / 1KB)) }
    return "$Bytes B"
}

$candidates = New-Object System.Collections.Generic.List[object]
$warnings = New-Object System.Collections.Generic.List[string]

function Add-Candidate {
    param(
        [string]$Category,
        [string]$Path
    )
    $bytes = Get-ItemSizeBytes -Path $Path
    $rel = $Path.Substring($repoRoot.Length).TrimStart('\', '/')
    $candidates.Add([pscustomobject]@{
        Category = $Category
        Path     = $Path
        Relative = $rel
        Bytes    = $bytes
    })
}

# 1. Non-whitelist top-level entries under .codex
Get-ChildItem -LiteralPath $codexRoot -Force | Where-Object {
    $whitelistRoot -notcontains $_.Name
} | ForEach-Object {
    Add-Candidate -Category 'non-whitelist-root' -Path $_.FullName
}

# 2. Python cache directories inside whitelisted folders
foreach ($dirName in $whitelistDirs) {
    $subRoot = Join-Path $codexRoot $dirName
    if (-not (Test-Path -LiteralPath $subRoot)) { continue }
    Get-ChildItem -LiteralPath $subRoot -Force -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -in @('__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache')
    } | ForEach-Object {
        Add-Candidate -Category 'cache-dir' -Path $_.FullName
    }
}

# 3. Tmp cleanup (all if -CleanTmp, otherwise items older than TmpMaxAgeDays)
$tmpRoot = Join-Path $codexRoot 'tmp'
if (Test-Path -LiteralPath $tmpRoot) {
    $cutoff = (Get-Date).AddDays(-$TmpMaxAgeDays)
    Get-ChildItem -LiteralPath $tmpRoot -Force | ForEach-Object {
        if ($CleanTmp) {
            Add-Candidate -Category 'tmp-all' -Path $_.FullName
        } else {
            $latest = $_.LastWriteTime
            if ($_.PSIsContainer) {
                $newestFile = Get-ChildItem -LiteralPath $_.FullName -Force -Recurse -File -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($null -ne $newestFile -and $newestFile.LastWriteTime -gt $latest) {
                    $latest = $newestFile.LastWriteTime
                }
            }
            if ($latest -lt $cutoff) {
                Add-Candidate -Category "tmp-older-${TmpMaxAgeDays}d" -Path $_.FullName
            }
        }
    }
}

# 4. Trash cleanup (only when -CleanTrash is specified)
$trashRoot = Join-Path $codexRoot 'trash'
if ($CleanTrash -and (Test-Path -LiteralPath $trashRoot)) {
    Get-ChildItem -LiteralPath $trashRoot -Force | ForEach-Object {
        Add-Candidate -Category 'trash' -Path $_.FullName
    }
}

# 5. Misplaced generated artifacts inside drafts/ (warning only, never auto-deleted)
$draftsRoot = Join-Path $codexRoot 'drafts'
if (Test-Path -LiteralPath $draftsRoot) {
    $disallowedDraftExts = @('.spz2bp', '.sig', '.log', '.bin', '.dat', '.png', '.jpg', '.pdf')
    $misplaced = Get-ChildItem -LiteralPath $draftsRoot -Force -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
        ($disallowedDraftExts -contains $_.Extension.ToLowerInvariant()) -or ($_.Length -gt 5MB)
    }
    if ($misplaced) {
        $misBytes = ($misplaced | Measure-Object Length -Sum).Sum
        $warnings.Add(("[drafts] Found {0} generated/large file(s) ({1}) inside .codex/drafts/; move to .codex/tmp/ or .codex/sources/." -f $misplaced.Count, (Format-Size $misBytes)))
    }
}

# Deduplicate nested candidate paths (keep highest-level parent)
$deduped = New-Object System.Collections.Generic.List[object]
$sorted = $candidates | Sort-Object { $_.Path.Length }
foreach ($c in $sorted) {
    $covered = $false
    foreach ($kept in $deduped) {
        if ($c.Path.StartsWith($kept.Path + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            $covered = $true
            break
        }
    }
    if (-not $covered) { $deduped.Add($c) }
}

# Size summary
Write-Host "=== .codex Usage Summary ==="
$totalBytes = 0L
foreach ($name in $whitelistDirs) {
    $p = Join-Path $codexRoot $name
    $b = Get-ItemSizeBytes -Path $p
    $totalBytes += $b
    Write-Host ("  {0,-12} {1,12}" -f ($name + '/'), (Format-Size $b))
    if ($name -eq 'sources' -and ($b / 1MB) -gt $SourcesWarnMiB) {
        $warnings.Add(("[quota] .codex/sources/ is {0} (threshold: {1} MiB)." -f (Format-Size $b), $SourcesWarnMiB))
    }
}
$extraBytes = 0L
Get-ChildItem -LiteralPath $codexRoot -Force | Where-Object { $whitelistDirs -notcontains $_.Name } | ForEach-Object {
    $extraBytes += Get-ItemSizeBytes -Path $_.FullName
}
$totalBytes += $extraBytes
if ($extraBytes -gt 0) {
    Write-Host ("  {0,-12} {1,12}" -f '(root/other)', (Format-Size $extraBytes))
}
Write-Host ("  {0,-12} {1,12}" -f 'TOTAL', (Format-Size $totalBytes))
if (($totalBytes / 1MB) -gt $TotalWarnMiB) {
    $warnings.Add(("[quota] Total .codex/ size is {0} (threshold: {1} MiB)." -f (Format-Size $totalBytes), $TotalWarnMiB))
}

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Warnings ==="
    foreach ($w in $warnings) { Write-Host "  ! $w" }
}

Write-Host ""
$modeLabel = if ($Apply) { 'APPLY (DELETING)' } else { 'DRY-RUN (PREVIEW ONLY)' }
Write-Host "=== Cleanup Candidates [$modeLabel] ==="
if ($deduped.Count -eq 0) {
    Write-Host "  Nothing to clean."
} else {
    $reclaimBytes = 0L
    foreach ($c in $deduped) {
        $reclaimBytes += $c.Bytes
        Write-Host ("  [{0,-18}] {1,-52} {2,10}" -f $c.Category, $c.Relative, (Format-Size $c.Bytes))
        if ($Apply) {
            Remove-Item -LiteralPath $c.Path -Recurse -Force
        }
    }
    Write-Host ("  Total reclaimable: {0} ({1} item(s))" -f (Format-Size $reclaimBytes), $deduped.Count)
    if (-not $Apply) {
        Write-Host "  Re-run with -Apply to execute deletion."
    }
}
