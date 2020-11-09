# Federated Mean App for the FeatureCloud Platform

This FeatureCloud app is based on the [FeatureCloud Flask Template](https://github.com/FeatureCloud/flask_template). 

### Usage
The app computes the mean of all .csv and .txt files in the FeatureCloud input directory.
The content of the files should be comma-seperated and look similar to this:

File 1:
    
    1,3,4,5,6

File 2:
    
    4,2,1
    
The local mean of both files will be computed and then aggregated in the coordinator to compute the mean of all participating sites.


### Technical Details

 - This app overwrites the api.py and web.py of the [FeatureCloud Flask Template](https://github.com/FeatureCloud/flask_template).
 - In the templates directory are the html templates for this app
 - In the requirements.txt are the project specific python requirements which will be installed in the docker image via Dockerfile
 - The build.sh automatically builds the Federated Mean App with the image name fc_mean
 