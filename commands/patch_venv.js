import { FileSystem, glob } from "https://deno.land/x/quickr@0.6.31/main/file_system.js"
import { Console } from "https://deno.land/x/quickr@0.6.31/main/console.js"
import { run, Stdout, Stderr } from "https://deno.land/x/quickr@0.6.31/main/run.js"

// depends on
    // system_tools having a variable named "cc" with a lib folder
    // patchelf executable
    // VIRTUAL_ENV existing

if (Console.env.VIRTUAL_ENV) {
    const ccLibsFolder = JSON.parse(Console.env.__FORNIX_NIX_PATH_EXPORT_FILE).libPathFor.cc
    const venvInfo = await FileSystem.info(Console.env.VIRTUAL_ENV)
    if (!ccLibsFolder) {
        console.log(`\n\n        I expected the system_tools.yaml to have a \`saveVariableAs: cc\`\n        Usually something like:\n            - (package):\n                load: [ "stdenv", "cc", "cc" ]\n                saveVariableAs: cc\n\n        but I didn't see one, or the lib folder didnt exist\n`)
    } else {
        if (venvInfo.isFolder) {
            const sharedObjectFiles = await glob(`${Console.env.VIRTUAL_ENV}/lib/**/*.so`)
            for (const eachSharedObjectFile of sharedObjectFiles) {
                // intentionally not awaited
                run`patchelf --set-rpath ${ccLibsFolder} ${eachSharedObjectFile}`
            }
        } else {
            console.log(`I don't see a venv folder, so it's kinda hard for me to patch it`)
            // 
        }
    }
}
