# =============================================================================
# main.py — Orquestrador do Pipeline
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Este script conecta os 3 módulos em sequência para uma cidade:
#
#   Etapa 1 — Crawler  : navega o site e anota arquivos encontrados
#   Etapa 2 — Downloader: baixa os arquivos
#   Etapa 3 — Analisador: detecta recorte de gênero nos arquivos baixados
#
# Como usar:
#   venv\Scripts\python main.py maringa           → roda as 3 etapas
#   venv\Scripts\python main.py maringa --etapa 1 → só o Crawler
#   venv\Scripts\python main.py maringa --etapa 2 → só o Downloader
#   venv\Scripts\python main.py maringa --etapa 3 → só o Analisador
# =============================================================================

import argparse
import sys

# Força UTF-8 no terminal do Windows — evita UnicodeEncodeError com emojis
# e caracteres especiais nos prints. Necessário pois o Windows usa cp1252 por padrão.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from src.config import CIDADES


def etapa_crawler(cidade: str, sem_limite: bool = False):
    from src.crawler import CrawlerUrbano
    crawler = CrawlerUrbano(cidade)
    crawler.iniciar_varredura(sem_limite=sem_limite)


def etapa_downloader(cidade: str, **_):
    from src.downloader import DownloaderUrbano
    downloader = DownloaderUrbano(cidade)
    downloader.realizar_downloads()


def etapa_analisador(cidade: str, **_):
    from src.analisador import AnalisadorGenero
    analisador = AnalisadorGenero(cidade)
    analisador.analisar()


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de coleta de dados públicos - TCC UTFPR",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "cidade",
        choices=list(CIDADES.keys()),
        help="Município a processar: maringa, londrina ou curitiba",
    )
    parser.add_argument(
        "--etapa",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help=(
            "Etapa a executar (omitir = todas):\n"
            "  1 = Crawler     (navega e anota arquivos)\n"
            "  2 = Downloader  (baixa os arquivos anotados)\n"
            "  3 = Analisador  (detecta recorte de gênero)"
        ),
    )
    parser.add_argument(
        "--sem-limite",
        action="store_true",
        default=False,
        help=(
            "Remove o limite de páginas do Crawler (MAX_PAGES).\n"
            "Usado para a varredura oficial completa."
        ),
    )

    args = parser.parse_args()
    cidade = args.cidade
    sem_limite = args.sem_limite

    print(f"\n{'='*60}")
    print(f"  TCC - Pipeline de Dados Publicos | {cidade.upper()}")
    print(f"{'='*60}")

    if args.etapa is None:
        print(" Modo: Pipeline completo (Etapas 1 -> 2 -> 3)\n")
        etapa_crawler(cidade, sem_limite=sem_limite)
        etapa_downloader(cidade)
        etapa_analisador(cidade)
    elif args.etapa == 1:
        print(" Modo: Somente Etapa 1 - Crawler\n")
        etapa_crawler(cidade, sem_limite=sem_limite)
    elif args.etapa == 2:
        print(" Modo: Somente Etapa 2 - Downloader\n")
        etapa_downloader(cidade)
    elif args.etapa == 3:
        print(" Modo: Somente Etapa 3 - Analisador\n")
        etapa_analisador(cidade)

    print(f"\n Pipeline encerrado. Resultados em: resultados/{cidade}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
