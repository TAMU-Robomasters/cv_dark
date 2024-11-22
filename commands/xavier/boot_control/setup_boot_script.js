#!/usr/bin/env sh
"\"",`$(echo --% ' |out-null)" >$null;function :{};function dv{<#${/*'>/dev/null )` 2>/dev/null;dv() { #>
echo "1.41.3"; : --% ' |out-null <#'; }; deno_version="$(dv)"; deno="$HOME/.deno/$deno_version/bin/deno"; if [ -x "$deno" ];then  exec "$deno" run -q -A --no-lock --no-config "$0" "$@";  elif [ -f "$deno" ]; then  chmod +x "$deno" && exec "$deno" run -q -A --no-lock --no-config "$0" "$@";  fi; has () { command -v "$1" >/dev/null; };  set -e;  if ! has unzip && ! has 7z; then echo "Can I try to install unzip for you? (its required for this command to work) ";read ANSWER;echo;  if [ "$ANSWER" =~ ^[Yy] ]; then  if ! has brew; then  brew install unzip; elif has apt-get; then if [ "$(whoami)" = "root" ]; then  apt-get install unzip -y; elif has sudo; then  echo "I'm going to try sudo apt install unzip";read ANSWER;echo;  sudo apt-get install unzip -y;  elif has doas; then  echo "I'm going to try doas apt install unzip";read ANSWER;echo;  doas apt-get install unzip -y;  else apt-get install unzip -y;  fi;  fi;  fi;   if ! has unzip; then  echo ""; echo "So I couldn't find an 'unzip' command"; echo "And I tried to auto install it, but it seems that failed"; echo "(This script needs unzip and either curl or wget)"; echo "Please install the unzip command manually then re-run this script"; exit 1;  fi;  fi;   if ! has unzip && ! has 7z; then echo "Error: either unzip or 7z is required to install Deno (see: https://github.com/denoland/deno_install#either-unzip-or-7z-is-required )." 1>&2; exit 1; fi;  if [ "$OS" = "Windows_NT" ]; then target="x86_64-pc-windows-msvc"; else case $(uname -sm) in "Darwin x86_64") target="x86_64-apple-darwin" ;; "Darwin arm64") target="aarch64-apple-darwin" ;; "Linux aarch64") target="aarch64-unknown-linux-gnu" ;; *) target="x86_64-unknown-linux-gnu" ;; esac fi;  print_help_and_exit() { echo "Setup script for installing deno  Options: -y, --yes Skip interactive prompts and accept defaults --no-modify-path Don't add deno to the PATH environment variable -h, --help Print help " echo "Note: Deno was not installed"; exit 0; };  for arg in "$@"; do case "$arg" in "-h") print_help_and_exit ;; "--help") print_help_and_exit ;; "-"*) ;; *) if [ -z "$deno_version" ]; then deno_version="$arg"; fi ;; esac done; if [ -z "$deno_version" ]; then deno_version="$(curl -s https://dl.deno.land/release-latest.txt)"; fi;  deno_uri="https://dl.deno.land/release/${deno_version}/deno-${target}.zip"; deno_install="${DENO_INSTALL:-$HOME/.deno/$deno_version}"; bin_dir="$deno_install/bin"; exe="$bin_dir/deno";  if [ ! -d "$bin_dir" ]; then mkdir -p "$bin_dir"; fi;  if has curl; then curl --fail --location --progress-bar --output "$exe.zip" "$deno_uri"; elif has wget; then wget --output-document="$exe.zip" "$deno_uri"; else echo "Error: curl or wget is required to download Deno (see: https://github.com/denoland/deno_install )." 1>&2; fi;  if has unzip; then unzip -d "$bin_dir" -o "$exe.zip"; else 7z x -o"$bin_dir" -y "$exe.zip"; fi; chmod +x "$exe"; rm "$exe.zip";  echo "Deno was installed successfully to $exe";  run_shell_setup() { $exe run -A --reload jsr:@deno/installer-shell-setup/bundled "$deno_install" "$@"; };  if [ -z "$CI" ] && [ -t 1 ] && $exe eval 'const [major, minor] = Deno.version.deno.split("."); if (major < 2 && minor < 42) Deno.exit(1)'; then if [ -t 0 ]; then run_shell_setup "$@"; else run_shell_setup "$@" </dev/tty; fi fi; if command -v deno >/dev/null; then echo "Run 'deno --help' to get started"; else echo "Run '$exe --help' to get started"; fi; echo; echo "Stuck? Join our Discord https://discord.gg/deno";  #>}; $DenoInstall = "${HOME}/.deno/$(dv)"; $BinDir = "$DenoInstall/bin"; $DenoExe = "$BinDir/deno.exe"; if (-not(Test-Path -Path "$DenoExe" -PathType Leaf)) { $DenoZip = "$BinDir/deno.zip"; $DenoUri = "https://github.com/denoland/deno/releases/download/v$(dv)/deno-x86_64-pc-windows-msvc.zip";  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;  if (!(Test-Path $BinDir)) { New-Item $BinDir -ItemType Directory | Out-Null; };  Function Test-CommandExists { Param ($command); $oldPreference = $ErrorActionPreference; $ErrorActionPreference = "stop"; try {if(Get-Command "$command"){RETURN $true}} Catch {Write-Host "$command does not exist"; RETURN $false}; Finally {$ErrorActionPreference=$oldPreference}; };  if (Test-CommandExists curl) { curl -Lo $DenoZip $DenoUri; } else { curl.exe -Lo $DenoZip $DenoUri; };  if (Test-CommandExists curl) { tar xf $DenoZip -C $BinDir; } else { tar -Lo $DenoZip $DenoUri; };  Remove-Item $DenoZip;  $User = [EnvironmentVariableTarget]::User; $Path = [Environment]::GetEnvironmentVariable('Path', $User); if (!(";$Path;".ToLower() -like "*;$BinDir;*".ToLower())) { [Environment]::SetEnvironmentVariable('Path', "$Path;$BinDir", $User); $Env:Path += ";$BinDir"; } }; & "$DenoExe" run -q -A --no-lock --no-config "$PSCommandPath" @args; Exit $LastExitCode; <# 
# */0}`;
import { OperatingSystem } from "https://deno.land/x/quickr@0.6.72/main/operating_system.js"
import { FileSystem, glob } from "https://deno.land/x/quickr@0.6.72/main/file_system.js"
import run from "https://esm.sh/jsr/@david/dax@0.42.0"
import { Console, clearAnsiStylesFrom, black, white, red, green, blue, yellow, cyan, magenta, lightBlack, lightWhite, lightRed, lightGreen, lightBlue, lightYellow, lightMagenta, lightCyan, blackBackground, whiteBackground, redBackground, greenBackground, blueBackground, yellowBackground, magentaBackground, cyanBackground, lightBlackBackground, lightRedBackground, lightGreenBackground, lightYellowBackground, lightBlueBackground, lightMagentaBackground, lightCyanBackground, lightWhiteBackground, bold, reset, dim, italic, underline, inverse, strikethrough, gray, grey, lightGray, lightGrey, grayBackground, greyBackground, lightGrayBackground, lightGreyBackground, } from "https://deno.land/x/quickr@0.6.72/main/console.js"

