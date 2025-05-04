"""
Exemplo de uso do cliente HTTP com deserialização automática.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

# Importar o cliente HTTP
from http_client import HttpClient, HttpClientConfig, HttpResponse

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Definir modelos de dados para a API
class Produto(BaseModel):
    """Modelo para produto retornado pela API."""
    id: int
    nome: str
    preco: float
    descricao: Optional[str] = None
    disponivel: bool = True
    categorias: List[str] = Field(default_factory=list)

class CriarProduto(BaseModel):
    """Modelo para criação de produto."""
    nome: str
    preco: float
    descricao: Optional[str] = None
    categorias: List[str] = Field(default_factory=list)

# Exemplo com API fictícia
def exemplo_basico():
    """Exemplo básico de uso do cliente HTTP."""
    # Criar um cliente para a API
    client = HttpClient(
        config=HttpClientConfig(
            base_url="https://api.exemplo.com/v1",
            default_headers={"X-API-Key": "sua-chave-api"}
        )
    )
    
    try:
        # Exemplo 1: GET com deserialização
        logger.info("Buscando produto por ID...")
        response = client.get("produtos/123", response_model=Produto)
        
        if response.success:
            produto = response.data
            logger.info(f"Produto encontrado: {produto.nome} - R$ {produto.preco:.2f}")
            
            # Acessar as propriedades do objeto deserializado
            if produto.disponivel:
                logger.info(f"Produto está disponível para compra")
                
            if produto.categorias:
                logger.info(f"Categorias: {', '.join(produto.categorias)}")
        else:
            logger.error(f"Erro ao buscar produto: {response.error_message}")
        
        # Exemplo 2: POST com envio de dados
        logger.info("\nCriando novo produto...")
        novo_produto = CriarProduto(
            nome="Smartphone XYZ",
            preco=999.90,
            descricao="Smartphone com câmera de alta resolução",
            categorias=["Eletrônicos", "Celulares", "Smartphones"]
        )
        
        response = client.post(
            "produtos", 
            data=novo_produto,  # Enviar objeto Pydantic
            response_model=Produto
        )
        
        if response.success:
            produto_criado = response.data
            logger.info(f"Produto criado com ID: {produto_criado.id}")
            logger.info(f"Tempo de resposta: {response.elapsed_ms:.2f}ms")
        else:
            logger.error(f"Erro ao criar produto: {response.error_message}")
            
    finally:
        # Fechar o cliente ao terminar (ou usar 'with')
        client.close()

# Exemplo com autenticação e tratamento de erros
def exemplo_avancado():
    """Exemplo mais avançado com autenticação e tratamento de erros."""
    # Função personalizada para extrair mensagens de erro
    def extrair_erro_personalizado(response):
        try:
            json_data = response.json()
            if "errors" in json_data:
                return json_data["errors"][0]["message"]
            return json_data.get("message", "Erro desconhecido")
        except:
            return response.text[:100]
    
    # Criar cliente com autenticação
    with HttpClient(
        config=HttpClientConfig(
            base_url="https://api.segura.exemplo.com/v2",
            default_headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "User-Agent": "MeuApp/1.0"
            },
            timeout=15,
            max_retries=2
        )
    ) as client:
        # Lista de produtos com paginação
        logger.info("Buscando lista de produtos...")
        response = client.get(
            "produtos", 
            params={"categoria": "eletronicos", "pagina": 1, "itens_por_pagina": 10},
            response_model=List[Produto],
            error_handler=extrair_erro_personalizado
        )
        
        if response.success:
            produtos = response.data
            logger.info(f"Encontrados {len(produtos)} produtos")
            
            for i, produto in enumerate(produtos[:3], 1):
                logger.info(f"{i}. {produto.nome} - R$ {produto.preco:.2f}")
                
            if len(produtos) > 3:
                logger.info(f"...e mais {len(produtos) - 3} produtos")
        else:
            logger.error(f"Erro na busca: {response.error_message}")
            
        # Simulação de erro para demonstrar tratamento
        logger.info("\nTestando cenário de erro...")
        response = client.get(
            "produtos/99999", 
            response_model=Produto,
            error_handler=extrair_erro_personalizado
        )
        
        if not response.success:
            logger.warning(f"Erro esperado: {response.error_message}")
            logger.warning(f"Código HTTP: {response.status_code}")

if __name__ == "__main__":
    logger.info("=== EXEMPLO BÁSICO ===")
    exemplo_basico()
    
    logger.info("\n=== EXEMPLO AVANÇADO ===")
    exemplo_avancado()
    
    logger.info("\nExemplos concluídos.") 