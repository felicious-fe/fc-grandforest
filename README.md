This is a federated app which is based on the [fc federated flask image](https://gitlab.lrz.de/Schaefjo/fc_federated_flask). To run this app, the user needs to upload a file in the same format as the "exemplary_data.txt".

 - This app overwrites the api.py as well as the web.py.
 - In the templates directory are the html templates for this app
 - In the requirements.txt are the project specific python requirements which will be installed in the docker image via Dockerfile
 - The build.sh automatically builds the federated k-means app with the correct name
 
DOCKERFILE:
 - FROM: This line tells docker on which image this app should be base upon, here it is the [fc federated flask image](https://gitlab.lrz.de/Schaefjo/fc_federated_flask)
 - COPY: copies the content in the right directory to overwrite the files from the [fc federated flask image](https://gitlab.lrz.de/Schaefjo/fc_federated_flask)
 - RUN pip3 install: installs the requirements from the requirements.txt which is now in the directory /app/fc_app/

BEFORE RUNNING THE BUILD.SH:
 - this image is based upon the [fc federated flask image](https://gitlab.lrz.de/Schaefjo/fc_federated_flask), and this image again is based upon the [fc federated base](https://gitlab.lrz.de/Schaefjo/fc_federated_base)
 - First run the build.sh from fc federated base, then from fc federated flask and then the one from the fc federated kmeans