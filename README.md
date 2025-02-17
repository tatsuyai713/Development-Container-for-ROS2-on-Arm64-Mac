# Development Container (aarch64 and x86_64 on Rosetta )for ROS 2 on Arm64 Mac

This Dockerfile is designed to create a Docker container specifically for ROS 2, optimized for M1/M2 Macs (ARM64 architecture).

## Getting Started

### Prerequisites
- Docker installed on your M1/M2 Mac

### Setup Instructions

1. **Install Docker for M1/M2 Mac**: 
   Follow the official Docker installation guide for ARM64-based Macs.
2. **Build the Container**: 
   Run the build script with the keyboard type as an argument. For instance, for Japanese, use

```
   ./build_container.sh JP
```

   For US keyboard type, replace `JP` with `US`.
   
3. **Start the Container**: 
   Initiate the container with

```
   ./start_container.sh
```
   
4. **Commit Changes**: 
   Save the current state of the Docker container using

```
   ./stop_container.sh
```
   
5. **Access the Container**: 
   For terminal access, run

```
   ./attach_container.sh
```

   to use bash inside the Docker container.
   
6. **Desktop Environment**: 
   To use the KDE Plasma Desktop via xrdp, connect using an RDP client to `127.0.0.1` or `localhost`.

### Recommended RDP Clients

- **Microsoft Remote Desktop**: 
  Supports sound playback. By setting the keyboard layout to Unicode, it also allows the input of the underscore character (`_`) using a Japanese keyboard.

These steps will guide you through setting up and using a ROS 2 Docker container on your M1/M2 Mac, including desktop access through RDP. Choose the Microsoft Remote Desktop for comprehensive functionality, including sound playback and full keyboard support.
