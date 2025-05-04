"""
Lambda API Gateway com Clean Architecture que utiliza PynamoDB e asyncio.

Este módulo implementa uma função Lambda integrada ao API Gateway,
seguindo os princípios da Clean Architecture, com acesso a DynamoDB
e chamadas assíncronas a APIs externas.
"""
import json
import logging
import os
import asyncio
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any, Union, TypeVar, Generic

import aiohttp
import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, ValidationError
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, ListAttribute, MapAttribute
from pynamodb.exceptions import DoesNotExist, PynamoDBConnectionError

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Tipo genérico para Request/Response
T = TypeVar("T")

# --- 1. CAMADA DE ENTIDADES (DOMÍNIO) ---

class ProductCategory(str, Enum):
    """Categorias de produtos disponíveis."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"
    OTHER = "other"

class PriceRange(BaseModel):
    """Faixa de preço de um produto."""
    min_price: float
    max_price: float

class ProductReview(BaseModel):
    """Avaliação de um produto."""
    rating: float
    comment: Optional[str] = None
    user_id: str
    date: str

class Product(BaseModel):
    """Entidade de domínio para Produto."""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: ProductCategory
    tags: List[str] = []
    stock: int
    reviews: List[ProductReview] = []
    external_rating: Optional[float] = None
    market_data: Optional[Dict[str, Any]] = None

    @property
    def average_rating(self) -> Optional[float]:
        """Calcular a média das avaliações do produto."""
        if not self.reviews:
            return None
        return sum(review.rating for review in self.reviews) / len(self.reviews)

    @property
    def is_available(self) -> bool:
        """Verificar se o produto está disponível em estoque."""
        return self.stock > 0

# --- 2. CAMADA DE CASOS DE USO (APLICAÇÃO) ---

class BaseRequest(BaseModel):
    """Modelo base para requisições."""
    pass

class BaseResponse(BaseModel):
    """Modelo base para respostas."""
    success: bool
    message: Optional[str] = None

class UseCaseError(Exception):
    """Erro de caso de uso."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class GetProductByIdRequest(BaseRequest):
    """Requisição para obter produto por ID."""
    product_id: str

class GetProductByIdResponse(BaseResponse):
    """Resposta para obter produto por ID."""
    product: Optional[Product] = None

class SearchProductsRequest(BaseRequest):
    """Requisição para buscar produtos."""
    category: Optional[ProductCategory] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    query: Optional[str] = None
    limit: int = 10

class SearchProductsResponse(BaseResponse):
    """Resposta para buscar produtos."""
    products: List[Product] = []
    total_count: int = 0

class UseCase(Generic[T]):
    """Interface base para casos de uso."""
    
    async def execute(self, request: Any) -> T:
        """Executa o caso de uso."""
        raise NotImplementedError("Método 'execute' deve ser implementado")

class GetProductByIdUseCase(UseCase[GetProductByIdResponse]):
    """Caso de uso para obter produto por ID."""
    
    def __init__(self, product_repository, external_rating_service, market_data_service):
        self.product_repository = product_repository
        self.external_rating_service = external_rating_service
        self.market_data_service = market_data_service
    
    async def execute(self, request: GetProductByIdRequest) -> GetProductByIdResponse:
        """Executa o caso de uso para obter produto por ID."""
        try:
            # Buscar produto no repositório
            product = await self.product_repository.get_by_id(request.product_id)
            
            if not product:
                return GetProductByIdResponse(
                    success=False,
                    message=f"Produto com ID {request.product_id} não encontrado"
                )
            
            # Buscar dados externos de forma assíncrona
            external_rating_task = asyncio.create_task(
                self.external_rating_service.get_product_rating(product.id)
            )
            market_data_task = asyncio.create_task(
                self.market_data_service.get_market_data(product.id)
            )
            
            # Aguardar resultados
            results = await asyncio.gather(
                external_rating_task, 
                market_data_task,
                return_exceptions=True
            )
            
            # Processar resultados das APIs externas
            if isinstance(results[0], Exception):
                logger.error(f"Erro ao obter avaliação externa: {str(results[0])}")
            else:
                product.external_rating = results[0]
                
            if isinstance(results[1], Exception):
                logger.error(f"Erro ao obter dados de mercado: {str(results[1])}")
            else:
                product.market_data = results[1]
            
            return GetProductByIdResponse(
                success=True,
                product=product
            )
            
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {str(e)}")
            return GetProductByIdResponse(
                success=False,
                message=f"Erro ao processar requisição: {str(e)}"
            )

