.PHONY: deploy sdist wheel clean

sdist:
	pipenv run python setup.py sdist

deploy: sdist
	pipenv run twine upload dist/*

deploy-test: sdist
	pipenv run twine upload --repository testpypi dist/*

clean:
	rm -rf dist build coworks.egg-info
	find . -type f -name \*.pyc -delete
	find . -type d -name __pycache__ -exec rm -rf {} \;
