#! /usr/bin/make 

default:
	python setup.py check build

.PHONY: register dist inspect upload clean docs test

register:
	if [ ! -f ~/.pypirc ]; then \
		echo "Missing ~/.pypirc file"; \
		exit 1; \
	fi; \
	python setup.py register

dist:
	python setup.py sdist

inspect:
	python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg/
	rm -rf *.egg-info/
	rm -f MANIFEST
	python setup.py sdist
	cd dist/ && tar xzvf *.tar.gz

upload:
	if [ ! -f ~/.pypirc ]; then \
		echo "Missing ~/.pypirc file"; \
		exit 1; \
	fi; \
	python setup.py sdist upload

clean:
	python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	rm -f MANIFEST
	rm -rf docs/_*/

docs:
	cd docs && make html

test:
	nosetests -c tests/nose.cfg
