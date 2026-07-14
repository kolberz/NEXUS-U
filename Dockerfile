FROM python:3.12-slim AS build
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir build && python -m build

FROM python:3.12-slim AS runtime
RUN addgroup --system nexus && adduser --system --ingroup nexus nexus
WORKDIR /app
COPY --from=build /build/dist/*.whl /tmp/nexus_u.whl
RUN python -m pip install --no-cache-dir /tmp/nexus_u.whl && rm /tmp/nexus_u.whl
RUN mkdir -p /app/artifacts && chown -R nexus:nexus /app
USER nexus
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
ENTRYPOINT ["nexus-u"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
