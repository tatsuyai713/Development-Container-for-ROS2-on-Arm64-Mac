# Development-Container-for-ROS2-on-Arm64-Mac

**[日本語のセットアップ・使い方ガイド](README_ja.md)**

Run an Ubuntu desktop and a ROS 2 development environment on an Apple Silicon Mac.
Connect through Chrome, Safari, or an RDP client to use Linux applications and development tools.
This edition uses Apple's `container`; Docker Desktop is not required for these instructions.

Follow **setup → build an image → start Ubuntu → connect → work → stop**.
The practical instructions come first; implementation details are at the end.

### What you can do

| Goal | How |
|---|---|
| Operate an Ubuntu desktop from the Mac | Open its HTTPS URL in Chrome or Safari, or connect with an RDP client |
| Learn and develop with ROS 2 | Load ROS 2 in Ubuntu's Konsole, run nodes, and build packages |
| Use Linux applications | Open Chrome inside Ubuntu; enable development tools for editors and LibreOffice |
| Work on Mac source files and documents | Enable home sharing and open `~/host_home` inside Ubuntu |
| Retain your environment between work sessions | Use **Stop Container**, then start it again from the Mac |
| Preserve installed applications for recreation | Use **Save Container Image**, then recreate when needed |

### Choose how to open the desktop