class SearchProductsUseCase(UseCase[SearchProductsResponse]):
    """Caso de uso para buscar produtos."""
    
    def __init__(self, product_repository):
        self.product_repository = product_repository
    
    async def execute(self, request: SearchProductsRequest) -> SearchProductsResponse:
        """Executa o caso de uso para buscar produtos."""
        try:
            # Preparar parâmetros de busca
            search_params = {}
            if request.category:
                search_params["category"] = request.category
            
            # Verificar se há um filtro de preço
            if request.min_price is not None or request.max_price is not None:
                price_range = {}
                if request.min_price is not None:
                    price_range["min_price"] = request.min_price
                if request.max_price is not None:
                    price_range["max_price"] = request.max_price
                search_params["price_range"] = price_range
            
            # Adicionar termo de busca, se fornecido
            if request.query:
                search_params["query"] = request.query
                
            # Definir limite de resultados
            search_params["limit"] = request.limit
            
            # Executar busca
            products, total_count = await self.product_repository.search(search_params)
            
            return SearchProductsResponse(
                success=True,
                products=products,
                total_count=total_count
            )
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {str(e)}")
            return SearchProductsResponse(
                success=False,
                message=f"Erro ao processar requisição: {str(e)}"
            )

# --- 3. CAMADA DE INTERFACE (ADAPTADORES) ---

# 3.1 Modelos de Persistência (PynamoDB)

class ReviewMapAttribute(MapAttribute):
    """Atributo de mapa para avaliações de produto."""
    rating = NumberAttribute()
    comment = UnicodeAttribute(null=True)
    user_id = UnicodeAttribute()
    date = UnicodeAttribute()

class ProductModel(Model):
    """Modelo PynamoDB para tabela de produtos."""
    class Meta:
        table_name = os.environ.get("PRODUCTS_TABLE", "products")
        region = os.environ.get("AWS_REGION", "us-east-1")
        
    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    price = NumberAttribute()
    category = UnicodeAttribute()
    tags = ListAttribute(of=UnicodeAttribute, default=[])
    stock = NumberAttribute()
    reviews = ListAttribute(of=ReviewMapAttribute, default=[])
    
    @classmethod
    def from_entity(cls, product: Product) -> "ProductModel":
        """Converte entidade de domínio para modelo PynamoDB."""
        reviews_data = []
        for review in product.reviews:
            reviews_data.append(ReviewMapAttribute(
                rating=review.rating,
                comment=review.comment,
                user_id=review.user_id,
                date=review.date
            ))
        
        return cls(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            category=product.category.value,
            tags=product.tags,
            stock=product.stock,
            reviews=reviews_data
        )
    
    def to_entity(self) -> Product:
        """Converte modelo PynamoDB para entidade de domínio."""
        reviews = []
        for review_data in self.reviews:
            reviews.append(ProductReview(
                rating=review_data.rating,
                comment=review_data.comment,
                user_id=review_data.user_id,
                date=review_data.date
            ))
        
        return Product(
            id=self.id,
            name=self.name,
            description=self.description,
            price=self.price,
            category=ProductCategory(self.category),
            tags=self.tags,
            stock=self.stock,
            reviews=reviews
        )

# 3.2 Repositórios

