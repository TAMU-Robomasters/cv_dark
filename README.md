### How do I get this code to run?

See [documentation/setup.md](https://github.com/TAMU-Robomasters/cv_dark/blob/master/documentation/setup.md)

### What is this repo?

Its the home of all Tamu RoboMaster's cool code. (If you're looking for *boring* low-level C code you'll have to find the embedded teams repo)<br>
<br>

### How does the code work?

- `main/main.py` is only ~12 lines of code
     - These are the 3 core functions in the codebase:
     - `model.when_frame_arrives()`
     - `aim.when_bounding_boxes_refresh()`
     - `communicate.when_aiming_refreshes()`
- Everything outside of those functions are just helpers for those functions 
- If a tool/function is generic (used in multiple places) put it in the toolbox folder
- If you need to set a constant (like `our_team_color`) do it in the `./main/info.yaml`
    - To use that value in python do:<br>
    ```py
    from toolbox.globals import path_to, config
    config.our_team_color
    ```

# At the competition

1. After ssh-ing into the Xavier, run `./commands/kill_booted_process` to stop the thing from running
2. To change the team color, edit the `commands/xavier/boot_control/boot_command.ignore` change WE_RED to WE_BLUE or vice versa

# How to Setup New Xavier 

Clone the sd card
- There should be an img file in the google drive
- There are command for copying the img file to the sd card in this repo (`commands/tools/export_to_sd_card`)
    - its interactive, so just run the command and follow the instructions

After putting the SD card into the xavier run:

```sh
cd ~/repos/cv_dark
sudo ./commands/reset_zerotier
sudo ./commands/xavier/boot_control/setup_boot_script
```

# Runtime Variable

```py
runtime.aiming
runtime.aiming.center_point
runtime.aiming.target_3d
runtime.aiming.target_status

runtime.modeling
runtime.modeling.best_bounding_box
runtime.modeling.bounding_boxes
runtime.modeling.confidences
runtime.modeling.current_confidence
runtime.modeling.enemy_boxes
runtime.modeling.found_robot

runtime.camera
runtime.camera.frame
runtime.camera.acceleration // only availiable for the D435i
runtime.camera.gyro // only availiable for the D435i

runtime.color_image
runtime.depth_image
runtime.frame_number
runtime.prev_loop_time
runtime.screen_center
runtime.total_fps
```