// helpers
const shellEscape = (arg)=>"'"+arg.replace(/'/g,`'"'"'`)+"'"
const userName = Deno.env.get("USER")
const home = Deno.env.get("HOME")

// 
// 
// parameters
// 
// 

const envVarsFile = FileSystem.makeAbsolutePath(`${home}/.zshrc`)
// note: the .ignore is because we don't want this to be synced with git
const pathToOnBootCommand          = FileSystem.makeAbsolutePath(`${FileSystem.thisFolder}/boot_command.ignore`)
const pathToActualInfinteRunScript = FileSystem.makeAbsolutePath(`${FileSystem.thisFolder}/cv_dark_infinite_run.ignore.sh`)
const pathToBootLogFile            = FileSystem.makeAbsolutePath(`${home}/boot.log`)
const pathToOldBootLogFile         = FileSystem.makeAbsolutePath(`${home}/boot.old.log`)
const projectFolder                = FileSystem.makeAbsolutePath(await FileSystem.walkUpUntil(".git/config"))
const pathToMainPy                 = `${projectFolder}/main/main.py`
const nameOfStartService           = "cv_dark_boot"
const autobootIdFile               = FileSystem.makeAbsolutePath(`${FileSystem.thisFolder}/autoboot_id`)

// 
// this initialized one time (no overwrite)
// 
const defaultBootCommand = `#!/usr/bin/env bash

# Edit me as needed
python3 ${shellEscape(pathToMainPy)} \
    @WE_BLUE \
    @BOARD=XAVIER \
    @GPU=TENSOR_RT \
    @CAMERA=REALSENSE \
    @SHOWTIME \
    autoboot_id:"$(${shellEscape(autobootIdFile)})"
`

// 
// this overwrites every time setup is run
// 
const contentsOfInfiniteRunScript = `#!/usr/bin/env bash

# 
# 
#  !!! THIS IS A GENERATED FILE !!! ${
    // 
    // Note: if you're reading this, ignore the "EDIT THE REAL ONE"
    //       (this file (setup_boot_script.js) is the "real one")
    // 
''}
#  EDIT THE REAL ONE INSIDE OF ${FileSystem.thisFile.replace(/\n/g,"")}
#  then run that file
# 

# note: when the boot script runs NOTHING is setup
#       this script:
#       1. sets up all the normal user stuff
#       2. logs all output to $HOME/boot.log
#       3. runs the following IN A LOOP: ${pathToOnBootCommand.replace(/\n/g,"")}

this_username=${shellEscape(userName)}
this_home=${shellEscape(home)}
boot_log=${shellEscape(pathToBootLogFile)}
old_boot_log=${shellEscape(pathToOldBootLogFile)}

# handle logging file
rm -f "$old_boot_log"
# copy old file
if [ -f "$boot_log" ]
then
    cp "$boot_log" "$old_boot_log"
fi
rm -f "$boot_log"

sudo -u "$this_username" -E this_username="$this_username" this_home="$this_home" -- bash -c ${shellEscape(`
    while true
    do
        . ${shellEscape(envVarsFile)}
        cd ${shellEscape(projectFolder)}
        . ${shellEscape(pathToOnBootCommand)}
        
        echo "#"
        echo "#"
        echo "#"
        echo "# PROCESS DIED"
        echo "# [RESTARTING now]"
        echo "#"
        echo "#"
        echo "#"
    done
`)} 2>>"$boot_log" 1>>"$boot_log"
`

// 
// sanity checks
// 
    if (!OperatingSystem.commonChecks.isLinux || OperatingSystem.commonChecks.isWsl) {
        throw Error(`\n\nThis script is ONLY for the Jetson. DO NOT RUN IT ON YOUR PC.\n\n`)
    }
    if (Deno.env.get("FORNIX_FOLDER")) {
        throw Error(`\n\nDon't run this script inside of the project env! (commands/start)\nIt needs to know the jetsons real home folder, and the project env uses a fake home folder\n`)
    }
    if (!FileSystem.sync.info(pathToMainPy).isFile) {
        throw Error(`\n\n\nI expected the main.py file to exist here:\n    ${pathToMainPy}\nBut it doesn't.\nOpen up the setup_boot_script.js file and fix that path to point to the actual file.\n\n`)
    }
    if (!nameOfStartService.match(/^[a-zA-Z_][a-zA-Z0-9_]+$/)) {
        throw Error(`\n\nInside of ${FileSystem.thisFile}.\nYou must have changed the nameOfStartService to something with invalid characters.\nIt needs to be a valid variable name\n`)
    }
    if (home != `/home/${userName}`) {
        console.warn(`\n\nThere is something weird going on\nNormally ${cyan("$HOME")} is /home/$username (aka it would be ${`/home/${userName}`})\nBut this time ${cyan("$HOME")} was ${home}\n\nIF YOU'RE RUNNING THIS INSIDE OF THE PROJECT ENV (commands/start)\nTHATS A PROBLEM\nIf that^ home is a fake home folder, this is going to break the boot script\n\n`)
        if (!(await Console.askFor.yesNo("Do you want to continue anyway? (yes/no)"))) {
            console.log(`\n\nAight...\n`)
            Deno.exit(1)
        }
        console.log(`\n\nContinuing anyway...\n`)
    }

// 
// 
// note: everything below runs right-now (user manually running the setup command)
// the strings-of-code like contentsOfInfiniteRunScript are what is actually run during boot-up
// 
// 

    // 
    // 
    // (setup) generate files
    // 
    // 

    // generate pathToOnBootCommand if it doesn't exist
    if (!FileSystem.sync.info(pathToOnBootCommand).isFile) {
        console.log(`\n\nGenerating ${pathToOnBootCommand}\n`)
        FileSystem.sync.write({
            path: pathToOnBootCommand,
            data: defaultBootCommand,
        })
        console.log(`Note: moving/renaming that file will break the boot script`)
    }
    // ensure those scripts are executable
    await FileSystem.addPermissions({
        path: pathToOnBootCommand,
        permissions: {
            owner: {
                canExecute: true,
            },
            group: {
                canExecute: true,
            },
            other: {
                canExecute: true,
            }
        },
    })

    // generate pathToActualInfinteRunScript if it doesn't exist
    console.log(`\n\nGenerating ${pathToActualInfinteRunScript}\n`)
    FileSystem.sync.write({
        path: pathToActualInfinteRunScript,
        data: contentsOfInfiniteRunScript,
    })
    // ensure those scripts are executable
    await FileSystem.addPermissions({
        path: pathToActualInfinteRunScript,
        permissions: {
            owner: {
                canExecute: true,
            },
            group: {
                canExecute: true,
            },
            other: {
                canExecute: true,
            }
        },
    })
    
    console.log(`Ensuring boot log files exist:`)
    await FileSystem.ensureIsFile(pathToBootLogFile)
    console.log(`   - ${cyan(pathToBootLogFile)}`)
    await FileSystem.ensureIsFile(pathToOldBootLogFile)
    console.log(`   - ${cyan(pathToOldBootLogFile)}`)

// 
// 
// actually register the service
// 
// 
const onBootRegistration = `[Unit]
Description=CV Dark Boot
After=network.target

[Service]
ExecStart=sudo -- ${shellEscape(pathToActualInfinteRunScript)}

[Install]
WantedBy=default.target
`

const targetPath = `/etc/systemd/system/${nameOfStartService}.service`
console.log(`\nInstalling service\n    name: ${cyan(nameOfStartService)}\n    installing to: ${yellow(targetPath)}\n`)
// NOTE: I would normally do these things using JS/Deno, but they need sudo permission
//       and one way to do that is run them in a shell script
const actionsThatNeedSudo = `
    echo "pipefail means that if any command fails, the script will stop" > /dev/null
    set -o pipefail

    echo ${shellEscape(onBootRegistration)} > ${shellEscape(targetPath)}

    echo "#"
    echo "# starting services"
    echo "#"
    systemctl enable ${nameOfStartService}
    systemctl start ${nameOfStartService}
`

try {
    var { code: exitCode } = await run`sudo bash -c ${actionsThatNeedSudo}`
} catch (error) {
    
}
var success = exitCode == 0
if (!sucess) {
    throw Error(`\n\nFailed: See above for details. For some reason the setup failed.`)
}

console.log(`

Done. Restart should now trigger the boot script to run in an infinite loop.
    ${green`boot script:`} ${pathToOnBootCommand}
    ${green`boot log:`} ${pathToBootLogFile}
    
`)
// (this comment is part of deno-guillotine, dont remove) #>
