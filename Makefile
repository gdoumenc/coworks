.PHONY: deploy fury sdist clean

sdist:
	pipenv run python setup.py sdist

fury: sdist
	(export VERSION=`python -c "import coworks;print(coworks.__version__)"`;\
	curl -F package=@dist/coworks-$$VERSION.tar.gz https://1PqF0I-J1eMroTnd6GFKWBV1Xxs0x5Xx8@push.fury.io/gdoumenc;\
	unset VERSION)

deploy: clean sdist
	pipenv run twine upload dist/*

deploy-test: clean sdist
	pipenv run twine upload --repository testpypi dist/*

clean:
	rm -rf dist build coworks.egg-info
	find . -type f -name \*.pyc -delete
	find . -type d -name __pycache__ -exec rm -rf {} \; || true
