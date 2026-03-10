FROM python:3.12

ARG PORT=8000

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=$PORT
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

COPY server/pyproject.toml pyproject.toml

RUN apt-get update && apt-get install -y libpq-dev

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN export PATH="/root/.local/bin:$PATH"

RUN /root/.local/bin/poetry install

COPY server/ /app/

# Override PyPI plugin versions with local copies that have the latest code
COPY plugins/enthusiast-common/enthusiast_common /usr/local/lib/python3.12/site-packages/enthusiast_common
COPY plugins/enthusiast-model-openai/enthusiast_model_openai /usr/local/lib/python3.12/site-packages/enthusiast_model_openai
COPY plugins/enthusiast-source-sample/enthusiast_source_sample /usr/local/lib/python3.12/site-packages/enthusiast_source_sample
COPY plugins/enthusiast-file-parsers/enthusiast_file_parsers /usr/local/lib/python3.12/site-packages/enthusiast_file_parsers
COPY server/plugins/enthusiast-source-custom/enthusiast_source_custom /usr/local/lib/python3.12/site-packages/enthusiast_source_custom
COPY server/plugins/enthusiast-source-dermlax/enthusiast_source_dermlax /usr/local/lib/python3.12/site-packages/enthusiast_source_dermlax

RUN chmod u+x /app/docker-entrypoint.sh

EXPOSE $PORT

ENTRYPOINT ["/app/docker-entrypoint.sh"]
