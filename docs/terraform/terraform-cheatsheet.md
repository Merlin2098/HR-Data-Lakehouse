# ⚡ Terraform Cheat Sheet (Beginner Friendly)

## BASIC WORKFLOW

init → plan → apply

---

## Commands

terraform init      # Initialize project  
terraform fmt       # Format code  
terraform validate  # Validate config  
terraform plan      # Preview changes  
terraform apply     # Apply changes  
terraform destroy   # Destroy infra  

---

## Concepts

resource = creates infra  
data = reads infra  
output = shows values  
variable = inputs  

---

## Debug

terraform state list  
terraform state show <resource>  

---

## AWS Profile

export AWS_PROFILE=client  
aws sts get-caller-identity  
