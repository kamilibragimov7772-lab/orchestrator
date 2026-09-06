# Orchestrator — un stack de orquestación verificable para Claude Code

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

Convierte una sesión de Claude Code en un orquestador: un briefing se transforma en un plan de
oleadas, cada oleada ejecuta subagentes especializados, cada oleada aterriza como un archivo y
un revisor independiente acepta o rechaza el resultado. 41 fichas de agente, 10 contratos
compartidos, 10 slash commands y 4 skills opcionales.

Licencia MIT. Autor: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**. Protocolo **2.16.0**.

> **Lee esto primero — el idioma.** El protocolo de orquestación, las fichas de agente y los
> criterios de aceptación están escritos **en ruso**. Las herramientas, los tests, la
> instalación y los comentarios del código están en inglés. Si lo que buscas son los agentes,
> vas a leer Markdown en ruso. Si lo que buscas es la fontanería que hace confiable a un stack
> de agentes, esa parte es independiente del idioma y es la razón de existir de este repo.

---

## Por qué existe

No faltan colecciones de subagentes para Claude Code. Lo que falta son las que puedes
verificar. La mayoría es una carpeta de archivos Markdown: nada demuestra que los hooks se
disparan, nada demuestra que el escáner de secretos mira los bytes correctos, y nada falla
cuando una comprobación deja de comprobar en silencio.

Este repo hace el trade-off contrario. La biblioteca de agentes es corriente; **lo que importa
es la fontanería que la rodea**:

| Lo que envían casi todas | Lo que envía este repo |
|---|---|
| Solo Markdown de agentes | Agentes **más** guards, instalador, doctor, puerta de aceptación, sync |
| Sin tests | **97 tests**, solo librería estándar, sin llamadas a API, sin red |
| «Añade esto a settings.json» | Instalador con preflight de colisiones; **doctor ejecuta el guard de verdad** y exige que bloquee |
| Se asume que los hooks funcionan | Smoke test de tres payloads: benigno debe pasar, secreto debe bloquear, comando peligroso debe bloquear |
| «Es seguro, confía en el prompt» | El texto del prompt nunca se trata como frontera de acceso — ver [SECURITY.md](SECURITY.md) |

Todo lo que puede comprobar un script lo comprueba un script, porque una regla que solo vive en
un prompt es una regla que deja de cumplirse sin avisar.

---

## Inicio rápido

Requiere **Python 3.10+** y **Git**. Sin API key, sin red, sin llamadas al modelo:

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

Eso ejecuta el linter de contratos de agente, el autotest del contador de preparación, la suite
completa y un escaneo de secretos. No toca nada fuera del checkout.

Instala en directorios que elijas tú — el instalador **primero planifica y nunca sobrescribe**:

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

