# Development-Container-for-ROS2-on-Arm64-Mac

[日本語版](README_ja.md)

This repository is the updated edition of
[`Development-Container-for-ROS2-on-Arm64-Mac`](https://github.com/tatsuyai713/Development-Container-for-ROS2-on-Arm64-Mac).
It preserves the original project's ROS 2 development workflow and XRDP desktop while moving
the current implementation to Apple's [`container`](https://github.com/apple/container) runtime.
The KDE Plasma desktop is available through either an RDP client or a web browser powered by
Selkies WebRTC.

The previous Docker implementations remain available in the repository's `22.04` and `24.04`
branches. The `apple-container` branch contains this current implementation.

## What the Updated Edition Provides

- Native `linux/arm64` builds and lightweight Linux VMs on Apple Silicon through Apple `container`
- Ubuntu 22.04 with ROS 2 Humble Desktop, or Ubuntu 24.04 with ROS 2 Jazzy Desktop Full
- `colcon`, `rosdep`, C/C++ and Python development tools, editors, Git, SSH tools, and LibreOffice
- KDE Plasma access through both Selkies in a browser and XRDP
- Independent display-language (`en`/`jp`) and keyboard-layout (`us`/`jp`) choices
- English-only packages by default, avoiding Japanese packages unless Japanese is selected
- Interactive build setup and first-run start setup with reusable settings in `configs/default.env`
- Host time-zone detection at start time instead of a fixed Tokyo default
- Persistent `/config` storage and optional macOS home and SSH-directory mounts
- Home and Trash icons on the KDE desktop
- Lifecycle scripts for build, start, stop, restart, shell, logs, status, and confirmed deletion
- Loopback port publishing for browser, XRDP, Foxglove, and ROS bridge services

Ubuntu 26.04 is intentionally not offered yet. It will be added after a compatible arm64
KDE/Selkies base image and the required ROS and XRDP package set can be verified.

## Requirements

- Apple Silicon Mac (`arm64`)
- macOS 26 or later
- Apple `container` 1.x
- 16 GB or more host memory recommended
- An RDP client if XRDP access is required

`install-container.sh` downloads an official Apple release package, validates its signing and
notarization information, and installs it. This operation requires administrator authorization.

## Quick Start

```bash
cd /path/to/Development-Container-for-ROS2-on-Arm64-Mac

# First installation only
./install-container.sh

# Start and verify the Apple container services
./setup.sh

# Interactively select image settings, then build
./build.sh

# Start with saved settings (the first run opens the setup wizard)
./start.sh
```

The build asks for the Ubuntu release, image name, language, keyboard, ROS installation,
development tools, and build resources. Each interactive build starts from the project defaults
rather than using the previous build answers as prompt defaults. It then asks for the desktop
password without saving that password in the configuration file. Use
`./build.sh --non-interactive` only when the saved build settings should be reused.

On the first run, the start command asks for ports, display settings, time zone, runtime resources,
mounts, and whether XRDP is enabled. Answers are saved to `configs/default.env`; later runs reuse
them without prompts. Use `./start.sh --reconfigure` to run the wizard again, or
`--non-interactive` in automation to fail instead of prompting when runtime setup is incomplete.

## Connecting to the Desktop

For a macOS account with UID 501, the default endpoints are:

| Service | Default endpoint | Purpose |
|---|---|---|
| Selkies HTTP | <http://127.0.0.1:50501> | Browser desktop |
| Selkies HTTPS | <https://127.0.0.1:60501> | Encrypted browser desktop |
| XRDP | `127.0.0.1:3389` | Native RDP client |
| Foxglove | `127.0.0.1:8765` | Port reserved for a Foxglove service |
| ROS bridge | `127.0.0.1:9090` | Port reserved for a ROS bridge service |

The web desktop and XRDP use the macOS username and the password entered during `./build.sh`.
They can be used at the same time, but they are separate Plasma sessions rather than two views
of the same display. The ports bind to `127.0.0.1` by default and are not exposed to the LAN.

## Build Choices

### Ubuntu and ROS 2

| Ubuntu | ROS distribution | Installed desktop package |
|---|---|---|
| 22.04 Jammy | ROS 2 Humble | `ros-humble-desktop` |
| 24.04 Noble (default) | ROS 2 Jazzy | `ros-jazzy-desktop-full` |

Set `INSTALL_ROS2=false` during the build to omit ROS packages. When enabled, the image also
installs `ros-dev-tools`, colcon, and rosdep. It does not create a workspace in the container's
writable home layer. Create one in persistent host storage, for example `~/host_home/ros2_ws`, if
needed. ROS is not sourced automatically. Enable it only in a shell that needs it with
`source /opt/ros/<distro>/setup.bash`. The selected base image must match the Ubuntu version;
the build stops on a mismatch.

The official Jammy arm64 repository does not publish a `ros-humble-desktop-full` binary package,
so the 22.04 image uses the supported `ros-humble-desktop` package. Noble arm64 does publish
`ros-jazzy-desktop-full`, which remains the choice for the 24.04 image.

### Language and keyboard

English is the default for both the display language and physical keyboard. The two settings are
independent:

- `USER_LANGUAGE=en` uses an English locale and does not add Japanese fonts or input packages.
- `USER_LANGUAGE=jp` adds the Japanese locale, fonts, Fcitx, and Mozc.
- `KEYBOARD_LAYOUT=us` selects a US keyboard and is the default.
- `KEYBOARD_LAYOUT=jp` selects a Japanese JIS keyboard.

These are image settings. Rebuild the image after changing them, then recreate the container.

### Development tools

`INSTALL_DEV_TOOLS=true` installs the core utilities offered by the previous edition, including
build-essential, CMake, Git, Vim, Emacs, tmux, Python tooling, rsync, SSH tools, networking and
archive commands, LibreOffice, and `clinfo`. Turn it off when a smaller image is preferred.

## Commands

| Command | Action |
|---|---|
| `./install-container.sh` | Install the official Apple container package |
| `./setup.sh` | Start and inspect Apple container services |
| `./configure.sh` | Interactively edit all saved settings |
| `./build.sh` | Build interactively, starting from project defaults each time |
| `./build.sh --non-interactive` | Build with explicitly saved image settings |
| `./start.sh` | Select a configuration when several exist, then start it |
| `./start.sh --reconfigure` | Interactively update runtime settings and recreate the container |
| `./start.sh --recreate` | Replace the container and reapply current runtime settings |
| `./start.sh --non-interactive` | Start with saved settings, or fail if runtime setup is incomplete |
| `./stop.sh` | Stop the container |
| `./restart.sh` | Restart the container |
| `./shell.sh` | Open an interactive Bash shell in the container |
| `./logs.sh` | Follow service logs |
| `./status.sh` | Show container state and resource usage |
| `./delete.sh` | Confirm, then delete the container while keeping image and volume |
| `./delete.sh --volume` | Also delete the persistent `/config` volume |
| `./prune.sh` | Remove dangling images |

Every command accepts the current project defaults. Build and start also accept
`--config path`; this allows multiple independently configured desktops.

When `configs/` contains multiple generated `.env` files, plain `./start.sh` first displays their
file name, Ubuntu release, container name, and image name. After selection, it checks that
configuration's first-run state and opens the runtime wizard only if needed. A direct `--config`
path bypasses the menu. Non-interactive startup requires `--config` when multiple files exist.

The generated container, image, and volume names include the Ubuntu release, for example
`development-container-for-ros2-on-arm64-mac-$USER-u22.04` and the corresponding `-u24.04`
name. To manage both releases without repeatedly changing one file, give each release its own
configuration:

```bash
./build.sh --config configs/22.04.env
./build.sh --config configs/24.04.env

# Select 22.04 or 24.04 from the menu
./start.sh

# Or bypass the menu
./start.sh --config configs/22.04.env
./start.sh --config configs/24.04.env
```

Choose different host ports in the two configurations if both containers must run at the same
time. Configuration files created by an older version keep their explicit names; changing their
Ubuntu version in the build wizard updates the former generated names without deleting the old
container, image, or volume.

## When Configuration Takes Effect

The configuration is explicit and divided into two phases:

| Setting type | Examples | Applied when |
|---|---|---|
| Image | Ubuntu, ROS, language, keyboard, tools | `./build.sh` creates an image |
| Runtime | ports, resolution, time zone, CPU, memory, mounts | `./start.sh` creates a container |

An existing container keeps the runtime options used at its creation. Use
`./start.sh --reconfigure` to edit runtime settings interactively and recreate the container. After
manual edits, run `./start.sh --recreate`. Recreation keeps the named volume but discards the container's writable
layer. A rebuild is required only for image-setting changes.

The configured `DPI` is authoritative for desktop text and font rendering. Retina browser
device-pixel-ratio reports cannot override it; `STREAM_SCALE` changes only the streamed display
dimensions.

On Ubuntu 22.04 arm64, the image explicitly installs a checksum-pinned, Jammy-compatible PixelFlux
wheel, following the wheel override strategy used by `kde-selkies-webtop-devcontainer`. Newer
arm64 wheels bundle FFmpeg libraries that reference `vaMapBuffer2`, which Jammy's libva does not
provide. Ubuntu 24.04 continues to use the PixelFlux version supplied by its base image.

The default time zone is detected from the Mac each time configuration is initialized. `UTC` is
used only if the host setting cannot be determined.

For a one-off custom base image:

```bash
BASE_IMAGE=ghcr.io/example/image:tag ./build.sh
```

For a clean build without the BuildKit cache:

```bash
NO_CACHE=true ./build.sh
```

## Storage, Security, and Deletion

- `/config` uses the named volume selected by `CONFIG_VOLUME`.
- The macOS home directory can be mounted at `~/host_home`.
- The host `~/.ssh` directory can be mounted at the same path in the container.
- A configured `SSL_DIR` is mounted read-only at `/config/ssl`.
- Browser, RDP, Foxglove, and ROS bridge ports publish only on loopback.
- The build password is supplied through a temporary BuildKit secret, not a regular build arg.

`./delete.sh` prints the exact container, image, and volume disposition and asks before deletion.
It keeps both image and volume by default. `--volume` also removes persistent desktop data, and
`--yes` is available for deliberate non-interactive cleanup.

## Migrating from the Previous Edition

Use the scripts in the `apple-container` branch for all new Apple `container` installations.
The previous Docker scripts and Dockerfiles remain available in the repository's `22.04` and
`24.04` branches. Host documents can be moved through the default `~/host_home` mount, while
ROS workspaces can be rebuilt with the installed colcon and rosdep tools. Put new workspaces under
the host-backed `~/host_home` mount if they must survive container deletion.

The former Commit and Flatten desktop actions are not carried into the active implementation.
Apple `container` does not provide the guest with a Docker socket. Permanent system changes now
belong in `Containerfile` or `rootfs/`, followed by `./build.sh` and
`./start.sh --recreate`. This makes the result reproducible; Home and Trash desktop icons remain.

## Current Limitations

- Only Apple Silicon and `linux/arm64` are supported.
- The selected base image must have an arm64 manifest and match the configured Ubuntu release.
- Rendering and Selkies encoding are software-based and may use significant CPU.
- Browser and XRDP access start independent Plasma sessions.
- Foxglove and ROS bridge ports are published, but their application nodes are not started by
  the container automatically.
- Docker Compose, Dev Containers, Ubuntu 26.04, and host-runtime control from desktop shortcuts
  are not currently supported.

## Official Resources

- [Apple container](https://github.com/apple/container)
- [Apple container command reference](https://github.com/apple/container/blob/main/docs/command-reference.md)
- [ROS 2 installation documentation](https://docs.ros.org/en/jazzy/Installation.html)
- [Selkies](https://github.com/selkies-project/selkies)
- [XRDP](https://github.com/neutrinolabs/xrdp)

## How the Updated Container Works

### 1. Host runtime and isolation

`setup.sh` starts Apple's supporting services. Apple `container` then runs each Linux container
inside a lightweight virtual machine backed by Apple's virtualization framework; Linux does not
share the macOS kernel. Both build and run commands request `linux/arm64`, and image setup checks
the Debian architecture again before continuing.

### 2. Configuration flow

`build.sh` invokes `configure.sh --build`. `start.sh` invokes `configure.sh --runtime` only when the
configuration is missing or `--reconfigure` is specified. Both write shell-safe values to the same
env file. Build choices become
files and packages in an image. Runtime choices become `container run` arguments and therefore
cannot be added to an already-created container. `--reconfigure` recreates the container so the
new runtime settings take effect.

### 3. Image construction

Apple BuildKit reads `Containerfile` and the selected KDE/Selkies arm64 base. First,
`rootfs/install-development.sh` verifies the Ubuntu release and installs XRDP, XorgXRDP, the
appropriate ROS apt source, the selected ROS desktop package, rosdep, colcon, and optional
development applications. Ubuntu 22.04 builds the PulseAudio XRDP modules using the original
project's PulseAudio 15.99.1 method in a disposable build stage; Ubuntu 24.04 uses the packaged
PipeWire XRDP module.

Next, `rootfs/customize-user.sh` aligns the Linux username, UID, and GID with the Mac account,
sets the Linux and web credentials from the temporary secret, prepares standard directories,
configures locale and XKB, applies KDE defaults, and creates Home and Trash
desktop icons. Japanese packages are installed only for a Japanese-language build.

### 4. VM and service startup

`start.sh` creates the `/config` volume and assembles VM resources, shared memory, loopback port
forwarding, environment variables, and optional bind mounts. Inside the VM, the image's s6 init
tree starts the virtual display, KDE Plasma, audio, authentication, and Selkies services. Added
s6 services start D-Bus, `xrdp-sesman`, and `xrdp` in dependency order when XRDP is enabled.

### 5. Browser and RDP display paths

The browser path renders Plasma on X display `:1` through Mesa llvmpipe. Selkies captures that
display, performs software video encoding, sends audio and video to the browser, and returns
keyboard, pointer, and microphone input. `STREAM_SCALE` reduces stream resolution independently
of desktop resolution, and `SELKIES_FRAMERATE` controls the requested frame rate.

The RDP path listens on container port 3389. After authentication, `xrdp-sesman` creates a
separate XorgXRDP display and launches `startplasma-x11` in its own D-Bus session. Its applications
use the session-specific `xrdp-sink` and `xrdp-source`, while the browser session retains the
Selkies `output` sink. Both paths use the same Linux account and storage, but not the same display
server or application processes.

### 6. Persistence boundaries

The image contains reproducible operating-system packages and project defaults. The container's
writable layer is disposable. `/config` survives recreation in its named volume, while bind
mounts directly expose selected macOS files. Therefore, system packages belong in the image,
desktop application state belongs in `/config`, and host documents belong in bind mounts. Only
`delete.sh --volume` intentionally removes the project's persistent volume.
