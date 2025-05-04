# Função Lambda com API Gateway: Endpoint REST

Este prompt gera uma função AWS Lambda que implementa um endpoint REST através do API Gateway.

## Contexto para IA

```
Você irá criar uma função AWS Lambda em Python que implementa um endpoint REST
através do API Gateway. A função deve seguir boas práticas de API design, incluindo
validação de entrada, tratamento adequado de erros, documentação via Swagger/OpenAPI,
e formatação consistente de respostas.
```

## Prompt Base

```
Crie uma função AWS Lambda em Python {VERSAO_PYTHON} que implementa um endpoint REST para {DESCRICAO_API}.

Requisitos:
- Implemente validação de entrada com Pydantic
- Estruture as respostas HTTP conforme padrões RESTful
- Adicione tratamento de erros com códigos HTTP apropriados
- Inclua logs estruturados para melhor observabilidade
- {REQUISITO_ADICIONAL}

Endpoint: {METODO_HTTP} {URL_PATH}

Operações que o endpoint deve suportar:
{OPERACOES}
```

## Exemplo Preenchido

```
Crie uma função AWS Lambda em Python 3.9 que implementa um endpoint REST para um serviço de gerenciamento de produtos.

Requisitos:
- Implemente validação de entrada com Pydantic
- Estruture as respostas HTTP conforme padrões RESTful
- Adicione tratamento de erros com códigos HTTP apropriados
- Inclua logs estruturados para melhor observabilidade
- Persistência no DynamoDB
- Documentação OpenAPI para o endpoint
- Implementação de paginação para listagem de produtos

Endpoint: POST /api/products

Operações que o endpoint deve suportar:
1. Criação de um novo produto com campos: nome, descrição, preço, categoria e SKU
2. Validação de SKU único no sistema
3. Resposta com o produto criado incluindo ID e timestamp
```

## Output Esperado

A IA deve gerar código completo para um endpoint REST implementado como Lambda, seguindo Clean Architecture. Exemplo:

