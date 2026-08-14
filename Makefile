SHELL     := /bin/bash
TF        := terraform
ENV_DIR   := infra/environments/dev
BOOT_DIR  := infra/bootstrap
AWS_PROFILE ?= gaugeinfra

.PHONY: init plan apply destroy validate fmt bootstrap-init bootstrap-apply \
	test test-unit test-dogfood test-mutation help

# ---------- Environnement dev ----------
init:
	cd $(ENV_DIR) && AWS_PROFILE=$(AWS_PROFILE) $(TF) init -backend-config=backend.tfvars

plan:
	cd $(ENV_DIR) && AWS_PROFILE=$(AWS_PROFILE) $(TF) plan

apply:
	cd $(ENV_DIR) && AWS_PROFILE=$(AWS_PROFILE) $(TF) apply

destroy:
	cd $(ENV_DIR) && AWS_PROFILE=$(AWS_PROFILE) $(TF) destroy

validate:
	cd $(ENV_DIR) && AWS_PROFILE=$(AWS_PROFILE) $(TF) init -backend=false && $(TF) validate

fmt:
	cd $(ENV_DIR) && $(TF) fmt -recursive

# ---------- Bootstrap (bucket d'état) ----------
bootstrap-init:
	cd $(BOOT_DIR) && $(TF) init

bootstrap-apply:
	cd $(BOOT_DIR) && AWS_PROFILE=$(AWS_PROFILE) $(TF) apply

help:
	@echo "Cibles: init | plan | apply | destroy | validate | fmt |"
	@echo "        bootstrap-init | bootstrap-apply |"
	@echo "        test | test-unit | test-dogfood | test-mutation"

# ---------- Tests backend ----------
test:            ## Tests complets + couverture >= 75 %
	uv run pytest --cov=parser --cov-fail-under=75 --cov-report=term-missing

test-unit:       ## Tests sans dogfooding
	uv run pytest -m "not dogfood"

test-dogfood:    ## Dogfooding seul
	uv run pytest -m dogfood

test-mutation:   ## Audit mutmut (viser >= 75 %)
	uv run mutmut run
