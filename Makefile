.PHONY: deploy sdist wheel clean

sdist:
	pipenv run python setup.py sdist

deploy: clean sdist
	pipenv run twine upload dist/*

deploy-test: clean sdist
	pipenv run twine upload --repository testpypi dist/*

clean:
	rm -rf dist build coworks.egg-info
	find . -type f -name \*.pyc -delete
	find . -type d -name __pycache__ -exec rm -rf {} \; || true