```
# Estrutura Clean Architecture para função Lambda com API Gateway

## domain/entities/product.py
from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    price: float = Field(..., gt=0)
    category: str
    sku: str = Field(..., min_length=3, max_length=20, regex=r'^[A-Za-z0-9\-]+$')
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('price must be positive')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Smartphone XYZ",
                "description": "Latest model with advanced features",
                "price": 799.99,
                "category": "electronics",
                "sku": "PHONE-XYZ-123"
            }
        }

class Product(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Smartphone XYZ",
                "description": "Latest model with advanced features",
                "price": 799.99,
                "category": "electronics",
                "sku": "PHONE-XYZ-123",
                "created_at": "2023-01-01T12:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    
    @classmethod
    def create(cls, base_product: ProductBase, product_id: str, 
               created_at: datetime, updated_at: datetime) -> 'Product':
        """Factory method to create a Product from a ProductBase."""
        return cls(
            id=product_id,
            created_at=created_at,
            updated_at=updated_at,
            **base_product.dict()
        )

## domain/repositories/product_repository.py
from typing import Protocol, Optional
from domain.entities.product import Product, ProductBase

class IProductRepository(Protocol):
    def create(self, product: Product) -> Product:
        """Create a new product in the database."""
        ...
    
    def check_sku_exists(self, sku: str) -> bool:
        """Check if a product with the given SKU already exists."""
        ...

## domain/exceptions.py
class DomainError(Exception):
    """Base exception for domain errors."""
    pass

class ProductAlreadyExistsError(DomainError):
    """Exception raised when a product with the same SKU already exists."""
    pass

class DatabaseError(DomainError):
    """Exception raised when a database operation fails."""
    pass

## application/dtos/product_dto.py
from pydantic import BaseModel
from typing import Optional
from domain.entities.product import ProductBase

class ProductCreateDTO(ProductBase):
    """DTO for creating a new product."""
    pass

class ProductResponseDTO(BaseModel):
    """DTO for returning a product."""
    id: str
    name: str
    description: str
    price: float
    category: str
    sku: str
    created_at: str
    updated_at: str

## application/usecases/create_product_usecase.py
import uuid
from datetime import datetime
from aws_lambda_powertools import Logger, Metrics, Tracer
from typing import Dict, Any, Protocol

from domain.entities.product import Product, ProductBase
from domain.repositories.product_repository import IProductRepository
from domain.exceptions import ProductAlreadyExistsError, DatabaseError
from application.dtos.product_dto import ProductCreateDTO, ProductResponseDTO

tracer = Tracer(service="products-api")
logger = Logger(service="products-api")
metrics = Metrics(namespace="ProductsAPI")

# Interfaces de input/output para o caso de uso
class CreateProductInputPort(Protocol):
    def execute(self, product_dto: ProductCreateDTO) -> ProductResponseDTO:
        """Execute the use case."""
        ...

class CreateProductOutputPort(Protocol):
    def present_product_creation_success(self, response_dto: ProductResponseDTO) -> None:
        """Present the success result of product creation."""
        ...
    
    def present_product_already_exists(self, sku: str) -> None:
        """Present the error of product already exists."""
        ...
    
    def present_database_error(self, error_message: str) -> None:
        """Present a database error."""
        ...

# Implementação do caso de uso
class CreateProductUseCase(CreateProductInputPort):
    def __init__(self, 
                 product_repository: IProductRepository,
                 output_port: CreateProductOutputPort):
        self.product_repository = product_repository
        self.output_port = output_port
    
    @tracer.capture_method
    def execute(self, product_dto: ProductCreateDTO) -> ProductResponseDTO:
        """Create a new product."""
        try:
            # Verificar se o SKU já existe
            if self.product_repository.check_sku_exists(product_dto.sku):
                logger.warning("Attempted to create product with existing SKU", 
                               extra={"sku": product_dto.sku})
                metrics.add_metric(name="DuplicateSKU", unit="Count", value=1)
                self.output_port.present_product_already_exists(product_dto.sku)
                # A resposta real será manipulada pelo output port, retornamos None aqui
                return None
            
            # Criar entidade de domínio
            now = datetime.now()
            product_id = str(uuid.uuid4())
            
            product = Product.create(
                base_product=product_dto,
                product_id=product_id,
                created_at=now,
                updated_at=now
            )
            
            # Persistir no repositório
            saved_product = self.product_repository.create(product)
            
            # Log e métricas
            logger.info("Product created", extra={"product_id": product_id, "sku": product_dto.sku})
            metrics.add_metric(name="ProductCreated", unit="Count", value=1)
            
            # Criar DTO de resposta
            response_dto = ProductResponseDTO(
                id=saved_product.id,
                name=saved_product.name,
                description=saved_product.description,
                price=saved_product.price,
                category=saved_product.category,
                sku=saved_product.sku,
                created_at=saved_product.created_at.isoformat(),
                updated_at=saved_product.updated_at.isoformat()
            )
            
            # Apresentar resultado através do output port
            self.output_port.present_product_creation_success(response_dto)
            return response_dto
            
        except Exception as e:
            # Converter para exceção de domínio
            logger.error(f"Error creating product: {str(e)}", exc_info=True)
            metrics.add_metric(name="ProductCreationError", unit="Count", value=1)
            self.output_port.present_database_error(str(e))
            return None

## infrastructure/repositories/dynamodb_product_repository.py
import os
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from typing import Dict, Any

from domain.entities.product import Product
from domain.repositories.product_repository import IProductRepository
from domain.exceptions import DatabaseError

logger = Logger(service="products-api")

class DynamoDBProductRepository(IProductRepository):
    def __init__(self, table_name: str = None, dynamodb_resource = None):
        self.table_name = table_name or os.environ.get("PRODUCTS_TABLE", "products")
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)
    
    def create(self, product: Product) -> Product:
        """Create a new product in DynamoDB."""
        try:
            item = {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "category": product.category,
                "sku": product.sku,
                "created_at": product.created_at.isoformat(),
                "updated_at": product.updated_at.isoformat()
            }
            
            self.table.put_item(Item=item)
            return product
            
        except ClientError as e:
            logger.error(f"DynamoDB error when creating product: {str(e)}")
            raise DatabaseError(f"Database error: {str(e)}")
    
    def check_sku_exists(self, sku: str) -> bool:
        """Check if a product with the given SKU already exists."""
        try:
            response = self.table.query(
                IndexName="sku-index",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("sku").eq(sku),
                Limit=1
            )
            
            return len(response.get("Items", [])) > 0
            
        except ClientError as e:
            logger.error(f"DynamoDB error when checking SKU: {str(e)}")
            raise DatabaseError(f"Database error: {str(e)}")

## interfaces/api/presenters/product_presenter.py
import json
from typing import Dict, Any, Optional
from application.dtos.product_dto import ProductResponseDTO
from application.usecases.create_product_usecase import CreateProductOutputPort

class ProductPresenter(CreateProductOutputPort):
    def __init__(self):
        self.response = None
    
    def present_product_creation_success(self, response_dto: ProductResponseDTO) -> None:
        """Present the success result of product creation."""
        self.response = {
            "statusCode": 201,
            "body": json.dumps({
                "message": "Product created successfully",
                "product": response_dto.dict()
            }),
            "headers": {
                "Content-Type": "application/json",
                "Location": f"/api/products/{response_dto.id}"
            }
        }
    
    def present_product_already_exists(self, sku: str) -> None:
        """Present the error of product already exists."""
        self.response = {
            "statusCode": 409,
            "body": json.dumps({
                "error": "Conflict", 
                "message": f"Product with SKU '{sku}' already exists"
            }),
            "headers": {"Content-Type": "application/json"}
        }
    
    def present_database_error(self, error_message: str) -> None:
        """Present a database error."""
        self.response = {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Database Error",
                "message": error_message
            }),
            "headers": {"Content-Type": "application/json"}
        }
    
    def get_response(self) -> Dict[str, Any]:
        """Get the final HTTP response."""
        if not self.response:
            # Default error response if no specific response was set
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred"
                }),
                "headers": {"Content-Type": "application/json"}
            }
        return self.response

## interfaces/api/handlers/product_handler.py
import json
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools import Logger, Tracer
from typing import Dict, Any

from application.dtos.product_dto import ProductCreateDTO
from application.usecases.create_product_usecase import CreateProductUseCase
from infrastructure.repositories.dynamodb_product_repository import DynamoDBProductRepository
from interfaces.api.presenters.product_presenter import ProductPresenter

app = APIGatewayRestResolver()
logger = Logger(service="products-api")
tracer = Tracer(service="products-api")

@app.post("/api/products")
@tracer.capture_method
def create_product():
    try:
        # Parse e validar request body
        request_body = app.current_event.json_body
        if not request_body:
            raise BadRequestError("Request body is required")
            
        # Validar com Pydantic
        try:
            product_dto = ProductCreateDTO(**request_body)
        except Exception as e:
            raise BadRequestError(f"Invalid product data: {str(e)}")
        
        # Criar componentes e injetar dependências
        repository = DynamoDBProductRepository()
        presenter = ProductPresenter()
        use_case = CreateProductUseCase(
            product_repository=repository,
            output_port=presenter
        )
        
        # Executar caso de uso
        use_case.execute(product_dto)
        
        # Obter resposta do presenter
        return presenter.get_response()
        
    except BadRequestError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Bad Request", "message": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "message": "An unexpected error occurred"}),
            "headers": {"Content-Type": "application/json"}
        }

## config/di_container.py
from typing import Dict, Any, Type, Optional
import inspect

class DIContainer:
    """A simple dependency injection container."""
    
    def __init__(self):
        self._services = {}
        self._singletons = {}
    
    def register(self, interface_type: Type, implementation_type: Type, singleton: bool = False) -> None:
        """Register a service with the container."""
        self._services[interface_type] = (implementation_type, singleton)
    
    def register_instance(self, interface_type: Type, instance: Any) -> None:
        """Register a pre-created instance as a singleton."""
        self._singletons[interface_type] = instance
    
    def resolve(self, interface_type: Type) -> Any:
        """Resolve a service from the container."""
        # Check if we have a pre-registered instance
        if interface_type in self._singletons:
            return self._singletons[interface_type]
            
        # Check if we have a registration for this type
        if interface_type not in self._services:
            raise ValueError(f"No registration found for {interface_type.__name__}")
            
        implementation_type, is_singleton = self._services[interface_type]
        
        # If it's a singleton and we've already created it, return the existing instance
        if is_singleton and implementation_type in self._singletons:
            return self._singletons[implementation_type]
            
        # Otherwise, construct a new instance by resolving its dependencies
        constructor_params = inspect.signature(implementation_type.__init__).parameters
        
        # Skip 'self' parameter
        params = {
            name: self.resolve(param.annotation) 
            for name, param in constructor_params.items() 
            if name != 'self' and param.annotation != inspect.Parameter.empty
        }
        
        instance = implementation_type(**params)
        
        # If it's a singleton, store it for future use
        if is_singleton:
            self._singletons[implementation_type] = instance
            
        return instance

## interfaces/api/app.py
import time
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
import json

from domain.repositories.product_repository import IProductRepository 
from application.usecases.create_product_usecase import CreateProductInputPort, CreateProductOutputPort, CreateProductUseCase
from infrastructure.repositories.dynamodb_product_repository import DynamoDBProductRepository
from interfaces.api.presenters.product_presenter import ProductPresenter
from config.di_container import DIContainer
from interfaces.api.handlers.product_handler import app

logger = Logger(service="products-api")
metrics = Metrics(namespace="ProductsAPI")
tracer = Tracer(service="products-api")

# Configuração do contêiner de injeção de dependências
container = DIContainer()

def setup_di_container():
    """Configurar o contêiner de injeção de dependências."""
    # Registrar repositories
    container.register(IProductRepository, DynamoDBProductRepository, singleton=True)
    
    # Registrar outros componentes conforme necessário
    # Podemos registrar factories para casos de uso também

# Lambda handler (entry point)
@logger.inject_lambda_context(correlation_id_path="requestId")
@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    # Configurar DI container (fora do handler para reduzir cold starts)
    setup_di_container()
    
    # Registrar início do processamento + cold start
    is_cold_start = getattr(lambda_handler, '_cold_start', True)
    if is_cold_start:
        metrics.add_metric(name="ColdStart", unit="Count", value=1)
        lambda_handler._cold_start = False
    
    # Registrar métricas de requisição
    metrics.add_metric(name="ApiRequests", unit="Count", value=1)
    start_time = time.time()
    
    try:
        # Processar evento com o resolver
        response = app.resolve(event, context)
        
        # Registrar métricas de latência
        execution_time = (time.time() - start_time) * 1000
        metrics.add_metric(name="ApiLatency", unit="Milliseconds", value=execution_time)
        
        return response
    except Exception as e:
        # Registrar métricas de erro
        metrics.add_metric(name="ApiErrors", unit="Count", value=1)
        logger.exception("Error handling Lambda event")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }),
            "headers": {"Content-Type": "application/json"}
        }
```

