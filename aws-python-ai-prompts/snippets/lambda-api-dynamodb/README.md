# Lambda API Gateway com Clean Architecture, PynamoDB e Asyncio

Este snippet implementa uma função AWS Lambda integrada ao API Gateway que segue os princípios da Clean Architecture, utiliza PynamoDB para acessar o DynamoDB e faz chamadas assíncronas a APIs externas usando asyncio.

## Funcionalidades

- Implementação completa de uma API REST usando Lambda + API Gateway
- Arquitetura limpa com separação clara entre domínio, casos de uso e infraestrutura
- Acesso ao DynamoDB através da biblioteca PynamoDB
- Chamadas assíncronas a múltiplas APIs externas usando asyncio e aiohttp
- Validação de dados com Pydantic
- Tratamento abrangente de erros
- Logging estruturado
- Configuração via variáveis de ambiente

## Estrutura do Código

O código é organizado seguindo os princípios da Clean Architecture:

1. **Camada de Entidades (Core)**
   - Modelos de domínio independentes de frameworks
   - Regras de negócio encapsuladas em entidades

2. **Camada de Casos de Uso (Aplicação)**
   - Implementação dos casos de uso da aplicação
   - Portas de entrada e saída (interfaces)
   - DTOs para request/response

3. **Camada de Interface (Adaptadores)**
   - Implementação de repositórios para DynamoDB
   - Serviços para acesso a APIs externas
   - Controlador para API Gateway

4. **Camada de Framework & Drivers**
   - Handler da Lambda
   - Configurações específicas da AWS
   - Inicialização de dependências

## Exemplo de Uso

```python
# Importar função handler
from lambda_api_dynamodb import lambda_handler

# Exemplo de evento do API Gateway para obter um produto pelo ID
event = {
    "httpMethod": "GET",
    "path": "/api/products/123",
    "pathParameters": {
        "productId": "123"
    }
}

# Invocar a função Lambda
response = lambda_handler(event, {})

# Resposta:
# {
#   "statusCode": 200,
#   "headers": {
#     "Content-Type": "application/json",
#     "Access-Control-Allow-Origin": "*",
#     "Access-Control-Allow-Methods": "GET, OPTIONS"
#   },
#   "body": "{\"success\":true,\"product\":{\"id\":\"123\",\"name\":\"Smartphone\",\"price\":999.99,...}}"
# }
```

## Instalação

Adicione as seguintes dependências ao seu `requirements.txt`:

```
pynamodb>=5.2.0
pydantic>=1.9.0
aiohttp>=3.8.1
boto3>=1.24.0
```

## Configuração

A função Lambda utiliza as seguintes variáveis de ambiente:

```
# Nome da tabela DynamoDB (default: "products")
PRODUCTS_TABLE=products

# Região AWS (default: "us-east-1")
AWS_REGION=us-east-1

# URL base da API de avaliações externas
RATINGS_API_URL=https://api.ratings.example.com

# Chave de API para a API de avaliações
RATINGS_API_KEY=sua-chave-api-ratings

# URL base da API de dados de mercado
MARKET_API_URL=https://api.market.example.com

# Chave de API para a API de dados de mercado
MARKET_API_KEY=sua-chave-api-market

# Nível de logging (default: "INFO")
LOG_LEVEL=INFO
```

## Implantação


## Endpoints da API

### 1. Obter um produto por ID

```
GET /products/{productId}
```

**Parâmetros:**
- `productId` (path): ID do produto

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "product": {
    "id": "123",
    "name": "Smartphone Premium",
    "description": "Smartphone de última geração",
    "price": 999.99,
    "category": "electronics",
    "tags": ["smartphone", "high-end", "5G"],
    "stock": 42,
    "reviews": [
      {
        "rating": 4.5,
        "comment": "Excelente produto!",
        "user_id": "user123",
        "date": "2023-06-15"
      }
    ],
    "external_rating": 4.3,
    "market_data": {
      "competitors_avg_price": 1050.0,
      "market_trend": "stable",
      "popularity_index": 87
    }
  }
}
```

### 2. Buscar produtos

```
GET /products
```

**Parâmetros de Query:**
- `category` (opcional): Filtrar por categoria (ex: electronics, clothing)
- `minPrice` (opcional): Preço mínimo
- `maxPrice` (opcional): Preço máximo
- `q` (opcional): Termo de busca (nome, descrição)
- `limit` (opcional): Número máximo de resultados (padrão: 10)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "products": [
    {
      "id": "123",
      "name": "Smartphone Premium",
      "description": "Smartphone de última geração",
      "price": 999.99,
      "category": "electronics",
      "tags": ["smartphone", "high-end"],
      "stock": 42,
      "reviews": []
    },
    {
      "id": "124",
      "name": "Tablet Ultra",
      "description": "Tablet com tela de alta resolução",
      "price": 699.99,
      "category": "electronics",
      "tags": ["tablet"],
      "stock": 18,
      "reviews": []
    }
  ],
  "total_count": 2
}
```

## Boas Práticas

### 1. Desempenho e Custo

- **Chamadas Assíncronas**: Utilizamos asyncio para fazer chamadas paralelas a APIs externas, reduzindo o tempo de resposta
- **PynamoDB**: Oferece uma camada de abstração sobre o DynamoDB com suporte a modelos
- **Reutilização do Controlador**: O controlador é criado uma única vez durante a inicialização da Lambda para otimizar o warm start

### 2. Segurança

- **Validação de Dados**: Todos os inputs são validados usando Pydantic
- **Secrets via Environment Variables**: As chaves de API são configuradas como variáveis de ambiente
- **IAM Permissions**: A Lambda deve ter apenas as permissões mínimas necessárias

### 3. Observabilidade

- **Logging Estruturado**: Logs informativos para acompanhar o fluxo de execução
- **Tratamento de Erros**: Erros são capturados, registrados e retornados adequadamente

## Limitações

- A implementação da PynamoDB não é assíncrona, embora as interfaces sejam definidas como async para consistência
- Para tabelas grandes, o método de scan utilizado não é eficiente e deveria ser substituído por GSIs e queries
- A criação manual do loop de eventos pode não ser necessária em versões mais recentes do runtime Lambda

## Recursos Adicionais

- [PynamoDB Documentation](https://pynamodb.readthedocs.io/)
- [Async/Await em Python](https://docs.python.org/3/library/asyncio-task.html)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [API Gateway Lambda Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html) 