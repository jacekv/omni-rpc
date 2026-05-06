.PHONY: dev prod-deploy logs

# Local development
dev:
	docker compose up --build

# Production deployment (Run this on the VPC)
prod-up:
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up --build

# 	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml pull --build
# 	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --remove-orphans

# View production logs
logs:
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml logs -f omni-rpc
