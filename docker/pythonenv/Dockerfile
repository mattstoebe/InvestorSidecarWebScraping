# Example image: ubuntu:24.04
# Argument to easy switch to different os versions.
ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}

# Build arguments - available only during the build
ARG WORKDIR=/home/ubuntu
ARG USER_ID="1000"
ARG GROUP_ID="1000"
ARG PYTHON_VERSION=""
ARG UV_VERSION="latest"


RUN apt-get update -yqq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    make \
    ca-certificates \
    curl \
    g++ \
    wget \
    unzip \
    groff \
    less \
    git \
    llvm \
    patch \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    && apt-get autoremove -qq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER ubuntu

ENV HOME=/home/ubuntu
ENV WORKDIR=${WORKDIR}
ENV PYTHONPATH=${WORKDIR}
ENV PATH=${HOME}/.local/bin:$PATH

WORKDIR ${HOME}

# install mise
RUN curl https://mise.run | sh

RUN mise use -g python@${PYTHON_VERSION} uv@${UV_VERSION} \
    && mise install

RUN ln -sf "$(mise which python)" "${HOME}/.local/bin/python" \
    && ln -sf "$(mise which uv)" "${HOME}/.local/bin/uv"

COPY --chown=${USER_ID}:${GROUP_ID} --chmod=744 docker/pythonenv/entrypoint.sh /
COPY --chown=${USER_ID}:${GROUP_ID} --chmod=744 pyproject.toml ${HOME}/

# Install dependencies in a separated virtual environment
RUN uv sync --no-dev \
    && uv cache clean \
    && rm -rf ${HOME}/.cache

WORKDIR ${WORKDIR}

ENTRYPOINT ["/entrypoint.sh"]