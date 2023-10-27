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

# How to Setup New Xavier

```sh
sudo ./commands/reset_zerotier
sudo ./commands/xavier/boot_control/setup_boot_script
```
