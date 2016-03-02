.PHONY: clean test

clean:
	find . -name \*.pyc -delete
	find . -name '__pycache__' -delete
	rm -f .coverage

test:
	tox
