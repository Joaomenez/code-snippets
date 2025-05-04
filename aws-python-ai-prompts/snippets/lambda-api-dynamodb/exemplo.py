"""
Exemplo de uso da função Lambda API Gateway com PynamoDB e chamadas assíncronas.
"""
import json
import logging
import uuid
from datetime import datetime

# Importar módulos para a função Lambda
from lambda_api_dynamodb import (
    ProductModel,
    ProductCategory,
    ProductReview,
    Product,
    lambda_handler
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def criar_produto_exemplo():
    """Cria produto de exemplo no DynamoDB."""
    # Criar um novo produto
    product_id = str(uuid.uuid4())
    
    # Criar dados de avaliações
    reviews = [
        ProductReview(
            rating=4.5,
            comment="Excelente produto! Recomendo.",
            user_id="user123",
            date=datetime.now().isoformat()
        ),
        ProductReview(
            rating=5.0,
            comment="Perfeito, superou minhas expectativas.",
            user_id="user456",
            date=datetime.now().isoformat()
        )
    ]
    
    # Criar entidade de domínio
    product = Product(
        id=product_id,
        name="Smartphone XYZ Pro",
        description="Smartphone de última geração com câmera de alta resolução",
        price=1299.99,
        category=ProductCategory.ELECTRONICS,
        tags=["smartphone", "5g", "premium"],
        stock=42,
        reviews=[r.dict() for r in reviews]
    )
    
    # Converter para modelo PynamoDB
    product_model = ProductModel.from_entity(product)
    
    # Salvar no DynamoDB
    try:
        product_model.save()
        logger.info(f"Produto criado com sucesso: {product_id}")
        return product_id
    except Exception as e:
        logger.error(f"Erro ao criar produto: {str(e)}")
        raise

def simular_api_gateway_request(http_method, path, path_params=None, query_params=None):
    """
    Simula uma requisição do API Gateway para a função Lambda.
    
    Args:
        http_method: Método HTTP (GET, POST, etc.)
        path: Caminho da requisição
        path_params: Parâmetros de caminho (opcional)
        query_params: Parâmetros de query string (opcional)
        
    Returns:
        Resposta da função Lambda
    """
    # Construir evento do API Gateway
    event = {
        "httpMethod": http_method,
        "path": path,
        "pathParameters": path_params or {},
        "queryStringParameters": query_params or {}
    }
    
    # Invocar função Lambda
    response = lambda_handler(event, {})
    
    # Extrair e parsear corpo da resposta
    if "body" in response:
        response["parsed_body"] = json.loads(response["body"])
    
    return response

def demonstrar_busca_por_id(product_id):
    """Demonstra busca de produto por ID."""
    logger.info("\n=== Buscando produto por ID ===")
    
    # Simular requisição GET para /products/{id}
    response = simular_api_gateway_request(
        http_method="GET",
        path=f"/products/{product_id}",
        path_params={"productId": product_id}
    )
    
    # Exibir resultado
    logger.info(f"Status code: {response['statusCode']}")
    
    if response.get("parsed_body", {}).get("success"):
        product = response["parsed_body"]["product"]
        logger.info(f"Produto encontrado: {product['name']} (R$ {product['price']})")
        logger.info(f"Categoria: {product['category']}")
        logger.info(f"Avaliações: {len(product['reviews'])}")
        
        if product.get("external_rating"):
            logger.info(f"Avaliação externa: {product['external_rating']}")
            
        if product.get("market_data"):
            logger.info(f"Dados de mercado: {product['market_data']}")
    else:
        logger.error(f"Erro: {response.get('parsed_body', {}).get('message', 'Desconhecido')}")
    
    return response

def demonstrar_busca_produtos(categoria=None, termo_busca=None, preco_min=None, preco_max=None):
    """Demonstra busca de produtos com filtros."""
    logger.info("\n=== Buscando produtos com filtros ===")
    
    # Preparar parâmetros de busca
    query_params = {}
    
    if categoria:
        query_params["category"] = categoria
    
    if termo_busca:
        query_params["q"] = termo_busca
    
    if preco_min is not None:
        query_params["minPrice"] = str(preco_min)
    
    if preco_max is not None:
        query_params["maxPrice"] = str(preco_max)
    
    # Adicionar limite
    query_params["limit"] = "10"
    
    # Descrição dos filtros
    filtros = []
    if categoria:
        filtros.append(f"categoria={categoria}")
    if termo_busca:
        filtros.append(f"termo='{termo_busca}'")
    if preco_min is not None:
        filtros.append(f"preço>={preco_min}")
    if preco_max is not None:
        filtros.append(f"preço<={preco_max}")
    
    if filtros:
        logger.info(f"Filtros aplicados: {', '.join(filtros)}")
    
    # Simular requisição GET para /products
    response = simular_api_gateway_request(
        http_method="GET",
        path="/products",
        query_params=query_params
    )
    
    # Exibir resultado
    logger.info(f"Status code: {response['statusCode']}")
    
    if response.get("parsed_body", {}).get("success"):
        products = response["parsed_body"]["products"]
        total = response["parsed_body"]["total_count"]
        
        logger.info(f"Encontrados {total} produtos, exibindo {len(products)}")
        
        for i, product in enumerate(products, 1):
            logger.info(f"{i}. {product['name']} - R$ {product['price']} ({product['category']})")
    else:
        logger.error(f"Erro: {response.get('parsed_body', {}).get('message', 'Desconhecido')}")
    
    return response

def demonstrar_requisicao_invalida():
    """Demonstra tratamento de requisição inválida."""
    logger.info("\n=== Demonstrando tratamento de erro ===")
    
    # Simular requisição para rota inexistente
    response = simular_api_gateway_request(
        http_method="GET",
        path="/invalid/path"
    )
    
    logger.info(f"Status code: {response['statusCode']}")
    logger.info(f"Mensagem: {response.get('parsed_body', {}).get('message', 'N/A')}")
    
    return response

def demonstrar_busca_parametros_invalidos():
    """Demonstra tratamento de parâmetros inválidos."""
    logger.info("\n=== Demonstrando validação de parâmetros ===")
    
    # Simular requisição com parâmetros inválidos
    response = simular_api_gateway_request(
        http_method="GET",
        path="/products",
        query_params={
            "category": "categoria_invalida",  # Categoria que não existe no enum
            "minPrice": "não_é_numero"  # Valor não numérico
        }
    )
    
    logger.info(f"Status code: {response['statusCode']}")
    logger.info(f"Mensagem: {response.get('parsed_body', {}).get('message', 'N/A')}")
    
    return response

def executar_demonstracao():
    """Executa a demonstração completa."""
    try:
        logger.info("Iniciando demonstração da Lambda API com DynamoDB e asyncio")
        
        # Verificar se a tabela existe e criar se necessário
        if not ProductModel.exists():
            logger.info("Criando tabela DynamoDB...")
            ProductModel.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
        
        # Criar produto de exemplo
        product_id = criar_produto_exemplo()
        
        # Demonstrar busca por ID
        demonstrar_busca_por_id(product_id)
        
        # Demonstrar busca com filtros
        demonstrar_busca_produtos(
            categoria=ProductCategory.ELECTRONICS.value,
            preco_min=1000
        )
        
        # Demonstrar busca por termo
        demonstrar_busca_produtos(termo_busca="smartphone")
        
        # Demonstrar tratamento de erros
        demonstrar_requisicao_invalida()
        demonstrar_busca_parametros_invalidos()
        
        logger.info("\nDemonstração concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro na demonstração: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
if __name__ == "__main__":
    executar_demonstracao() 