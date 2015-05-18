# Install the base image
FROM python:2.7

# make sure apt is up to date
RUN apt-get update

# install nodejs and npm
RUN apt-get install -y nodejs npm

# Install less & bower
RUN npm install -g less
RUN npm install -g bower

# Symlink /usr/bin/nodejs to /usr/bin/node
RUN ln -s /usr/bin/nodejs /usr/bin/node

COPY . /app/
WORKDIR /app/
RUN pip install -r requirements.txt
RUN bower install --allow-root
