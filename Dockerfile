FROM fc_template_flask:latest

COPY . /app/fc_server

RUN pip3 install -r ./app/fc_server/requirements.txt



