# entry-file-guard.ps1 - Stop hook (v2)
#
# Rule (2026-07-31): if sources of a project changed during this session,
# that project MUST have a CLAUDE.md entry file, and it MUST have been touched in
# THIS session. Missing -> create. Not updated this session -> update.
#
# Canon: ~/.claude/_project_entry_canon.md
# Log:   ~/.claude/entry-file-guard.log
#
# ASCII ONLY inside this file. Precedent: the first risk-guard.ps1 was written with
# Cyrillic literals and died on the PowerShell 5.1 parser.
#
# Fail-open by design: any internal error exits 0 and logs. A guard that breaks the
# session gets disabled within a day, and then it guards nothing.
#
# v2 fixes, all found by gates on v1:
#   1. stdout forced to UTF-8. PS 5.1 emitted cp866 for Cyrillic paths; Claude Code
#      read it as UTF-8, the JSON was discarded, and the log still said [BLOCK].
#      Green log, zero protection.
#   2. $env:USERPROFILE can never be a project root. <HOME>\package.json
#      made the home folder the root for every marker-less project, which would have
#      produced one CLAUDE.md there and a permanent [OK] for everything else.
#   3. '\OneDrive\' removed from the ignore list. Documents and Desktop are redirected
#      into OneDrive on this machine, so that single entry disabled the guard for most
#      real working folders. The vault is excluded by name instead.
#   4. Staleness is measured against SESSION START, not against the newest source file.
#      Old logic punished the correct behaviour (update the entry file first, then code)
#      and let the wrong one pass. Inverted incentive.
#   5. Changed files are detected by mtime on disk, not only from the transcript.
#      Edits made through Bash/PowerShell and edits made by subagents never appear in
#      the parent transcript, and that is most of how this stack actually works.

$ErrorActionPreference = 'Stop'

# Fix 1: the block message travels through stdout. Force UTF-8 both ways.
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch { }

$LogFile    = Join-Path $env:USERPROFILE '.claude\entry-file-guard.log'
$EntryName  = 'CLAUDE.md'
# v3.1 (gate iteration 2, part B): MinLines was 8, but the canon explicitly allows a
# dormant project a 3-6 line entry file. The guard must not forbid what the canon permits.
$MinLines   = 5

# v3.1: ScanCap was 20000. Measured on this machine: the largest project alone holds
# 21603 .py files - it would hit the cap and never be verified.
# Reference speed: a full 14960-entry walk takes ~1.9s, so 80000 stays inside the 30s
# timeout with room to spare. The scan also exits early on the first recent file.
$ScanCap    = 80000

function Write-GuardLog {
    param([string]$Level, [string]$Message)
    try {
        $stamp = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
        Add-Content -Path $LogFile -Value "$stamp [$Level] $Message" -Encoding utf8
        $item = Get-Item $LogFile -ErrorAction SilentlyContinue
        if ($item -and $item.Length -gt 204800) {
            $keep = Get-Content $LogFile -Tail 400
            Set-Content -Path $LogFile -Value $keep -Encoding utf8
        }
    } catch { }
}

# NOTE: CLAUDE.md is deliberately NOT a project marker. It is the thing we are
# checking for; using it as a marker makes the check circular - any folder that
# already has one is declared a project and validates itself.
$ProjectMarkers = @(
    '.git', 'package.json', 'pyproject.toml', 'requirements.txt', 'go.mod',
    'Cargo.toml', 'composer.json', 'pubspec.yaml', 'Gemfile', 'pom.xml',
    'astro.config.mjs', 'next.config.js'
)

# Directories that are never projects. OneDrive itself is NOT here (v2 fix 3) -
# Documents and Desktop live inside it. Only the vault and machine noise are excluded.
#
# v3 fix (gate iteration 2, NEW-A): the vault fragment used to be written as the
# LATIN string '\Obsidian ' while the folder is Cyrillic - it never matched, so the
# vault was treated as a guarded project and every orchestrator run would have been
# blocked demanding an update to the knowledge base's own CLAUDE.md. Cyrillic literals
# are not allowed in this file, so the vault is matched by the Obsidian marker
# directory '.obsidian' instead of by name. Codepage-proof.
$IgnoreFragments = @(
    '\.claude\',
    '\AppData\',
    '\node_modules\',
    '\.venv\', '\venv\', '\site-packages\', '\.tox\',
    '\dist\', '\build\', '\.next\', '\__pycache__\', '\.git\',
    '\vault\',
    '\_QUARANTINE\', '\_ARCHIVE\', '\_orchestr\'
)

# A folder containing any of these is a knowledge base / note vault, never a code project.
$VaultMarkers = @('.obsidian')

# Heavy directories skipped while scanning for recent changes.
$SkipDirs = @('node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build', '.next', 'site-packages', '.tox')

$CodeExtensions = @(
    '.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.ps1', '.sh', '.bash',
    '.astro', '.vue', '.svelte', '.go', '.rs', '.java', '.rb', '.php', '.sql',
    '.html', '.css', '.scss', '.toml', '.service', '.yml', '.yaml'
)

