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
COPY assets/project-x11-session.sh /usr/local/share/project-x11-session.sh
COPY rootfs/install-chrome.sh /usr/local/libexec/install-chrome.sh
COPY rootfs/patch-selkies-dpi.sh /usr/local/libexec/patch-selkies-dpi.sh
COPY rootfs/patch-selkies-audio.py /usr/local/libexec/patch-selkies-audio.py
COPY rootfs/patch-selkies-plasma.py /usr/local/libexec/patch-selkies-plasma.py
COPY rootfs/patch-selkies-client.py /usr/local/libexec/patch-selkies-client.py
COPY assets/selkies-hardware-decoder.js assets/selkies-safari-clipboard.js /usr/local/share/project-selkies/
RUN UBUNTU_VERSION="${UBUNTU_VERSION}" \
    INSTALL_ROS2="${INSTALL_ROS2}" \
    INSTALL_DEV_TOOLS="${INSTALL_DEV_TOOLS}" \
    /usr/local/libexec/install-development.sh && \
    /usr/local/libexec/patch-selkies-dpi.sh && \
    python3 /usr/local/libexec/patch-selkies-audio.py && \
    python3 /usr/local/libexec/patch-selkies-plasma.py && \
    python3 /usr/local/libexec/patch-selkies-client.py && \
    rm -f \
      /usr/local/libexec/install-development.sh \
      /usr/local/libexec/install-chrome.sh \
      /usr/local/libexec/patch-selkies-dpi.sh \
      /usr/local/libexec/patch-selkies-plasma.py \
      /usr/local/libexec/patch-selkies-audio.py

# init-nginx refreshes the served dashboard and runs upstream compatibility
# hooks. Apply our shared client fixes after those hooks on every startup.
RUN printf '\npython3 /usr/local/libexec/patch-selkies-client.py\n' >> /etc/s6-overlay/s6-rc.d/init-nginx/run

COPY --from=xrdp-pulseaudio-builder /xrdp-pulseaudio-root/ /

COPY rootfs/customize-user.sh /usr/local/libexec/customize-apple-container-user.sh
COPY assets/kubuntu-kdeglobals /tmp/kubuntu-kdeglobals
COPY assets/home.desktop /tmp/home.desktop
COPY assets/trash.desktop /tmp/trash.desktop
COPY assets/xrdp-session.sh /usr/local/share/xrdp-session.sh
COPY rootfs/custom-cont-init.d/50-xrdp /custom-cont-init.d/50-xrdp
COPY rootfs/s6-overlay/ /etc/s6-overlay/
COPY assets/container-action.py /usr/local/bin/project-container-action
COPY assets/container-*.desktop /usr/local/share/project-container-actions/

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
    /usr/local/bin/project-container-action \
    /usr/local/share/xrdp-session.sh \
    /custom-cont-init.d/50-xrdp \
    /etc/s6-overlay/s6-rc.d/svc-xrdp-sesman/run \
    /etc/s6-overlay/s6-rc.d/svc-xrdp/run

# Avoid the distro Xsession -> im-launch path: im-config 0.62 assumes a
# systemd journal, which is not available in this s6-managed container.
RUN install -m 755 /usr/local/share/xrdp-session.sh /etc/xrdp/startwm.sh

EXPOSE 3000 3001 3389 8765 9090
VOLUME ["/config"]

# Keep root as the image user because s6 initializes system services before
# dropping privileges for the desktop session.
USER root
