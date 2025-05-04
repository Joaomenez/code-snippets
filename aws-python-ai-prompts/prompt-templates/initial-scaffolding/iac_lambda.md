# Infraestrutura como Código (IaC) para AWS Lambda

Este prompt auxilia na criação de código de infraestrutura para implantação de funções AWS Lambda usando Terraform ou AWS CDK.

## Contexto para IA

```
```

## Prompt Base

```
Crie código de infraestrutura como código usando...
```

## Exemplo Preenchido

```

```

## Output Esperado (Terraform)



```hcl
# main.tf - Terraform para função Lambda de processamento de pedidos

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = var.aws_region
}

#------------------------------------------------------------------------------
# Variáveis
#------------------------------------------------------------------------------
```


## Como Adaptar
