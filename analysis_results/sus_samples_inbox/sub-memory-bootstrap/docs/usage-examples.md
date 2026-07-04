# 사용 예제

이 문서는 `sub-memory`를 실제로 사용하는 예시를 모아 둔 문서입니다. 예시는 로컬 에이전트 실행, CLI 연동, 그리고 Codex skill 사용 예시까지 포함합니다.

## 1. 로컬 에이전트 바로 실행

```bash
source .venv/bin/activate
sub-memory-agent
```

예시:

```text
You> 지난주 출장에서 정리한 TODO 기억해?
AI> 지난 대화 기록 기준으로 출장 관련 메모를 먼저 불러와서 정리해보면 ...
```

이 흐름에서는 런타임이 자동으로 다음을 수행합니다.

- 답변 전 `recall_associated_memory`
- 답변 후 `store_memory`
- 필요 시 `reinforce_memory`
- 세션이 길어지면 오래된 턴을 compact summary로 축약

## 2. Codex에서 MCP 연결 후 사용하는 예시

목표:

- 코드 수정 전 과거 메모를 참조
- 작업 후 새 결정을 메모에 저장

예시 요청:

```text
Before answering, use the sub_memory MCP tools to recall any prior notes about this repo, then summarize what matters for today's task.
```

한글 예시 요청:

```text
답변하기 전에 sub_memory MCP 도구로 이 저장소와 관련된 이전 메모를 먼저 찾아보고, 오늘 작업에 필요한 내용만 짧게 정리해줘.
```

읽기 전용 시작 예시:

```text
Use get_memory_status and recall_associated_memory only. Do not store or reinforce anything yet.
```

한글 읽기 전용 예시:

```text
지금은 get_memory_status와 recall_associated_memory만 사용하고, 저장이나 강화는 하지 마.
```

쓰기까지 허용하는 예시:

```text
Use sub_memory to recall prior notes, complete the task, then store the final user/assistant exchange if it changed implementation decisions.
```

한글 쓰기 허용 예시:

```text
sub_memory로 관련 메모를 먼저 찾아서 작업을 진행하고, 구현 결정이 바뀌었다면 마지막 사용자/어시스턴트 대화를 저장해줘.
```

## 3. Gemini CLI에서 사용하는 예시

예시 요청:

```text
Recall any prior memory related to MCP integration in this repo, then explain the current setup status and missing pieces.
```

한글 예시 요청:

```text
이 저장소의 MCP 연동과 관련된 이전 메모가 있으면 먼저 찾아보고, 현재 설정 상태와 아직 비어 있는 항목을 설명해줘.
```

운영 팁:

- `GEMINI.md`에 “관련 과거 맥락이 있으면 먼저 sub_memory recall 수행” 규칙을 넣어두면 반복 지시를 줄일 수 있습니다.

## 4. Claude Code에서 사용하는 예시

예시 요청:

```text
Use the sub-memory MCP server to recall previous design decisions about this project before reviewing the code.
```

한글 예시 요청:

```text
코드 리뷰를 시작하기 전에 sub-memory MCP 서버로 이 프로젝트의 이전 설계 결정을 먼저 찾아서 참고해줘.
```

리뷰 전에 유용한 예시:

```text
Check get_memory_status first, then recall memory about agent integration and use that context during the review.
```

한글 리뷰 예시:

```text
먼저 get_memory_status로 연결 상태를 확인하고, 에이전트 연동 관련 메모를 찾아서 그 내용을 리뷰에 반영해줘.
```

## 5. 설치형 Skill을 사용하는 예시

Skill 설치 후 Codex에서 아래처럼 요청하면 온보딩을 한 번에 밀 수 있습니다.
이 흐름에서는 로컬 설치뿐 아니라 project-local `.codex/config.toml`와 `AGENTS.md`도 함께 준비됩니다.

### 예시 A: 첫 설치

```text
Use sub-memory-bootstrap to set up this repository locally, verify the install, and show me the exact Codex/Gemini/Claude MCP snippets for this machine.
```

```text
sub-memory-bootstrap을 사용해서 이 저장소를 로컬에 설치하고, 설치 검증까지 한 뒤, 현재 머신 기준 Codex/Gemini/Claude MCP 설정 스니펫을 보여줘.
```

공용 MCP 신규 설치형:

```text
$skill-installer https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git --path .
sub-memory-bootstrap으로 <project-dir> 에 공용 sub-memory MCP를 신규 설치해줘. shared MCP daemon 방식으로 맞추고 project-local Codex 설정까지 반영해줘.
```

### 예시 B: 재검증

```text
Use sub-memory-bootstrap to validate the existing installation and tell me whether the shared MCP daemon is running and which URL this repo should use.
```

