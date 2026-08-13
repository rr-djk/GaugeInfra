SHELL     := /bin/bash
TF        := terraform
ENV_DIR   := infra/environments/dev
BOOT_DIR  := infra/bootstrap
AWS_PROFILE ?= gaugeinfra

.PHONY: init plan apply destroy validate fmt bootstrap-init bootstrap-apply help

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
	@echo "Cibles: init | plan | apply | destroy | validate | fmt | \
		bootstrap-init | bootstrap-apply"
