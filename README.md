# bob-the-builder
Bob-the-builder downloads your src from https://github.com and 'docker-compose build's, then 'docker-compose run [yourtest docker]' and then pushed your image to https://hub.docker.com if your build and tests where succesfull.  
  
Bob has three part:
* A command line interface tool 'bob'
* A website so you can visually see what is build and the logs related to the build.
* The workers / builders. The are servers that sit and watch a AWS message queue for build jobs.

## example:

in this example we will build https://github.com/metocean/bob-the-builder-example  
  
1) get the source and submit the build job to your bob the builder servers  
```
$ git clone https://github.com/metocean/bob-the-builder-example.git
$ cd bob-the-builder-example/
$ bob build
ok - building: metocean/bob-the-builder-example - master
```
2) you check check the build status via
```
$ bob ps
{state} - {repo} - {branch} - {tag} - {duration} - {builder_hostname} - {created_by}
building - metocean/bob-the-builder-example - master - latest - 0:00 - bob2.metocean.co.nz - gregc
```
or the bob website  
![Image of tasks]
(https://github.com/metocean/bob-the-builder/blob/master/docs/images/bob-tasks.png)
![Image of task]
(https://github.com/metocean/bob-the-builder/blob/master/docs/images/bob-task.png)

## setting up a project to use bob
You need to add two files to you projects repo for bob to know how to build:  
  
1. docker-compose.yml  - the bob worker uses this for building / testing  
2. bob-the-builder.yml - this tells the bob worker where to push the image into docker hub, and who to email once it has finished doing so.  
  
### Example using service name:  
**docker-compose.yml:**
```
version: '2'
services:
  server:
    build: ./server/
  client:
    build: ./client/
    depends_on:
      - server
    links:
      - server
```
**bob-the-builder.yml:**
```
docker_compose:
    file: docker-compose.yml
    test_service: client
    services_to_push:
        server: metocean/bob-example-server
        client: metocean/bob-example-client
notification_emails:
    - [some-one-at]@gmail.com
```
  
### Example using image name:  
**docker-compose.yml:**
```
version: '2'
services:
  model:
    image: metocean/ww3:model
    build:
      context: ./docker/model
      args:
        physics: st4
  wrapper-base:
    image: metocean/ww3:wrapper-base
    build:
      context: ./docker/wrapper-base
      dockerfile: Dockerfile
    depends_on:
      - model
  ww3:
    image: metocean/ww3
    build:
      context: ./
      args:
        mopybranch: master
    depends_on:
      - wrapper-base
```
**bob-the-builder.yml:**
```
docker_compose:
    file: docker-compose.yml
    #test_service: test_fc
    services_to_push:
        "metocean/ww3:model": "metocean/ww3:model"
        "metocean/ww3:wrapper-base": "metocean/ww3:wrapper-base"
        "metocean/ww3:latest": "metocean/ww3"
notification_emails:
    - [some-one-at]@gmail.com
```
varabile description in bob-the-builder.yml:  
* docker_compose:
  * file: points *to the docker compose file to build (default: docker-compose.yml')*
  * test_service: *points to the docker compose service to run / test. If this docker exits with a non-zero the build fails.*
  * services_to_push: *tell bob what services to push to docker hub.*
    * server: *metocean/bob-example-server e.g. service "server" is push to docker hub as "metocean/bob-example-server"*

## github web_hooks
if you want bob to build your repo on a "release" you can add the following hook  
**Payload URL:** *https://bob.[your bob webserver]/github_webhook*  
**Secret:** *[your secret in webserver-settings.yml]*  
**Content type:** application/json  
**select:** 'Send me everything.'  

## install

### install client
```
sudo pip install git+https://github.com/metocean/bob-the-builder.git
```

### install webserver
```
pip install -r https://raw.githubusercontent.com/metocean/bob-the-builder/master/requirements-webserver.txt
sudo pip install git+https://github.com/metocean/bob-the-builder.git
```

### install worker
```
sudo apt-get install python3-dev python3-pycurl git unzip
pip install -r https://raw.githubusercontent.com/metocean/bob-the-builder/master/requirements-worker.txt
sudo pip install git+https://github.com/metocean/bob-the-builder.git
```

## config
You can store the settings for bob in if:  
* /usr/local/etc/bob
* /etc/bob
  
If you would like only your user to use bob store them in:  
* ${HOME}/.bob/

### config AWS connection for SQS and DynamoDB
```
mkdir -p ${HOME}/.bob/
touch ${HOME}/.bob/aws-settings.yml
```
```
region_name: us-west-2
aws_access_key_id: AKIAIOSFODNN7_EXAMPLE_ID
aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCY_EXAMPLE_KEY
```
### config worker
```
mkdir -p ${HOME}/.bob/
touch ${HOME}/.bob/worker-settings.yml
```
```
git_hub:
  login: *******
  password: ******

docker_hub:
  login: ******
  password: ******

email:
  host: smtp.gmail.com
  port: 587
  starttls: true
  login: ******@metocean.co.nz
  password: ******
  from: *****@metocean.co.nz
```
