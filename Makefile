PHONY: test


test:
	pytest src/phony/tests


install:
	pip install -r requirements/development.txt


fmt:
	black .