```text
sub-memory-bootstrap으로 기존 설치 상태를 다시 점검하고, 공용 MCP 서버가 떠 있는지와 이 저장소가 써야 할 URL을 알려줘.
```

공용 MCP 업데이트형:

```text
sub-memory-bootstrap으로 <project-dir> 의 공용 sub-memory MCP 설정을 업데이트해줘. 먼저 현재 checkout을 최신으로 맞추고, 그 다음 의존성, project-local Codex 설정, shared MCP daemon 을 다시 맞춰줘.
```

### 예시 C: 문서화 포함

```text
Use sub-memory-bootstrap to inspect this repo, verify the local install path, and draft a short onboarding note for another engineer.
```

```text
sub-memory-bootstrap으로 이 저장소를 점검하고, 로컬 설치 경로를 확인한 뒤, 다른 개발자에게 전달할 짧은 온보딩 메모를 작성해줘.
```

온보딩 후 새 Codex 세션 예시:

```text
이 저장소의 기존 설계 결정을 먼저 기억에서 확인한 뒤 오늘 작업 계획을 정리해줘.
```

위 흐름은 `AGENTS.md`와 project-local Codex MCP 설정이 함께 로드된 새 세션에서 가장 잘 동작합니다.
이때 Codex는 `local_agent`와 비슷하게 답변 전 recall, 답변 후 store, 필요 시 reinforce, 장문 멀티턴 시 compact summary 흐름을 따르도록 유도됩니다.

## 6. compact를 염두에 둔 멀티턴 예시

대화가 길어질수록 원문 전체를 계속 들고 가면 토큰이 빠르게 늘어납니다.
이때 `sub_memory`가 있으면 모든 원문을 그대로 유지하지 않아도, 중요한 결정은 다시 recall할 수 있습니다.

예시 요청:

```text
이 대화가 길어지면 전체 원문을 계속 유지하지 말고, 적절한 시점에 compact summary를 만들고 sub_memory recall을 같이 사용해서 이어가자.
```

한글 실전형 예시:

```text
이제부터 멀티턴이 길어지면 작업 상태를 짧게 compact해서 이어가고, 예전 결정은 필요할 때 sub_memory에서 다시 불러와줘.
```

코드 작업형 예시:

```text
작업이 길어지면 현재 결정사항, 남은 TODO, 주의점만 compact summary로 유지하고, 이전 구현 배경은 sub_memory로 recall해서 이어가줘.
```

이 흐름이 의미하는 것은 아래와 같습니다.

1. 최근 몇 턴만 비교적 자세히 들고 갑니다.
2. 오래된 세션 내용은 짧은 working summary로 줄입니다.
3. 장기 맥락은 `memory.db`에서 다시 recall합니다.

즉, compact는 “기억을 버리는 것”이 아니라 “프롬프트에 항상 싣는 원문 양을 줄이는 것”에 가깝습니다.

## 7. 자주 쓰는 점검 예시

### MCP 엔트리포인트 확인

```bash
sub-memory-mcp --help
```

### 공용 MCP 데몬 상태 확인

```bash
skills/sub-memory-bootstrap/scripts/manage_mcp_daemon.sh status "$(pwd)"
```

### 에이전트 엔트리포인트 확인

```bash
sub-memory-agent --help
```

### 테스트 실행

```bash
python -m unittest discover -s tests
```

### 메모리 DB 경로와 노드 수 확인

이 항목은 MCP가 연결된 뒤 `get_memory_status` tool로 조회합니다.

예시 요청:

```text
Call get_memory_status and tell me which memory.db file this repo is using.
```

한글 예시 요청:

```text
get_memory_status를 호출해서 이 저장소가 어떤 memory.db 파일을 쓰고 있는지 알려줘.
```

## 8. 안전한 운영 순서

권장 순서는 아래와 같습니다.

1. `get_memory_status`로 현재 연결 상태 확인
2. `recall_associated_memory`만 열어 읽기 위주 검증
3. 실제로 도움이 되는지 확인
4. 그 다음 `store_memory`
5. 마지막으로 `reinforce_memory`

이 순서로 가면 초기에 불필요한 쓰기나 가중치 누적을 피할 수 있습니다.

추가 운영 주의:

- `sub-memory-mcp`를 세션마다 직접 띄우는 방식은 피하는 편이 좋습니다.
- 각 세션이 모델과 메모리 서비스를 따로 적재하면 메모리 사용량이 커지고, 같은 `memory.db`를 두고 락 경합이 생길 수 있습니다.
- 가능하면 공용 MCP 데몬 1개를 유지하고, 모든 세션이 같은 MCP URL을 사용하도록 맞추는 것이 안전합니다.
