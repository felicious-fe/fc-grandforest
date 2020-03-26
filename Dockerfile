FROM fc_template:latest

COPY . /app/fc_server

RUN pip3 install -r ./app/fc_server/requirements.txt



