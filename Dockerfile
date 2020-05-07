FROM fc_template_flask:latest

COPY . /app/fc_app

RUN pip3 install -r ./app/fc_app/requirements.txt



