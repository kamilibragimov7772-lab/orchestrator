# Orchestrator — uma stack de orquestração verificável para Claude Code

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

Transforma uma sessão do Claude Code em um orquestrador: um briefing vira um plano de ondas,
cada onda executa subagentes especializados, cada onda entrega um arquivo, e um revisor
independente aceita ou rejeita o resultado. 41 fichas de agente, 10 contratos compartilhados,
10 slash commands e 4 skills opcionais.

Licença MIT. Autor: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**. Protocolo **2.16.0**.

> **Leia isto primeiro — o idioma.** O protocolo de orquestração, as fichas de agente e os
> critérios de aceitação estão escritos **em russo**. As ferramentas, os testes, a instalação e
> os comentários do código estão em inglês. Se você quer os agentes em si, vai ler Markdown em
> russo. Se você quer o encanamento que torna uma stack de agentes confiável, essa parte
> independe de idioma — e é a razão de este repositório existir.

---

## Por que isto existe

Não faltam coleções de subagentes para Claude Code. Faltam as que dá para verificar. A maioria
é uma pasta de arquivos Markdown: nada prova que os hooks disparam, nada prova que o scanner de
segredos olha os bytes certos, e nada falha quando uma verificação para de verificar em silêncio.

Este repositório faz o trade-off oposto. A biblioteca de agentes é comum; **o encanamento em
volta dela é o ponto**:

| O que a maioria entrega | O que este entrega |
|---|---|
| Só o Markdown dos agentes | Agentes **mais** guards, instalador, doctor, portão de aceitação, sync |
| Sem testes | **97 testes**, só biblioteca padrão, sem chamadas de API, sem rede |
| «Adicione isto ao settings.json» | Instalador com preflight de colisões; **o doctor roda o guard de verdade** e exige que ele bloqueie |
| Presume-se que os hooks funcionam | Smoke test de três payloads: benigno tem de passar, segredo tem de bloquear, comando perigoso tem de bloquear |
| «É seguro, confie no prompt» | Texto de prompt nunca é tratado como fronteira de acesso — veja [SECURITY.md](SECURITY.md) |

Tudo o que um script consegue verificar é verificado por um script, porque uma regra que só vive
num prompt é uma regra que deixa de ser seguida sem avisar.

---

## Início rápido

Requer **Python 3.10+** e **Git**. Sem API key, sem rede, sem chamadas ao modelo:

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

Isso roda o linter de contratos de agente, o autoteste do contador de prontidão, a suíte
completa e uma varredura de segredos. Não toca em nada fora do checkout.

Instale em diretórios que você escolhe — o instalador **planeja antes e nunca sobrescreve**:

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

