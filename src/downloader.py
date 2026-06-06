# =============================================================================
# downloader.py — Classe DownloaderUrbano (Módulo 2 do Pipeline)
# TCC: Mapeamento de Dados Públicos no Paraná — Perspectivas de Gênero
# UTFPR — Adriana Sarturi
# =============================================================================
#
# Responsabilidade: ler o inventário gerado pelo Crawler e baixar apenas
# os arquivos elencados para download (planilhas, compactados e txt).
#
# =============================================================================

import hashlib
import time
import warnings
from pathlib import Path

import pandas as pd

from src.config import DIR_RESULTADOS, PAUSA_ENTRE_REQUESTS, SUFIXO_PASTA
from src.utils import fazer_request, sanitizar_nome_arquivo

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Extensões que o Downloader baixa — subconjunto do que o Crawler anota.
EXTENSOES_DOWNLOAD = {".xlsx", ".xls", ".xlsm", ".ods", ".zip", ".rar", ".txt"}

class DownloaderUrbano:
    """
    Downloader para arquivos de dados (planilhas, compactados e txt) encontrados pelo Crawler.

    Uso:
        downloader = DownloaderUrbano("maringa")
        downloader.realizar_downloads()

    Entrada: resultados/{cidade}_oficial/inventario_links.xlsx
    Saída:   resultados/{cidade}_oficial/downloads/
             resultados/{cidade}_oficial/inventario_links.xlsx (atualizado com status_download)
    """

    def __init__(self, nome_cidade: str):
        self.nome_cidade = nome_cidade

        self.dir_cidade    = DIR_RESULTADOS / (nome_cidade + SUFIXO_PASTA)
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
        # Resolve colisão de nomes: se o arquivo já existe, adiciona sufixo numérico.
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
    # DEDUPLICAÇÃO PÓS-DOWNLOAD
    # =========================================================================

    def _deduplicar_downloads(self, df: "pd.DataFrame") -> tuple[int, "pd.DataFrame"]:
        """
        Remove arquivos fisicamente idênticos (mesmo hash MD5) da pasta de downloads.
        Para cada grupo de duplicatas, mantém o arquivo com o nome mais curto
        (geralmente o original, sem sufixo _1, _2, etc.) e deleta os demais.
        Atualiza o DataFrame do inventário marcando as entradas removidas.

        Retorna: (quantidade de duplicatas removidas, tabela do inventário atualizada)
        """
        from collections import defaultdict

        # 1. Calcula MD5 de todos os arquivos em disco
        hash_map: dict[str, list[Path]] = defaultdict(list)
        for arquivo in self.dir_downloads.iterdir():
            if arquivo.is_file():
                md5 = hashlib.md5(arquivo.read_bytes()).hexdigest()
                hash_map[md5].append(arquivo)

        # 2. Para cada hash com mais de um arquivo, mantém o de nome mais curto
        removidos = 0
        nomes_removidos: set[str] = set()
        for md5, arquivos in hash_map.items():
            if len(arquivos) <= 1:
                continue
            arquivos.sort(key=lambda p: (len(p.name), p.name))
            manter = arquivos[0]   # nome mais curto = original sem sufixo
            for duplicata in arquivos[1:]:
                duplicata.unlink()
                nomes_removidos.add(duplicata.name)
                removidos += 1
                print(f"Duplicata removida: {duplicata.name} (idêntica a {manter.name})")

        # 3. Atualiza inventário: marca as entradas cujos arquivos foram removidos
        for idx, row in df.iterrows():
            status = str(row.get("status_download", ""))
            if status.startswith("BAIXADO"):
                nome_arquivo = status.replace("BAIXADO → ", "")
                if nome_arquivo in nomes_removidos:
                    df.at[idx, "status_download"] = f"DUPLICATA_REMOVIDA → {nome_arquivo}"

        return removidos, df

    # =========================================================================
    # MOTOR PRINCIPAL
    # =========================================================================

    def realizar_downloads(self):
        """
        Lê o inventário, baixa os arquivos elegíveis e atualiza a planilha
        com o resultado de cada download (coluna 'status_download').

        Status possíveis:
          BAIXADO            — arquivo salvo com sucesso
          DUPLICATA_REMOVIDA — arquivo idêntico (mesmo hash MD5) já existia; cópia deletada
          TIPO_IGNORADO      — extensão fora da lista EXTENSOES_DOWNLOAD (ex: .pdf)
          ERRO_HTTP_XXX      — servidor retornou erro (403, 404, etc.)
          FALHA              — erro de conexão / timeout após retentativas
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
        baixados_novos = 0
        ja_baixados = 0
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
            status_atual = str(row.get("status_download", ""))
            if status_atual.startswith("BAIXADO"):
                print(f"Já baixado: {url[:60]}")
                ja_baixados += 1
                continue
            if status_atual.startswith("DUPLICATA_REMOVIDA"):
                continue  # arquivo idêntico já foi removido, não re-baixar

            # Verifica se deve baixar este tipo
            if not self._deve_baixar(tipo_arquivo):
                df.at[idx, "status_download"] = "TIPO_IGNORADO"
                ignorados += 1
                continue

            # Gera nome do arquivo e resolve colisão imediatamente.
            # Não verifica existência por nome gerado: URLs diferentes podem
            # gerar o mesmo nome (ex: mesmo texto de link em páginas distintas).
            # _resolver_colisao garante que cada URL receba um arquivo único
            # (dados.xlsx, dados_1.xlsx, dados_2.xlsx, etc.).
            nome_arquivo = self._gerar_nome_arquivo(url, texto, tipo_arquivo)
            caminho_final = self._resolver_colisao(nome_arquivo)

            # Tenta baixar o arquivo
            print(f"Baixando [{tipo_arquivo}]: {url[:60]}")
            response = fazer_request(url, stream=True)

            if response is None:
                df.at[idx, "status_download"] = "FALHA"
                print(f" ❌ Falha de conexão/timeout: {url[:60]}")
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
                baixados_novos += 1

            except Exception as e:
                df.at[idx, "status_download"] = f"FALHA_ESCRITA: {type(e).__name__}"
                erros += 1

            # Pausa entre downloads
            time.sleep(PAUSA_ENTRE_REQUESTS)

        # Deduplicação pós-download: remove arquivos com conteúdo idêntico (hash MD5)
        print(f"\n{'='*60}")
        print(f" Deduplicando arquivos (hash MD5)...")
        duplicatas_removidas, df = self._deduplicar_downloads(df)

        # Salva o inventário atualizado com a coluna status_download
        df.to_excel(self.arquivo_inventario, index=False)

        print(f"\n{'='*60}")
        print(f" Downloads encerrados: {self.nome_cidade.upper()}")
        print(f" Novos downloads:                  {baixados_novos}")
        print(f" Já baixados (sessões anteriores): {ja_baixados}")
        print(f" Duplicatas removidas (MD5):        {duplicatas_removidas}")
        print(f" Arquivos vazios descartados:       {vazios}")
        print(f" Ignorados (tipo não elegível):    {ignorados}")
        print(f" Erros:                            {erros}")
        print(f" Inventário atualizado: {self.arquivo_inventario}")
        print(f"{'='*60}\n")
