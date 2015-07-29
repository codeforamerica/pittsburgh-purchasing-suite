[![Build Status](https://travis-ci.org/codeforamerica/pittsburgh-purchasing-suite.svg?branch=master)](https://travis-ci.org/codeforamerica/pittsburgh-purchasing-suite)

# Pittsburgh Purchasing Suite

## What is it?

The Pittsburgh Purchasing Suite is a collection of small applets backed by a common data store. These applets allow users to manage, view, and advertise contracts.

#### What's the status?
Core Pittsburgh Purchasing Suite features are in alpha, with other features in different stages of early development.

##### Feature status:

| Feature | Status |
|---------|--------|
| **Scout** - a tool to look up contracts | [Alpha Deployed](http://pittsburgh-purchasing.herokuapp.com/scout/) |
| **Atlas** - a tool to explore the procurement process | [Alpha Deployed](http://pittsburgh-purchasing.herokuapp.com/sherpa/) |
| **Beacon** - a tool to be notified about new opportunities | [Alpha Deployed](http://pittsburgh-purchasing.herokuapp.com/beacon/) |
| **Conductor** - a tool for managing contracts & contract renewal | [Alpha Deployed](http://pittsburgh-purchasing.herokuapp.com/conductor/) (required login) |

## Who made it?
The purchasing suite is a project of the 2015 Pittsburgh Code for America [fellowship team](http://codeforamerica.org/governments/pittsburgh).

## How
The purchasing suite is a [Flask](http://flask.pocoo.org/) app. It uses [Postgres](http://www.postgresql.org/) for a database and uses [bower](http://bower.io/) to manage most of its dependencies. It also uses [less](http://lesscss.org/) to compile style assets. Big thanks to the [cookiecutter-flask](https://github.com/sloria/cookiecutter-flask) project for a nice kickstart.

### With Docker

#### Setting up Docker

The best way to get set up with Docker is to install [boot2docker](http://boot2docker.io/), a tiny core linux VM specifically designed to run Docker containers. For a complete description of how to download and get started with Docker using boot2docker, the best resource is on [Docker's site](http://docs.docker.com/installation/mac/). The Suite also uses [Docker Compose](https://docs.docker.com/compose/), a tool for managing and linking multiple containers together. Installation instructions for Compose can be found [here](https://docs.docker.com/compose/install/).

Once you've installed and verified that Docker, boot2docker, and Docker Compose are installed and ready for use on your system, go ahead and clone the repo:

```bash
git clone https://github.com/codeforamerica/pittsburgh-purchasing-suite
cd pittsburgh-purchasing-suite
```

Now that you have the code, you'll need to create your environment file to make sure that the containers link properly:

```bash
sh dockerenv.sh
```

This will create a new `.dockerenv` file with the necessary variables set for you. The `dockerenv.sh` script will output the address of your Docker container. If you don't remember it, you can run `boot2docker ip` to find it at any time. For now, you should be ready build your web container:

```bash
docker-compose build web
```

#### Setting up the database

While Docker will create a Postgres container for you, it won't set up the database tables. Fortunately, you can run one-off commands with Docker Compose. Here are some tasks that have been set up for you:

```bash
# create the db models
docker-compose run web python manage.py db upgrade
# create a user
docker-compose run web python manage.py seed_user -e <your-email-here> -r <your-desired-role>
# import some baseline data
docker-compose run web python manage.py seed
docker-compose run web python manage.py import_nigp --replace t
```

Now everything should be ready to go.

```bash
docker-compose up
```

Navigate to the IP address that you found when you ran `boot2docker ip` at port 9000, and you should be up and running.

### Without Docker

Though using Docker is a good way to get started, you can also use the app without Docker.

#### Core Dependencies

It is highly recommended that you use use [virtualenv](https://readthedocs.org/projects/virtualenv/) (and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/) for convenience). For a how-to on getting set up, please consult this [howto](https://github.com/codeforamerica/howto/blob/master/Python-Virtualenv.md). Additionally, you'll need node to install bower (see this [howto](https://github.com/codeforamerica/howto/blob/master/Node.js.md) for more on Node), and it is recommended that you use [postgres.app](http://postgresapp.com/) to handle your Postgres (assuming you are developing on OSX).

#### Developing the Pittsburgh Purchasing Suite
Use the following commands to bootstrap your development environment:

**python app**:

```bash
# clone the repo
git clone https://github.com/codeforamerica/pittsburgh-purchasing-suite
# change into the repo directory
cd pittsburgh-purchasing-suite
# install python dependencies
# NOTE: if you are using postgres.app, you will need to make sure to
# set your PATH to include the bin directory. For example:
# export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.4/bin/
pip install -r requirements/dev.txt
# note, if you are looking to deploy, you won't need dev dependencies.
# uncomment & run this command instead:
# pip install -r requirements.txt
```

**NOTE**: The app's configuration lives in [`settings.py`](https://github.com/codeforamerica/pittsburgh-purchasing-suite/blob/master/purchasing/settings.py). When different configurations (such as `DevConfig`) are referenced in the next sections, they are contained in that file.

**email**:

The app uses [Flask-Mail](https://pythonhosted.org/Flask-Mail/) to handle sending emails. This includes emails about subscriptions to various contracts, notifications about contracts being followed, and others. In production, the app relies on [Sendgrid](https://sendgrid.com/), but in development, it uses the [Gmail SMTP server](https://support.google.com/a/answer/176600?hl=en). If you don't need to send emails, you can disable emails by setting `MAIL_SUPPRESS_SEND = True` in the `DevConfig` configuration object.

If you would like to send email over the Gmail SMTP server, you will need to add two environmental variables: `MAIL_USERNAME` and `MAIL_PASSWORD`. You can use Google's [app passwords](https://support.google.com/accounts/answer/185833?hl=en) to create a unique password only for the app.

**database**:

```bash
# login to postgres. If you are using postgres.app, you can click
# the little elephant in your taskbar to open this instead of using
# psql
psql
create database purchasing;
```

Once you've created your database, you'll need to open `purchasing/settings.py` and edit the `DevConfig` object to use the proper [SQLAlchemy database configuration string](http://docs.sqlalchemy.org/en/rel_1_0/core/engines.html#postgresql). If you named your database `purchasing`, you probably won't have to change anything. Then:

```bash
# upgrade your database to the latest version
python manage.py db upgrade
```

By default, SQLAlchemy logging is turned off. If you want to enable it, you'll need to add a `SQLALCHEMY_ECHO` flag to your environment.

**front-end**:

If you haven't installed [npm](https://www.npmjs.com/), please consult this [howto](https://github.com/codeforamerica/howto/blob/master/Node.js.md#install) for the best way to do so. On Mac, you can also use [homebrew](http://brew.sh/).

Once you install node, run the following:

```bash
# install bower, less, and uglifyjs
# you may need to use sudo
npm install -g bower
npm install -g uglifyjs
npm install -g less
# use bower to install the dependencies
bower install
```

**login and user accounts**

Right now, the Pittsburgh Purchasing Suite uses [persona](https://login.persona.org/about) to handle authentication. The app uses its own user database to manage roles and object-based authorization. You will need to sign in through persona and then enter yourself into the database in order to have access to admin and other pages.

A manage task has been created to allow you to quickly create a user to access the admin and other staff-only tasks. To add an email, run the following command (NOTE: if you updated your database as per above, you will probably want to give youself a role of 1, which will give you superadmin privledges), putting your email/desired role in the appropriate places:

```bash
python manage.py seed_user -e <your-email-here> -r <your-desired-role>
```

Now, logging in through persona should also give you access to the app.

**up and running**

If you boot up the app right now, it will have no data. If you want to add some data, a small manage task has been added to allow for quick data importation.

```bash
# run the data importers
python manage.py seed
```

Now you should be ready to roll with some seed data to get you started!

```bash
# run the server
python manage.py server
```

### Testing

In order to run the tests, you will need to create a test database. You can follow the same procedures outlined in the install section. By default, the database should be named `purchasing_test`:

```bash
psql
create database purchasing_test;
```

Tests are located in the `purchasing_test` directory. To run the tests, run

```bash
PYTHONPATH=. nosetests purchasing_test/
```

from inside the root directory. For more coverage information, run

```bash
PYTHONPATH=. nosetests purchasing_test/ -v --with-coverage --cover-package=purchasing_test --cover-erase
```

## License
See [LICENSE.md](https://github.com/codeforamerica/pittsburgh-purchasing-suite/blob/master/LICENSE.md).
