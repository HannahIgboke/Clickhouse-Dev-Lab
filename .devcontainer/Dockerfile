FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# The base image has a yarn APT repository with an expired GPG key.
# This breaks apt-get update when the docker-in-docker feature runs.
# Since we don't need yarn, simply remove the problematic repo.
RUN rm -f /etc/apt/sources.list.d/yarn.list /etc/apt/sources.list.d/yarn*.list \
    && apt-get update || true