function Test-Ignored {
    param([string]$Path)
    foreach ($frag in $IgnoreFragments) { if ($Path -like "*$frag*") { return $true } }
    return $false
}

function Get-ProjectRoot {
    param([string]$FilePath)
    try {
        $home_ = $env:USERPROFILE.TrimEnd('\')
        $dir = if (Test-Path $FilePath -PathType Container) { $FilePath } else { Split-Path -Parent $FilePath }
        $depth = 0
        while ($dir -and $depth -lt 8) {
            $cur = $dir.TrimEnd('\')

            # v2 fix 2: the home folder is never a project, whatever manifests sit in it.
            if ($cur -ieq $home_) { return $null }

            # v3 fix (gate iteration 2): the old guard compared STRING LENGTHS against the
            # home path, which killed every project on another drive - D:\work\app never
            # resolved even with a .git in it. A drive root is the real stop condition.
            if ($cur -match '^[A-Za-z]:\\?$') { return $null }

            # v3 fix (NEW-A): a note vault is not a code project.
            foreach ($vm in $VaultMarkers) {
                if (Test-Path (Join-Path $dir $vm)) { return $null }
            }

            foreach ($marker in $ProjectMarkers) {
                if (Test-Path (Join-Path $dir $marker)) { return $dir }
            }
            $parent = Split-Path -Parent $dir
            if (-not $parent -or $parent -eq $dir) { break }
            $dir = $parent
            $depth++
        }
    } catch { }
    return $null
}

# Fix 5: ask the filesystem what changed, not the transcript.
# v3 fix (gate iteration 2, MEDIUM): hitting the scan cap used to return $null - the
# same value as "nothing changed here". "Did not look" and "looked and found nothing"
# are different answers and must not share a return value.
function Get-RecentSource {
    param([string]$Root, [datetime]$Since)
    $seen = 0
    $stack = New-Object System.Collections.Stack
    $stack.Push($Root)
    while ($stack.Count -gt 0) {
        $dir = $stack.Pop()
        try { $entries = [System.IO.Directory]::GetFileSystemEntries($dir) } catch { continue }
        foreach ($e in $entries) {
            if ($seen -ge $ScanCap) { return '__CAP__' }
            $seen++
            try {
                if ([System.IO.Directory]::Exists($e)) {
                    $leaf = Split-Path $e -Leaf
                    if ($SkipDirs -contains $leaf) { continue }
                    $stack.Push($e)
                } else {
                    $ext = [System.IO.Path]::GetExtension($e).ToLower()
                    if ($CodeExtensions -notcontains $ext) { continue }
                    if ([System.IO.File]::GetLastWriteTime($e) -gt $Since) { return $e }
                }
            } catch { continue }
        }
    }
    return $null
}

try {
    # Read stdin as raw UTF-8. [Console]::In honours the console codepage, which on a
    # ru-RU box is cp866 - Cyrillic paths arrive mangled and never match anything.
    $stdin  = [Console]::OpenStandardInput()
    $reader = New-Object System.IO.StreamReader($stdin, (New-Object System.Text.UTF8Encoding($false)))
    $raw    = $reader.ReadToEnd()
    if (-not $raw) { exit 0 }
    $payload = $raw | ConvertFrom-Json

    if ($payload.stop_hook_active -eq $true) {
        Write-GuardLog 'SKIP' 'stop_hook_active=true, not re-blocking'
        exit 0
    }

    $transcript = $payload.transcript_path
    if (-not $transcript -or -not (Test-Path $transcript)) {
        Write-GuardLog 'SKIP' "no transcript at '$transcript'"
        exit 0
    }

    # Session start: when this transcript was created.
    #
    # v3 fix (gate iteration 2, NEW-B): transcripts are reused by --continue, and some
    # live for days (measured: 23 of 140 older than 12h, max 91h). Taking CreationTime
    # literally stretched "this session" across days, which silently passed an entry
    # file updated two days ago in an earlier sitting. Clamp the window to 8 hours.
    $sessionStart = (Get-Item $transcript).CreationTime
    $now = Get-Date
    $floor = $now.AddHours(-8)
    if ($sessionStart -gt $now) { $sessionStart = $now.AddHours(-1) }
    if ($sessionStart -lt $floor) { $sessionStart = $floor }

    # Candidate projects: everything the transcript mentions, plus cwd.
    $candidates = New-Object System.Collections.Generic.HashSet[string]
    # v4 fix (2026-08-05): the cwd-derived root was added WITHOUT the ignore check,
    # while the transcript-derived root below (see 'Test-Ignored ($r + ...)') always had it.
    # That asymmetry made the guard fire on its own home: a Bash call rewrites
    # ~/.claude/shell-snapshots/snapshot-bash-*.sh, the folder got picked up as a
    # project, and the session was told to update the GLOBAL CLAUDE.md because of a
    # throwaway shell snapshot. Fourth false positive of the same family - and a hook
    # that cries wolf is worse than no hook: people learn to click past it.
    if ($payload.cwd) {
        $r = Get-ProjectRoot $payload.cwd
        if ($r -and -not (Test-Ignored ($r.TrimEnd('\') + '\'))) { [void]$candidates.Add($r) }
    }
    foreach ($line in [System.IO.File]::ReadLines($transcript)) {
        if ($line -notmatch 'file_path') { continue }
        try { $evt = $line | ConvertFrom-Json } catch { continue }
        $content = $evt.message.content
        if (-not $content -or $content -is [string]) { continue }
        foreach ($block in $content) {
            if ($block.type -ne 'tool_use') { continue }
            # v3 fix (gate iteration 2, MEDIUM): the tool-name filter had been dropped,
            # so a mere Read made a folder a candidate. Only writes count.
            if ($block.name -notin @('Write', 'Edit', 'NotebookEdit')) { continue }
            $fp = $block.input.file_path
            if (-not $fp) { continue }
            if (Test-Ignored $fp) { continue }
            $r = Get-ProjectRoot $fp
            if ($r -and -not (Test-Ignored ($r + '\'))) { [void]$candidates.Add($r) }
        }
    }

    if ($candidates.Count -eq 0) { exit 0 }

    $violations = @()
    $checked = @()
    foreach ($root in $candidates) {
        $recent = Get-RecentSource -Root $root -Since $sessionStart
        if ($recent -eq '__CAP__') {
            Write-GuardLog 'WARN' "scan cap ($ScanCap) hit, project NOT verified: $root"
            continue
        }
        if (-not $recent) { continue }   # project untouched this session
        $checked += $root

        $entry = Join-Path $root $EntryName

        if (-not (Test-Path $entry)) {
            $violations += [PSCustomObject]@{ Root = $root; Kind = 'MISSING'; Detail = "no $EntryName in project root"; Proof = $recent }
            continue
        }

        $lines = 0
        try { $lines = (Get-Content $entry | Where-Object { $_.Trim().Length -gt 0 }).Count } catch { }
        if ($lines -lt $MinLines) {
            $violations += [PSCustomObject]@{ Root = $root; Kind = 'STUB'; Detail = "$EntryName has only $lines non-empty lines - placeholder, not an entry file"; Proof = $recent }
            continue
        }

        # Fix 4: was it touched in THIS session?
        if ((Get-Item $entry).LastWriteTime -lt $sessionStart) {
            $mins = [int]((Get-Date) - $sessionStart).TotalMinutes
            $violations += [PSCustomObject]@{ Root = $root; Kind = 'STALE'; Detail = "sources changed during this session ($mins min) but $EntryName was not updated"; Proof = $recent }
        }
    }

    if ($violations.Count -eq 0) {
        # v3 fix (gate iteration 2, MEDIUM): OK used to be written for every candidate,
        # including ones that were never verified. A log line that says OK about a folder
        # nobody checked is exactly the false comfort this hook exists to prevent.
        foreach ($root in $checked) { Write-GuardLog 'OK' "entry file in order: $root" }
        exit 0
    }

    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine('ENTRY FILE GUARD: project sources changed in this session, but the project entry file is missing, stale or a stub.')
    [void]$sb.AppendLine('')
    foreach ($v in $violations) {
        Write-GuardLog 'BLOCK' "$($v.Kind) :: $($v.Root) :: $($v.Detail)"
        [void]$sb.AppendLine("- [$($v.Kind)] $($v.Root)")
        [void]$sb.AppendLine("  $($v.Detail)")
        [void]$sb.AppendLine("  changed this session: $($v.Proof)")
        [void]$sb.AppendLine('')
    }
    [void]$sb.AppendLine('Required before finishing: create or update CLAUDE.md in each project root above.')
    [void]$sb.AppendLine('Rules: ~/.claude/_project_entry_canon.md . Target under 200 lines.')
    [void]$sb.AppendLine('Selection axis is derivability, NOT topic: do not write what the model can get by reading the code (file-by-file descriptions, a folder tree that duplicates ls, a dependency list copied from the manifest). Do write what cannot be derived: entry points, where to make which edit, gotchas, external links, project-specific architectural decisions.')
    [void]$sb.AppendLine('A one-line placeholder does not satisfy this rule. If the project genuinely needs no entry file (one-off script, throwaway folder), say so to the user explicitly instead of skipping silently.')

    # Write raw UTF-8 bytes straight to the stream. Write-Output goes through the
    # console encoding and corrupts non-ASCII paths - that is exactly how v1 failed.
    $json  = @{ decision = 'block'; reason = $sb.ToString() } | ConvertTo-Json -Compress
    $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($json)
    $out   = [Console]::OpenStandardOutput()
    $out.Write($bytes, 0, $bytes.Length)
    $out.Flush()
    exit 0

} catch {
    Write-GuardLog 'ERROR' ("guard failed, failing open: " + $_.Exception.Message)
    exit 0
}