class ProductRepository:
    """Repositório para acesso a dados de produtos."""
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Busca um produto pelo ID."""
        try:
            # Note: PynamoDB não é assíncrono, mas envolvemos em uma função async
            # para manter consistência com a interface
            product_data = ProductModel.get(product_id)
            return product_data.to_entity()
        except DoesNotExist:
            return None
        except PynamoDBConnectionError as e:
            logger.error(f"Erro de conexão com DynamoDB: {str(e)}")
            raise UseCaseError(f"Erro de banco de dados: {str(e)}", 500)
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {str(e)}")
            raise UseCaseError(f"Erro ao buscar produto: {str(e)}", 500)
    
    async def search(self, params: Dict[str, Any]) -> tuple[List[Product], int]:
        """
        Busca produtos com filtros.
        
        Args:
            params: Dicionário com parâmetros de busca
                - category: Categoria de produtos
                - price_range: Faixa de preço (dict com min_price, max_price)
                - query: Termo de busca para nome/descrição
                - limit: Limite de resultados
                
        Returns:
            Tupla com lista de produtos e contagem total
        """
        try:
            # Como a PynamoDB não suporta consultas complexas facilmente,
            # simulamos uma implementação com scan e filtragem
            
            # Iniciar com scan básico
            scan_kwargs = {}
            
            # Filtrar por categoria, se especificada
            if "category" in params:
                scan_kwargs["category"] = params["category"].value
            
            # Note: Em um ambiente real, você usaria índices secundários
            # e construção de query complexa em vez de scan com filter
            product_items = list(ProductModel.scan(**scan_kwargs))
            
            # Aplicar filtros adicionais na memória (não ideal para produção)
            filtered_items = []
            for item in product_items:
                # Filtrar por faixa de preço
                if "price_range" in params:
                    price_range = params["price_range"]
                    if "min_price" in price_range and item.price < price_range["min_price"]:
                        continue
                    if "max_price" in price_range and item.price > price_range["max_price"]:
                        continue
                
                # Filtrar por termo de busca
                if "query" in params and params["query"]:
                    search_term = params["query"].lower()
                    if (search_term not in item.name.lower() and 
                        (not item.description or search_term not in item.description.lower())):
                        continue
                
                filtered_items.append(item)
            
            # Limitar resultados
            limit = params.get("limit", 10)
            total_count = len(filtered_items)
            limited_items = filtered_items[:limit]
            
            # Converter para entidades
            products = [item.to_entity() for item in limited_items]
            
            return products, total_count
            
        except PynamoDBConnectionError as e:
            logger.error(f"Erro de conexão com DynamoDB: {str(e)}")
            raise UseCaseError(f"Erro de banco de dados: {str(e)}", 500)
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {str(e)}")
            raise UseCaseError(f"Erro ao buscar produtos: {str(e)}", 500)

# 3.3 Serviços Externos

class ExternalRatingService:
    """Serviço para obter avaliações de produtos de uma API externa."""
    
    def __init__(self, api_base_url: str = None, api_key: str = None):
        self.api_base_url = api_base_url or os.environ.get("RATINGS_API_URL", "https://api.ratings.example.com")
        self.api_key = api_key or os.environ.get("RATINGS_API_KEY", "")
    
    async def get_product_rating(self, product_id: str) -> Optional[float]:
        """Busca a avaliação média de um produto em uma API externa."""
        try:
            url = f"{self.api_base_url}/products/{product_id}/rating"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("rating")
                    elif response.status == 404:
                        logger.info(f"Avaliação não encontrada para produto {product_id}")
                        return None
                    else:
                        logger.warning(f"Erro ao buscar avaliação: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout ao buscar avaliação para produto {product_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar avaliação externa: {str(e)}")
            return None

class MarketDataService:
    """Serviço para obter dados de mercado de uma API externa."""
    
    def __init__(self, api_base_url: str = None, api_key: str = None):
        self.api_base_url = api_base_url or os.environ.get("MARKET_API_URL", "https://api.market.example.com")
        self.api_key = api_key or os.environ.get("MARKET_API_KEY", "")
    
    async def get_market_data(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Busca dados de mercado para um produto em uma API externa."""
        try:
            url = f"{self.api_base_url}/market-data/products/{product_id}"
            headers = {"X-API-Key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.info(f"Dados de mercado não encontrados para produto {product_id}")
                        return None
                    else:
                        logger.warning(f"Erro ao buscar dados de mercado: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout ao buscar dados de mercado para produto {product_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar dados de mercado: {str(e)}")
            return None

# --- 4. CAMADA DE FRAMEWORK & DRIVERS ---

# 4.1 Controladores

class APIGatewayController:
    """Controlador para requisições do API Gateway."""
    
    def __init__(self, get_product_use_case: GetProductByIdUseCase, search_products_use_case: SearchProductsUseCase):
        self.get_product_use_case = get_product_use_case
        self.search_products_use_case = search_products_use_case
    
    async def handle_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manipula requisições do API Gateway.
        
        Args:
            event: Evento do API Gateway
            
        Returns:
            Resposta formatada para o API Gateway
        """
        try:
            http_method = event.get("httpMethod", "")
            path = event.get("path", "")
            path_parameters = event.get("pathParameters") or {}
            query_parameters = event.get("queryStringParameters") or {}
            
            # Rota para obter produto por ID
            if http_method == "GET" and "/products/" in path and path_parameters.get("productId"):
                return await self._handle_get_product(path_parameters.get("productId"))
                
            # Rota para buscar produtos
            elif http_method == "GET" and path.endswith("/products"):
                return await self._handle_search_products(query_parameters)
                
            # Rota desconhecida
            else:
                return self._create_response(404, {"success": False, "message": "Rota não encontrada"})
                
        except Exception as e:
            logger.error(f"Erro ao processar requisição: {str(e)}")
            return self._create_response(500, {"success": False, "message": f"Erro interno: {str(e)}"})
    
    async def _handle_get_product(self, product_id: str) -> Dict[str, Any]:
        """Manipula requisição para obter produto por ID."""
        request = GetProductByIdRequest(product_id=product_id)
        response = await self.get_product_use_case.execute(request)
        
        if not response.success:
            status_code = 404 if "não encontrado" in response.message else 500
            return self._create_response(status_code, response.dict())
        
        return self._create_response(200, response.dict())
    
    async def _handle_search_products(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Manipula requisição para buscar produtos."""
        try:
            # Converter e validar parâmetros
            search_request = SearchProductsRequest(
                category=ProductCategory(query_params["category"]) if "category" in query_params else None,
                min_price=float(query_params["minPrice"]) if "minPrice" in query_params else None,
                max_price=float(query_params["maxPrice"]) if "maxPrice" in query_params else None,
                query=query_params.get("q"),
                limit=int(query_params.get("limit", 10))
            )
            
            response = await self.search_products_use_case.execute(search_request)
            
            if not response.success:
                return self._create_response(500, response.dict())
            
            return self._create_response(200, response.dict())
            
        except ValidationError as e:
            return self._create_response(400, {
                "success": False,
                "message": f"Parâmetros inválidos: {str(e)}"
            })
    
    def _create_response(self, status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
        """Cria resposta formatada para o API Gateway."""
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS"
            },
            "body": json.dumps(body)
        }

