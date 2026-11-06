# SPDX-License-Identifier: AGPL-3.0-or-later
# Builds the TempleOS stopwatch module to WebAssembly with Zig. No bundler, no npm, no libc.
# zig itself is not committed: point ZIG at any zig 0.14.x install.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$zig  = $env:ZIG
if (-not $zig) { $zig = Get-ChildItem (Join-Path $root "tools\zig") -Recurse -Filter zig.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName }
if (-not $zig) { $zig = Join-Path $root "..\netrisplan2\tools\zig\zig-x86_64-windows-0.14.1\zig.exe" }
if (-not (Test-Path $zig)) { throw "zig.exe not found; set ZIG to a zig 0.14.x install" }

$out = Join-Path $root "build\wasm"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$target = "wasm32-freestanding"
$opt    = "-O", "ReleaseSmall"

$exports = @(
  "--export=tsr_seed",
  "--export=tsr_rand",
  "--export=tsr_randf",
  "--export=tsr_state",
  "--export=tsr_mode",
  "--export=tsr_draws",
  "--export=tsr_god_press",
  "--export=tsr_god_cnt",
  "--export=tsr_god_bits",
  "--export=tsr_god_flush"
)
Push-Location $out
& $zig build-exe (Join-Path $root "src\templeos_rng.zig") -target $target $opt -fno-entry $exports
if ($LASTEXITCODE -ne 0) { throw "stopwatch build failed" }
Pop-Location

Write-Host "== built =="
Get-ChildItem $out -Filter *.wasm | ForEach-Object { "{0,10}  {1}" -f $_.Length, $_.Name }
