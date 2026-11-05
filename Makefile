.PHONY: test package up down logs

test:
	mvn -B -pl agent test

package:
	mvn -B -DskipTests package

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app
