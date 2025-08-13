.PHONY: deploy dev test freeze

install:
	pip install -r src/requirements.txt

freeze:
	pip freeze > src/requirements.txt

deploy:
	sam build && sam deploy

dev:
	sam local start-api

test:
	sam build && sam local start-api