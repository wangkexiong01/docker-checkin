FROM alpine
MAINTAINER wangkexiong <wangkexiong@gmail.com>

ENV TZ "Asia/Shanghai"

COPY working /working
COPY startup.sh /working/startup.sh

EXPOSE 5000
WORKDIR /working
VOLUME ["/working/database"]

RUN apk add --no-cache python py-lxml py-pip bash ca-certificates tzdata py-mysqldb && \
    pip install --no-cache-dir -r requirements.txt && \
    dos2unix startup.sh && \
    chmod +x startup.sh

CMD ["/bin/sh", "-c", "/working/startup.sh"]
