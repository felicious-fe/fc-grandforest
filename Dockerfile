FROM python:3.8

# Install required system packages and python modules
RUN apt-get update
RUN apt-get install -y supervisor nginx
RUN pip3 install --upgrade pip
RUN pip3 install gunicorn

# Install required R packages
# It's better to install packages as binary package via apt-get than to compile them in R
RUN apt-get install -y r-cran-devtools r-cran-tidyverse r-cran-biocmanager
RUN R -e "BiocManager::install(\"org.Hs.eg.db\", update = FALSE, ask = FALSE)"
RUN R -e "install.packages(\"geomnet\")"

COPY server_config/supervisord.conf /supervisord.conf
COPY server_config/nginx /etc/nginx/sites-available/default
COPY server_config/docker-entrypoint.sh /entrypoint.sh

COPY . /app

# INSTALL GRANDFOREST
# Old Version:
#RUN R -e "devtools::install_github(\"simonlarsen/grandforest\")"
# Before executing this Dockerfile, clone the grandforest-federizable repository next to this file.
RUN R -e "devtools::install(\"/app/grandforest-federalizable\")"

RUN pip3 install -r ./app/requirements.txt

EXPOSE 9000 9001

ENTRYPOINT ["sh", "/entrypoint.sh"]
