FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Fix expired yarn GPG key that breaks apt-get update when the
# docker-in-docker feature tries to install packages.
# Download first, then dearmor, to avoid pipe-related gpg errors in a build context.
RUN curl -fsSL -o /tmp/yarn-pubkey.gpg https://dl.yarnpkg.com/debian/pubkey.gpg \
    && gpg --batch --no-tty --dearmor -o /usr/share/keyrings/yarn-archive-keyring.gpg /tmp/yarn-pubkey.gpg \
    && rm -f /tmp/yarn-pubkey.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/yarn-archive-keyring.gpg] https://dl.yarnpkg.com/debian stable main" \
        > /etc/apt/sources.list.d/yarn.list