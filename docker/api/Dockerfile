FROM python:3.9
ARG API_HOST
ARG API_PORT
ARG MONGO_URL

RUN useradd --create-home app
WORKDIR /home/app
USER app

# in order to avoid re-installation of requirements on every source file update
COPY --chown=app:app api/requirements.txt .
ENV PATH="/home/app/.local/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=app:app .env .
COPY --chown=app:app ./api/ ./api/
CMD uvicorn api.main:app --host $API_HOST --port $API_PORT --workers `nproc`
