# risk-guard.ps1 -- PreToolUse hook: block irreversible / outward-facing actions
#
# Protocol v2.8.0, section "Risk of action". Orthogonal to gates:
# gates measure OUTPUT QUALITY, this measures IRREVERSIBILITY.
# A perfectly-written `rm -rf` is still a catastrophe.
#
# high = irreversible OR outward-facing -> deny (exit 2) + reason on stderr.
# Everything else passes silently (exit 0).
#
# Native permission prompts do NOT cover this: they go quiet under
# bypassPermissions. This hook works regardless.
#
# Wired into settings.json from day one -- an unwired hook is protect-canon #2
# (written 04.05, never wired, 0 hits in 2.5 months, deleted 17.07).
#
# !! ASCII-ONLY. PowerShell 5.1 corrupts Cyrillic inside .ps1 -> ParserError.
# !! First version of this file was written with Russian strings and was DEAD
# !! on arrival (exit 1 on every command). Do not reintroduce Cyrillic here.
# !! Russian-facing text belongs in the protocol, not in this script.

$ErrorActionPreference = 'SilentlyContinue'

$log = Join-Path $env:USERPROFILE '.claude\risk-guard.log'
function Write-Log($msg) {
    Add-Content -Path $log -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) -Encoding utf8
}
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 200KB)) {
    Get-Content $log -Tail 300 | Set-Content $log -Encoding utf8
}

# --- read hook payload -------------------------------------------------
# stdin FIRST: that is the channel Claude Code actually uses for PreToolUse.
# Fixed 2026-08-31. The hook read only $args[0] and
# $env:CLAUDE_HOOK_INPUT, so every real invocation fell through to `exit 0`
# and the log stayed empty for 45 days -- it looked installed and enforced
# nothing. Verified by mutation: the same payload
# `git push --force origin main` gives exit 0 via $args[0] and exit 2 via
# stdin after this fix. The neighbouring secret-guard.ps1 was healthy all
# along precisely because it reads [Console]::In.
$raw = $null
try { if (-not [Console]::IsInputRedirected) { } else { $raw = [Console]::In.ReadToEnd() } } catch { }
if (-not $raw) { $raw = $args[0] }
if (-not $raw) { $raw = $env:CLAUDE_HOOK_INPUT }
if (-not $raw) { exit 0 }   # manual/test run -> silent pass

try { $payload = $raw | ConvertFrom-Json } catch { exit 0 }

if ($payload.tool_name -ne 'Bash') { exit 0 }   # shell commands only

$cmd = $payload.tool_input.command
if (-not $cmd) { exit 0 }

# --- CONFIG: your production hosts -------------------------------------
# ProdHosts: ssh aliases / hostnames as you type them (`ssh prod ...`).
#            Empty list = every ssh host counts as production.
# OwnHosts:  IPs / hostnames of your OWN servers; HTTP writes to them are
#            not "third-party". Empty list = only localhost is exempt.
# Refresh both when servers change: a rule that guards a decommissioned
# alias guards nothing (silent gap), and an own-host list with a dead IP
# produces false denies on the live one.
$ProdHosts = @()
$OwnHosts  = @()
$hostsRe = if ($ProdHosts.Count -gt 0) { ($ProdHosts | ForEach-Object { [regex]::Escape($_) }) -join '|' } else { '[\w.@:-]+' }
$ownRe   = (@('localhost', '127\.0\.0\.1') + @($OwnHosts | ForEach-Object { [regex]::Escape($_) })) -join '|'

# --- HIGH-risk patterns (protocol v2.8.0, closed list) -----------------
# Keep 'why' strings ASCII. They are shown to the orchestrator, which
# translates for the user.
$highRisk = @(
    @{ p = 'git\s+push\s+.*(--force|-f\b)';                      why = 'git push --force: rewrites shared history, irreversible' },
    @{ p = 'git\s+reset\s+--hard\s+origin/(main|master)';         why = 'git reset --hard on shared branch: destroys work' },
    @{ p = 'git\s+push\s+.*--delete|git\s+branch\s+-D\s';         why = 'deleting branch/tag: irreversible' },
    @{ p = 'rm\s+-rf\s+(/|~|\$HOME)';                             why = 'rm -rf on root/home: irreversible' },
    @{ p = 'Remove-Item\s+.*-Recurse.*-Force';                    why = 'recursive force delete, no recycle bin: irreversible' },
    @{ p = 'DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE';            why = 'DROP/TRUNCATE: data cannot be restored' },
    # Production hosts come from $ProdHosts above (see CONFIG).
    @{ p = 'ssh\s+(' + $hostsRe + ')\b.*(systemctl\s+(restart|stop)|docker\s+(down|rm))'; why = 'prod service restart/stop: live projects of other people' },
    @{ p = 'ssh\s+(' + $hostsRe + ')\b.*rm\s+-rf';               why = 'rm -rf on production: irreversible' },
    @{ p = 'crontab\s+-r';                                        why = 'crontab -r: wipes all cron jobs at once' },
    # Writes to our OWN hosts ($OwnHosts above) and to localhost are not third-party.
    @{ p = 'curl\s+.*-X\s*(POST|PUT|DELETE|PATCH)\s+https?://(?!' + $ownRe + ')'; why = 'write to a THIRD-PARTY api: outward-facing, cannot be recalled' },
    @{ p = 'api\.telegram\.org.*(sendMessage|sendPhoto|sendVideo|sendDocument)'; why = 'sending a message to a human: cannot be unsent' }
)

# Strip arguments of echo/printf before matching. Added 2026-08-31 together with
# the stdin fix: the very first live invocations logged DENY for
# `echo "... git push --force origin main"` -- text, not an action. A guard that
# fires on quoted text trains its reader to ignore it, which is the same defect
# as an alert that cried 545 times in 5 days. Real commands after a
# separator (`echo x; git push --force`) are still matched: only the echo
# argument itself is blanked, not the rest of the line.
$cmdForMatch = [regex]::Replace(
    $cmd,
    '(?<=\b(?:echo|printf)\s)("[^"]*"|''[^'']*''|[^;|&\r\n]*)',
    ' ')

foreach ($rule in $highRisk) {
    if ($cmdForMatch -match $rule.p) {
        $short = $cmd.Substring(0, [Math]::Min(120, $cmd.Length))
        Write-Log ("DENY: {0} | cmd: {1}" -f $rule.why, $short)

        $reason = "RISK-GUARD (protocol v2.8.0): this action is rated HIGH -- $($rule.why). " +
                  "The protocol requires STOP and asking the user first, not 'did it and reported after'. " +
                  "If the user has already approved this exact action in the current conversation, tell them the hook fired and ask them to confirm once more."

        [Console]::Error.WriteLine($reason)
        exit 2
    }
}

exit 0
