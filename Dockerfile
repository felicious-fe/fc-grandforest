FROM python:3.8

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y redis-server supervisor nginx r-cran-devtools r-cran-forcats

RUN pip3 install --upgrade pip
RUN pip3 install gunicorn
RUN R -e "devtools::install_github(\"simonlarsen/grandforest\")"

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY nginx/default /etc/nginx/sites-available/default
COPY docker-entrypoint.sh /entrypoint.sh

COPY . /app

RUN pip3 install -r ./app/requirements.txt

EXPOSE 9000 9001

ENTRYPOINT ["sh", "/entrypoint.sh"]