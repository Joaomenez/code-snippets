# Função Lambda Básica

Este prompt gera uma função AWS Lambda básica em Python que segue boas práticas de desenvolvimento.

## Contexto para IA

```
Você irá criar uma função AWS Lambda em Python que siga as melhores práticas
de desenvolvimento, incluindo estrutura adequada, tratamento de erros, logging
e monitoramento.
```

## Prompt Base

```
Crie uma função AWS Lambda em Python {VERSAO_PYTHON} que {DESCRICAO_FUNCIONALIDADE}.

Requisitos:
- Implemente logs estruturados para facilitar o debugging
- Adicione tratamento adequado de exceções
- Inclua métricas básicas para monitorar a execução
- Organize o código seguindo os princípios de Clean Architecture
- {REQUISITO_ADICIONAL}

A função Lambda é acionada por {TIPO_TRIGGER} e deve processar {TIPO_DADO_ENTRADA}.
```

## Exemplo Preenchido

```
Crie uma função AWS Lambda em Python 3.9 que processe arquivos JSON carregados em um bucket S3 e persista dados em uma tabela DynamoDB.

Requisitos:
- Implemente logs estruturados para facilitar o debugging
- Adicione tratamento adequado de exceções
- Inclua métricas básicas para monitorar a execução
- Organize o código seguindo os princípios de Clean Architecture
- Valide o formato dos arquivos JSON de entrada
- Implemente retry para falhas transitórias no DynamoDB

A função Lambda é acionada por eventos S3 e deve processar arquivos JSON contendo dados de usuários (nome, email, idade).
```

## Output Esperado

A IA deve gerar código completo para uma função Lambda, seguindo os princípios de Clean Architecture:

