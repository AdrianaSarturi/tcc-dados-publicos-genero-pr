# =============================================================================
# config.py — Configurações Centralizadas do Crawler Oficial
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Por que este arquivo existe?
# Pra centralizar todos os parâmetros que podem mudar em um único lugar. 
# Qualquer ajuste (ex: mudar o MAX_PAGES) acontece aqui, e todos os módulos
# que importam este arquivo já recebem o valor atualizado automaticamente.
#
# =============================================================================

from pathlib import Path

# Diretório raiz do projeto (pasta tcc-dados-publicos-genero-pr/)
# Path(__file__) aponta para este arquivo (config.py), .parent é src/,
# e .parent.parent sobe para a raiz do projeto.
DIR_RAIZ = Path(__file__).parent.parent

# Pasta onde os resultados de cada cidade serão salvos (criada em runtime)
DIR_RESULTADOS = DIR_RAIZ / "resultados"
SUFIXO_PASTA   = "_oficial"  # pastas com dados finalizados do TCC


# =============================================================================
# CIDADES — Configuração das 3 cidades-alvo
# =============================================================================
#
# "sementes": lista de URLs onde o crawler começa a navegar.
#             Foi incluido o site oficial de cada prefeitura, do portal da transparência e 
#             do dados abertos no caso de Curitiba.
# "dominios": incluido o domínio do site oficial da prefeitura + do portal de transparência
#             O crawler rejeita qualquer link fora desses domínios.
#             Usa endswith() — cobre subdomínios automaticamente.
#
# Portais verificados em: 20/04/2025
# =============================================================================

CIDADES = {
    "curitiba": {
        "sementes": [
            "https://www.curitiba.pr.gov.br/",
            "https://www.transparencia.curitiba.pr.gov.br/",
            "https://dadosabertos.curitiba.pr.gov.br/",
        ],
        # Subdomínios cobertos automaticamente pelo endswith():
        # www., transparencia., dadosabertos., etc.
        "dominios": ["curitiba.pr.gov.br"],
    },

    "londrina": {
        "sementes": [
            "https://portal.londrina.pr.gov.br/",
            "https://portal.londrina.pr.gov.br/transparencia",
            # Sistema terceirizado (Equiplano)
            "https://portal-prefeitura-londrina.equiplano.cloud/inicio",
        ],
        "dominios": [
            "londrina.pr.gov.br",                         # cobre portal., www., etc.
            "portal-prefeitura-londrina.equiplano.cloud", # domínio externo necessário
        ],
        # Subd. excluído: identificado durante varredura-piloto (mai/2026)
        # pref.londrina.pr.gov.br: era um encurtador de URLs (Shlink) da prefeitura,
        # desativado entre fev–mai/2026. DNS ainda resolve, mas todas as URLs retornam
        # HTTP 404. O portal ainda contém links para esse subd., gerando ~26k requisições
        # inúteis se não bloqueado explicitamente.
        # Evidência: Wayback Machine (28 capturas, fev/2026) + teste HTTP direto.
        "dominios_excluidos": [
            "pref.londrina.pr.gov.br",
        ],
    },

    "maringa": {
        "sementes": [
            "https://www.maringa.pr.gov.br/",
            # Sistema terceirizado (Elotech)
            "https://maringa.oxy.elotech.com.br/portaltransparencia/1/",
        ],
        "dominios": [
            "maringa.pr.gov.br",           # cobre www., www3., tributos., storage., etc.
            "maringa.oxy.elotech.com.br",  # domínio externo necessário
        ],
    },
}


# =============================================================================
# PARÂMETROS DE CRAWLING
# =============================================================================
#
# MAX_PAGES: limite de páginas processadas por sessão.
#   Papel: controle de sessão, não segurança contra loop.
#   O set `visited` já garante que nenhuma URL é processada duas vezes.
#   Com o checkpoint ativo, o crawler retoma de onde parou na próxima execução.
#
# MAX_DEPTH: profundidade máxima da navegação BFS.
#
# REQUEST_TIMEOUT: tempo máximo de espera por resposta do servidor (segundos).
#   Prefeituras podem ser lentas — 15s evita travar sem desistir rápido demais.
#
# MAX_RETRIES: tentativas antes de registrar falha permanente.
#
# PAUSA_ENTRE_REQUESTS: intervalo entre requisições (segundos).
#   Respeita o servidor da prefeitura e reduz risco de bloqueio por volume.
#
# USER_AGENT: como o crawler se identifica para o servidor.
#   Boa prática ética em pesquisa acadêmica — identifica a instituição
#   e o e-mail de contato, diferenciando de bots maliciosos.

MAX_PAGES            = 100000 
MAX_DEPTH            = 10
REQUEST_TIMEOUT      = 15    # segundos
MAX_RETRIES          = 3
PAUSA_ENTRE_REQUESTS = 1.5   # segundos

USER_AGENT = (
    "CrawlerTCC-UTFPR/1.0 "
    "(Pesquisa academica - Mapeamento de Dados Publicos no Parana; "
    "Engenharia de Software UTFPR; "
    "contato: adrianasarturi@alunos.utfpr.edu.br)"
)


# =============================================================================
# PALAVRAS_GENERO — Termos usados pelo Analisador (src/analisador.py)
# =============================================================================

PALAVRAS_GENERO = [
    # Termos diretos
    "genero", "gênero", "gender",
    "sexo", "sex",
    "identidade de gênero", "identidade de genero",

    # Valores que costumam preencher essa coluna (rede de segurança caso a coluna venha sem nome)
    "feminino", "masculino", "female", "male",
    "mulher", "mulheres", "woman", "women",
    "homem", "homens", "man", "men", 
]
