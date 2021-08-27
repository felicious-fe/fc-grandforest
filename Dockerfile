FROM python:3.8-bullseye

# Install required system packages and python modules
RUN apt-get update && apt-get install -y supervisor nginx
RUN pip3 install --upgrade pip
RUN pip3 install gunicorn

# Install required R packages
# It's better/faster/more stable to install packages as binary package via apt-get than to compile them in R, but they are versioned very conservatively
RUN apt-get update && apt-get install -y libtool r-cran-devtools r-cran-tidyverse r-cran-svglite r-cran-biocmanager r-cran-survival r-cran-nloptr
RUN R -e "BiocManager::install(\"org.Hs.eg.db\", update = FALSE, ask = FALSE)"
RUN R -e "BiocManager::install(\"ComplexHeatmap\", update = FALSE, ask = FALSE)"
RUN R -e "devtools::install_version(\"geomnet\", version = \"0.3.1\", repos = \"http://cran.us.r-project.org\")"
RUN R -e "install.packages(\"survminer\")"


COPY server_config/supervisord.conf /supervisord.conf
COPY server_config/nginx /etc/nginx/sites-available/default
COPY server_config/docker-entrypoint.sh /entrypoint.sh

COPY . /app

# INSTALL GRANDFOREST
# Before executing this Dockerfile, clone the grandforest-federizable repository next to this file.
RUN R -e "devtools::install(\"/app/federated-grandforest-R\")"

RUN pip3 install -r ./app/requirements.txt

EXPOSE 9000 9001

ENTRYPOINT ["sh", "/entrypoint.sh"]
