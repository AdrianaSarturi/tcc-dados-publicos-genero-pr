# =============================================================================
# utils.py — Funções Utilitárias Compartilhadas
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Por que este arquivo existe?
# Este módulo funciona como uma "caixa de ferramentas" para o pipeline.
# Funções de validação, tratamento de URLs e requisições HTTP seguras 
# ficam centralizadas aqui para serem importadas sob demanda pelo Crawler,
# pelo Downloader ou pelo Analisador, evitando duplicação de código.
# =============================================================================

import time
import re
from urllib.parse import urlparse, urldefrag

import requests

from src.config import REQUEST_TIMEOUT, MAX_RETRIES, PAUSA_ENTRE_REQUESTS, USER_AGENT


# =============================================================================
# NORMALIZAÇÃO DE URL
# =============================================================================

def normalizar_url(url: str) -> str:
    """
    Padroniza uma URL removendo fragmentos (#ancora) e garantindo que
    não haja barras duplas acidentais no caminho.

    Por que remover fragmentos?
    http://site.com/pagina e http://site.com/pagina#secao são a MESMA página
    no servidor — só diferem na navegação do browser. Sem essa normalização,
    o crawler visitaria a mesma página duas vezes.

    """
    url, _ = urldefrag(url)  # remove tudo após o '#'
    return url.strip()


# =============================================================================
# VALIDAÇÃO DE DOMÍNIO
# =============================================================================

def is_valid_domain(url: str, dominios: list[str]) -> bool:
    """
    Verifica se a URL pertence a um dos domínios válidos da cidade.

    Usa .endswith() para cobrir subdomínios automaticamente, exemplo:
      "curitiba.pr.gov.br" cobre:

        www.curitiba.pr.gov.br           ✅
        dados.curitiba.pr.gov.br         ✅
        transparencia.curitiba.pr.gov.br ✅
        google.com                       ❌

    Recebe uma lista de domínios (e não apenas um string) para suportar
    cidades que usam sistemas terceirizados (Londrina/Equiplano, Maringá/Elotech).

    """
    try:
        netloc = urlparse(url).netloc.lower()
        return any(netloc.endswith(dominio.lower()) for dominio in dominios)
    except Exception:
        return False


# =============================================================================
# IDENTIFICAÇÃO DE ARQUIVOS
# =============================================================================

# Extensões de PÁGINAS WEB — o Crawler usa estas apenas para NAVEGAR, não anota.
# Tudo que tiver extensão e NÃO for página web ou midia será anotado no inventário.
EXTENSOES_PAGINA_WEB = {
    ".html", ".htm", ".xhtml",
    ".php", ".asp", ".aspx", ".jsp", ".cfm",
    ".cgi", ".pl",
    ".css", ".js",
}

# Extensões de MÍDIA — ignoradas pelo inventário.
# Imagens de notícias, ícones e logos não têm valor para pesquisa de dados.
# Vídeos e áudios também estão fora do escopo do TCC.
EXTENSOES_MIDIA = {
    # Imagens
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".svg", ".webp", ".ico", ".tiff", ".tif",
    # Video
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv",
    # Audio
    ".mp3", ".wav", ".ogg", ".aac", ".flac", ".wma",
    # Fontes e assets web
    ".woff", ".woff2", ".ttf", ".eot",
}

def is_arquivo(url: str) -> bool:
    """
    Retorna True se a URL aponta para um arquivo de dados (não página web, não midia).
    """
    try:
        caminho = urlparse(url).path.lower()
        ultimo_segmento = caminho.split("/")[-1]

        # Sem extensao = pagina de navegacao (ex: /secretarias, /sobre)
        if "." not in ultimo_segmento:
            return False

        extensao = "." + ultimo_segmento.rsplit(".", 1)[-1]

        # Exclui paginas web e midia (imagens, video, audio)
        if extensao in EXTENSOES_PAGINA_WEB or extensao in EXTENSOES_MIDIA:
            return False

        return True

    except Exception:
        return False


def is_midia(url: str) -> bool:
    """
    Retorna True se a URL aponta para um arquivo de mídia (imagem, video, audio).

    Usado para descartar URLs que não devem ser inventariadas nem navegadas.
    Sem este check, URLs como /sistema/imagens/foto.jpg são enfileiradas
    pelo BFS como páginas a visitar, poluindo a fila e o terminal.
    """
    try:
        caminho = urlparse(url).path.lower()
        ultimo_segmento = caminho.split("/")[-1]
        if "." not in ultimo_segmento:
            return False
        extensao = "." + ultimo_segmento.rsplit(".", 1)[-1]
        return extensao in EXTENSOES_MIDIA
    except Exception:
        return False


def get_extensao(url: str) -> str:
    """
    Retorna a extensão do arquivo da URL (ex: '.xlsx', '.pdf').
    Retorna string vazia se não for um arquivo.

    """
    try:
        caminho = urlparse(url).path.lower()
        ultimo_segmento = caminho.split("/")[-1]
        if "." in ultimo_segmento:
            return "." + ultimo_segmento.rsplit(".", 1)[-1]
        return ""
    except Exception:
        return ""


# =============================================================================
# SANITIZAÇÃO DE NOMES DE ARQUIVO
# =============================================================================

def sanitizar_nome_arquivo(nome: str) -> str:
    """
    Remove caracteres inválidos de um nome de arquivo para salvar em disco.

    # Caracteres inválidos no Windows: \\ / : * ? " < > |
    Substitui por underscore. Limita o comprimento para evitar erros
    de path muito longo.

    """
    nome_limpo = re.sub(r'[\\/:*?"<>|]', "_", nome)
    return nome_limpo[:200]  # limite seguro para Windows


# =============================================================================
# REQUISIÇÃO COM RETENTATIVAS
# =============================================================================

def fazer_request(url: str, stream: bool = False) -> requests.Response | None:
    """
    Realiza uma requisição HTTP com retentativas automáticas e backoff exponencial.

    Por que isso existe?
    Prefeituras apresentam instabilidades constantes (erros 403, 500, timeouts).
    Sem retentativas, o crawler simplesmente pularia essas páginas/arquivos.
    Com backoff exponencial, cada tentativa espera o dobro da anterior:
      Tentativa 1: falhou → aguarda 2s
      Tentativa 2: falhou → aguarda 4s
      Tentativa 3: falhou → registra falha permanente

    Parâmetros:
      url    : URL a ser acessada
      stream : True para downloads de arquivo (não carrega tudo na memória)

    Retorna:
      Response do requests se bem-sucedido, None se todas as tentativas falharem.
    """
    headers = {"User-Agent": USER_AGENT}

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                stream=stream,
                verify=True,   # valida certificado SSL
            )
            # Consideramos sucesso qualquer resposta do servidor,
            # mesmo 403 ou 404 — o chamador decide o que fazer com o status.
            return response

        except requests.exceptions.SSLError:
            # Alguns sites governamentais têm certificados SSL desatualizados.
            # Tenta novamente sem validação SSL.
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    stream=stream,
                    verify=False,  # ignora SSL inválido
                )
                return response
            except Exception:
                pass

        except requests.exceptions.RequestException:
            # Timeout, erro de conexão, etc.
            pass

        # Backoff exponencial: 2s, 4s, 8s...
        if tentativa < MAX_RETRIES:
            espera = 2 ** tentativa
            time.sleep(espera)

    # Todas as tentativas falharam
    return None
