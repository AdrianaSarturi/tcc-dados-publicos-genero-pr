# Evidências de Execução

Esta pasta contém os registros visuais (prints de terminal) capturados
durante a execução do pipeline de coleta de dados para o TCC. Esses registros
servem como evidência técnica da metodologia adotada, dos mecanismos de resiliência e dos resultados obtidos.

## Inventário de Evidências

| Arquivo | Descrição / Contexto no TCC |
|---|---|
| `londrina_encerramento.png` | Resumo final da varredura (Etapa 1) de Londrina, comprovando a finalização da coleta com 141.768 páginas visitadas (acumulado), 43.030 arquivos registrados no inventário e profundidade máxima de depth=10 atingida. |
| `maringa_teste_profundidade_20.png` | Teste de Maringá sem limite (atingindo depth=20). Evidência crucial que justificou a alteração metodológica para `MAX_DEPTH=10` ao identificar loops em calendários e páginas de redirecionamento. |
| `maringa_encerramento.png` | Resumo final da varredura (Etapa 1) de Maringá, comprovando a finalização da coleta com 8.821 páginas visitadas (acumulado), 13.340 arquivos registrados no inventário e profundidade máxima de depth=10 atingida. |
| `selenium_fallback.png` | Demonstração da resiliência do crawler durante a varredura de Curitiba: acionamento automático do Selenium após bloqueios HTTP 403 consecutivos no portal municipal, evidenciando a estratégia de fallback implementada para contornar restrições de acesso automatizado. |
| `sessao_dinamica_maringa.png` | Detecção da barreira técnica gerada por URLs com parâmetro `sessao=` dinâmico (sistema Elotech), mitigada via rotina de normalização e deduplicação. |
| `Exemplo_de_documento_protegido_senha.png` | Exemplo de documento protegido por senha, ilustrando um exemplo de limitação técnica. |
| `download_documentos.png` | Descoberta de arquivos `.ashx` no portal legislativo de Curitiba (`legisladocexterno.curitiba.pr.gov.br`), evidenciando o padrão de entrega dinâmica de documentos (atos, diários, anexos) — tipo registrado no inventário mas não analisável pelo módulo de mineração de texto por não ser um formato tabular estruturado. |
| `curitiba_salvamento_checkpoint.png` | Registro do mecanismo de persistência de dados (checkpoint) atuando de forma incremental, garantindo a robustez contra falhas. |
| `curitiba_encerramento.png` | Resumo final da varredura (Etapa 1) de Curitiba, comprovando a finalização da coleta com 153.230 páginas visitadas (acumulado), 73.173 arquivos registrados no inventário e profundidade máxima de depth=10 atingida. |
| `curitiba_encerramento_2.png` | Tela de encerramento do crawler de Curitiba detalhando o resumo da sessão, arquivos salvos no inventário (73.173) e contagem final de erros/bloqueios (1.162). |
