install:
	pip install -r requirements/dev.txt
	npm install
	bower install

setup:
	make install
	python manage.py db upgrade
	python manage.py seed_user -e $(ADMIN_EMAIL) -r 1
