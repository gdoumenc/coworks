.PHONY: deploy fury sdist clean

sdist:
	pipenv run python setup.py sdist

fury: sdist
	curl -F package=@dist/coworks-0.6.0a1.tar.gz https://1PqF0I-J1eMroTnd6GFKWBV1Xxs0x5Xx8@push.fury.io/gdoumenc

deploy: clean sdist
	pipenv run twine upload dist/*

deploy-test: clean sdist
	pipenv run twine upload --repository testpypi dist/*

clean:
	rm -rf dist build coworks.egg-info
	find . -type f -name \*.pyc -delete
	find . -type d -name __pycache__ -exec rm -rf {} \; || true
