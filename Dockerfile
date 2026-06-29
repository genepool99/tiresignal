ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache python3

WORKDIR /app
COPY *.py ./
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
