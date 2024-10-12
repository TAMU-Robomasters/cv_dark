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

const defaultBootCommand = `#!/usr/bin/env bash

# Edit me as needed
python3 ${shellEscape(pathToMainPy)} @WE_BLUE @BOARD=XAVIER @GPU=TENSOR_RT @CAMERA=REALSENSE @SHOWTIME
`

const contentsOfInfiniteRunScript = `#!/usr/bin/env bash

# 
# 
#  !!! THIS IS A GENERATED FILE !!!
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
    // if (!OperatingSystem.commonChecks.isLinux || OperatingSystem.commonChecks.isWsl) {
    //     throw Error(`\n\nThis script is ONLY for the Jetson. DO NOT RUN IT ON YOUR PC.\n\n`)
    // }
    if (Deno.env.get("FORNIX_FOLDER")) {
        throw Error(`\n\nDon't run this script inside of the project env! (commands/start)\nIt needs to know the jetsons real home folder, and the project env uses a fake home folder\n`)
    }
    if (!FileSystem.sync.info(pathToMainPy).isFile) {
        throw Error(`\n\n\nI expected the main.py file to exist here:\n    ${pathToMainPy}\nBut it doesn't.\nOpen up the setup_boot_script.js file and fix that path to point to the actual file.\n\n`)
    }
    if (!FileSystem.sync.info(pathToActualInfinteRunScript).isFile) {
        throw Error(`\n\n\nI was going to tell the system to run this file:\n    ${pathToActualInfinteRunScript}\nBut it doesn't exist.\nOpen up the setup_boot_script.js file and fix that path to point to the actual file.\n\n`)
    }
    if (!nameOfStartService.match(/^[a-zA-Z_][a-zA-Z0-9_]+$/)) {
        throw Error(`\n\nInside of ${FileSystem.thisFile}.\nYou must have changed the nameOfStartService to something with invalid characters.\nIt needs to be a valid variable name\n`)
    }
    if (home != `/home/${userName}`) {
        console.warn(`\n\nThere is something weird going on\nNormally ${cyan("$HOME")} is /home/$username (aka it would be ${`/home/${userName}`})\nBut this time ${cyan("$HOME")} was ${home}\n\nIF YOU'RE RUNNING THIS INSIDE OF THE PROJECT ENV (commands/start)\nTHATS A PROBLEM\nIf that^ home is a fake home folder, this is going to break the boot script\n\n`)
        await new Promise(r=>setTimeout(r,14000))
    }

// 
// 
// note: everything below runs right-now
// (but everything above sets what to do on-boot)
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