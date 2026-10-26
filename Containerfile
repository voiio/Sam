FROM python:3.15-alpine
WORKDIR /app

ARG TTS_VOICE=onyx

COPY . /app
RUN python -m pip install /app
CMD ["python", "-m", "sam", "run", "slack"]
