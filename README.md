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
- Ubuntu 22.04 with ROS 2 Humble Desktop Full, or Ubuntu 24.04 with ROS 2 Jazzy Desktop Full
- `colcon`, `rosdep`, C/C++ and Python development tools, editors, Git, SSH tools, and LibreOffice
- KDE Plasma access through both Selkies in a browser and XRDP
- Independent image-language (`en`/`ja`) and keyboard-layout (`us`/`jp`) choices
- English-only packages by default, avoiding Japanese packages unless Japanese is selected
- Interactive build and start commands with reusable settings in `configs/default.env`
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

# Interactively select runtime settings, then create or start the container
./start.sh
```

The build asks for the Ubuntu release, image name, language, keyboard, ROS installation,
development tools, and build resources. It then asks for the desktop password without saving
that password in the configuration file.

The start command asks for ports, display settings, time zone, runtime resources, mounts, and
whether XRDP is enabled. Answers from both commands are saved to `configs/default.env`.
Use `--non-interactive` to reuse saved answers in automation.

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
| 22.04 Jammy | ROS 2 Humble | `ros-humble-desktop-full` |
| 24.04 Noble (default) | ROS 2 Jazzy | `ros-jazzy-desktop-full` |

Set `INSTALL_ROS2=false` during the build to omit ROS packages. When enabled, the image also
installs `ros-dev-tools`, colcon, and rosdep, creates `~/ros2_ws/src`, and automatically sources
the selected ROS environment in Bash. The selected base image must match the Ubuntu version;
the build stops on a mismatch.

### Language and keyboard

English is the default image language. The two settings are independent:

- `USER_LANGUAGE=en` uses an English locale and does not add Japanese fonts or input packages.
- `USER_LANGUAGE=ja` adds the Japanese locale, fonts, Fcitx, and Mozc.
- `KEYBOARD_LAYOUT=us` selects a US XKB keyboard and is the default.
- `KEYBOARD_LAYOUT=jp` selects a Japanese XKB keyboard.

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
| `./build.sh` | Interactively configure and build the arm64 image |
| `./build.sh --non-interactive` | Build with saved image settings |
| `./start.sh` | Interactively configure and start the desktop |
| `./start.sh --recreate` | Replace the container and reapply current runtime settings |
| `./start.sh --non-interactive` | Start with saved runtime settings |
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

## When Configuration Takes Effect

The configuration is explicit and divided into two phases:

| Setting type | Examples | Applied when |
|---|---|---|
| Image | Ubuntu, ROS, language, keyboard, tools | `./build.sh` creates an image |
| Runtime | ports, resolution, time zone, CPU, memory, mounts | `./start.sh` creates a container |

An existing container keeps the runtime options used at its creation. Interactive `start.sh`
detects changed saved settings and recreates the container. After manual edits, run
`./start.sh --recreate`. Recreation keeps the named volume but discards the container's writable
layer. A rebuild is required only for image-setting changes.

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
ROS workspaces can be rebuilt with the installed colcon and rosdep tools.

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

`build.sh` invokes `configure.sh --build`, while `start.sh` invokes
`configure.sh --runtime`. Both write shell-safe values to the same env file. Build choices become
files and packages in an image. Runtime choices become `container run` arguments and therefore
cannot be added to an already-created container. `start.sh` compares configuration checksums to
decide whether recreation is necessary.

### 3. Image construction

Apple BuildKit reads `Containerfile` and the selected KDE/Selkies arm64 base. First,
`rootfs/install-development.sh` verifies the Ubuntu release and installs XRDP, XorgXRDP, the
appropriate ROS apt source, the selected Desktop Full package, rosdep, colcon, and optional
development applications. On Ubuntu 24.04 it also installs the PipeWire XRDP module.

Next, `rootfs/customize-user.sh` aligns the Linux username, UID, and GID with the Mac account,
sets the Linux and web credentials from the temporary secret, prepares standard directories and
`~/ros2_ws/src`, configures locale and XKB, applies KDE defaults, and creates Home and Trash
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
separate XorgXRDP display and launches `startplasma-x11` in its own D-Bus session. Both paths use
the same Linux account and storage, but not the same display server or application processes.

### 6. Persistence boundaries

The image contains reproducible operating-system packages and project defaults. The container's
writable layer is disposable. `/config` survives recreation in its named volume, while bind
mounts directly expose selected macOS files. Therefore, system packages belong in the image,
desktop application state belongs in `/config`, and host documents belong in bind mounts. Only
`delete.sh --volume` intentionally removes the project's persistent volume.
