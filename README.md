# Mapeamento de Dados Públicos no Paraná: Perspectivas de Gênero

Projeto de Trabalho de Conclusão de Curso em Engenharia de Software - UTFPR.

## 📌 Sobre o projeto

Este trabalho tem como objetivo analisar a disponibilidade de dados públicos em cidades do estado do Paraná, abrangendo tanto dados diretamente relacionados ao planejamento urbano quanto aqueles com potencial para subsidiá-lo, com foco na presença ou ausência de informações desagregadas por gênero.

## 🎯 Objetivos

- Mapear portais de dados públicos municipais do Paraná
- Identificar e baixar arquivos de dados disponíveis nos portais
- Verificar a presença de dados desagregados por gênero via mineração de dados
- Realizar curadoria qualitativa para classificar os arquivos detectados
- Documentar barreiras técnicas e lacunas na disponibilização de dados abertos

## 💻 Tecnologias

- `Python 3.14` — Linguagem principal
- `requests` — Requisições HTTP para acesso às páginas
- `beautifulsoup4` — Parsing de HTML e extração de links
- `selenium` — Fallback para evasão de bloqueios anti-bot
- `pandas` — Manipulação e exportação de dados tabulares
- `openpyxl` — Motor de leitura/escrita de arquivos `.xlsx`

## 🚀 Como executar

### 1. Pré-requisitos

- Python 3.14 instalado
- Google Chrome instalado (necessário para o Selenium)

### 2. Instalar dependências

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv

# Ativar o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Executar o pipeline

```bash
# Rodar o pipeline completo para uma cidade (Etapas 1 → 2 → 3)
python main.py maringa
python main.py londrina
python main.py curitiba

# Rodar apenas uma etapa específica
python main.py maringa --etapa 1   # Crawler: navega e anota arquivos
python main.py maringa --etapa 2   # Downloader: baixa os arquivos
python main.py maringa --etapa 3   # Analisador: detecta recorte de gênero

# Varredura completa sem limite de páginas
python main.py maringa --sem-limite
```

Os resultados são gerados na pasta `resultados/<cidade>/`.

## 📊 Resultados

Os resultados da análise estão organizados por município na pasta `resultados/`:

| Município | Diretório |
|-----------|-----------|
| Maringá | `resultados/maringa_oficial/` |
| Londrina | `resultados/londrina_oficial/` |
| Curitiba | `resultados/curitiba_oficial/` |

Cada diretório contém os inventários de arquivos coletados e os relatórios de classificação por recorte de gênero.

## 📄 Proposta

A proposta desenvolvida no TCC 01 pode ser acessada em:  
[Proposta do projeto](docs/TCC%2001_Proposta.pdf)

## 🗄️ Base de Dados Bruta

Os arquivos coletados durante a pesquisa (downloads e extraídos) estão disponíveis no Google Drive:  
[Acessar base de dados bruta](https://drive.google.com/drive/folders/1JzrvB0snuPFuVCkFLBCbddMnNyjN3JhL?usp=drive_link)

## 🎓 Instituição

UTFPR - Universidade Tecnológica Federal do Paraná

## 👩‍💻 Autores

**Adriana Sarturi**  
Graduanda em Engenharia de Software - UTFPR  

**Tarlis Tortelli Portela**  
Professor Orientador
