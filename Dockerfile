# ---------------------------------------
# BASE IMAGE
# ---------------------------------------
ARG TARGET_ARCH=linux/amd64
ARG HTTPS_ENABLED=false

FROM --platform=${TARGET_ARCH} python:3.13 AS builder

RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan -t rsa bitbucket.org >> ~/.ssh/known_hosts && \
    git config --global url."git@bitbucket.org:".insteadOf "https://bitbucket.org/"

WORKDIR /usr/src

COPY ./requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r ./requirements.txt

COPY . .


# ---------------------------------------
# DEV IMAGE
# ---------------------------------------
FROM builder AS atmail-webhooks-dev-image

EXPOSE ${LOCAL_PORT} ${DOCKER_PORT}

ENTRYPOINT [ "bash", "-c", "./webhooks.sh -p $DOCKER_PORT", "--https" ]


# ---------------------------------------
# STG & PROD IMAGE
# ---------------------------------------
FROM --platform=${TARGET_ARCH} ubuntu:24.04 AS atmail-webhooks-image

ARG USER=atmail-webhooks
ARG APP_DIR=/home/${USER}

RUN --mount=type=cache,target=/var/cache/apt/ apt-get update && \
    apt-get upgrade -y && \
    apt-get full-upgrade -y && \
    apt-get install -y sudo ca-certificates && \
    apt-get autoremove -y && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/*-

RUN groupadd -r atmail && \
    useradd -r -d /usr/local/bin/${USER} -s /sbin/nologin ${USER} && \
    echo atmail-webhooks ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER} && \
    mkdir -p ${APP_DIR}

WORKDIR ${APP_DIR}

COPY --from=builder /usr/local /usr/local

COPY --from=builder /usr/src ${APP_DIR}

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r ./requirements.txt

RUN mkdir -p /usr/local/etc/atmail/${USER} && \
    chown -R ${USER}:atmail ${APP_DIR}

USER ${USER}

EXPOSE ${LOCAL_PORT} ${DOCKER_PORT}

ENTRYPOINT [ "bash", "-c", "./webhooks.sh -p $DOCKER_PORT", "--https" ]
