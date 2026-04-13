param(
    [string]$Repo = "henacodes/stela",
    [string]$Tag = "latest",
    [string]$AppName = "stela",
    [string]$ProductName = "Stela",
    [string]$InstallDir = "$env:LOCALAPPDATA\Stela"
)

$ErrorActionPreference = "Stop"

function Write-Log([string]$Message) {
    Write-Host "`n[stela-install] $Message"
}

function Get-ArchToken {
    switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()) {
        "X64" { return "x64" }
        "Arm64" { return "arm64" }
        default { throw "Unsupported architecture: $([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture)" }
    }
}

function Select-ReleaseAsset([object[]]$Assets, [string]$Arch, [string]$NameHint) {
    $best = $null
    $bestScore = -1

    foreach ($a in $Assets) {
        $n = [string]$a.name
        $url = [string]$a.browser_download_url
        if ([string]::IsNullOrWhiteSpace($n) -or [string]::IsNullOrWhiteSpace($url)) {
            continue
        }

        $nl = $n.ToLowerInvariant()
        $score = 0
        if ($nl.Contains($NameHint.ToLowerInvariant())) { $score += 6 }
        if ($nl.Contains("windows")) { $score += 8 }
        if ($nl.Contains($Arch)) { $score += 8 }
        if ($Arch -eq "x64" -and ($nl.Contains("amd64") -or $nl.Contains("x86_64"))) { $score += 6 }
        if ($Arch -eq "arm64" -and $nl.Contains("aarch64")) { $score += 6 }
        if ($nl.EndsWith(".zip")) { $score += 5 }
        if ($nl.EndsWith(".msi") -or $nl.EndsWith(".exe")) { $score += 2 }

        if ($score -gt $bestScore) {
            $bestScore = $score
            $best = $a
        }
    }

    if ($null -eq $best -or $bestScore -le 0) {
        throw "Could not find a matching Windows release asset."
    }

    return $best
}

$arch = Get-ArchToken
$apiUrl = if ($Tag -eq "latest") {
    "https://api.github.com/repos/$Repo/releases/latest"
} else {
    "https://api.github.com/repos/$Repo/releases/tags/$Tag"
}

Write-Log "Fetching release metadata from $apiUrl"
$release = Invoke-RestMethod -Uri $apiUrl -Headers @{ "User-Agent" = "stela-install-script" }
if ($null -eq $release.assets -or $release.assets.Count -eq 0) {
    throw "No release assets found in $Repo for tag $Tag"
}

$asset = Select-ReleaseAsset -Assets $release.assets -Arch $arch -NameHint $AppName
$assetName = [string]$asset.name
$assetUrl = [string]$asset.browser_download_url
Write-Log "Selected asset: $assetName"

$tmp = Join-Path $env:TEMP ("stela_install_" + [guid]::NewGuid().ToString("N"))
New-Item -Path $tmp -ItemType Directory | Out-Null

try {
    $assetFile = Join-Path $tmp $assetName
    Write-Log "Downloading asset"
    Invoke-WebRequest -Uri $assetUrl -OutFile $assetFile -Headers @{ "User-Agent" = "stela-install-script" }

    $extractDir = Join-Path $tmp "extract"
    New-Item -Path $extractDir -ItemType Directory | Out-Null

    if ($assetName.ToLowerInvariant().EndsWith(".zip")) {
        Expand-Archive -Path $assetFile -DestinationPath $extractDir -Force
    } else {
        throw "Unsupported asset type for Windows installer: $assetName"
    }

    $exe = Get-ChildItem -Path $extractDir -Recurse -Filter "$AppName.exe" | Select-Object -First 1
    if ($null -eq $exe) {
        throw "Could not find $AppName.exe in downloaded asset"
    }

    $bundleDir = $exe.Directory.FullName

    Write-Log "Installing to $InstallDir"
    if (Test-Path $InstallDir) {
        Remove-Item -Path (Join-Path $InstallDir "*") -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        New-Item -Path $InstallDir -ItemType Directory | Out-Null
    }
    Copy-Item -Path (Join-Path $bundleDir "*") -Destination $InstallDir -Recurse -Force

    # Optional PATH update for current user
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    if ($userPath -notlike "*$InstallDir*") {
        $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $InstallDir } else { "$userPath;$InstallDir" }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    }

    $exePath = Join-Path $InstallDir "$AppName.exe"

    Write-Log "Registering Open With associations"
    New-Item -Path "HKCU:\Software\Classes\Stela.Document" -Force | Out-Null
    Set-ItemProperty -Path "HKCU:\Software\Classes\Stela.Document" -Name "(default)" -Value "Stela Document"
    New-Item -Path "HKCU:\Software\Classes\Stela.Document\shell\open\command" -Force | Out-Null
    Set-ItemProperty -Path "HKCU:\Software\Classes\Stela.Document\shell\open\command" -Name "(default)" -Value ('"' + $exePath + '" "%1"')

    New-Item -Path "HKCU:\Software\Classes\.pdf\OpenWithProgids" -Force | Out-Null
    New-ItemProperty -Path "HKCU:\Software\Classes\.pdf\OpenWithProgids" -Name "Stela.Document" -Value "" -PropertyType String -Force | Out-Null

    New-Item -Path "HKCU:\Software\Classes\.epub\OpenWithProgids" -Force | Out-Null
    New-ItemProperty -Path "HKCU:\Software\Classes\.epub\OpenWithProgids" -Name "Stela.Document" -Value "" -PropertyType String -Force | Out-Null

    Write-Log "Install complete"
    Write-Host "Run: $exePath"
    Write-Host "Note: Open a new terminal/session if PATH changes are not visible yet."
}
finally {
    Remove-Item -Path $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