# 4.2 Lambda Handler

def create_controller():
    """Cria e configura o controlador com as dependências."""
    # Inicializar repositórios e serviços
    product_repository = ProductRepository()
    external_rating_service = ExternalRatingService()
    market_data_service = MarketDataService()
    
    # Inicializar casos de uso
    get_product_use_case = GetProductByIdUseCase(
        product_repository, 
        external_rating_service,
        market_data_service
    )
    
    search_products_use_case = SearchProductsUseCase(
        product_repository
    )
    
    # Criar controlador
    return APIGatewayController(get_product_use_case, search_products_use_case)

# Criar controlador global para reutilização entre invocações da Lambda
controller = create_controller()

async def _handler(event, context):
    """Handler assíncrono para a função Lambda."""
    logger.debug(f"Recebido evento: {json.dumps(event)}")
    
    try:
        # Processar requisição do API Gateway
        return await controller.handle_request(event)
    except Exception as e:
        logger.error(f"Erro não tratado: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "message": "Erro interno do servidor"
            })
        }

def lambda_handler(event, context):
    """
    Função handler principal para AWS Lambda.
    
    Args:
        event: Evento recebido do API Gateway
        context: Contexto da função Lambda
        
    Returns:
        Resposta formatada para o API Gateway
    """
    # Criar loop de eventos se não existir
    loop = asyncio.get_event_loop()
    
    # Executar handler assíncrono
    return loop.run_until_complete(_handler(event, context)) 