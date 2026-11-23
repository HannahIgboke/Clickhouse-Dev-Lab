FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Fix expired yarn GPG key that breaks apt-get update when the
# docker-in-docker feature tries to install packages.
# --batch --no-tty avoids gpg trying to open /dev/tty in a build.
RUN curl -fsSL https://dl.yarnpkg.com/debian/pubkey.gpg \
    | gpg --batch --no-tty --dearmor -o /usr/share/keyrings/yarn-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/yarn-archive-keyring.gpg] https://dl.yarnpkg.com/debian stable main" \
        > /etc/apt/sources.list.d/yarn.list