| Connection | Open on the Mac | Example address (UID 501, default ports) |
|---|---|---|
| [Browser](#browser) | Google Chrome or Safari | `https://127.0.0.1:60501` |
| [RDP](#rdp) | An RDP client | `127.0.0.1:3389` |

The browser opens the Selkies client and does not require an RDP client.
RDP requires XRDP to be enabled in the startup configuration. These are separate desktop sessions.
Actual ports depend on your settings; find yours using the steps below.
For an existing installation, go to **Daily use**.

- [First-time setup](#setup)
- [Connect to the desktop](#connect): [Browser](#browser) / [RDP](#rdp) / [Clipboard](#clipboard)
- [Use the desktop icons](#desktop)
- [Daily use](#daily)
- [Save files and share them with the Mac](#files)
- [Use ROS 2 and applications](#usage)
- [Save, restore, and update an environment](#save)
- [Troubleshooting](#troubleshooting)
- [Commands and multiple environments](#commands)
- [Technical details and limitations](#technical)

<a id="setup"></a>
## 1. First-time setup

### Step 1: Check the requirements

| Item | Requirement |
|---|---|
| Mac | Apple Silicon, not Intel |
| macOS | 26 or later |
| Apple container | Project validation used 1.2.2; installation is covered below |
| Python | Python 3.9 or later on the Mac |
| Memory | 16 GB or more recommended |
| Disk | Tens of gigabytes for the development image and build cache, plus additional space for saved images |
| Network | Internet access for image and package downloads |
| Client | A browser, and optionally an RDP client |

Open **Terminal on the Mac** and check:

```bash
uname -m
sw_vers -productVersion
python3 --version
```

`uname -m` should report `arm64`. If Python is missing, install it from the
[official Python website](https://www.python.org/downloads/macos/) before continuing.

This guide labels commands as either **Mac Terminal** or **Ubuntu terminal**.
Run them in the specified place. Copy only the commands inside a code block, not explanatory
text or command output.

### Step 2: Download the project

**Run in Mac Terminal:**

```bash
mkdir -p ~/repos
cd ~/repos
git clone --branch apple-container https://github.com/tatsuyai713/Development-Container-for-ROS2-on-Arm64-Mac.git
cd Development-Container-for-ROS2-on-Arm64-Mac
```

If you already have the project, enter its existing directory instead of cloning it again.
Run subsequent `./...sh` commands from that directory.
The current implementation is on `apple-container`. The `22.04` and `24.04` branches contain
an older Docker edition and use different instructions.

### Step 3: Install Apple container

If it is not installed, run in **Mac Terminal**:

```bash
./install-container.sh
```

The script downloads an official Apple installer and checks its signature and notarization.
Follow the administrator authorization prompt. For an existing installation, check its version:

```bash
container --version
```

### Step 4: Start the supporting service

**Run in Mac Terminal:**

```bash
./setup.sh
```

Continue when `Setup complete` appears. This starts the Mac service that runs containers;
it does not yet start the Ubuntu desktop.

### Step 5: Build the Ubuntu image

An **image** is the starting filesystem containing Ubuntu and its installed applications.
Building it can take some time.

**Run in Mac Terminal:**

```bash
./build.sh
```

Answer the questions in order. Press Enter to accept the value in brackets.

| Question | Suggested first-time answer |
|---|---|
| Ubuntu version | `24.04` is the default; `22.04` and `26.04` are also available |
| Image name / Base image | Press Enter to use the names generated for the selected Ubuntu release |
| Desktop display language | `en` for English or `jp` for Japanese |
| Physical keyboard layout | `us` for US or `jp` for Japanese JIS |
| Install ROS 2 development environment | `true` to use ROS 2 |
| Install development tools | `true` for general development tools and LibreOffice |
| Build virtual CPUs / Build memory | Start with the defaults, `4` and `8G` |

Display language and keyboard layout are independent. Japanese input packages, including Mozc,
are added when the display language is `jp`.

| Ubuntu | ROS 2 distribution | Desktop package |
|---|---|---|
| 22.04 | Humble | Desktop |
| 24.04, default | Jazzy | Desktop Full |
| 26.04 | Lyrical | Desktop Full |

Next, choose a password for the Ubuntu, web, and RDP login. It is a development-environment
password that you choose, rather than an automatically copied Mac login password.
Characters are hidden while typing. The password is not saved in the configuration file.

The build is complete when `Built:` and the image name appear. By default, settings are
saved in `configs/default.env`.

**For a dedicated Ubuntu 26.04 configuration**, replace `./build.sh` above with the following,
and answer `26.04` at the Ubuntu version question. The filename alone does not select a release.
Use this same configuration when starting it.

```bash
./build.sh --config configs/26.04.env
```

If the image and configuration already exist, skip rebuilding and continue to startup.

### Step 6: Start Ubuntu

**Run in Mac Terminal:**

```bash
./start.sh
```

For the dedicated 26.04 configuration, use this instead:

```bash
./start.sh --config configs/26.04.env
```

The first startup asks about resources, display settings, ports, and shared folders.

| Setting | First-time guidance |
|---|---|
| Container name / Persistent /config volume | Normally press Enter |
| Desktop resolution | `1920x1080` |
| DPI / Stream scale / Frame rate | `96` / `1.0` / `30` |
| Timezone | Detected from the Mac |
| HTTP / HTTPS ports | Normally press Enter; use different ports for simultaneous environments |
| Enable XRDP | `true` if you want RDP access |
| Virtual CPUs / Memory / Shared memory | Defaults are `4` / `8G` / `4G` |
| Mount macOS home | `true` to access your Mac files from Ubuntu |
| Mount ~/.ssh | `true` only if you need your Mac SSH settings and keys in Ubuntu |
| SSL directory | Leave blank unless supplying your own certificate |

Editing a shared file in Ubuntu edits the actual Mac file. Startup also installs the client fixes
and desktop management shortcuts. A newly created container prints HTTP and HTTPS addresses,
and an RDP address if enabled. It does not automatically open a browser.
Resuming an existing container does not print these addresses; reuse the previous address or
check it as described below.

<a id="connect"></a>
## 2. Connect to the desktop

### Step 1: Find your address and credentials

| Item | Value |
|---|---|
| Browser URL | `https://127.0.0.1:<HTTPS_PORT>` |
| RDP address | `127.0.0.1:<RDP_PORT>`, available only with `ENABLE_XRDP=true` |
| Username | The short Mac username used when building the image |
| Password | The password you entered in `build.sh`; it is not synchronized with your Mac password |

Replace port placeholders with actual numbers. If you did not keep the initial startup output,
check the configuration in **Mac Terminal**. This example uses the dedicated 26.04 configuration;
replace it with `configs/default.env` if you used the default configuration.

```bash
sed -n -E '/^(UBUNTU_VERSION|CONTAINER_NAME|HTTP_PORT|HTTPS_PORT|ENABLE_XRDP|RDP_PORT)=/p' configs/26.04.env
id -un
```

For `HTTPS_PORT=60501`, open `https://127.0.0.1:60501`. That is the default for Mac UID 501,
not a universal port. `127.0.0.1` refers to this Mac; these instructions connect from the same Mac.

Editing the configuration file alone does not change an existing container's ports.
To inspect actual mappings, run `./status.sh --config configs/26.04.env` and find `publishedPorts`.
Use the Mac `hostPort` mapped to container port 3001 for HTTPS or 3389 for RDP.

<a id="browser"></a>
### Step 2: Connect with Chrome or Safari

1. Open **Google Chrome or Safari on the Mac** running the container.
2. Enter the HTTPS URL in its address bar, for example `https://127.0.0.1:60501`.
3. If a self-signed certificate warning appears, verify that it is your local environment and configure certificate trust. See [custom certificates](#certificates) below.
4. Log in with the username and build-time password identified above.
5. Wait for the KDE desktop. Click a text field and check that you can type.
6. Open **Konsole** or **Chrome** from the application menu. This second Chrome runs inside Ubuntu.

This is the Selkies browser client; no RDP application or RDP setup is needed.
An HTTP port is also published, but this guide uses **HTTPS** for secure-context clipboard and video APIs.
Safari clipboard access may require browser permission as well as certificate trust.
For sound, click inside the page before playback and check the Mac volume and the browser tab's mute setting.

<a id="rdp"></a>
### Step 3: Connect with an RDP client (alternative)

1. Set **Enable XRDP=`true`** in the startup configuration. If an existing container has it disabled, preserve your data first, then enable it through `./start.sh --reconfigure --config configs/26.04.env`. This recreates the container; use your own configuration path.
2. Open an RDP client on the Mac and add a PC connection.
3. Enter your RDP address, such as `127.0.0.1:3389`, as the PC name. Do not add `https://` or use the browser's HTTPS port.
4. Enter the username and password identified in Step 1.
5. Enable audio playback on the local computer for sound. Enable clipboard redirection if you want to copy and paste.
6. Connect. If the XRDP login screen offers a session selector, choose **Xorg**, then log in with the same credentials.
7. Wait for the Ubuntu desktop, then open your applications.

Browser and RDP connections are separate desktop sessions: windows opened in one do not appear in the other.
They share the Ubuntu user's files. Safari clipboard buttons do not appear in RDP;
RDP copy and paste uses the client's clipboard redirection.

<a id="clipboard"></a>
### Safari copy and paste

The bottom-right buttons show the transfer direction. They transfer text.

| Direction | Steps |
|---|---|
| Mac to Ubuntu | Copy on the Mac → select the destination application in Ubuntu → **Paste: Mac → Container** |
| Ubuntu to Mac | Copy in the Ubuntu application → **Copy: Container → Mac** → paste in the Mac application |

Copy in the source application before using the button. Errors appear beside the buttons;
no manual text-entry dialogs are opened. Native Cmd+V over the remote desktop is also supported.
Check HTTPS, certificate trust, and Safari clipboard permission if access is denied.

<a id="desktop"></a>
## 3. Use the desktop icons

These icons are on the **Ubuntu desktop** opened through your browser or RDP client, not on the Mac desktop.
Double-click an icon to use it. Management shortcuts have English names.
If asked to trust or allow a launcher, allow it to run.

| Icon | What it does | When to use it |
|---|---|---|
| **Home** | Opens the Ubuntu user's home directory | Find files or open `host_home` |
| **Trash** | Opens the trash | Review deleted files |
| **Container Status** | Shows the container state and the latest saved image | Check status and the image selected for recreation |
| **Stop Container** | Stops this container without deleting it | Finish today's work |
| **Restart Container** | Stops and starts this container | Restart the environment |
| **Save Container Image** | Saves the current environment as a new starting image | Preserve installed applications and settings across recreation |

### Open files with Home and Trash

**Home** opens the Ubuntu home directory. Open `host_home` inside it to access Mac files when home sharing is enabled.
**Trash** opens Ubuntu's trash. Before deleting shared Mac files, remember that they are the actual files on the Mac.

### Check Container Status

1. Double-click **Container Status**.
2. Read the container state and, if a save exists, the image selected for the next recreation.
3. Close with OK. Checking status does not stop or save the container.

### Stop or restart

**Stop Container** and **Restart Container** ask for confirmation. Executing them disconnects
browser and RDP sessions. After a stop, run `./start.sh` on the Mac to resume. After a restart,
wait for startup and reconnect. Save open documents in their applications first.

To finish work:

1. Save documents and source files.
2. Double-click **Stop Container** and choose Yes in the confirmation.
3. The connection closes. Next time, run `./setup.sh` and `./start.sh` on the Mac and reopen the same connection.

To restart:

1. Save your work and double-click **Restart Container**.
2. Choose Yes. The connection closes temporarily.
3. Wait for startup, then reload the browser page or reconnect with the RDP client. If it is not ready yet, wait and retry.

### Save the environment with Save Container Image

1. Save your open documents and source files in their applications.
2. Double-click the icon.
3. Read the confirmation and choose Yes to proceed, or No to cancel.
4. Wait for the completion message. This can take several minutes; do not submit repeated saves.
5. On success, the message shows the new image name and the archive location on the Mac.

The save captures files, installed applications, and settings on disk. It does not restore open windows or running processes.
Saving leaves the running desktop available and keeps the original image.
The next `./start.sh --recreate` uses the latest successful save. Each save creates another
image and archive, so disk usage increases.

This is different from saving a document. Mounted Mac files and `/config` volume contents are
not included in the saved image; they remain in their own storage locations.

<a id="daily"></a>
## 4. Daily use

### Resume work

**In Mac Terminal, from the project directory:**

```bash
./setup.sh
./start.sh
```

Then connect with your browser or RDP client. You do not need to rebuild for everyday startup.
If several configurations exist, select the desired environment from the startup menu.
For the same 26.04 environment each time, use `./start.sh --config configs/26.04.env` explicitly.
Continue with [ROS 2 and applications](#usage) or the [desktop icons](#desktop).

### Finish work

Save open documents and use **Stop Container**, or run in **Mac Terminal**:

```bash
./stop.sh
```

Stopping retains the container's files, installed applications, and settings. You do not need
to save an image every time you stop. Closing a browser tab does not stop the container.

### Inspect or restart the environment

**Run in Mac Terminal:**

```bash
./status.sh
```

```bash
./restart.sh
```

Runtime commands use the configuration last successfully started. Without that record, they
select an existing environment; if the target is ambiguous, they ask you to choose or require
`--config` in non-interactive use. Every runtime command also accepts an explicit `--config`.

<a id="files"></a>
## 5. Save files and share them with the Mac

**Stopping** retains the existing container. **Recreating** replaces it using a starting image.
Changes made only inside the container after the latest image save are not carried into a recreation.

| Location or content | Stop and start | Recreate | Included in Save Container Image? |
|---|---|---|---|
| Mac files under `~/host_home` | Retained | Retained when sharing the same Mac folder | No; stored on the Mac |
| Data under `/config` | Retained | Retained with the same named volume | No; stored in a separate volume |
| Normal Ubuntu home, Desktop, Documents | Retained | Returns to the selected image's saved state | Yes, except mounted paths |
| Installed Ubuntu applications and system settings | Retained | Returns to the selected image's state | Yes |

Persisting `/config` does not automatically redirect every home-directory file or application
setting there. Check where important data is actually stored.

With `Mount macOS home=true`, open **Home**, then `host_home`, to see the Mac home directory.
For example, Ubuntu's `~/host_home/ros2_ws` is the Mac's `~/ros2_ws`.

Create a workspace from an **Ubuntu terminal**:

```bash
mkdir -p ~/host_home/ros2_ws/src
```

Source files here remain on the Mac even after recreation. Edits and deletions affect the original
Mac files; this mount does not create a separate copy. With `MOUNT_HOME=false`, transfer important
files to other persistent storage yourself.

<a id="usage"></a>
## 6. Use ROS 2 and applications

### Open an Ubuntu terminal

Search for **Konsole** in the Ubuntu application menu. Run the commands in this section there,
not in Mac Terminal.

### Test ROS 2

Use an image built with ROS 2 enabled. Load the installed distribution in each terminal:

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
ros2 --help
```

For a message-passing test, open two Ubuntu terminals.

**Ubuntu terminal 1: publisher**

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
ros2 run demo_nodes_cpp talker
```

**Ubuntu terminal 2: subscriber**

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
ros2 run demo_nodes_cpp listener
```

Both should print messages. Stop each with Ctrl+C. This checks communication inside the
container. Connecting to a physical robot or another PC requires separate network configuration.

### Create a ROS 2 package

Example with Mac home sharing enabled, in an **Ubuntu terminal**:

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
mkdir -p ~/host_home/ros2_ws/src
cd ~/host_home/ros2_ws/src
ros2 pkg create --build-type ament_cmake my_first_package
cd ..
colcon build --symlink-install
source install/setup.bash
```

This keeps the source on the Mac while building in Ubuntu. Build outputs are Linux arm64
programs, not native Mac applications.

### Use other applications

- Search for **Chrome** in the application menu to open Google Chrome inside Ubuntu.
- Development-tool builds include Git, C/C++ and Python tools, Vim, Emacs, tmux, and LibreOffice.
- Japanese-language builds provide Mozc through the input-method menu.
- RDP audio also depends on the Mac client's audio-redirection settings.

<a id="save"></a>
## 7. Save, restore, and update an environment

Run commands in this section in **Mac Terminal**. With multiple environments, select the same configuration for both build and start.
For example, use `./build.sh --config configs/26.04.env` and `./start.sh --recreate --built-image --config configs/26.04.env` for 26.04.
`--recreate` deletes and replaces the current container. Review [file persistence](#files) before proceeding.

### Save the environment and recreate it

1. Save open files in their applications.
2. Run **Save Container Image** and wait for its success message.
3. Optionally check the selected image with **Container Status**.
4. Run in **Mac Terminal**:

```bash
./start.sh --recreate
```

The container is replaced with the latest successful saved image. Reconnect your browser or RDP
client. Later changes made only inside the container are not retained. The same shared folders
and named volume continue to provide their own data.

Saved archives and state are under `~/.local/state/ros2-container-control/` on the Mac.
Images use unique `saved-...` tags. A failed save does not change the image selected for the next
recreation. This is not a replacement for application-coordinated database backups.

### Return to the configured build image

Preserve current container-only changes first, then run in **Mac Terminal**:

```bash
./start.sh --recreate --built-image
```

This selects the image in your build configuration instead of the latest desktop save.

### Change Ubuntu release, language, keyboard, or installed tools

Build again, then explicitly select the newly built image:

```bash
./build.sh
./start.sh --recreate --built-image
```

Interactive builds ask from the project defaults each time. To reuse the saved build settings:

```bash
./build.sh --non-interactive
./start.sh --recreate --built-image
```

The password is requested again unless provided through the supported environment variable.

### Change ports, display settings, CPU, or memory

```bash
./start.sh --reconfigure
```

This edits runtime settings and recreates the container; a rebuild is not required.
Save necessary changes first. The latest saved image is used when available.

### Remove an environment

For an ordinary end of work, use **Stop Container** instead. To remove a container:

```bash
./delete.sh
```

Check the displayed target before answering `y`. The image and `/config` volume are kept by
default. `./delete.sh --volume` also removes the persistent `/config` volume. It does not delete
the shared Mac directory itself.

<a id="troubleshooting"></a>
## 8. Troubleshooting

| Symptom | First step |
|---|---|
| Container service is stopped | Run `./setup.sh`, then `./start.sh` |
| `Container ... not found` | Check `container list --all`; if deleted, create it again with `start.sh --config` and the intended configuration |
| Connection does not open | Check `container list` and use the actual startup URL and port |
| Login fails | Check the short username with `id -un`; use the build-time password |
| Port is already in use | Stop the conflicting container or configure different ports |
| Safari cannot type | Click the Ubuntu input field; reload the page and update the client as shown below |
| Safari clipboard is denied | Check HTTPS, certificate trust, permission, and the error beside the buttons |
| RDP has no sound | Enable playback on the local computer in the RDP client |
| Management icons are missing or the Mac does not respond | Reinstall the desktop actions as shown below |
| Save reports `could not read block` | Update the desktop actions; the fixed exporter falls back to a guest filesystem copy |
| Save reports another operation is running | Wait for that operation to finish; do not submit repeated requests |
| Disk usage grows | Check saved images, archives, and build cache |

Find the running container's name in **Mac Terminal**:

```bash
container list
```

Replace `<container-name>` below with the actual name; do not type the angle brackets.

Update browser, input, and clipboard fixes:

```bash
./update-client.sh <container-name>
```

Install or update the management icons and Mac-side service:

```bash
./desktop-actions.sh <container-name>
```

Keep the container running while doing this. Existing containers use their host-home mount;
new containers get a dedicated management mount. An older container with neither mount needs
recreation through `start.sh` after preserving necessary data.

View logs in **Mac Terminal**:

```bash
./logs.sh
```

Ctrl+C stops following logs, not the container. Management-service errors are in:

```bash
tail -n 60 ~/.local/state/ros2-container-control/agent.log
```

Check disk space:

```bash
df -h .
container system df
```

`./prune.sh` asks before removing dangling, untagged images. It does not remove all tagged saved
images or backup archives. For black screens or immediate RDP disconnects, inspect the logs and image version.
`update-client.sh` applies browser fixes; it does not update XRDP or Ubuntu packages.
For those fixes, preserve necessary files on the Mac or other storage, build from the current project sources,
and recreate with `--recreate --built-image`. Keep a saved image for recovery, but recreating from an older
saved image alone does not incorporate fixes in a new build.

<a id="commands"></a>
## 9. Commands and multiple environments

Run these in **Mac Terminal**, from the project directory.

| Command | Purpose |
|---|---|
| `./install-container.sh` | Install Apple container |
| `./setup.sh` | Start and check the Mac service |
| `./build.sh` | Configure and build an image |
| `./build.sh --non-interactive` | Build with saved settings |
| `./start.sh` | Select and start an environment |
| `./start.sh --recreate` | Recreate from the latest saved image, or configured image if no save exists |
| `./start.sh --recreate --built-image` | Recreate from the configured build image |
| `./start.sh --reconfigure` | Edit runtime settings and recreate |
| `./start.sh --non-interactive` | Never prompt; fail if required settings or selection are missing |
| `./stop.sh` / `./restart.sh` | Stop or restart the selected environment |
| `./shell.sh` | Open Bash inside the container; leave with `exit` |
| `./status.sh` / `./logs.sh` | Show state or follow logs |
| `./update-client.sh <container-name>` | Update client fixes in a running container |
| `./desktop-actions.sh <container-name>` | Install or update desktop management |
| `./delete.sh` | Confirm deletion; keep image and volume |
| `./delete.sh --volume` | Also remove the persistent volume |
| `./prune.sh` | Confirm removal of dangling images |

### Keep separate Ubuntu environments

For a separate Ubuntu 26.04 configuration, run:

```bash
./build.sh --config configs/26.04.env
./start.sh --config configs/26.04.env
```

**Choose `26.04` at the build question. The filename does not select the Ubuntu release.**
Use separate files for 22.04 and 24.04 as needed. Generated container, image, and volume names
include the Mac username and Ubuntu release. Use different ports for simultaneous environments.

Start remembers the successfully selected configuration. Stop, restart, shell, logs, status,
and delete share the runtime selection logic: explicit `--config` or `CONFIG_FILE` first,
then the last started configuration, then existing environments if no record exists.
Ambiguous non-interactive selection fails instead of choosing an arbitrary release.

Explicitly choose the target for any runtime command:

```bash
./stop.sh --config configs/26.04.env
./restart.sh --config configs/26.04.env
./shell.sh --config configs/26.04.env
./status.sh --config configs/26.04.env
./logs.sh --config configs/26.04.env
./delete.sh --config configs/26.04.env
```

`CONFIG_FILE=configs/26.04.env ./stop.sh` remains supported. Runtime commands accept
`--non-interactive` to forbid selection prompts. Start itself offers the configuration menu
when multiple files exist and no explicit configuration is supplied.

### Manage the entire Apple container service

```bash
./container-service.sh status
./container-service.sh start
```

`./container-service.sh stop` and `restart` affect all containers using the service, including
other projects. For daily shutdown, use **Stop Container** or `./stop.sh` for just one environment.

<a id="technical"></a>
## 10. Technical details and limitations

The earlier sections are sufficient for ordinary use. This section explains implementation,
configuration boundaries, and current limits.

### Runtime and image construction

Apple `container` uses a lightweight Linux VM per container, rather than sharing the Mac kernel.
Build and run request `linux/arm64`; installation also checks the Debian architecture and Ubuntu release.

| Ubuntu | Default base image | ROS package |
|---|---|---|
| 22.04 | `ghcr.io/tatsuyai713/webtop-kde-base-arm64-u22.04:1.1.0` | `ros-humble-desktop` |
| 24.04 | `ghcr.io/tatsuyai713/webtop-kde-base-arm64-u24.04:1.1.0` | `ros-jazzy-desktop-full` |
| 26.04 | `ghcr.io/tatsuyai713/webtop-kde-base-arm64-u26.04:1.1.0` | `ros-lyrical-desktop-full` |

Jammy arm64 uses the available Desktop package. The base image must match the selected Ubuntu release.
`Containerfile` and `rootfs/install-development.sh` install XRDP, ROS, colcon, rosdep, and optional tools.
`rootfs/customize-user.sh` aligns the Linux username, UID, and GID with the Mac, prepares credentials,
and configures the desktop. Passwords are supplied through a BuildKit secret, not a normal build argument
or saved configuration entry.

Official Google Chrome Stable for Linux arm64 is installed independently of the optional development tools.
The installer downloads `google-chrome-stable_current_arm64.deb` and checks its package name and architecture.
Ubuntu 22.04 uses a checksum-pinned Jammy-compatible PixelFlux wheel because newer bundled FFmpeg libraries
require `vaMapBuffer2`, which Jammy's libva does not provide. Ubuntu 24.04 uses the base image's PixelFlux.

### When settings apply

| Settings | Apply with |
|---|---|
| Ubuntu, ROS, language, keyboard, tools | Build, then `start.sh --recreate --built-image` |
| Ports, resolution, DPI, CPU, memory, mounts | `start.sh --reconfigure`, or edit settings and recreate |
| Client fixes | Applied by start; also available through `update-client.sh` |
| Desktop management | Installed by start; also available through `desktop-actions.sh` |

Interactive builds call `configure.sh --build` and reset build questions to project defaults.
`--non-interactive` reuses saved values. The runtime wizard runs only for first-time configuration
or `--reconfigure`. Time zone defaults to the Mac setting, with `UTC` as a fallback.

One-off custom base image:

```bash
BASE_IMAGE=ghcr.io/example/image:tag ./build.sh
```

Build without cache:

```bash
NO_CACHE=true ./build.sh
```

### Display, keyboard, and audio

s6 starts X11, Plasma, audio, authentication, nginx, and Selkies. Browsers receive display `:1`;
XRDP starts a separate XorgXRDP session. Files are shared between sessions, not application windows.

For Ubuntu 26.04, the single-display Selkies monitor patch avoids a Plasma 6 screen-name mismatch.
XRDP uses the project session script instead of the `im-launch` path requiring a systemd journal.
Its Plasma runtime directory is separate while the PipeWire endpoint remains shared.

Ubuntu 22.04 and 24.04 build matching PulseAudio XRDP modules; 26.04 uses PipeWire XRDP modules.
Per-session audio endpoints prevent RDP from taking over the browser's audio output.
Japanese builds use Fcitx on older releases and Fcitx 5 on 26.04, with Mozc.

Safari focuses an editable keyboard-assist input. Ordinary keys and IME are handled by Selkies,
and the assist handler does not resend an already processed Enter. Held keys are released when
leaving the page or changing focus. Clipboard text is written before the remote paste shortcut.
Startup reapplies the client patch after the base dashboard refresh, and cache settings prevent stale files.

### Graphics and performance

Linux OpenGL uses Mesa llvmpipe on the CPU; stream encoding is also software-based. This project
provides no Linux access to Metal or the Apple GPU. ARM64 virtualization and CPU instructions such
as NEON remain available.

Chrome and Safari on the receiving Mac prefer hardware H.264 decoding. The client derives the actual
profile, constraints, and level from SPS data and falls back when unsupported. This does not enable
GPU rendering inside Ubuntu.

`KWIN_EFFECTS_FORCE_ANIMATIONS=1` allows animations with software rendering. Individual effects are
controlled in KDE settings. Higher resolution, frame rate, and heavier effects increase CPU work.
`DPI` controls text scaling, `STREAM_SCALE` controls streamed dimensions, and `FRAMERATE` controls the
target frame rate. Retina device pixel ratio does not override the configured DPI.

### Ports and storage

HTTP defaults to `50000 + Mac UID`, HTTPS to `60000 + UID`, RDP to 3389, Foxglove to 8765,
and ROS bridge to 9090. Ports publish on Mac loopback only. Foxglove and ROS bridge nodes are
not started automatically; the ports only reserve access for services you run separately.
External robot/PC communication needs its own network design.

`CONFIG_VOLUME` mounts at `/config`. `MOUNT_HOME` and `MOUNT_SSH` control optional Mac shares.

<a id="certificates"></a>

For custom HTTPS certificates, set startup option `SSL_DIR` to the absolute Mac path of your certificate directory.
The certificate must cover the hostname or IP used to connect, and its issuer must be trusted on the Mac.
A configured `SSL_DIR` must contain `cert.pem` and `cert.key`; it mounts read-only at `/config/ssl`.
Mount and port changes require recreation.

### Desktop control and image saving

The Mac LaunchAgent `io.github.tatsuyai713.ros2-container-control` handles requests through a shared
channel. It accepts only status, stop, restart, and save for registered containers. Requests cannot
choose another container or supply arbitrary shell commands. New containers receive a dedicated
channel mount, including when Mac home sharing is disabled. Existing containers can use an existing
host-home mount.

Saving creates a single-layer OCI image: a flatten operation rather than Docker incremental commit
or previous-layer merge. When native `container export` fails on a running container, GNU tar in the
guest copies the filesystem while excluding all mounted contents and transient `/run` state and X locks.
That fallback is a live file copy, not an atomic snapshot. Read and permission errors fail the save.
Only a successful import and configuration verification update the image selected for recreation.

Archives and runtime settings are kept under `~/.local/state/ros2-container-control/backups/` on the Mac.
The image preserves its effective command, environment, user, working directory, and metadata.
Published ports and mounts are runtime settings; use the saved project configuration and `start.sh`
to restore them. For reproducible infrastructure, also describe added packages in `Containerfile`
or `rootfs/`: an image save does not edit those sources.

### Current scope

- Apple Silicon and Linux arm64 only.
- No Docker Compose, Dev Containers, or Docker-compatible host API.
- Browser and RDP do not mirror the same screen.
- No guest GPU rendering or hardware stream encoding.
- Saved images exclude volumes and mounted host data.
- Older Docker branches remain available, but their DOOD scripts cannot run unchanged here.

## References

- [Apple container](https://github.com/apple/container)
- [Apple container command reference](https://github.com/apple/container/blob/main/docs/command-reference.md)
- [ROS 2 documentation](https://docs.ros.org/)
- [Selkies](https://github.com/selkies-project/selkies)
- [XRDP](https://github.com/neutrinolabs/xrdp)
- [Reference for clipboard controls and management icons](https://github.com/tatsuyai713/kde-selkies-webtop-devcontainer)
