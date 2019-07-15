# jobcase-exercise
Jobcase Exercise

Repo containing code for an interview example for Jobcase.  
The original ask was:

> Using Python:
  
  1 Create an ssh key pair on ec2
  2 Create an AWS instance as an t2.micro using AWS Linux ami named "jobcase-test-app" that installs the following packages on launch: apache, mysql, python, logrotate, aws-client
  3 Tag the instance with the following: Project: Jobcase, Environment: Development,   Project: Test-Lab

Some assumptions were made:
- The AMI is already present on AWS and is made with AWS Linux not AWS Linux 2.
- "that installs" refers to the creation code and not the AMI itself.
- "apache" refers to httpd.
- "aws-client" refers to aws-cli.
- Tags on resources have unique names, so we can't have both "Jobcase" and 
"Test-Lab" as a Project tag.  Opted to concatenate them.

This project was built with Pantsbuild (https://www.pantsbuild.org/).  It makes
creating pex files and managing dependencies extremely easy.  The project comes 
with tests and can be launched using `./pants test tests::` from the project 
root directory.  The tests run primarily using moto (
https://github.com/spulec/moto) which mocks out boto3.  The code itself 
leverages boto3 to connect and send requests to AWS.  The pex file can be 
recreated using `./pants binary src:create-instance`.  I used pyenv 
(https://github.com/pyenv/pyenv) to install and manage multiple python versions.
The pex file requires that a version of python is installed, but otherwise 
includes all of the dependencies.  Tested with both python 2 and python 3.  Only
enabled the pex file to be run on OSX.