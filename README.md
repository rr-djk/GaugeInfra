# GaugeInfra

Prédit le coût mensuel AWS d'un code Terraform avant déploiement, évalue les compromis de résilience et recommande des configurations plus efficaces.

![CI](https://github.com/rr-djk/GaugeInfra/actions/workflows/security-scan.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.11-7B42BC?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?logo=amazonwebservices&logoColor=white)

## Pourquoi

Les mauvaises décisions d'infrastructure peuvent augmenter drastiquement les coûts cloud tout en réduisant la résilience du système. GaugeInfra intervient **avant** le déploiement : il analyse le code Terraform, estime son coût mensuel et identifie les risques avant qu'ils ne deviennent des factures ou des pannes.

## Fonctionnalités visées

- **Analyse de code Terraform** : coller un fichier `.tf` ou l'uploader directement dans le navigateur.
- **Calcul de coût déterministe** : estimation du coût mensuel par ressource + total, via l'AWS Price List API.
- **Analyse IA** : synthèse en langage naturel, risques de résilience (ex. Single-AZ vs Multi-AZ) et recommandations d'optimisation via Amazon Nova Lite sur Amazon Bedrock.
- **Résultats en deux sections distinctes** : les chiffres exacts d'un côté, l'analyse qualitative de l'autre, pour distinguer clairement ce qui est garanti de ce qui est une recommandation.

## Architecture

**Principe de conception clé** : le coût est toujours calculé par du code Python déterministe (matching ressources Terraform ↔ AWS Price List API), jamais par le LLM. Bedrock intervient seulement _après_, sur des données déjà calculées, pour l'analyse qualitative car un LLM pourrait ne pas être fiable pour de l'arithmétique déterministe.

## État actuel

Le projet en est à ses débuts :

- **L'infrastructure AWS du projet est en place et déployée en dev** : frontend S3/CloudFront (avec OAC et security headers), API Gateway HTTP, Lambda Python 3.12, policy IAM d'accès à Bedrock.
- **Le cœur de l'outil n'est pas encore implémenté** : le parsing Terraform, le calcul de coûts et l'analyse IA sont à venir.
- **Le frontend n'existe pas encore**.
- **CI de sécurité active** : Trivy (SCA), Semgrep (SAST) et Checkov (IaC) sur chaque PR.

## Cibles Makefile

| Cible                                          | Description                                      |
| ---------------------------------------------- | ------------------------------------------------ |
| `make init`                                    | Initialise le backend S3 de l'environnement dev  |
| `make plan` / `make apply` / `make destroy`    | Cycle de vie de l'environnement dev              |
| `make validate`                                | Valide la configuration **sans credentials AWS** |
| `make fmt`                                     | Formate le code Terraform                        |
| `make bootstrap-init` / `make bootstrap-apply` | Crée le bucket d'état (une seule fois)           |

## Limites

- Le parsing Terraform, le calcul de coûts et l'analyse IA ne sont **pas encore implémentés**.
- Pas de nom de domaine personnalisé : le site est servi via l'URL `*.cloudfront.net` par défaut (HTTPS géré par AWS).
- Les ressources non supportées seront signalées explicitement, jamais ignorées silencieusement.
