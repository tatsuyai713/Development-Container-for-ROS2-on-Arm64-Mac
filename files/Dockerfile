FROM --platform=linux/amd64 ghcr.io/tatsuyai713/development-container-for-ros-2-on-m1-2-mac:v22.04-x86_64

ARG UID=9001
ARG GID=9001
ARG UNAME=ubuntu
ARG HOSTNAME=docker
ARG NEW_HOSTNAME=${HOSTNAME}-Docker
ARG USERNAME=$UNAME
ARG HOME=/home/$USERNAME
ARG LOCALE="US"

USER root

# Temporary Fix for ROS 2
RUN rm -rf /etc/apt/sources.list.d/ros2.list
RUN apt update && sudo apt install curl -y
RUN curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.1.0/ros2-apt-source_1.1.0.jammy_all.deb"
RUN dpkg -i /tmp/ros2-apt-source.deb

RUN if [ "${LOCALE}" = "JP" ]; then \
    apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y \
    language-pack-ja-base \
    language-pack-ja \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    ; \
fi

# Set locale
RUN if [ "${LOCALE}" = "JP" ]; then \
        cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
        && echo 'Asia/Tokyo' > /etc/timezone; \
fi
RUN if [ "${LOCALE}" = "JP" ]; then \
        locale-gen ja_JP.UTF-8 \
        && echo 'LC_ALL=ja_JP.UTF-8' > /etc/default/locale \
        && echo 'LANG=ja_JP.UTF-8' >> /etc/default/locale\
        && LANG=ja_JP.UTF-8 \
        && LANGUAGE=ja_JP:ja \
        && LC_ALL=ja_JP.UTF-8; \
fi
RUN if [ "${LOCALE}" = "JP" ]; then \
    apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y \
    init systemd locales fcitx-mozc language-pack-ja \
    net-tools iputils-ping curl wget telnet less vim sudo \
    g++ cmake fcitx-libs-dev libdbus-1-dev fcitx-module-dbus kde-config-fcitx \
    && dbus-launch --sh-syntax --exit-with-session > /dev/null \
    ; \
fi

RUN if [ "${LOCALE}" = "JP" ]; then \
    rm -f /etc/localtime && ln -s /usr/share/zoneinfo/Asia/Tokyo /etc/localtime; \
fi

RUN useradd -u $UID -m $USERNAME && \
        echo "$USERNAME:$USERNAME" | chpasswd && \
        usermod --shell /bin/bash $USERNAME && \
        usermod -aG sudo $USERNAME && \
        echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME && \
        chmod 0440 /etc/sudoers.d/$USERNAME && \
        usermod  --uid $UID $USERNAME && \
        groupmod --gid $GID $USERNAME && \
        chown -R $USERNAME:$USERNAME $HOME && \
        chmod 666 /dev/null && \
        chmod 666 /dev/urandom


# Set supervisord conf for xrdp service
RUN { \
      echo "[supervisord]"; \
      echo "user=root"; \
      echo "nodaemon=true"; \
      echo "logfile=/var/log/supervisor/supervisord.log"; \
      echo "childlogdir=/var/log/supervisor"; \
      echo "[program:dbus]"; \
      echo "command=/usr/bin/dbus-daemon --system --nofork --nopidfile"; \
      echo "[program:xrdp-sesman]"; \
      echo "command=/usr/sbin/xrdp-sesman --nodaemon"; \
      echo "[program:xrdp]"; \
      echo "command=/usr/sbin/xrdp --nodaemon"; \
      echo "user=xrdp"; \
      echo "[program:pulseaudio]"; \
      echo "priority=15"; \
      echo "directory=/home/$USERNAME"; \
      echo "command=/usr/bin/pulseaudio"; \
      echo "user=$USERNAME"; \
      echo "autostart=true"; \
      echo "autorestart=true"; \
      echo "stopsignal=TERM"; \
      echo "environment=HOME=/home/$USERNAME,XDG_RUNTIME_DIR=/tmp/runtime-$USERNAME"; \
      echo "stdout_logfile=/var/log/pulseaudio.log"; \
      echo "stderr_logfile=/var/log/pulseaudio.err"; \
    } > /etc/supervisor/xrdp.conf
    

USER $USERNAME

# initialize rosdep
RUN rosdep update

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc

RUN if [ "${LOCALE}" = "JP" ]; then \
    echo "export LANG=ja_JP.UTF-8" >> ~/.bashrc; \
fi


RUN LANG=C xdg-user-dirs-update --force
RUN touch /home/${USERNAME}/Desktop/home.desktop
RUN touch /home/${USERNAME}/Desktop/trash.desktop

# Make Desktop Icons
RUN { \
    echo "[Desktop Entry]"; \
    echo "Encoding=UTF-8"; \
    echo "Name=Home"; \
    echo "GenericName=Personal Files"; \
    echo "URL[$e]=$HOME"; \
    echo "Icon=user-home"; \
    echo "Type=Link"; \
    } > /home/${USERNAME}/Desktop/home.desktop

RUN { \
    echo "[Desktop Entry]"; \
    echo "Name=Trash"; \
    echo "Comment=Contains removed files"; \
    echo "Icon=user-trash-full"; \
    echo "EmptyIcon=user-trash"; \
    echo "URL=trash:/"; \
    echo "Type=Link"; \
    } > /home/${USERNAME}/Desktop/trash.desktop

USER root
RUN chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/*
RUN chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.config


# Copy entrypoint file
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