```python
# src/interfaces/lambda_handler.py
import json
import logging
import os
from typing import Dict, Any

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from application.dtos.usuario_dto import UsuarioEntradaDTO
from application.usecases.processar_usuario_usecase import ProcessarUsuarioUseCase
from infrastructure.repositories.dynamodb_usuario_repository import DynamoDBUsuarioRepository
from domain.exceptions import ValidationError, PersistenceError

# Configuração
logger = Logger(service="processa-usuarios")
metrics = Metrics(namespace="ProcessaUsuariosLambda")
tracer = Tracer(service="processa-usuarios")

# Inicialização de recursos
s3_client = boto3.client('s3')

# Injeção de dependências
usuario_repository = DynamoDBUsuarioRepository(
    table_name=os.environ.get("USUARIOS_TABLE", "usuarios"),
    logger=logger
)
usecase = ProcessarUsuarioUseCase(
    usuario_repository=usuario_repository,
    logger=logger
)

@logger.inject_lambda_context(correlation_id_path="requestId")
@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handler principal da função Lambda.
    Processa arquivos JSON do S3 e salva dados no DynamoDB.
    """
    # Registrar início do processamento
    logger.info("Iniciando processamento de arquivos S3")
    metrics.add_metric(name="InvocacaoLambda", unit="Count", value=1)
    
    try:
        # Extrair informações do bucket e arquivo dos eventos S3
        records_processados = 0
        records_com_erro = 0
        
        for record in event.get('Records', []):
            try:
                # Extrair informações do evento S3
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                
                logger.info(f"Processando arquivo", extra={"bucket": bucket, "key": key})
                
                # Obter o arquivo do S3
                with tracer.capture_method("s3_get_object"):
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    content = response['Body'].read().decode('utf-8')
                
                # Converter JSON para objeto
                dados = json.loads(content)
                if not isinstance(dados, list):
                    dados = [dados]
                
                # Processar cada usuário do arquivo
                for usuario_data in dados:
                    try:
                        # Converter para DTO
                        usuario_dto = UsuarioEntradaDTO(**usuario_data)
                        
                        # Executar caso de uso
                        resultado = usecase.execute(usuario_dto)
                        
                        records_processados += 1
                        logger.info(f"Usuário processado com sucesso", 
                                    extra={"email": usuario_dto.email})
                    except ValidationError as e:
                        records_com_erro += 1
                        logger.warning(f"Erro de validação ao processar usuário: {str(e)}",
                                     extra={"dados": usuario_data})
                        metrics.add_metric(name="ErrosValidacao", unit="Count", value=1)
                    except Exception as e:
                        records_com_erro += 1
                        logger.error(f"Erro ao processar usuário: {str(e)}",
                                    extra={"dados": usuario_data})
                        metrics.add_metric(name="ErrosProcessamento", unit="Count", value=1)
            
            except ClientError as e:
                logger.error(f"Erro ao acessar S3: {str(e)}")
                metrics.add_metric(name="ErrosS3", unit="Count", value=1)
                records_com_erro += 1
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {str(e)}")
                metrics.add_metric(name="ErrosJSON", unit="Count", value=1)
                records_com_erro += 1
            except Exception as e:
                logger.error(f"Erro não esperado: {str(e)}", exc_info=True)
                metrics.add_metric(name="ErrosInesperados", unit="Count", value=1)
                records_com_erro += 1
        
        # Métricas finais
        metrics.add_metric(name="RegistrosProcessados", unit="Count", value=records_processados)
        metrics.add_metric(name="RegistrosComErro", unit="Count", value=records_com_erro)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Processamento concluído",
                "processados": records_processados,
                "erros": records_com_erro
            })
        }
    
    except Exception as e:
        logger.exception(f"Erro crítico no handler: {str(e)}")
        metrics.add_metric(name="ErroCritico", unit="Count", value=1)
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Erro ao processar eventos",
                "error": str(e)
            })
        }

# src/application/dtos/usuario_dto.py
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional

class UsuarioEntradaDTO(BaseModel):
    """DTO para dados de entrada de usuário."""
    nome: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    idade: int = Field(..., gt=0, lt=120)
    
    @validator('nome')
    def nome_deve_ser_valido(cls, v):
        if not v.strip():
            raise ValueError('nome não pode ser vazio')
        return v.strip()

class UsuarioSaidaDTO(BaseModel):
    """DTO para dados de saída de usuário."""
    id: str
    nome: str
    email: str
    idade: int
    criado_em: str

# src/application/usecases/processar_usuario_usecase.py
import uuid
from datetime import datetime

from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import IUsuarioRepository
from domain.exceptions import ValidationError, PersistenceError
from application.dtos.usuario_dto import UsuarioEntradaDTO, UsuarioSaidaDTO

class ProcessarUsuarioUseCase:
    """Caso de uso para processar usuários"""
    
    def __init__(self, usuario_repository: IUsuarioRepository, logger):
        self.usuario_repository = usuario_repository
        self.logger = logger
    
    def execute(self, usuario_dto: UsuarioEntradaDTO) -> UsuarioSaidaDTO:
        """Executa o processamento de um usuário."""
        try:
            # Criar entidade de domínio
            usuario = Usuario(
                id=str(uuid.uuid4()),
                nome=usuario_dto.nome,
                email=usuario_dto.email,
                idade=usuario_dto.idade,
                criado_em=datetime.now().isoformat()
            )
            
            # Persistir no repositório
            self.usuario_repository.salvar(usuario)
            
            # Retornar DTO de saída
            return UsuarioSaidaDTO(
                id=usuario.id,
                nome=usuario.nome,
                email=usuario.email,
                idade=usuario.idade,
                criado_em=usuario.criado_em
            )
        
        except Exception as e:
            self.logger.error(f"Erro no caso de uso: {str(e)}")
            raise

# src/domain/entities/usuario.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class Usuario(BaseModel):
    """Entidade que representa um usuário no domínio."""
    id: str
    nome: str
    email: str
    idade: int
    criado_em: str

# src/domain/repositories/usuario_repository.py
from typing import Protocol, Optional, List
from domain.entities.usuario import Usuario

class IUsuarioRepository(Protocol):
    """Interface para repositório de usuários."""
    
    def salvar(self, usuario: Usuario) -> None:
        """Salva um usuário no banco de dados."""
        ...
    
    def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        """Busca um usuário pelo ID."""
        ...
    
    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        """Busca um usuário pelo email."""
        ...

# src/domain/exceptions.py
class DomainError(Exception):
    """Base exception para erros de domínio."""
    pass

class ValidationError(DomainError):
    """Erro de validação."""
    pass

class PersistenceError(DomainError):
    """Erro de persistência."""
    pass

# src/infrastructure/repositories/dynamodb_usuario_repository.py
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from typing import Optional, Dict, Any
import json
import time

from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import IUsuarioRepository
from domain.exceptions import PersistenceError

class DynamoDBUsuarioRepository(IUsuarioRepository):
    """Implementação do repositório de usuários usando DynamoDB."""
    
    def __init__(self, table_name: str, logger, max_retries: int = 3, dynamodb_resource = None):
        self.table_name = table_name
        self.logger = logger
        self.max_retries = max_retries
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def salvar(self, usuario: Usuario) -> None:
        """Salva um usuário no DynamoDB com retry para falhas transitórias."""
        item = {
            'id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'idade': usuario.idade,
            'criado_em': usuario.criado_em
        }
        
        retry_count = 0
        last_exception = None
        
        while retry_count < self.max_retries:
            try:
                self.table.put_item(Item=item)
                return
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                
                # Se for um erro retentável
                if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # Exponential backoff
                    self.logger.warning(f"Erro transitório ao salvar usuário, tentando novamente em {wait_time}s",
                                      extra={"retry": retry_count, "error": error_code})
                    time.sleep(wait_time)
                    last_exception = e
                else:
                    # Erro não retentável
                    self.logger.error(f"Erro ao salvar usuário: {str(e)}")
                    raise PersistenceError(f"Erro ao salvar no DynamoDB: {str(e)}")
        
        # Se chegou aqui, todas as tentativas falharam
        self.logger.error(f"Erro ao salvar usuário após {self.max_retries} tentativas")
        raise PersistenceError(f"Erro ao salvar no DynamoDB após {self.max_retries} tentativas: {str(last_exception)}")
    
    def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        """Busca um usuário pelo ID."""
        try:
            response = self.table.get_item(Key={'id': usuario_id})
            item = response.get('Item')
            
            if not item:
                return None
            
            return Usuario(**item)
        except ClientError as e:
            self.logger.error(f"Erro ao buscar usuário por ID: {str(e)}")
            raise PersistenceError(f"Erro ao buscar no DynamoDB: {str(e)}")
    
    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        """Busca um usuário pelo email usando um índice secundário global."""
        try:
            # Assumindo que existe um GSI chamado 'email-index'
            response = self.table.query(
                IndexName='email-index',
                KeyConditionExpression=Key('email').eq(email)
            )
            
            items = response.get('Items', [])
            if not items:
                return None
            
            return Usuario(**items[0])
        except ClientError as e:
            self.logger.error(f"Erro ao buscar usuário por email: {str(e)}")
            raise PersistenceError(f"Erro ao buscar no DynamoDB: {str(e)}")
```

