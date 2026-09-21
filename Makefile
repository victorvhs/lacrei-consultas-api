.PHONY: setup up down up-payments superuser seed lint test test-local pre-push openapi build deploy rollback sim-pay sim-chaos tf-check

setup:
	cp -n .env.example .env || true

up:
	docker compose up -d --build

down:
	docker compose down

up-payments:
	docker compose --profile payments up -d --build

superuser:
	docker compose exec api python manage.py createsuperuser

seed:
	docker compose exec api python manage.py shell -c "from scripts.seed import run; run()"

lint:
	poetry run ruff check .
	poetry run lint-imports

test:
	poetry run coverage run manage.py test --settings=config.settings.test --verbosity=2
	poetry run coverage report --fail-under=95

test-local:
	docker compose up -d db
	DATABASE_URL=postgres://lacrei:lacrei@localhost:5432/lacrei_test SECRET_KEY=test-secret-key \
		poetry run coverage run manage.py test --settings=config.settings.test --verbosity=2
	poetry run coverage report --fail-under=95

pre-push: lint test-local

openapi:
	poetry run python manage.py spectacular --file doc/openapi.yaml --validate

build:
	docker build -t lacrei-saude:$${APP_VERSION:-dev} .

deploy:
	APP_IMAGE=lacrei-saude:$${TAG:-latest} docker compose -f docker-compose.release.yml up -d

rollback:
	APP_IMAGE=lacrei-saude:$${TAG:-previous} docker compose -f docker-compose.release.yml up -d

sim-pay:
	curl -X POST http://localhost:8080/_sim/pay -H "Content-Type: application/json" -d '{"pagamento_id":"$(PAGAMENTO)"}'

sim-chaos:
	curl -X POST http://localhost:8080/_sim/chaos -H "Content-Type: application/json" -d '{"cenario":"$(CENARIO)"}'

tf-check:
	cd infra/terraform && terraform fmt -check -recursive && terraform init -backend=false && terraform validate