Revisa el plan y vuelve a ejecutarlo con `--apply`. Si algún archivo destino existe y difiere,
la instalación se detiene y conserva el tuyo. Después confirma el resultado:

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal` instala siete roles para investigación y entregables en Markdown. `full` añade los
pipelines de software / sitios web / medios y sus dependencias externas. Notas de Windows y
cómo apuntar Claude Code al nuevo directorio: [INSTALL.md](INSTALL.md).

---

## Qué incluye

| Capa | Para qué sirve | Frontera de verificación |
|---|---|---|
| `_orchestr_protocol.md`, `agents/`, `commands/` | Enrutado, contratos, definition of done | El linter revisa estructura; la calidad de la respuesta exige aceptación humana |
| `tools/verify.py`, `tests/` | Un comando reproducible, con casos negativos | Sin API de Claude, sin MCP externo |
| `tools/guard.py` | Detección en PreToolUse de credenciales y comandos destructivos | **Defensa en profundidad heurística** — conserva permisos y sandbox del host |
| `tools/install.py`, `tools/doctor.py` | Instalación no destructiva; informe de preparación | Doctor no prueba autenticación ni calidad del modelo |
| `tools/acceptance-gate/` | Chequeos deterministas del run-log más un worker revisor opcional | El worker de modelo está **desactivado por defecto**; end-to-end no certificado |
| `tools/sync_stack.py` | Puente Git sobre una allowlist exacta | Opcional; se niega a fusionar ramas divergentes por ti |
| `tools/export_session.py` | Exportación de transcripciones opt-in | **Desactivada**; el redactado se basa en patrones, no es una garantía de privacidad |

### La puerta de aceptación

La idea que más costó dejar bien. Cuando una ejecución cierra, un **contexto separado** — que
nunca vio el razonamiento del orquestador — juzga el entregable contra el briefing. Primero
corre un script determinista y el modelo solo juzga lo que el script no puede:

- `run_status` y `verdict` son campos distintos. Una ejecución que no está `done` devuelve
  *«no sujeta a aceptación»*, no un aprobado falso.
- `SKIP` produce **«incompleto»**, nunca «aceptado». Un PDF se reporta como *solo firma —
  ábrelo en un visor*; un `.docx` como *la estructura parsea, la aceptación visual va aparte*.
- Los códigos de salida se distinguen: `0` aceptado · `1` rechazado · `3` incompleto ·
  `4` no aplicable · `2` error.

El motivo, medido por el autor sobre 259 ejecuciones: una regla que llega a un validador se
cumple entre el 76% y el 100% de las veces; esa misma regla como texto de prompt, entre 0% y 39%.

---

## Lo que deliberadamente no hace

La confianza es, sobre todo, una lista de cosas que una herramienta se niega a hacer a tus espaldas:

- **Ninguna exportación, réplica, push a Git, cron o proceso de modelo automáticos al instalar.**
  Todo eso es opt-in y requiere configuración explícita.
- **Nada de réplicas estilo `robocopy /MIR`.** Podían borrar en el destino archivos que no
  estaban en el origen. Se eliminó.
- **No sobrescribe.** Los archivos en conflicto detienen la instalación; tus settings y hooks se
  fusionan, no se reemplazan.
- **Nada de aprobados silenciosos.** Una dependencia ausente o una comprobación no ejecutada
  reportan `NOT CHECKED` o `SKIP`. Nunca reporta un aprobado que no se ganó.
- **Ninguna nota que no haya demostrado.** Se apuntó a un «9,5/10» y **no está certificado** —
  los puntos abiertos están listados en [`audit_9_5/`](audit_9_5/), no diluidos en una media.

---

## Estado de verificación

CI corre Windows / Linux / macOS × Python 3.10 y 3.12, parsea todos los scripts PowerShell y
escanea **todo el historial de Git** con Gitleaks. Ver [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Límites honestos, porque una insignia verde no es evidencia:

- Los tests cubren el comportamiento de las herramientas, no la calidad de lo que escriben los agentes.
- La aceptación end-to-end con modelo real **no** está cubierta por la suite.
- Los guards son heurísticos. Complementan los permisos del host; no los sustituyen.

---

## Documentación

| Archivo | Qué responde |
|---|---|
| [INSTALL.md](INSTALL.md) | Instalación, conexión con Claude Code, particularidades de Windows |
| [AGENTS.md](AGENTS.md) | Punto de entrada para trabajar en este código |
| [SECURITY.md](SECURITY.md) | Qué protegen y qué no protegen los guards; privacidad de la exportación |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Las comprobaciones que debe pasar un cambio |
| [CHANGELOG.md](CHANGELOG.md) | Cambios de comportamiento |

## Base metodológica

Referencia de ingeniería: **NIST SSDF 1.1** (NIST, 2022) — reproducir un defecto, corregirlo y
añadir una regresión que rechace el caso roto — junto con la documentación oficial del host
([Claude Code hooks](https://code.claude.com/docs/en/hooks)). Verificado el 2026-09-06. SSDF se
usa para seleccionar riesgos, no como certificado de conformidad.

## Licencia

[MIT](LICENSE). Autor: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**.
