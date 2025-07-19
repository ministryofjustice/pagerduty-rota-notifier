.PHONY: test container-build container-test container-scan container-run

PYTHONPATH := .

PAGERDUTY_SCHEDULE_ID ?= dummy
PAGERDUTY_TOKEN       ?= dummy
SLACK_CHANNEL         ?= dummy
SLACK_TOKEN           ?= dummy

CONTAINER_IMAGE_NAME     ?= ghcr.io/ministryofjustice/pagerduty-rota-notifier
CONTAINER_IMAGE_TAG      ?= local
CONTAINER_NAME           ?= pagerduty-rota-notifier

test:
	@echo "Running pytest"
	PYTHONPATH=$(PYTHONPATH) \
	PAGERDUTY_SCHEDULE_ID=$(PAGERDUTY_SCHEDULE_ID) \
	PAGERDUTY_TOKEN=$(PAGERDUTY_TOKEN) \
	SLACK_CHANNEL=$(SLACK_CHANNEL) \
	SLACK_TOKEN=$(SLACK_TOKEN) \
	uv run pytest test

container-build:
	@echo "Building container image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)"
	docker build --platform linux/amd64 --file Dockerfile --tag $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG) .

container-test: container-build
	@echo "Testing container image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)"
	container-structure-test test --platform linux/amd64 --config test/container-structure-test.yml --image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)

container-scan: container-test
	@echo "Scanning container image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG) for vulnerabilities"
	trivy image --platform linux/amd64 --severity HIGH,CRITICAL $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)

container-run: container-test
	@echo "Running container image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)"
	docker run --rm --platform linux/amd64 --name $(CONTAINER_NAME) \
		--env PAGERDUTY_SCHEDULE_ID=$(PAGERDUTY_SCHEDULE_ID) \
		--env PAGERDUTY_TOKEN=$(PAGERDUTY_TOKEN) \
		--env SLACK_CHANNEL=$(SLACK_CHANNEL) \
		--env SLACK_TOKEN=$(SLACK_TOKEN) \
		$(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)
