FROM postgres:14.3
ENV TZ Europe/Moscow
RUN localedef -i ru_RU -c -f UTF-8 -A /usr/share/locale/locale.alias ru_RU.1251
ENV LANG ru_RU.1251