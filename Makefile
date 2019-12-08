.PHONY: sdist wheel clean

sdist:
	python setup.py sdist

wheel:
	python setup.py bdist_wheel

clean:
	-rm -rf dist build sleet.egg-info
	-find . -type f -name \*.pyc -delete
	-find . -type d -name __pycache__ -exec rm -rf {} \;
