# bob-the-builder
Builds / Test Docker Compose files in GIT HUB and the Pushes them to Docker Hub.

## install

### install client
pip install -r https://raw.githubusercontent.com/metocean/bob-the-builder/master/requirements-client.txt
sudo pip install -e git+https://github.com/metocean/bob-the-builder.git/#egg=bob

### install webserver
pip install -r https://raw.githubusercontent.com/metocean/bob-the-builder/master/requirements-webserver.txt
sudo pip install -e git+https://github.com/metocean/bob-the-builder.git/#egg=bob

### install worker
pip install -r https://raw.githubusercontent.com/metocean/bob-the-builder/master/requirements-worker.txt
sudo pip install -e git+https://github.com/metocean/bob-the-builder.git/#egg=bob

## config
### config worker
```
mkdir ${HOME}/.bob/
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

### config AWS connection for SQS and DynamoDB
```
mkdir ${HOME}/.aws/
touch ${HOME}/.aws/config
```
```
[default]
region=us-west-2
aws_access_key_id=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```
