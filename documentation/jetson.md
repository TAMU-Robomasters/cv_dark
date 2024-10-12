
connecting to tamu wifi:
- Security: WPA & WPA2 Enterprise
- Authentication: Protected EAP (PEAP)
- No CA certificate is required
- Inner Authenication: MSCHAPv2

set power mode to be 20W two core


If setting up from scratch, see `commands/xavier/setup`
That script will run all of these:
- `./commands/setup/ssh_server`
- `./commands/setup/zerotier`
- `./commands/setup/cli_tools`
- `./commands/setup/opencv`
- `./commands/setup/onyx`
- `./commands/setup/realsense`
- `./commands/setup/zed`


Finally, when ready for competition, run `commands/xavier/boot_control/setup_boot_script`
If the boot script is already setup, just edit `commands/xavier/boot_control/boot_command.ignore`