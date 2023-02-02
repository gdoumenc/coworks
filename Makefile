.PHONY: deploy fury dist clean

include .env
export

dist:
	pipenv run python setup.py bdist_wheel
	rm -rf build

fury: clean dist
	(export VERSION=`python -c "import coworks;print(coworks.version.__version__)"`;\
	curl -F package=@dist/coworks-$$VERSION-py2.py3-none-any.whl https://$$FURY_TOKEN@push.fury.io/gdoumenc;\
	unset VERSION)

deploy: clean dist
	pipenv run twine upload dist/*

deploy-test: clean dist
	pipenv run twine upload --repository testpypi dist/*

plugins.zip: clean coworks/operators.py coworks/sensors.py coworks/biz/*
	mkdir -p dist
	zip -r dist/plugins.zip $^

clean:
	rm -rf dist build coworks.egg-info terraform .pytest_cache 1>/dev/null 2>&1
	find . -type f -name '*.py[co]' -delete 1>/dev/null 2>&1
	find . -type d -name '__pycache__' -delete 1>/dev/null 2>&1
