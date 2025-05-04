import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, Callable

import requests
from pydantic import BaseModel, ValidationError
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry

# Configuração de logging
logger = logging.getLogger(__name__)

# Tipo genérico para os modelos de resposta
T = TypeVar('T', bound=BaseModel)


class HttpMethod(Enum):
    """Métodos HTTP suportados."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class HttpResponse(Generic[T]):
    """Resposta HTTP padronizada com dados deserializados."""
    success: bool
    status_code: int
    data: Optional[T] = None
    error_message: Optional[str] = None
    raw_response: Optional[requests.Response] = None
    headers: Optional[Dict[str, str]] = None
    elapsed_ms: Optional[float] = None


class HttpClientConfig:
    """Configuração para o cliente HTTP."""
    
    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_on_status: List[int] = None,
        default_headers: Dict[str, str] = None,
        auth: Optional[tuple] = None,
        log_request_body: bool = False,
        log_response_body: bool = False
    ):
        """
        Inicializa a configuração do cliente HTTP.
        
        Args:
            base_url: URL base para todas as requisições
            timeout: Timeout em segundos
            verify_ssl: Se True, verifica certificados SSL
            max_retries: Número máximo de retentativas para erros transitórios
            retry_backoff_factor: Fator de espera entre retentativas
            retry_on_status: Lista de códigos HTTP para retentativa (padrão: 429, 500, 502, 503, 504)
            default_headers: Cabeçalhos padrão para todas as requisições
            auth: Tupla (username, password) para autenticação básica
            log_request_body: Se True, loga os corpos das requisições
            log_response_body: Se True, loga os corpos das respostas
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_on_status = retry_on_status or [429, 500, 502, 503, 504]
        self.default_headers = default_headers or {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.auth = auth
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body


class HttpClient:
    """
    Cliente HTTP que faz requisições e deserializa respostas automaticamente em DTOs.
    """
    
    def __init__(self, config: Optional[HttpClientConfig] = None):
        """
        Inicializa o cliente HTTP.
        
        Args:
            config: Configuração do cliente (opcional)
        """
        self.config = config or HttpClientConfig()
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """
        Cria e configura uma sessão HTTP com retry e outras configurações.
        
        Returns:
            Sessão HTTP configurada
        """
        session = requests.Session()
        
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_backoff_factor,
            status_forcelist=self.config.retry_on_status,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        if self.config.auth:
            session.auth = self.config.auth
            
        return session
    
    def _build_url(self, endpoint: str) -> str:
        """
        Constrói a URL completa a partir da URL base e do endpoint.
        
        Args:
            endpoint: Endpoint da API
            
        Returns:
            URL completa
        """
        # Se o endpoint já for uma URL completa, retorná-la
        if endpoint.startswith(("http://", "https://")):
            return endpoint
            
        # Caso contrário, combinar com a URL base
        endpoint = endpoint.lstrip("/")
        return f"{self.config.base_url}/{endpoint}"
    
    def _prepare_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Combina os cabeçalhos padrão com os adicionais.
        
        Args:
            additional_headers: Cabeçalhos adicionais para a requisição
            
        Returns:
            Cabeçalhos combinados
        """
        headers = self.config.default_headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def request(
        self,
        method: HttpMethod,
        endpoint: str,
        response_model: Optional[Type[T]] = None,
        data: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        error_handler: Optional[Callable[[requests.Response], str]] = None
    ) -> HttpResponse[T]:
        """
        Faz uma requisição HTTP e deserializa a resposta.
        
        Args:
            method: Método HTTP (GET, POST, etc)
            endpoint: Endpoint da API
            response_model: Modelo Pydantic para deserialização (opcional)
            data: Dados a serem enviados no corpo da requisição
            params: Parâmetros de query string
            headers: Cabeçalhos adicionais
            timeout: Timeout em segundos (sobrescreve o padrão)
            error_handler: Função para extrair mensagem de erro da resposta
            
        Returns:
            Objeto HttpResponse com os dados deserializados ou erro
        """
        url = self._build_url(endpoint)
        final_headers = self._prepare_headers(headers)
        timeout_value = timeout or self.config.timeout
        
        # Preparar corpo da requisição se necessário
        request_body = None
        if data is not None:
            if isinstance(data, (dict, list)):
                request_body = json.dumps(data)
            elif isinstance(data, BaseModel):
                request_body = data.json()
            else:
                request_body = data
                
        # Logar detalhes da requisição
        log_extra = {
            "method": method.value,
            "url": url,
            "headers": {k: v for k, v in final_headers.items() if k.lower() != "authorization"}
        }
        
        if self.config.log_request_body and request_body:
            log_extra["request_body"] = request_body
            
        logger.debug(f"Iniciando requisição {method.value} para {url}", extra=log_extra)
        
        start_time = time.time()
        raw_response = None
        
        try:
            # Fazer a requisição
            raw_response = self.session.request(
                method=method.value,
                url=url,
                data=request_body,
                params=params,
                headers=final_headers,
                timeout=timeout_value,
                verify=self.config.verify_ssl
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            status_code = raw_response.status_code
            
            # Logar resposta recebida
            log_extra = {
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "headers": dict(raw_response.headers)
            }
            
            if self.config.log_response_body:
                try:
                    log_extra["response_body"] = raw_response.text[:1000]  # Limitar tamanho
                except:
                    pass
                
            logger.debug(
                f"Resposta recebida: {status_code} ({elapsed_ms:.2f}ms)",
                extra=log_extra
            )
            
            # Verificar se a requisição foi bem-sucedida (2xx)
            raw_response.raise_for_status()
            
            # Se não há modelo de resposta, retornar sucesso com corpo cru
            if response_model is None:
                return HttpResponse(
                    success=True,
                    status_code=status_code,
                    headers=dict(raw_response.headers),
                    raw_response=raw_response,
                    elapsed_ms=elapsed_ms
                )
            
            # Tentar deserializar a resposta
            try:
                # Se a resposta for vazia, retornar None como dados
                if not raw_response.text or raw_response.text.isspace():
                    return HttpResponse(
                        success=True,
                        status_code=status_code,
                        data=None,
                        headers=dict(raw_response.headers),
                        raw_response=raw_response,
                        elapsed_ms=elapsed_ms
                    )
                
                # Tentar parsear JSON
                json_data = raw_response.json()
                
                # Deserializar no modelo Pydantic
                data_object = response_model(**json_data)
                
                return HttpResponse(
                    success=True,
                    status_code=status_code,
                    data=data_object,
                    headers=dict(raw_response.headers),
                    raw_response=raw_response,
                    elapsed_ms=elapsed_ms
                )
            except ValidationError as e:
                logger.error(
                    f"Erro de validação ao deserializar resposta: {str(e)}",
                    extra={"url": url, "response_body": raw_response.text[:500]}
                )
                return HttpResponse(
                    success=False,
                    status_code=status_code,
                    error_message=f"Erro de validação: {str(e)}",
                    headers=dict(raw_response.headers),
                    raw_response=raw_response,
                    elapsed_ms=elapsed_ms
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Erro ao decodificar JSON da resposta: {str(e)}",
                    extra={"url": url, "response_body": raw_response.text[:500]}
                )
                return HttpResponse(
                    success=False,
                    status_code=status_code,
                    error_message=f"Resposta inválida: {str(e)}",
                    headers=dict(raw_response.headers),
                    raw_response=raw_response,
                    elapsed_ms=elapsed_ms
                )
                
        except requests.exceptions.HTTPError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            status_code = e.response.status_code if hasattr(e, 'response') else 0
            
            # Extrair mensagem de erro da resposta
            error_message = "Erro HTTP"
            if raw_response:
                if error_handler:
                    try:
                        error_message = error_handler(raw_response)
                    except Exception as ex:
                        logger.warning(f"Erro ao extrair mensagem de erro: {str(ex)}")
                        
                if not error_message or error_message == "Erro HTTP":
                    try:
                        # Tentar extrair erro do JSON
                        json_response = raw_response.json()
                        error_message = (
                            json_response.get('error') or
                            json_response.get('message') or
                            json_response.get('errorMessage') or
                            str(e)
                        )
                    except:
                        error_message = raw_response.text or str(e)
            
            logger.error(
                f"Erro HTTP {status_code}: {error_message}",
                extra={"url": url, "method": method.value, "elapsed_ms": elapsed_ms}
            )
            
            return HttpResponse(
                success=False,
                status_code=status_code,
                error_message=error_message,
                headers=dict(raw_response.headers) if raw_response else None,
                raw_response=raw_response,
                elapsed_ms=elapsed_ms
            )
            
        except RequestException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            logger.error(
                f"Erro de requisição: {str(e)}",
                extra={"url": url, "method": method.value, "elapsed_ms": elapsed_ms}
            )
            
            return HttpResponse(
                success=False,
                status_code=0,
                error_message=str(e),
                elapsed_ms=elapsed_ms
            )
    
    def get(
        self, 
        endpoint: str, 
        response_model: Optional[Type[T]] = None,
        **kwargs
    ) -> HttpResponse[T]:
        """
        Faz uma requisição GET.
        
        Args:
            endpoint: Endpoint da API
            response_model: Modelo Pydantic para deserialização
            **kwargs: Argumentos adicionais para o método request
            
        Returns:
            Objeto HttpResponse com os dados deserializados ou erro
        """
        return self.request(HttpMethod.GET, endpoint, response_model, **kwargs)
    
    def post(
        self, 
        endpoint: str, 
        data: Any = None,
        response_model: Optional[Type[T]] = None,
        **kwargs
    ) -> HttpResponse[T]:
        """
        Faz uma requisição POST.
        
        Args:
            endpoint: Endpoint da API
            data: Dados a serem enviados no corpo da requisição
            response_model: Modelo Pydantic para deserialização
            **kwargs: Argumentos adicionais para o método request
            
        Returns:
            Objeto HttpResponse com os dados deserializados ou erro
        """
        return self.request(HttpMethod.POST, endpoint, response_model, data=data, **kwargs)
    
    def put(
        self, 
        endpoint: str, 
        data: Any = None,
        response_model: Optional[Type[T]] = None,
        **kwargs
    ) -> HttpResponse[T]:
        """
        Faz uma requisição PUT.
        
        Args:
            endpoint: Endpoint da API
            data: Dados a serem enviados no corpo da requisição
            response_model: Modelo Pydantic para deserialização
            **kwargs: Argumentos adicionais para o método request
            
        Returns:
            Objeto HttpResponse com os dados deserializados ou erro
        """
        return self.request(HttpMethod.PUT, endpoint, response_model, data=data, **kwargs)
    
    def patch(
        self, 
        endpoint: str, 
        data: Any = None,
        response_model: Optional[Type[T]] = None,
        **kwargs
    ) -> HttpResponse[T]:
        """
        Faz uma requisição PATCH.
        
        Args:
            endpoint: Endpoint da API
            data: Dados a serem enviados no corpo da requisição
            response_model: Modelo Pydantic para deserialização
            **kwargs: Argumentos adicionais para o método request
            
        Returns:
            Objeto HttpResponse com os dados deserializados ou erro
        """
        return self.request(HttpMethod.PATCH, endpoint, response_model, data=data, **kwargs)
    
    def delete(
        self, 
        endpoint: str, 
        response_model: Optional[Type[T]] = None,
        **kwargs
    ) -> HttpResponse[T]:
        """
        Faz uma requisição DELETE.
        
        Args:
            endpoint: Endpoint da API
            response_model: Modelo Pydantic para deserialização
            **kwargs: Argumentos adicionais para o método request
            
        Returns:
            Objeto HttpResponse com os dados deserializados ou erro
        """
        return self.request(HttpMethod.DELETE, endpoint, response_model, **kwargs)
        
    def close(self):
        """Fecha a sessão HTTP."""
        self.session.close()
        logger.debug("Sessão HTTP fechada")
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 