Revise o plano e rode de novo com `--apply`. Se algum arquivo de destino existir e for
diferente, a instalação para e preserva o seu. Depois confirme o resultado:

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal` instala sete papéis para pesquisa e entregáveis em Markdown. `full` acrescenta os
pipelines de software / sites / mídia e suas dependências externas. Notas de Windows e como
apontar o Claude Code para o novo diretório: [INSTALL.md](INSTALL.md).

---

## O que vem na caixa

| Camada | Para que serve | Fronteira de verificação |
|---|---|---|
| `_orchestr_protocol.md`, `agents/`, `commands/` | Roteamento, contratos, definition of done | O linter checa estrutura; a qualidade da resposta exige aceitação humana |
| `tools/verify.py`, `tests/` | Um comando reproduzível, com casos negativos | Sem API do Claude, sem MCP externo |
| `tools/guard.py` | Detecção em PreToolUse de credenciais e comandos destrutivos | **Defesa em profundidade heurística** — mantenha permissões e sandbox do host |
| `tools/install.py`, `tools/doctor.py` | Instalação não destrutiva; relatório de prontidão | O doctor não testa autenticação nem qualidade do modelo |
| `tools/acceptance-gate/` | Checagens determinísticas do run-log mais um worker revisor opcional | O worker de modelo vem **desligado**; end-to-end não certificado |
| `tools/sync_stack.py` | Ponte Git sobre uma allowlist exata | Opcional; recusa-se a mesclar branches divergentes por você |
| `tools/export_session.py` | Exportação de transcrições opt-in | **Desligada**; a redação é por padrões, não é garantia de privacidade |

### O portão de aceitação

A ideia que mais demorou a ficar certa. Quando uma execução fecha, um **contexto separado** —
que nunca viu o raciocínio do orquestrador — julga o entregável contra o briefing. Um script
determinístico roda primeiro e o modelo só julga o que o script não consegue:

- `run_status` e `verdict` são campos distintos. Uma execução que não está `done` retorna
  *«não sujeita a aceitação»*, não um falso aprovado.
- `SKIP` gera **«incompleto»**, nunca «aceito». Um PDF é reportado como *só a assinatura —
  abra num leitor*; um `.docx` como *a estrutura faz parse, a aceitação visual é à parte*.
- Os códigos de saída são distintos: `0` aceito · `1` rejeitado · `3` incompleto ·
  `4` não aplicável · `2` erro.

O motivo, medido pelo autor em 259 execuções: uma regra que entrou num validador se sustenta de
76% a 100% das vezes; a mesma regra como texto de prompt, de 0% a 39%.

---

## O que ele deliberadamente não faz

Confiança é, em grande parte, uma lista de coisas que a ferramenta se recusa a fazer pelas suas costas:

- **Nenhuma exportação, espelhamento, push de Git, cron ou processo de modelo automáticos na
  instalação.** Cada um deles é opt-in e exige configuração explícita.
- **Nada de espelhamento no estilo `robocopy /MIR`.** Ele podia apagar no destino arquivos que
  não estavam na origem. Foi removido.
- **Não sobrescreve.** Arquivos em conflito interrompem a instalação; suas settings e hooks são
  mesclados, não substituídos.
- **Nada de aprovação silenciosa.** Uma dependência ausente ou uma checagem não executada
  reportam `NOT CHECKED` ou `SKIP`. Nunca reporta um aprovado que não conquistou.
- **Nenhuma nota que não tenha provado.** Um «9,5/10» foi a meta e **não foi certificado** — os
  itens em aberto estão listados em [`audit_9_5/`](audit_9_5/), não diluídos numa média.

---

## Status de verificação

O CI roda Windows / Linux / macOS × Python 3.10 e 3.12, faz parse de todos os scripts PowerShell
e varre **todo o histórico do Git** com Gitleaks. Veja [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Limites honestos, porque um selo verde não é evidência:

- Os testes cobrem o comportamento das ferramentas, não a qualidade do que os agentes escrevem.
- A aceitação end-to-end com modelo real **não** está coberta pela suíte.
- Os guards são heurísticos. Complementam as permissões do host; não as substituem.

---

## Documentação

| Arquivo | O que responde |
|---|---|
| [INSTALL.md](INSTALL.md) | Instalação, ligação ao Claude Code, especificidades do Windows |
| [AGENTS.md](AGENTS.md) | Ponto de entrada para trabalhar neste código |
| [SECURITY.md](SECURITY.md) | O que os guards protegem e o que não; privacidade da exportação |
| [CONTRIBUTING.md](CONTRIBUTING.md) | As verificações que uma mudança precisa passar |
| [CHANGELOG.md](CHANGELOG.md) | Mudanças de comportamento |

## Base metodológica

Referência de engenharia: **NIST SSDF 1.1** (NIST, 2022) — reproduzir um defeito, corrigi-lo e
adicionar uma regressão que rejeite o caso quebrado — junto com a documentação oficial do host
([Claude Code hooks](https://code.claude.com/docs/en/hooks)). Verificado em 2026-09-06. O SSDF é
usado para selecionar riscos, não como certificado de conformidade.

## Licença

[MIT](LICENSE). Autor: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**.
