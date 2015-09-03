install:
	pip install -r requirements/dev.txt
	bower install

setup:
	make install
	createdb purchasing
	python manage.py seed_user -e $(ADMIN_EMAIL) -r 1
	python manage.py seed
