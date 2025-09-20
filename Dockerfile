FROM public.ecr.aws/sam/build-python3.13:latest AS builder

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Installer Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

WORKDIR /app

# Copier les fichiers de dépendances
COPY pyproject.toml poetry.lock ./

RUN mkdir -p /tmp/deps && \
    curl -L -o /tmp/deps/awslambdaric-3.1.1.tar.gz \
    https://files.pythonhosted.org/packages/source/a/awslambdaric/awslambdaric-3.1.1.tar.gz

# Installer les dépendances Python
RUN poetry install --no-interaction --no-ansi --sync

# Copier le code source
COPY . .

# Rendre le script d’entrée exécutable
RUN chmod +x /app/entrypoint.sh

# Définir le PYTHONPATH pour que `app/` soit reconnu comme un package
ENV PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
