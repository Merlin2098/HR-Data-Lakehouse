lakehouse-aws/
│
├── infra/                         # 🧱 Infraestructura (Terraform)
│   ├── main.tf
│   ├── provider.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars
│
│   ├── modules/
│   │   ├── s3/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │
│   │   ├── iam/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │
│   │   ├── glue/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │
│   └── env/
│       ├── dev.tfvars
│       ├── prod.tfvars
│
├── src/                           # 🔥 LÓGICA DEL SISTEMA
│
│   ├── glue/
│   │   ├── bronze_to_silver.py
│   │   ├── silver_to_gold.py
│
│   ├── configs/
│   │   ├── transformations.yaml
│   │   ├── contracts.yaml
│
│   ├── queries/
│   │   ├── bronze_to_silver.sql
│   │   ├── silver_to_gold.sql
│
│   ├── common/                    # (opcional pero PRO)
│   │   ├── s3_utils.py
│   │   ├── config_loader.py
│   │   ├── query_loader.py
│
├── tests/
│   ├── test_configs.py
│   ├── test_queries.py
│
├── Makefile (opcional)
├── README.md
└── .gitignore
