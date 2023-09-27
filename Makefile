.PHONY: deploy fury dist clean

include .env
export

dist:
	flit build

fury: clean dist
	fury push dist/coworks-`awk -F'"' '{print $$2}' coworks/version.py`-py3-none-any.whl

deploy: clean dist
	flit publish --repository pypi

deploy-test: clean dist
	flit publish --repository pypitest

plugins.zip: clean coworks/operators.py coworks/sensors.py coworks/biz/*
	mkdir -p dist
	zip -r dist/plugins.zip $^

clean:
	@rm -rf dist build coworks.egg-info terraform .pytest_cache 1>/dev/null 2>&1
	@find . -type f -name '*.py[co]' -delete 1>/dev/null 2>&1
	@find . -type d -name '__pycache__' -delete 1>/dev/null 2>&1
