FROM python:3.8

RUN apt-get update
RUN apt-get install -y supervisor nginx r-cran-devtools r-cran-forcats r-cran-readr

RUN pip3 install --upgrade pip
RUN pip3 install gunicorn


COPY server_config/supervisord.conf /supervisord.conf
COPY server_config/nginx /etc/nginx/sites-available/default
COPY server_config/docker-entrypoint.sh /entrypoint.sh

COPY . /app

# INSTALL GRANDFOREST
# Old Version:
#RUN R -e "devtools::install_github(\"simonlarsen/grandforest\")"
# Before executing this Dockerfile, clone the grandforest-federizable repository next to this file.
RUN R -e "devtools::install(\"/app/grandforest-federizable\")"

RUN pip3 install -r ./app/requirements.txt

EXPOSE 9000 9001

ENTRYPOINT ["sh", "/entrypoint.sh"]
