.PHONY: deploy dev test

deploy:
	sam build && sam deploy

dev:
	sam local start-api

test:
	sam build && sam local start-api