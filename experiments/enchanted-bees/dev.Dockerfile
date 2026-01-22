FROM mcr.microsoft.com/dotnet/sdk:8.0

ARG USER_ID=1000
ARG GROUP_ID=1000
ENV DEBIAN_FRONTEND=noninteractive

# Install system packages including Python and pip
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-pip python3-distutils git curl ca-certificates apt-transport-https gnupg lsb-release locales procps sudo gnupg2 dirmngr \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC and mssql-tools (sqlcmd) using keyring (avoid apt-key)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 mssql-tools \
    && ln -s /opt/mssql-tools/bin/sqlcmd /usr/local/bin/sqlcmd || true \
    && ln -s /opt/mssql-tools/bin/bcp /usr/local/bin/bcp || true \
    && rm -rf /var/lib/apt/lists/*

# Install Python tooling into the container image (no virtualenv used)
# Ensure pip/setuptools/wheel are up-to-date for installs performed at build-time.
# Use --break-system-packages so pip can upgrade system-managed packages in this image.
RUN python3 -m pip install --upgrade --break-system-packages pip setuptools wheel

# Copy requirements and install them into the image at build-time for reproducibility.
# If runtime installs are required, the dev entrypoint should install into the user/system
# Python environment (pip or pip --user) and must not create/expect a virtualenv.
COPY src/requirements.txt /tmp/requirements.txt
RUN if [ -f /tmp/requirements.txt ]; then python3 -m pip install --break-system-packages --no-cache-dir -r /tmp/requirements.txt; fi

# Create a non-root developer user named `dev` without an image-embedded password.
# Make UID/GID configurable via build args to match host mapping.
RUN groupadd -g ${GROUP_ID} dev || true \
    && useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash dev || true \
    && mkdir -p /workspace \
    && chown -R dev:dev /workspace /home/dev

# Grant passwordless sudo to the dev user for convenience
RUN echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev-nopasswd \
    && chmod 0440 /etc/sudoers.d/dev-nopasswd

# Add an entrypoint that can optionally install requirements from a mounted workspace
COPY dev-entrypoint.sh /usr/local/bin/dev-entrypoint.sh
RUN chmod +x /usr/local/bin/dev-entrypoint.sh

ENV HOME=/home/dev
WORKDIR /workspace

USER dev

ENTRYPOINT ["/usr/local/bin/dev-entrypoint.sh"]
CMD ["/bin/bash"]
