import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, Union
import boto3
from botocore.exceptions import ClientError
import tempfile
import uuid
from pydantic import BaseModel, create_model, Field, ValidationError

# Configuração de logging
logger = logging.getLogger(__name__)

# Tipo genérico para o modelo de dados
T = TypeVar('T', bound=BaseModel)

class S3Reference(BaseModel):
    """Referência a um arquivo no S3."""
    bucket: str
    key: str
    version_id: Optional[str] = None
    
class SQSMessage(BaseModel):
    """Modelo para mensagem SQS com possíveis referências ao S3."""
    message_id: str
    receipt_handle: str 
    body: Dict[str, Any]
    attributes: Optional[Dict[str, str]] = None
    s3_references: Optional[List[S3Reference]] = None

@dataclass
class ProcessingResult(Generic[T]):
    """Resultado do processamento de uma mensagem SQS."""
    success: bool
    message_id: str
    receipt_handle: str
    data: Optional[T] = None
    error: Optional[Exception] = None
    downloaded_files: List[str] = None
    
    def __post_init__(self):
        if self.downloaded_files is None:
            self.downloaded_files = []

class SQSS3Processor(Generic[T]):
    """
    Processador que consome mensagens SQS, baixa arquivos referenciados no S3,
    e deserializa os dados em objetos do modelo especificado.
    """
    
    def __init__(
        self,
        queue_url: str,
        data_model: type[T],
        aws_region: Optional[str] = None,
        max_messages: int = 10,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 30,
        s3_client=None,
        sqs_client=None,
        temp_dir: Optional[str] = None
    ):
        """
        Inicializa o processador SQS-S3.
        
        Args:
            queue_url: URL da fila SQS
            data_model: Classe modelo Pydantic para deserialização
            aws_region: Região AWS (opcional, usa a do ambiente se não especificada)
            max_messages: Número máximo de mensagens para receber por vez
            wait_time_seconds: Tempo de long-polling em segundos
            visibility_timeout: Tempo de visibilidade das mensagens em segundos
            s3_client: Cliente S3 customizado (opcional)
            sqs_client: Cliente SQS customizado (opcional)
            temp_dir: Diretório temporário para arquivos baixados (opcional)
        """
        self.queue_url = queue_url
        self.data_model = data_model
        self.max_messages = max_messages
        self.wait_time_seconds = wait_time_seconds
        self.visibility_timeout = visibility_timeout
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
        # Criar clientes AWS se não fornecidos
        aws_region = aws_region or os.environ.get('AWS_REGION', 'us-east-1')
        self.s3 = s3_client or boto3.client('s3', region_name=aws_region)
        self.sqs = sqs_client or boto3.client('sqs', region_name=aws_region)
    
    def receive_messages(self) -> List[SQSMessage]:
        """
        Recebe mensagens da fila SQS.
        
        Returns:
            Lista de mensagens SQS recebidas
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=self.wait_time_seconds,
                VisibilityTimeout=self.visibility_timeout,
                AttributeNames=['All'],
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Recebidas {len(messages)} mensagens da fila {self.queue_url}")
            
            return [
                SQSMessage(
                    message_id=msg['MessageId'],
                    receipt_handle=msg['ReceiptHandle'],
                    body=json.loads(msg['Body']) if isinstance(msg['Body'], str) else msg['Body'],
                    attributes=msg.get('Attributes'),
                )
                for msg in messages
            ]
            
        except ClientError as e:
            logger.error(f"Erro ao receber mensagens: {str(e)}")
            raise
    
    def download_s3_file(self, s3_ref: S3Reference) -> str:
        """
        Baixa um arquivo do S3 para o sistema de arquivos local.
        
        Args:
            s3_ref: Referência ao arquivo no S3
            
        Returns:
            Caminho do arquivo local
        """
        try:
            # Criar nome de arquivo temporário único
            temp_file = os.path.join(
                self.temp_dir, 
                f"{uuid.uuid4()}_{os.path.basename(s3_ref.key)}"
            )
            
            # Configurar parâmetros para download
            download_args = {
                'Bucket': s3_ref.bucket,
                'Key': s3_ref.key
            }
            
            if s3_ref.version_id:
                download_args['VersionId'] = s3_ref.version_id
                
            # Realizar download
            logger.debug(
                f"Baixando arquivo s3://{s3_ref.bucket}/{s3_ref.key} para {temp_file}"
            )
            
            self.s3.download_file(
                Bucket=s3_ref.bucket,
                Key=s3_ref.key,
                Filename=temp_file
            )
            
            logger.info(f"Arquivo baixado com sucesso: {s3_ref.key}")
            return temp_file
            
        except ClientError as e:
            logger.error(
                f"Erro ao baixar arquivo s3://{s3_ref.bucket}/{s3_ref.key}: {str(e)}"
            )
            raise
    
    def extract_s3_references(self, message: SQSMessage) -> List[S3Reference]:
        """
        Extrai referências S3 da mensagem SQS.
        Este método pode ser sobrescrito para lógica personalizada de extração.
        
        Args:
            message: Mensagem SQS
            
        Returns:
            Lista de referências S3 encontradas na mensagem
        """
        references = []
        
        # Se a mensagem já tem referências explícitas, usar elas
        if message.s3_references:
            return message.s3_references
        
        # Tentar encontrar referências no formato padrão no corpo da mensagem
        body = message.body
        
        # Verificar formatos comuns de referência S3
        if "s3" in body and "bucket" in body.get("s3", {}) and "key" in body.get("s3", {}):
            s3_info = body["s3"]
            references.append(S3Reference(
                bucket=s3_info["bucket"],
                key=s3_info["key"],
                version_id=s3_info.get("versionId") or s3_info.get("version_id")
            ))
        
        # Verificar outro formato comum (lista de arquivos)
        elif "files" in body and isinstance(body["files"], list):
            for file_info in body["files"]:
                if isinstance(file_info, dict) and "bucket" in file_info and "key" in file_info:
                    references.append(S3Reference(
                        bucket=file_info["bucket"],
                        key=file_info["key"],
                        version_id=file_info.get("versionId") or file_info.get("version_id")
                    ))
        
        return references
    
    def parse_data(self, message: SQSMessage, downloaded_files: List[str] = None) -> T:
        """
        Parseia os dados da mensagem para o modelo especificado.
        Este método pode ser sobrescrito para lógica personalizada de parsing.
        
        Args:
            message: Mensagem SQS
            downloaded_files: Lista de arquivos baixados do S3
            
        Returns:
            Instância do modelo de dados
        """
        try:
            # Tentar usar diretamente o corpo da mensagem
            try:
                return self.data_model(**message.body)
            except ValidationError:
                # Se não for possível, tentar encontrar dados em campos comuns
                if "data" in message.body:
                    return self.data_model(**message.body["data"])
                
                # Se houver arquivos baixados, tentar ler o primeiro
                if downloaded_files and len(downloaded_files) > 0:
                    with open(downloaded_files[0], 'r') as f:
                        file_content = json.load(f)
                        return self.data_model(**file_content)
                
                # Tentar uma última alternativa com campos conhecidos
                if "payload" in message.body:
                    return self.data_model(**message.body["payload"])
                    
                # Se nada funcionar, reenviar a exceção original
                raise
                
        except Exception as e:
            logger.error(f"Erro ao parsear mensagem {message.message_id}: {str(e)}")
            raise
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Exclui uma mensagem da fila SQS.
        
        Args:
            receipt_handle: Identificador de recebimento da mensagem
            
        Returns:
            True se a exclusão for bem-sucedida, False caso contrário
        """
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao excluir mensagem: {str(e)}")
            return False
    
    def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """
        Remove arquivos temporários.
        
        Args:
            file_paths: Lista de caminhos de arquivos para remover
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Arquivo temporário removido: {file_path}")
            except OSError as e:
                logger.warning(f"Erro ao remover arquivo temporário {file_path}: {str(e)}")
    
    def process_message(self, message: SQSMessage) -> ProcessingResult[T]:
        """
        Processa uma única mensagem SQS.
        
        Args:
            message: Mensagem SQS a ser processada
            
        Returns:
            Resultado do processamento
        """
        downloaded_files = []
        
        try:
            # Extrair referências S3
            s3_references = self.extract_s3_references(message)
            
            # Baixar arquivos referenciados
            for s3_ref in s3_references:
                local_file = self.download_s3_file(s3_ref)
                downloaded_files.append(local_file)
            
            # Parsear dados
            data = self.parse_data(message, downloaded_files)
            
            # Criar resultado de sucesso
            return ProcessingResult(
                success=True,
                message_id=message.message_id,
                receipt_handle=message.receipt_handle,
                data=data,
                downloaded_files=downloaded_files
            )
            
        except Exception as e:
            logger.error(
                f"Erro ao processar mensagem {message.message_id}: {str(e)}",
                exc_info=True
            )
            return ProcessingResult(
                success=False,
                message_id=message.message_id,
                receipt_handle=message.receipt_handle,
                error=e,
                downloaded_files=downloaded_files
            )
        finally:
            # Limpar arquivos temporários se configurado para isso
            if os.environ.get('AUTO_CLEANUP_TEMP_FILES', 'true').lower() == 'true':
                self.cleanup_temp_files(downloaded_files)
    
    def process_queue(
        self, 
        handler: Optional[Callable[[ProcessingResult[T]], bool]] = None,
        auto_delete: bool = True
    ) -> List[ProcessingResult[T]]:
        """
        Processa mensagens da fila.
        
        Args:
            handler: Função opcional para processar cada resultado
            auto_delete: Se True, apaga mensagens processadas com sucesso
            
        Returns:
            Lista de resultados do processamento
        """
        results = []
        
        try:
            # Receber mensagens
            messages = self.receive_messages()
            
            if not messages:
                logger.info("Nenhuma mensagem para processar")
                return []
            
            # Processar cada mensagem
            for message in messages:
                result = self.process_message(message)
                results.append(result)
                
                # Chamar handler personalizado, se fornecido
                if handler and callable(handler):
                    handler_result = handler(result)
                    
                    # Se o handler retornar False, não excluir a mensagem
                    if auto_delete and handler_result is False:
                        auto_delete = False
                
                # Excluir mensagem se processada com sucesso e auto_delete ativado
                if auto_delete and result.success:
                    self.delete_message(result.receipt_handle)
                    
            return results
            
        except Exception as e:
            logger.error(f"Erro ao processar fila: {str(e)}", exc_info=True)
            raise 