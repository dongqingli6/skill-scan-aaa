# Getting Started

이 문서는 `sub-memory`를 로컬에 설치하고, 공용 MCP 서버를 한 번 띄운 뒤 `Codex`, `Gemini CLI`, `Claude Code`가 같은 endpoint를 바라보도록 연결하는 가장 짧은 시작 경로를 정리합니다.

범위는 로컬 설치, 공용 MCP 서버, Web UI, CLI 연동까지입니다. 앱 연동(`ChatGPT 앱`, `Gemini 앱`, `Claude 앱`)은 현재 TODO로 남겨둡니다.

## 1. 준비 사항

- Python `3.10+`
- macOS 기준 권장 버전: `python3.11`
- 로컬에서 로드 가능한 `sqlite-vec`
- OpenAI API Key
  - `sub-memory-agent` 실행 시 필요
  - `sub-memory-mcp`와 `sub-memory-web`만 사용할 때는 없어도 됨

## 2. 로컬 설치

프로젝트 루트에서 실행합니다.

먼저 `sub-memory-bootstrap` 스킬을 전역에 설치하거나 업데이트합니다.

```text
$skill-installer https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git --path .
```

설치 직후에는 `Restart Codex to pick up new skills.`를 수행한 뒤, 이 저장소 루트에서 아래를 실행합니다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
mkdir -p ~/.codex/sub-memory
cp .env ~/.codex/sub-memory/.env
```

`.env` 파일에서 필요한 값을 채웁니다.

```dotenv
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-5-mini
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
SQLITE_VEC_PATH=
RECALL_DEPTH=2
RECALL_LIMIT=6
MEMORY_DB_PATH=memory.db
COMPACT_AFTER_TURNS=4
COMPACT_KEEP_RECENT_TURNS=2
COMPACT_SUMMARY_CHAR_LIMIT=2400
METRICS_LOG_PATH=.sub-memory/metrics.jsonl
METRICS_RETENTION_DAYS=30
```

compact 관련 기본값 의미:

- `COMPACT_AFTER_TURNS`
  - 이 횟수만큼 substantive turn이 쌓이면 오래된 세션 내용을 compact 후보로 봅니다.
- `COMPACT_KEEP_RECENT_TURNS`
  - compact 후에도 원문에 가깝게 남겨둘 최근 턴 수입니다.
- `COMPACT_SUMMARY_CHAR_LIMIT`
  - compact된 working summary의 최대 길이입니다.

## 3. 설치 확인

```bash
sub-memory-agent --help
sub-memory-mcp --help
sub-memory-web --help
python -m unittest discover -s tests
```

정상 설치되면 다음 세 엔트리포인트를 사용할 수 있습니다.

- `sub-memory-agent`
- `sub-memory-mcp`
- `sub-memory-web`

## 3A. 신규 설치와 업데이트를 분리해서 실행하기

신규 설치:

```bash
skills/sub-memory-bootstrap/scripts/install_shared_mcp.sh "$(pwd)"
```

업데이트:

```bash
git pull --ff-only
skills/sub-memory-bootstrap/scripts/update_shared_mcp.sh "$(pwd)"
```

이 스크립트의 책임은 아래와 같습니다.

- 공통 선행 조건: `sub-memory-bootstrap` 스킬이 이미 `~/.codex/skills`에 설치되어 있어야 함
- 신규 설치: 의존성 설치, project-local Codex 설정 생성, shared MCP daemon 기동
- 업데이트: 현재 checkout 기준 의존성 재설치, project-local Codex 설정 재생성, shared MCP daemon 재시작
- 둘 다 끝난 뒤에는 저장소 루트에서 새 Codex 세션을 시작하는 것이 가장 안전함

## 4. 공용 MCP 서버 시작

권장 방식은 공용 `streamable-http` MCP 데몬을 한 번 띄우고, 각 세션은 같은 URL을 바라보게 하는 것입니다.

```bash
python3 skills/sub-memory-bootstrap/scripts/configure_codex_project.py --project-dir "$(pwd)"
skills/sub-memory-bootstrap/scripts/manage_mcp_daemon.sh start "$(pwd)"
```

상태 확인:

```bash
skills/sub-memory-bootstrap/scripts/manage_mcp_daemon.sh status "$(pwd)"
```

종료:

```bash
skills/sub-memory-bootstrap/scripts/manage_mcp_daemon.sh stop "$(pwd)"
```

기본 MCP URL:

```text
http://127.0.0.1:8766/mcp
```

주의:

- 세션마다 `sub-memory-mcp`를 별도로 실행하는 방식은 권장하지 않습니다.
- 그렇게 하면 각 세션이 임베딩 모델과 메모리 서비스를 중복 적재하므로 메모리 사용량이 빠르게 늘어날 수 있습니다.
- 또한 동일한 `memory.db`에 대해 락 경합과 초기화 지연이 더 자주 발생할 수 있습니다.
- 운영 기준은 공용 MCP 데몬 1개를 유지하고, 모든 세션이 동일한 URL에 연결하는 것입니다.

`sub-memory-agent`는 별도로 최근 세션 턴을 모두 길게 유지하지 않습니다.
대신 오래된 세션 내용을 짧은 working summary로 compact하고, 최근 몇 턴과 `memory.db` recall을 함께 사용합니다.
그래서 멀티턴이 길어져도 토큰 사용량을 비교적 낮게 유지할 수 있습니다.

## 5. Codex 연결

project-local 설정 파일은 아래 경로에 생성됩니다.

- `.codex/config.toml`
- `AGENTS.md`

생성된 `Codex` 설정 예시는 아래 형태입니다.

```toml
[mcp_servers.sub_memory]
url = "http://127.0.0.1:8766/mcp"
enabled_tools = ["recall_associated_memory", "store_memory", "reinforce_memory", "get_memory_status"]
startup_timeout_sec = 30
tool_timeout_sec = 120
```

권장 초기 설정:

- 먼저 `get_memory_status`, `recall_associated_memory`만 열어 읽기 위주로 검증
- 검증 후 `store_memory`, `reinforce_memory`까지 확장

중요:

- 공용 MCP 서버를 띄운 뒤 새 Codex 세션을 시작해야 project-local 설정이 안정적으로 반영됩니다.

## 6. Gemini CLI와 Claude Code 연결

### Gemini CLI

```json
{
  "mcpServers": {
    "sub_memory": {
      "url": "http://127.0.0.1:8766/mcp",
      "timeout": 30000
    }
  }
}
```

### Claude Code

```bash
claude mcp add --transport http sub-memory http://127.0.0.1:8766/mcp
```

## 7. Web UI 실행

Web UI는 MCP와 별개 프로세스입니다. 보통 공용 MCP 서버를 먼저 띄운 뒤 Web UI를 실행합니다.

```bash
skills/sub-memory-bootstrap/scripts/start_web_ui.sh "$(pwd)"
```

브라우저 주소:

```text
http://127.0.0.1:8765/ui
```

## 8. 한 번에 처리하는 Codex Skill 제공 방식

Codex용 배포 저장소를 별도로 제공합니다.

- GitHub: `https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap`
- 목적: 로컬 설치, 공용 MCP 서버 기동, CLI 설정 스니펫 생성까지 한 번에 처리

### Skill 설치

배포 저장소는 루트에도 `SKILL.md`가 있으므로, 저장소 루트를 그대로 전역 Codex skill 디렉터리로 복사하거나 심볼릭 링크를 걸 수 있습니다.

`skill-installer`를 쓰는 경우에는 아래 둘 중 하나를 사용합니다.

```text
$skill-installer https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap/tree/main/skills/sub-memory-bootstrap
```

```text
$skill-installer https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git --path .
```

`--path .`는 전체 저장소를 skill 디렉터리에 설치합니다.
`--path skills/sub-memory-bootstrap`는 nested skill만 설치하지만, 첫 bootstrap 실행 시
`$CODEX_HOME/repos/sub-memory-bootstrap`
또는 `~/.codex/repos/sub-memory-bootstrap` 아래에 전체 저장소 checkout을 자동으로 받아
동일한 설치 흐름을 이어갑니다.

수동 설치는 아래처럼 진행합니다.

```bash
git clone https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git
mkdir -p ~/.codex/skills
cp -R sub-memory-bootstrap ~/.codex/skills/sub-memory-bootstrap
```

또는:

```bash
git clone https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git
mkdir -p ~/.codex/skills
ln -s "$(pwd)/sub-memory-bootstrap" ~/.codex/skills/sub-memory-bootstrap
```

`CODEX_HOME`를 따로 쓰는 환경이라면 `~/.codex/skills` 대신 `$CODEX_HOME/skills` 아래에 두면 됩니다.

### Skill이 하는 일

- `scripts/bootstrap_local.sh`로 로컬 설치 자동화
- `scripts/manage_mcp_daemon.sh`로 공용 MCP 서버 기동/중지/상태 확인
- `scripts/configure_codex_project.py`로 project-local `.codex/config.toml` 생성
- `AGENTS.md`에 `sub_memory` 사용 규칙 managed block 반영
  - 답변 전 `recall_associated_memory`
  - 답변 후 `store_memory`
  - 필요 시 `reinforce_memory`
  - 긴 멀티턴에서는 compact summary로 active thread 축약
- `scripts/render_cli_snippets.py`로 현재 경로 기준 절대경로 설정 스니펫 생성
- `sub-memory-agent --help`, `sub-memory-mcp --help`, `sub-memory-web --help`, 테스트 명령으로 기본 검증 유도

### Skill 사용 예시

Codex에서 아래처럼 요청하면 됩니다.

```text
Use sub-memory-bootstrap to install this repo locally, start the shared MCP daemon, and generate Codex, Gemini CLI, and Claude Code config snippets.
```

또는:

```text
Use sub-memory-bootstrap to validate the local setup and tell me the shared sub-memory MCP URL for this repo.
```

한글로는 아래처럼 요청해도 됩니다.

```text
sub-memory-bootstrap을 사용해서 이 저장소를 로컬에 설치하고, 공용 MCP 서버를 시작한 뒤, Codex/Gemini/Claude용 MCP 설정 스니펫을 현재 머신 경로 기준으로 작성해줘.
```

```text
sub-memory-bootstrap으로 현재 설치 상태를 점검하고, 이 저장소가 바라보는 공용 sub-memory MCP URL을 알려줘.
```

Skill 실행이 끝나면 아래 두 파일이 준비됩니다.

- project-local Codex MCP 등록: `.codex/config.toml`
- 새 세션용 사용 규칙: `AGENTS.md`

따라서 `sub-memory-bootstrap`으로 온보딩한 뒤에는 저장소 루트에서 새 Codex 세션을 시작하는 것이 가장 안정적입니다.

### 자연어 요청 예시

신규 설치:

```text
$skill-installer https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git --path .
sub-memory-bootstrap으로 <project-dir> 에 공용 sub-memory MCP를 신규 설치해줘. 세션별 stdio가 아니라 shared MCP daemon 방식으로 맞추고, project-local Codex 설정까지 반영해줘.
```

업데이트:

```text
sub-memory-bootstrap으로 <project-dir> 의 공용 sub-memory MCP 설정을 업데이트해줘. 먼저 현재 checkout을 최신으로 맞추고, 그 다음 의존성, project-local Codex 설정, shared MCP daemon 을 다시 맞춰줘.
```

## 9. 다음 문서

- [사용 예제](./usage-examples.md)
- 상위 요약: [README.md](../README.md)
