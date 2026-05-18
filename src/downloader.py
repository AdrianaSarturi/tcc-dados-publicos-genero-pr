# =============================================================================
# downloader.py — Classe DownloaderUrbano (Módulo 2 do Pipeline)
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Responsabilidade: ler o inventário gerado pelo Crawler e baixar apenas
# os arquivos com dados estruturados.
#
# =============================================================================

import time
import warnings
from pathlib import Path

import pandas as pd

from src.config import DIR_RESULTADOS, PAUSA_ENTRE_REQUESTS
from src.utils import fazer_request, sanitizar_nome_arquivo

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Extensões que o Downloader baixa — subconjunto do que o Crawler anota.
EXTENSOES_DOWNLOAD = {".xlsx", ".xls", ".xlsm", ".csv", ".ods", ".zip", ".rar"}

class DownloaderUrbano:
    """
    Downloader para arquivos de dados estruturados encontrados pelo Crawler.

    Uso:
        downloader = DownloaderUrbano("maringa")
        downloader.realizar_downloads()

    Entrada: resultados/{cidade}/inventario_links.xlsx (gerado pelo Crawler)
    Saída:   resultados/{cidade}/downloads/ (arquivos baixados)
             resultados/{cidade}/inventario_links.xlsx (atualizado com status_download)
    """

    def __init__(self, nome_cidade: str):
        self.nome_cidade = nome_cidade

        self.dir_cidade   = DIR_RESULTADOS / nome_cidade
        self.dir_downloads = self.dir_cidade / "downloads"
        self.dir_downloads.mkdir(parents=True, exist_ok=True)

        self.arquivo_inventario = self.dir_cidade / "inventario_links.xlsx"

    # =========================================================================
    # LÓGICA DE DOWNLOAD
    # =========================================================================

    def _deve_baixar(self, tipo_arquivo: str) -> bool:
        """Verifica se o tipo de arquivo está na lista de downloads."""
        return str(tipo_arquivo).lower() in EXTENSOES_DOWNLOAD

    def _gerar_nome_arquivo(self, url: str, texto_no_site: str, tipo_arquivo: str) -> str:
        """
        Gera um nome de arquivo legível a partir do texto do link (quando existe)
        ou do final da URL (quando não existe).

        Prioriza o texto do link porque é mais descritivo:
          "Dados de Mobilidade 2023" → dados_de_mobilidade_2023.xlsx
        Em vez do nome da URL que pode ser um código:
          "rel_mob_2023_v3_final_NOVO.xlsx" → menos legível
        """
        extensao = str(tipo_arquivo if tipo_arquivo else "").lower()

        # Tenta usar o texto do link como nome base
        if texto_no_site and len(texto_no_site.strip()) > 3:
            nome_base = sanitizar_nome_arquivo(texto_no_site.strip())
        else:
            # Fallback: usa o último segmento da URL
            nome_base = sanitizar_nome_arquivo(url.split("/")[-1].split("?")[0])

        # Garante que a extensão está no nome
        if not nome_base.lower().endswith(extensao):
            nome_base = f"{nome_base}{extensao}"

        return nome_base

    def _resolver_colisao(self, nome_arquivo: str) -> Path:
        """
        Resolve colisão de nomes: se o arquivo já existe, adiciona sufixo numérico.
        Lógica reaproveitada do Experimento 04.

        Exemplo:
          dados_genero.xlsx já existe →
          dados_genero_1.xlsx, dados_genero_2.xlsx, etc.
        """
        caminho = self.dir_downloads / nome_arquivo
        if not caminho.exists():
            return caminho

        # Separa nome e extensão para inserir o sufixo
        stem = Path(nome_arquivo).stem
        suffix = Path(nome_arquivo).suffix
        contador = 1
        while True:
            novo_nome = f"{stem}_{contador}{suffix}"
            caminho_novo = self.dir_downloads / novo_nome
            if not caminho_novo.exists():
                return caminho_novo
            contador += 1

    # =========================================================================
    # MOTOR PRINCIPAL
    # =========================================================================

    def realizar_downloads(self):
        """
        Lê o inventário, baixa os arquivos elegíveis e atualiza a planilha
        com o resultado de cada download (coluna 'status_download').

        Status possíveis:
          BAIXADO        — arquivo salvo com sucesso
          JA_EXISTE      — arquivo já estava na pasta de downloads
          TIPO_IGNORADO  — extensão fora da lista EXTENSOES_DOWNLOAD (ex: .pdf)
          ERRO_HTTP_XXX  — servidor retornou erro (403, 404, etc.)
          FALHA          — erro de conexão / timeout após retentativas
        """
        if not self.arquivo_inventario.exists():
            print(f"Inventário não encontrado: {self.arquivo_inventario}")
            print("Execute o Crawler primeiro para gerar a planilha.")
            return

        df = pd.read_excel(self.arquivo_inventario)

        # Adiciona coluna de status se ainda não existir
        if "status_download" not in df.columns:
            df["status_download"] = ""

        total = len(df)
        baixados = 0
        ignorados = 0
        erros = 0
        vazios = 0

        print(f"\n{'='*60}")
        print(f"Downloader iniciado: {self.nome_cidade.upper()}")
        print(f"Total de arquivos no inventário: {total}")
        print(f"Pasta de downloads: {self.dir_downloads}")
        print(f"{'='*60}\n")

        for idx, row in df.iterrows():
            url          = str(row.get("url_encontrada", ""))
            tipo_arquivo = str(row.get("tipo_arquivo", "")).lower()
            texto        = str(row.get("texto_no_site", ""))

            # Já foi processado em execução anterior?
            if str(row.get("status_download", "")).startswith("BAIXADO"):
                print(f"Já baixado: {url[:60]}")
                baixados += 1
                continue

            # Verifica se deve baixar este tipo
            if not self._deve_baixar(tipo_arquivo):
                df.at[idx, "status_download"] = "TIPO_IGNORADO"
                ignorados += 1
                continue

            # Gera nome do arquivo e verifica colisão
            nome_arquivo = self._gerar_nome_arquivo(url, texto, tipo_arquivo)
            caminho_destino = self.dir_downloads / nome_arquivo

            if caminho_destino.exists():
                df.at[idx, "status_download"] = "JA_EXISTE"
                print(f"Já existe: {nome_arquivo}")
                baixados += 1
                continue

            # Tenta baixar o arquivo
            print(f"Baixando [{tipo_arquivo}]: {url[:60]}")
            response = fazer_request(url, stream=True)

            if response is None:
                df.at[idx, "status_download"] = "FALHA"
                erros += 1
                continue

            if response.status_code != 200:
                df.at[idx, "status_download"] = f"ERRO_HTTP_{response.status_code}"
                print(f" ❌ HTTP {response.status_code}: {url[:60]}")
                erros += 1
                continue

            # Validação 1: Pelo cabeçalho HTTP (se o servidor informar)
            tamanho_informado = response.headers.get("Content-Length")
            if tamanho_informado and int(tamanho_informado) < 50:
                df.at[idx, "status_download"] = "ARQUIVO_VAZIO"
                print(f" ⚠️ Arquivo vazio descartado via header ({tamanho_informado} bytes): {url[:60]}")
                vazios += 1
                continue

            # Salva o arquivo em disco (em chunks para não sobrecarregar a memória)
            caminho_final = self._resolver_colisao(nome_arquivo)
            try:
                with open(caminho_final, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Validação 2: Pelo arquivo salvo no disco
                tamanho_bytes = caminho_final.stat().st_size
                if tamanho_bytes < 50:
                    caminho_final.unlink()  # Deleta o arquivo do disco
                    df.at[idx, "status_download"] = "ARQUIVO_VAZIO"
                    print(f" ⚠️ Arquivo vazio descartado do disco ({tamanho_bytes} bytes): {caminho_final.name}")
                    vazios += 1
                    continue

                df.at[idx, "status_download"] = f"BAIXADO → {caminho_final.name}"
                print(f" ✅ Salvo: {caminho_final.name} ({tamanho_bytes / 1024:.1f} KB)")
                baixados += 1

            except Exception as e:
                df.at[idx, "status_download"] = f"FALHA_ESCRITA: {type(e).__name__}"
                erros += 1

            # Pausa entre downloads
            time.sleep(PAUSA_ENTRE_REQUESTS)

        # Salva o inventário atualizado com a coluna status_download
        df.to_excel(self.arquivo_inventario, index=False)

        print(f"\n{'='*60}")
        print(f" Downloads encerrados: {self.nome_cidade.upper()}")
        print(f" Baixados/já existentes: {baixados}")
        print(f" Arquivos vazios descartados: {vazios}")
        print(f" Ignorados (tipo não elegível): {ignorados}")
        print(f" Erros: {erros}")
        print(f" Inventário atualizado: {self.arquivo_inventario}")
        print(f"{'='*60}\n")
