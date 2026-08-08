# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ghcr.io/tatsuyai713/webtop-kde-base-arm64-u24.04:1.1.0

FROM ${BASE_IMAGE} AS xrdp-pulseaudio-builder

ARG UBUNTU_VERSION=24.04
COPY rootfs/build-xrdp-pulseaudio.sh /usr/local/libexec/build-xrdp-pulseaudio.sh
RUN UBUNTU_VERSION="${UBUNTU_VERSION}" /usr/local/libexec/build-xrdp-pulseaudio.sh

FROM ${BASE_IMAGE}

ARG USER_NAME
ARG USER_UID
ARG USER_GID
ARG USER_LANGUAGE=en
ARG USER_LANG_ENV=en_US.UTF-8
ARG USER_LANGUAGE_ENV=en_US:en
ARG USER_INPUT_METHOD=
ARG USER_XMODIFIERS=
ARG KEYBOARD_LAYOUT=us
ARG UBUNTU_VERSION=24.04
ARG INSTALL_ROS2=true
ARG INSTALL_DEV_TOOLS=true

ENV HOME="/home/${USER_NAME}" \
    USER_NAME="${USER_NAME}" \
    SHELL="/bin/bash" \
    LANG="${USER_LANG_ENV}" \
    LANGUAGE="${USER_LANGUAGE_ENV}" \
    LC_ALL="${USER_LANG_ENV}" \
    GTK_IM_MODULE="${USER_INPUT_METHOD}" \
    QT_IM_MODULE="${USER_INPUT_METHOD}" \
    XMODIFIERS="${USER_XMODIFIERS}" \
    INPUT_METHOD="${USER_INPUT_METHOD}" \
    SDL_IM_MODULE="${USER_INPUT_METHOD}" \
    GLFW_IM_MODULE="${USER_INPUT_METHOD}"

COPY rootfs/install-development.sh /usr/local/libexec/install-development.sh
COPY rootfs/patch-selkies-dpi.sh /usr/local/libexec/patch-selkies-dpi.sh
COPY rootfs/patch-selkies-audio.py /usr/local/libexec/patch-selkies-audio.py
RUN UBUNTU_VERSION="${UBUNTU_VERSION}" \
    INSTALL_ROS2="${INSTALL_ROS2}" \
    INSTALL_DEV_TOOLS="${INSTALL_DEV_TOOLS}" \
    /usr/local/libexec/install-development.sh && \
    /usr/local/libexec/patch-selkies-dpi.sh && \
    python3 /usr/local/libexec/patch-selkies-audio.py && \
    rm -f \
      /usr/local/libexec/install-development.sh \
      /usr/local/libexec/patch-selkies-dpi.sh \
      /usr/local/libexec/patch-selkies-audio.py

COPY --from=xrdp-pulseaudio-builder /xrdp-pulseaudio-root/ /

COPY rootfs/customize-user.sh /usr/local/libexec/customize-apple-container-user.sh
COPY assets/kubuntu-kdeglobals /tmp/kubuntu-kdeglobals
COPY assets/home.desktop /tmp/home.desktop
COPY assets/trash.desktop /tmp/trash.desktop
COPY assets/xrdp-session.sh /usr/local/share/xrdp-session.sh
COPY rootfs/custom-cont-init.d/50-xrdp /custom-cont-init.d/50-xrdp
COPY rootfs/s6-overlay/ /etc/s6-overlay/

RUN --mount=type=secret,id=user_password,required=true \
    USER_NAME="${USER_NAME}" \
    USER_UID="${USER_UID}" \
    USER_GID="${USER_GID}" \
    USER_LANGUAGE="${USER_LANGUAGE}" \
    KEYBOARD_LAYOUT="${KEYBOARD_LAYOUT}" \
    USER_PASSWORD_FILE=/run/secrets/user_password \
    /usr/local/libexec/customize-apple-container-user.sh && \
    rm -f /usr/local/libexec/customize-apple-container-user.sh

RUN chmod 755 \
    /usr/local/share/xrdp-session.sh \
    /custom-cont-init.d/50-xrdp \
    /etc/s6-overlay/s6-rc.d/svc-xrdp-sesman/run \
    /etc/s6-overlay/s6-rc.d/svc-xrdp/run

EXPOSE 3000 3001 3389 8765 9090
VOLUME ["/config"]

# Keep root as the image user because s6 initializes system services before
# dropping privileges for the desktop session.
USER root
