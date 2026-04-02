# 🧪 Terraform AWS Connection Check

This project is a **minimal Terraform setup** designed to validate connectivity between Terraform and an AWS account.

It is intended as a **pre-deployment validation tool** before provisioning any real infrastructure.

---

## 🎯 Purpose

Before deploying resources in AWS (especially in client environments), it's critical to verify:

- AWS credentials are valid
- Terraform can authenticate successfully
- The correct AWS account is being used
- The correct region is configured

This project performs those checks safely without creating any resources.

---

## ⚙️ What this project does

This project uses Terraform **data sources** to:

- Retrieve the current AWS account ID
- Retrieve the current IAM identity (ARN)
- Retrieve the active AWS region

It does **NOT** create, modify, or delete any AWS resources.

---

## 🚀 How to use

terraform init
terraform validate
terraform plan
terraform apply
