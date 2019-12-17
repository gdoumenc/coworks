.PHONY: deploy sdist wheel clean

sdist:
	python setup.py sdist

deploy : sdist
	twine upload dist/*

wheel:
	python setup.py bdist_wheel

clean:
	-rm -rf dist build coworks.egg-info
	-find . -type f -name \*.pyc -delete
	-find . -type d -name __pycache__ -exec rm -rf {} \;
