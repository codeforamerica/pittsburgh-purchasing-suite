install:
	pip install -r requirements/dev.txt
	npm install
	bower install

setup:
	make install
	python manage.py db upgrade
	python manage.py seed_user -e $(ADMIN_EMAIL) -r 1
	python manage.py seed

include docs/Makefile

BUILDDIR = docs/build
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) docs/source
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) docs/source

doc:
	sphinx_check()
	$(SPHINXBUILD) -b html -E $(ALLSPHINXOPTS) $(BUILDDIR)/html