## Como Adaptar

Para usar este template:

1. Substitua `{VERSAO_PYTHON}` pela versão do Python desejada (ex: 3.9, 3.10)
2. Em `{DESCRICAO_FUNCIONALIDADE}`, explique o propósito da função Lambda
3. Descreva requisitos específicos em `{REQUISITO_ADICIONAL}`
4. Especifique o `{TIPO_TRIGGER}` (S3, API Gateway, SQS, etc.)
5. Indique o `{TIPO_DADO_ENTRADA}` que a função processará

## Boas Práticas para Funções Lambda

1. **Estrutura e Organização**
   - Separe o handler principal da lógica de negócios
   - Use Clean Architecture para melhor testabilidade e manutenção
   - Isole a configuração da aplicação do código de negócio

2. **Logging e Observabilidade**
   - Use bibliotecas como AWS Lambda Powertools para logging estruturado
   - Adicione informações contextuais nos logs (IDs, parâmetros importantes)
   - Implemente métricas customizadas para monitorar pontos críticos

3. **Tratamento de Erros**
   - Trate exceções específicas de forma diferenciada
   - Use hierarquia de exceções para maior clareza
   - Não deixe exceções não tratadas
   - Implemente retries com backoff exponencial para operações transitórias

4. **Performance**
   - Minimize inicializações no handler para reduzir cold starts
   - Use variáveis de ambiente para configuração
   - Mantenha as dependências ao mínimo necessário

5. **Segurança**
   - Valide todas as entradas
   - Use princípio de menor privilégio para IAM roles
   - Nunca hardcode credenciais ou segredos 