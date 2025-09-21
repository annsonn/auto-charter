param(
    [Parameter(Mandatory=$true)]
    [string]$Root,
    [Parameter(Mandatory=$true)]
    [string]$Image,
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    [string[]]$Inputs
)

$ErrorActionPreference = 'Stop'
$rootPath = [System.IO.Path]::GetFullPath($Root)
$outputDirFull = Join-Path $rootPath $OutputDir
if (-not (Test-Path $outputDirFull)) {
    New-Item -ItemType Directory -Path $outputDirFull | Out-Null
}

function Resolve-InputFile {
    param([string]$Item)
    if ([string]::IsNullOrWhiteSpace($Item)) { return $null }
    if ([System.IO.Path]::IsPathRooted($Item)) {
        if (Test-Path -LiteralPath $Item -PathType Leaf) { return (Get-Item -LiteralPath $Item) }
    } else {
        $direct = Join-Path $rootPath $Item
        if (Test-Path -LiteralPath $direct -PathType Leaf) { return (Get-Item -LiteralPath $direct) }
        $songsPath = Join-Path (Join-Path $rootPath 'songs') $Item
        if (Test-Path -LiteralPath $songsPath -PathType Leaf) { return (Get-Item -LiteralPath $songsPath) }
    }
    return $null
}

$files = @()
if (-not $Inputs -or $Inputs.Count -eq 0) {
    $songsDir = Join-Path $rootPath 'songs'
    if (-not (Test-Path -LiteralPath $songsDir -PathType Container)) {
        Write-Host "Songs directory not found: $songsDir"
        exit 0
    }
    $files = Get-ChildItem -LiteralPath $songsDir -Filter '*.mp3' -File
} else {
    foreach ($item in $Inputs) {
        $resolved = Resolve-InputFile -Item $item
        if ($resolved) {
            $files += $resolved
        } else {
            Write-Warning "Skipping $item (not found)."
        }
    }
}

if (-not $files -or $files.Count -eq 0) {
    Write-Host 'No MP3 files found to convert.'
    exit 0
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($rootPath.Length).TrimStart([char]'\')
    $relativeUnix = $relative -replace '\\','/'
    $basename = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $outRelative = Join-Path $OutputDir ($basename + '.opus')
    $outRelativeUnix = $outRelative -replace '\\','/'
    $outAbs = Join-Path $rootPath $outRelative
    $outDir = [System.IO.Path]::GetDirectoryName($outAbs)
    if (-not (Test-Path -LiteralPath $outDir -PathType Container)) {
        New-Item -ItemType Directory -Path $outDir | Out-Null
    }
    Write-Host "Converting $relative -> $outRelative"

    $dockerArgs = @(
        'run',
        '--rm',
        '-v', "${rootPath}:/work",
        $Image,
        '-y',
        '-i', "/work/$relativeUnix",
        '-c:a', 'libopus',
        '-b:a', '160k',
        "/work/$outRelativeUnix"
    )

    & docker @dockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Conversion failed for $($file.FullName)"
    }
}