## Como Adaptar

Para usar este template:

1. Substitua `{VERSAO_PYTHON}` pela versão do Python desejada (ex: 3.9, 3.10)
2. Em `{DESCRICAO_API}`, explique o propósito da API
3. Especifique o `{METODO_HTTP}` e `{URL_PATH}` do endpoint
4. Descreva as `{OPERACOES}` que o endpoint deve suportar em detalhes
5. Adicione requisitos específicos em `{REQUISITO_ADICIONAL}`, como persistência, autenticação, etc.

## Boas Práticas para APIs REST com Lambda

1. **API Design**
   - Use verbos HTTP corretamente (GET, POST, PUT, DELETE)
   - Estruture URLs por recursos, não ações
   - Use códigos de status HTTP apropriados
   - Forneça mensagens de erro descritivas

2. **Validação**
   - Valide todos os inputs do usuário
   - Use modelos de dados Pydantic para validação
   - Retorne erros de validação detalhados

3. **Performance**
   - Minimize lógica no handler Lambda
   - Use classes/funções auxiliares para organizar o código
   - Configure corretamente o timeout da Lambda

4. **Monitoramento**
   - Implemente logs estruturados
   - Adicione métricas personalizadas para operações críticas
   - Use tracing distribuído para depuração

5. **Segurança**
   - Considere implementar autenticação (Cognito, JWT)
   - Aplique princípio de menor privilégio nas IAM Roles
   - Proteja contra injeção e outros ataques 