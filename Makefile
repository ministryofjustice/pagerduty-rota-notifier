.PHONY: test container-build container-test container-scan

PYTHONPATH := .

PAGERDUTY_SCHEDULE_ID ?= dummy
PAGERDUTY_TOKEN       ?= dummy
SLACK_CHANNEL         ?= dummy
SLACK_TOKEN           ?= dummy

CONTAINER_IMAGE_NAME     ?= ghcr.io/ministryofjustice/pagerduty-rota-notifier
CONTAINER_IMAGE_TAG      ?= local
TRIVY_DB_REPOSITORY      ?= public.ecr.aws/aquasecurity/trivy-db:2
TRIVY_JAVA_DB_REPOSITORY ?= public.ecr.aws/aquasecurity/trivy-java-db:1

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
	@ARCH=`uname --machine`; \
	case $$ARCH in \
	aarch64 | arm64) \
		echo "Building on $$ARCH architecture"; \
		docker build --platform linux/amd64 --file Dockerfile --tag $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG) . ;; \
	*) \
		echo "Building on $$ARCH architecture"; \
		docker build --file Dockerfile --tag $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG) . ;; \
	esac

container-test: container-build
	@echo "Running container structure tests"
	container-structure-test test --platform linux/amd64 --config test/container-structure-test.yml --image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)

container-scan: container-test
	@echo "Scanning container image $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG) for vulnerabilities"
	trivy image --platform linux/amd64 --severity HIGH,CRITICAL $(CONTAINER_IMAGE_NAME):$(CONTAINER_IMAGE_TAG)
