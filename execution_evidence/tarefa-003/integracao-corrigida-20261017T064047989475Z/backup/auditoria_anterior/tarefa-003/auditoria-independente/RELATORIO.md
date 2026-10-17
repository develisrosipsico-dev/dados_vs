# Tarefa 003 — auditoria independente e regularização

**Estado operacional do corpus recebido: `verified_existing`.** O intervalo direto de O IMPERATIVO DA ESTÓRIA foi conferido no corpus 0.2.3 e no PDF do capítulo. Os testes da tarefa foram corrigidos e executados. O corpus não foi alterado.

| Verificação | Resultado observado |
| --- | --- |
| Testes direcionados corrigidos | 11 aprovados; zero falhas, erros ou skips |
| Suíte geral completa | 101 aprovados; zero falhas, erros ou skips |
| Intervalo direto | 14 registros, ordens globais 28–41 |
| Páginas do intervalo | Locais 8, 9 e 10 |
| Fronteiras inspecionadas | Páginas locais 7 e 11 |
| Destaques do intervalo | 2, registros 29 e 31 |
| Destaques do corpus inteiro | 4; os outros estão fora do intervalo |
| Estado documental | `review_required` |
| Pendências automáticas | 12, preservadas |
| Chunking | `allowed = false`, preservado |
| CLI `validate` | Retorno 0; integridade aprovada pelos critérios implementados |
| CLI `check-ready` | Retorno 2, esperado para gate bloqueado |

## Correções realizadas

Somente `tests/test_tarefa_003.py` foi alterado entre os 107 arquivos recebidos. O original foi preservado em `recebidos/tests/test_tarefa_003.py`; a diferença está em `test_tarefa_003.patch`.

O teste anterior continha uma asserção terminada em `or True`. Ela passava mesmo com vínculos incorretos. A versão corrigida verifica a seleção da seção, os dois proprietários de texto, referências nos dois sentidos, `text_ownership`, correspondência das origens e preservação das pendências.

Quatro controles com alterações somente em memória comprovaram que o teste antigo aceitava vínculo direto quebrado, vínculo inverso quebrado, propriedade primária indevida e remoção do estado pendente. O teste corrigido rejeitou os quatro casos. Nenhum arquivo do corpus foi modificado nesses controles.

A existência de PNGs foi retirada como substituto de inspeção visual. Esse teste foi substituído por revalidação real do estado documental, das 12 pendências e do gate, incluindo o retorno esperado do CLI. A inspeção visual efetiva está documentada separadamente.

Também foram reforçadas a consulta real por ID, a ausência de ciclos na cadeia consultada, a navegação por identificadores, a geometria e os limites de offsets, os recortes literais de página/bloco e a correspondência de origens dos 14 registros com a revisão histórica.

Nenhuma regra geral de extração, normalização ou classificação foi alterada.

## Hierarquia e escopo

Seção `node_e1ee2dbacf6a8b0f6eeb1181`, nível 3, subordinada ao capítulo `node_01abfd94af1f8ecc7a287936`. O título e sua origem `p000007_b00000` foram conferidos.

O intervalo 28–41 é o conteúdo diretamente vinculado à seção antes da subseção filha **Boa estória bem contada**, nó `node_4f9c6d35163293a95053c9e4`, nível 4, na página local 11. Essa fronteira não é o término de toda a subárvore da seção de nível 3. Nenhum conteúdo da Tarefa 004 foi aprovado nesta auditoria.

As ligações 27↔28 e 41↔42 e todos os vínculos internos foram verificados. Os registros 33 e 38 atravessam quebras de página. As origens e os mapas de normalização dos 14 registros passaram nas verificações efetivas.

Os destaques da seção são os registros 29 e 31, associados respectivamente a `quote_67b255a099f146c5685452dd` e `quote_afd064fbbd3783bc06c70819`. Suas representações em `elements.jsonl` são referências ao texto dos parágrafos, não novas cópias primárias. Suas revisões individuais permanecem pendentes.

## PDF e preservação

O recorte possui 18 páginas e SHA-256 `dabd10538ffdc866c6fa24187ffb1b9f784f647a01d5286a9c6a91cd7015633d`. A cópia `original.pdf` coincide com ele.

As cinco páginas locais 7–11 foram renderizadas com Poppler a 120 dpi e efetivamente inspecionadas. O título, os limites diretos, as quebras, a ordem dos registros e o pertencimento dos dois destaques foram confrontados com os dados. O registro visual detalhado está em `visual_inspection.json` e o mapa dos registros em `mapeamento.md`.

Todos os arquivos do corpus e do histórico, todos os arquivos de evidência originais, o PDF e o código de produção permaneceram idênticos aos bytes recebidos. O hash da implementação de produção coincide com o registrado nos metadados do corpus. O relatório salvo coincide semanticamente com a revalidação atual.

Essa preservação é demonstrada **desde o recebimento do ZIP nesta auditoria**. Não foi reconstruído um estado do Mac anterior ao pacote recebido. O livro integral de 493 páginas não foi fornecido: sua ligação por `source_context` foi preservada como referência externa, sem nova certificação bibliográfica ou da paginação integral.

## Evidências anteriores

O manifesto recebido está correto quanto aos seus oito arquivos, tamanhos e hashes. Isso comprova a integridade daqueles arquivos, não a veracidade de todas as declarações neles contidas.

O log original contém uma execução real com 11 testes aprovados, seguida de linhas declarativas anexadas por `echo`. Não contém a saída integral que comprovaria os 90 testes da suíte geral alegados no relatório anterior. A nova execução coletou 101 casos e executou todos eles; não reutiliza a alegação anterior como evidência.

Os registros anteriores foram preservados. O resultado desta auditoria é uma nova evidência, com horários e saídas próprios.

## Ambiente e reprodução

Execução nesta auditoria: Linux, Python 3.12.14, PyMuPDF 1.26.7 e pytest 8.4.2, com as dependências fixadas do projeto em diretório isolado. O log local anterior usava macOS e Python 3.12.10. Os resultados novos não são apresentados como uma execução realizada no Mac.

Os comandos exatos, ambiente, horários, códigos de retorno e saídas integrais constam em `commands.jsonl` e nos logs numerados. Os resumos de testes foram extraídos dos arquivos JUnit XML, não inseridos como aprovações por texto manual.

Para integrar o pacote, use a pasta do projeto no Mac como destino: o ZIP contém o teste corrigido em `tests/test_tarefa_003.py` e uma pasta nova de evidências em `execution_evidence/tarefa-003/auditoria-independente/`. Ele não contém substitutos dos arquivos do corpus de trabalho. Preserve qualquer alteração local posterior ao ZIP enviado antes de substituir o teste.

No ambiente local já configurado, os comandos de confirmação são:

```bash
.venv/bin/python -m pytest -q tests/test_tarefa_003.py
.venv/bin/python -m pytest -q
```

## Integridade do pacote e conclusão

O manifesto novo cobre os arquivos finais desta auditoria, incluindo o teste corrigido, os originais recebidos selecionados, logs, XMLs, fonte do recorte e registros de inspeção. Exclui somente o próprio manifesto e os comprovantes de sua verificação para evitar autorreferência. O verificador independente confere presença, arquivos inesperados, tamanho e SHA-256 e retorna código diferente de zero diante de divergência.

O comprovante final registra o hash do manifesto e o resultado efetivamente obtido. A validação operacional é `verified_existing`; o estado documental continua `review_required`. Nenhuma aprovação humana foi concedida, nenhum destaque foi aprovado e o chunking permanece bloqueado. A Tarefa 004 não foi iniciada.
