# Estrutura Inicial de Projeto com Clean Architecture

Este prompt gera a estrutura base de uma aplicação Python seguindo Clean Architecture para AWS Lambda ou ECS.

## Contexto para IA

```
Você irá criar a estrutura de diretórios e arquivos iniciais para uma aplicação Python seguindo
Clean Architecture. A estrutura deve separar claramente as camadas de domínio, aplicação, 
infraestrutura e apresentação, permitindo alta testabilidade e baixo acoplamento.
```

## Prompt Base

```
Crie a estrutura inicial de uma aplicação Python seguindo Clean Architecture para rodar como {AMBIENTE_EXEC}.

Requisitos:
- Estrutura com pastas seguindo Clean Architecture
- Código pronto para uso com `boto3`
- Observabilidade com Datadog `ddtrace`
- Tipagem com `pydantic`
- Testes unitários com `pytest`
- `{PONTO_ENTRADA}` funcional
- `requirements.txt` ou `pyproject.toml`

O objetivo da aplicação é {DESCRICAO_OBJETIVO}.

Siga SOLID, DRY, KISS, GRASP e padrões de projeto (GoF).
```

## Exemplo Preenchido

```
Crie a estrutura inicial de uma aplicação Python seguindo Clean Architecture para rodar como AWS Lambda.

Requisitos:
- Estrutura com pastas seguindo Clean Architecture
- Código pronto para uso com `boto3`
- Observabilidade com Datadog `ddtrace`
- Tipagem com `pydantic`
- Testes unitários com `pytest`
- Handler Lambda funcional que processa eventos SQS
- `requirements.txt`

O objetivo da aplicação é processar pedidos recebidos via SQS, validar os dados, armazenar no DynamoDB e enviar confirmação por email via SES.

Siga SOLID, DRY, KISS, GRASP e padrões de projeto (GoF).
```

## Como Adaptar

Para usar este template:

1. Substitua `{AMBIENTE_EXEC}` por "AWS Lambda" ou "ECS Task/Container"
2. Substitua `{PONTO_ENTRADA}` por "handler Lambda" ou "main.py" (conforme o ambiente)
3. Forneça a `{DESCRICAO_OBJETIVO}` com o propósito da aplicação

## Output Esperado

A IA deve gerar:

1. **Estrutura completa de diretórios** que siga Clean Architecture
```
my_project/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   ├── repositories.py
│   │   └── services/
│   │
│   ├── application/
│   │   ├── dtos/
│   │   ├── usecases/
│   │   └── services/
│   │
│   ├── presentation/         # Se aplicável
│   │   ├── api/
│   │   └── cli/
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── models/
│   │   │   ├── mappers/
│   │   │   └── repositories/
│   │   │
│   │   └── apis/
│   │       ├── dtos/
│   │       ├── mappers/
│   │       └── adapters/
│   │
│   ├── common/               # Cross-cutting concerns
│   │   ├── logging/
│   │   ├── monitoring/
│   │   └── exceptions/
│   │
│   └── config/              # Composition Root & configs
│
├── tests/
├── requirements.txt
└── README.md
```

2. **Arquivos básicos** com exemplos funcionais:
   - `domain/entities/`: Exemplo de entidade básica
   - `domain/repositories.py`: Interfaces de repositório
   - `application/usecases/`: Exemplo de caso de uso básico
   - `infrastructure/`: Exemplos de implementação de repositório
   - Ponto de entrada: `handler.py` ou `main.py`
   - `tests/`: Estrutura de teste básica
   - `requirements.txt`: Dependências essenciais

3. **README.md** com instruções básicas

## Estrutura Detalhada a ser Gerada

```
my_project/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── order.py
│   │   ├── repositories.py            # Interfaces (contratos) de repositório
│   │   └── services/                  # Regras de negócio que operam em múltiplas entidades
│   │       └── calculate_discount.py
│   │
│   ├── application/
│   │   ├── dtos/
│   │   │   ├── create_order_dto.py    # DTO de input p/ CreateOrderUseCase
│   │   │   └── order_response_dto.py  # DTO de output dos casos de uso
│   │   ├── usecases/
│   │   │   └── create_order_usecase.py
│   │   └── services/
│   │       └── order_service.py       # Orquestra casos de uso, não contém regras
│   │
│   ├── presentation/                  # Para APIs/Web/CLI
│   │   ├── api/                       # API REST/GraphQL
│   │   │   ├── controllers/
│   │   │   ├── middlewares/
│   │   │   ├── validators/
│   │   │   └── routes.py
│   │   └── cli/                       # Interface de linha de comando
│   │       └── commands/
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── models/
│   │   │   ├── dtos/
│   │   │   ├── mappers/
│   │   │   └── repositories/
│   │   │
│   │   └── apis/
│   │       ├── dtos/
│   │       ├── mappers/
│   │       └── adapters/
│   │
│   ├── common/                        # Cross-cutting concerns
│   │   ├── logging/
│   │   ├── security/
│   │   ├── monitoring/
│   │   └── exceptions/
│   │
│   └── config/                       # Composition Root & configs
│       ├── di_container.py
│       ├── settings.py
│       └── logging_config.py
│
├── tests/
├── requirements.txt
└── README.md
``` 