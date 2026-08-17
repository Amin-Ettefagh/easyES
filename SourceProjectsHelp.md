

این‌ها را عمداً از پروژه‌های مشخصی که در تصویرت داری تکرار نکردم. پروژه‌هایی مثل LangGraph، CrewAI، AutoGen/AG2، OpenHands، Dify، Flowise، Langflow، LiteLLM، Langfuse، Phoenix، Activepieces، n8n، Plane، OpenProject، Odoo، ERPNext و غیره از قبل در فولدرهایت هستند. پروژه‌های بالا بخش‌های مهم دیگری مثل **durable execution، memory، sandbox، browser/computer use، integration fabric، authorization، realtime communication و agent runtime** را پر می‌کنند. Temporal برای Workflowهای durable و retry مناسب است، Hatchet برای background task/agent orchestration، Nango برای integrationها، MCP برای قرارداد Toolها و E2B برای اجرای ایزوله Agentها اهمیت ویژه دارند. ([GitHub][1])

# حالا کل چیزی که داری، دقیقاً کجای پروژه ما به درد می‌خورد؟

بهترین روش این است که ریپوها را نه به‌عنوان «محصول آماده»، بلکه به‌عنوان **R&D Reference برای هر Subsystem از easyES** ببینی.

---

## 1. Agent Definition / Agent Framework

### `CrewAI`

تعریف Agent، Role، Goal، Tool و Crew و همکاری چند Agent.

**برای ما:** طراحی `Actor → Agent → Role → Goal → Delegation`.

---

### `AutoGen`

Multi-Agent Conversation و تعامل Agentها.

**برای ما:** الگوی:

```text
Agent
↕
Agent
↕
Human
```

و Group Conversation.

---

### `AG2`

ادامه اکوسیستم AutoGen با تمرکز بیشتر روی سیستم‌های Agentic.

**برای ما:** بررسی مدل Conversation، Agent hierarchy، tools و human-in-the-loop.

---

### `CAMEL`

Framework تحقیقاتی Multi-Agent و Role Playing.

**برای ما:** فوق‌العاده مهم برای:

```text
Role
Persona
Society
Agent Communication
Task Delegation
```

---

### `LangChain`

Primitiveهای عمومی AI Application.

**برای ما:** بیشتر Reference برای:

```text
Model
Tool
Retriever
Prompt
Chain
Callback
```

نه Core سیستم.

---

### `LangGraph`

یکی از مهم‌ترین ریپوهای موجودت.

Agent را به State Machine/Graph تبدیل می‌کند.

**برای ما:**

```text
Node
Edge
State
Condition
Loop
Human Approval
Checkpoint
Resume
```

مخصوصاً همان چیزی که پرسیدی:

```text
Build
↓
Test
↓
Failed?
├─ Yes → Fix → Test ↺
└─ No → Continue
```

---

### `LangGraphJS`

همان ایده LangGraph برای TypeScript.

برای بررسی API Design سمت Node/TS مهم است.

---

### `PydanticAI` — جدید

Agent Framework با Typed Input/Output و ساختار Production-oriented. ([GitHub][2])

**خیلی مهم برای ما:**

```text
Agent Contract
Structured Output
Tool Contract
Dependency
Validation
Human Approval
```

---

### `Pydantic AI Harness` — جدید

Capability Library رسمی Pydantic AI است و قابلیت‌هایی مثل Tool/Search و building blocks برای تبدیل Agent عمومی به Agent تخصصی ارائه می‌دهد. ([GitHub][3])

**برای ما:** Reference عالی برای همان مفهوم:

```text
Actor
+
Capability
+
Skill
```

---

### `Mastra` — جدید

Framework کامل TypeScript برای Agents + Workflows + Memory و اجرای Production. ([GitHub][4])

**برای ما:** یکی از مهم‌ترین Referenceهای جدید، مخصوصاً اگر Backend بخشی TS باشد.

---

### `smolagents` — جدید

Agent Framework بسیار مینیمال HuggingFace. ([GitHub][5])

**برای ما:** بفهمیم Minimum Primitive واقعی یک Agent چیست و سیستم را Over-engineer نکنیم.

---

# 2. AI Company / Multi-Agent Organization

### `MetaGPT`

ایده بسیار نزدیک به پروژه ما.

Software Company را به Multi-Agent System تبدیل می‌کند:

```text
PM
Architect
Engineer
QA
...
```

**برای ما:** Organization Simulation + SOP + Role Collaboration.

---

### `ChatDev`

یکی از مهم‌ترین R&Dهای تو.

یک Software Company مجازی با Agentهای دارای Role.

```text
CEO
CTO
Programmer
Tester
Reviewer
```

**برای ما:** بررسی lifecycle یک Project توسط یک سازمان Agent-based.

`ChatDev` و `ChatDev-main` به احتمال زیاد دو کپی/نسخه از یک پروژه‌اند؛ لازم نیست هر دو را جدا R&D کنی.

---

### `agency-agents-main`

از اسم Folder نمی‌توانم upstream دقیقش را با اطمینان تعیین کنم؛ ولی اگر همان Agency Agents معروف باشد، مجموعه‌ای از تعریف Role/Personaهای تخصصی است.

**برای ما:** Agent Template / Role Template / Skill Template.

---

### `thebotcompany-main`

اسم Folder برای تشخیص upstream کافی نیست.

اگر همان پروژه Company-of-Agents مدنظر توست، قسمت مهمش الگوی Organization/Worker Collaboration است.

---

### `the-system-main`

از اسم فولدر upstream دقیق قابل تعیین نیست؛ برای جلوگیری از نسبت دادن اشتباه، این یکی را باید از URL گیت یا `git remote -v` تشخیص دهیم.

---

### `OpenFang` — جدید

این یکی را جدی بررسی کن.

خود پروژه آن را **Agent Operating System** معرفی می‌کند و Agentهای دائمی، schedule و autonomous execution دارد. ([GitHub][6])

**برای ما:**

```text
Agent Runtime
Persistent Agent
Daemon
Schedule
Agent Lifecycle
```

---

### `SwarmClaw` — جدید

Self-hosted Agent Runtime با:

```text
Agent
Swarm
Delegation
Memory
MCP
Skills
Schedule
```

است. ([GitHub][7])

**خیلی نزدیک به Control Plane بخشی از سیستم ماست.**

---

### `Dapr Agents` — جدید

برای Agentهای resilient و stateful و workflowهای قابل اطمینان ساخته شده است. ([GitHub][8])

برای ما مهم چون باید هزاران Agent را **واقعاً در Production** اجرا کنیم، نه فقط Demo.

---

# 3. Workflow / Process / Loop Engine

این قسمت برای پروژه ما فوق‌العاده حیاتی است.

### `n8n`

Workflow Visual Builder.

**برای ما:**

```text
Node
Trigger
Action
Condition
Integration
Loop
```

UI/UX آن بسیار ارزش بررسی دارد.

---

### `Activepieces`

مشابه n8n و Open Source Automation.

**برای ما:** Connector + Action + Trigger architecture.

---

### `Temporal` — جدید

یکی از مهم‌ترین پروژه‌هایی که نداشتی.

Durable Execution یعنی Workflow حتی اگر Worker/Server crash کند بتواند ادامه پیدا کند؛ retry و recovery نیز جزو مدل آن است. ([GitHub][1])

برای:

```text
Project
↓
Task
↓
Run
↓
Failure
↓
Retry
↓
Resume
```

فوق‌العاده مهم است.

**حتماً R&D عمیق.**

---

### `Hatchet` — جدید

Background tasks + AI agents + Durable Workflows + queues + retry + monitoring. ([GitHub][9])

برای Execution Engine ما Reference بسیار خوبی است.

---

### `Conductor` — جدید

Workflow Engine برای orchestration فرآیندهای distributed و agentic. نسخه فعال OSS در `conductor-oss/conductor` است. ([GitHub][10])

برای:

```text
Long Running Workflow
Task Dependencies
Retries
Events
Distributed Workers
```

---

### `Prefect` — جدید

Workflow orchestration مخصوصاً برای Python/Data؛ scheduling، retry و event automation دارد. ([GitHub][11])

برای Projectهای Data/Research/ML داخل easyES مفید است.

---

### `browser-use/workflow-use` — جدید

ترکیب جالبی از deterministic workflow و self-healing browser automation است. ([GitHub][12])

برای مفهوم:

```text
Normal Automation
↓ failure
AI Recovery
```

خیلی ارزش R&D دارد.

---

# 4. Agent Runtime / Execution

### `OpenHands`

AI Software Developer Runtime.

**برای ما بسیار مهم است.**

بررسی کن:

```text
Agent
Workspace
Terminal
Files
Browser
Runtime
Sandbox
Events
Conversation
```

نه صرفاً Agent Logic.

`OpenHands` و `OpenHands-main` احتمالاً duplicate هستند.

---

### `SWE-agent`

Agent برای حل Issueهای واقعی Software Engineering.

**برای ما:**

```text
Issue
→ Analyze
→ Edit
→ Test
→ Retry
→ Patch
```

دقیقاً نمونه Loop توسعه نرم‌افزار.

---

### `SWE-AF`

برای بررسی Software Agent Workflow/Factory.

---

### `software-agent-sdk`

اگر همان SDK معروف Software Agent باشد، بیشتر Interface اجرای Coding Agent ارزش دارد؛ upstream را از نام Folder به‌تنهایی نمی‌شود قطعی کرد.

---

### `aider`

AI Pair Programmer مبتنی بر Git.

**برای ما:** Human + AI Worker بسیار مهم است:

```text
Human
+
AI
+
Repository
```

---

### `Continue`

Open-source coding assistant/platform.

**برای ما:** اتصال AI Worker به IDE و Contextهای development.

---

# 5. Sandbox

### `E2B` — جدید

یکی از مهم‌ترین چیزهایی است که در لیستت کم بود.

Infrastructure برای اجرای Code تولیدشده توسط AI داخل Sandbox ایزوله. ([GitHub][13])

برای:

```text
AI Worker
↓
Sandbox
├─ Files
├─ Terminal
├─ Python
├─ Network
└─ Process
```

**حتماً R&D عمیق.**

---

### `E2B Code Interpreter`

تمرکز مستقیم روی اجرای Code در Sandbox دارد. ([GitHub][14])

برای `Execution Runtime` ما.

---

# 6. Browser / Computer Use

### `browser-use` — جدید

به Agent اجازه می‌دهد Browser را مثل انسان کنترل کند: کلیک، تایپ، فرم و navigation. ([GitHub][15])

برای سیستم ما Tool بسیار حیاتی است.

چون خیلی از سازمان‌ها API کامل ندارند.

---

### `qa-use` — جدید

Browser-use را برای QA و تست E2E استفاده می‌کند. ([GitHub][16])

دقیقاً برای:

```text
Developer AI
↓
Build
↓
QA AI
↓
Browser Test
↓
Fail
↓
Developer AI
↺
```

عالی است.

---

# 7. Tools / Connectors

### `MCP Servers` — جدید

MCP استاندارد اتصال AI به Tool و Data Source است. ([GitHub][17])

برای معماری ما:

```text
Actor
↓
Tool Interface
↓
MCP
↓
GitHub / DB / Slack / ...
```

باید یکی از Protocolهای First-Class باشد.

---

### `MCP Python SDK`

برای ساخت MCP Client/Server و expose کردن Tool، Resource و Prompt. ([GitHub][18])

---

### `awesome-mcp-servers`

خودش Engine نیست؛ Catalog بسیار بزرگ MCP Serverهاست. ([GitHub][19])

برای **Tool Marketplace R&D** فوق‌العاده است.

---

### `Nango` — جدید

یکی از مهم‌ترین ریپوهای لیست جدید.

Open-source integration platform است و صدها API را پوشش می‌دهد؛ Auth، execution، scaling و observability integrationها را مدیریت می‌کند. ([GitHub][20])

برای:

```text
Connector Registry
OAuth
Credential
API Integration
Sync
Action
Trigger
```

**حتماً عمیق بررسی کن.**

---

### `Nango Integration Templates`

Templateهای آماده integration. ([GitHub][21])

برای Marketplace/Connector Template.

---

# 8. AI Gateway / Model Layer

### `LiteLLM`

یکی از مهم‌ترین ریپوهای موجودت.

یک Interface مشترک برای Model Providerها.

برای:

```text
OpenAI
Claude
Gemini
Mistral
DeepSeek
Local
...
       ↓
Unified Model Gateway
```

---

### `ai-gateway`

بسته به upstream دقیق؛ هدف این دسته عموماً routing مدل‌هاست.

---

### `Portkey Gateway` — جدید

Gateway متن‌باز برای route کردن درخواست‌های AI میان تعداد زیادی Model و Provider، همراه با load balancing/guardrail capabilities. ([GitHub][22])

برای Model Gateway ما بسیار مرتبط است.

---

### `llm-cost-aware-gateway`

برای Routing بر اساس Cost.

در سیستم ما:

```text
Task
↓
Required Quality
Budget
Latency
↓
Model Router
```

---

### `LLM-Cost-Guardian`

کنترل Budget/Cost مدل‌ها.

برای Governance مالی Agentها.

---

# 9. Memory

### `Mem0` — جدید

Memory Layer مخصوص Agentها. ([GitHub][23])

برای:

```text
Actor Memory
User Memory
Agent Memory
Long-term Memory
```

**حتماً R&D.**

---

### `Graphiti` — جدید

Temporal Knowledge Graph برای Agentها؛ تغییر Factها در طول زمان و provenance را نگه می‌دارد. ([GitHub][24])

این برای easyES فوق‌العاده مهم است:

```text
Alice works in Team A

↓ بعداً

Alice moved to Team B
```

سیستم فقط Knowledge فعلی را نمی‌خواهد؛ **History دانش سازمان** هم مهم است.

---

# 10. Knowledge / RAG

### `LlamaIndex` — جدید

Data ingestion، indexing، retrieval و query building. ([GitHub][25])

برای:

```text
Organization Knowledge
Project Knowledge
Agent Context
RAG
Retrieval
```

---

### `Qdrant` — جدید

Vector DB برای semantic retrieval و vector search. ([GitHub][26])

برای Knowledge/Memory Retrieval.

---

### `Weaviate` — جدید

Vector/semantic database دیگر.

برای مقایسه معماری Knowledge Layer با Qdrant.

---

# 11. Observability / Evaluation

### `Langfuse`

الان داری و بسیار مهم است.

Tracing + Prompt Management + Evaluation + Metrics. ([GitHub][27])

برای:

```text
Agent Run
Model Call
Tool Call
Prompt
Cost
Latency
Evaluation
```

---

### `Phoenix`

Observability + Evaluation + Experimentation. ([GitHub][28])

برای Evaluation Layer/Arena خیلی مهم است.

---

### `AgentOps`

تمرکز روی Monitoring Agentها.

برای Agent Run، Session و performance.

---

### `Helicone`

LLM observability / gateway / usage analytics.

برای Cost و Request analytics.

---

### `OpenLLMetry`

### `OpenLLMetry JS`

Instrumentation برای LLM Appها بر پایه استانداردهای observability.

---

### `OpenLIT` — جدید

OpenTelemetry-native AI engineering/observability با monitoring، eval، prompt management و guardrail capabilities. ([GitHub][29])

برای Unified Telemetry Layer ما ارزشمند است.

---

### `OpenTelemetry`

اگرچه در تصویرت implementationهایی از OpenLLMetry داری، خود OpenTelemetry باید استاندارد پایه Tracing باشد.

---

# 12. Evaluation / Code Review

### `PR-Agent`

Review خودکار Pull Request با AI.

برای:

```text
Developer Actor
↓
PR
↓
Reviewer Actor
↓
Feedback
↓
Fix
```

---

### `reviewdog`

Framework برای اجرای Linter/Analyzer و گذاشتن feedback روی Code Review.

برای Automated Reviewer Tool.

---

### `danger-js`

Rule-based automated PR review.

جذابیتش برای ما این است که Reviewer لزوماً AI نیست.

می‌تواند:

```text
Rule Engine
AI
Human
```

باشد.

همین دقیقاً فلسفه Actor سیستم ماست.

---

# 13. No-Code AI Builder

### `Dify`

AI App/Workflow/Agent Platform.

یکی از مهم‌ترین UI/UX Referenceها.

بررسی کن:

```text
App
Workflow
Model
Prompt
Knowledge
Tool
Variable
Execution Log
```

---

### `Flowise`

Visual LLM/Agent Workflow Builder.

برای Node Editor.

---

### `Langflow`

Visual Flow Builder برای Agent/LLM.

برای Workflow Designer.

---

### `open-agent-builder-main`

اگر همان Agent Builder شناخته‌شده باشد، برای Agent Configuration UI مفید است؛ ولی upstream با نام فولدر قطعی نیست.

---

### `sim`

اگر منظورت `simstudioai/sim` باشد، Workflow/Agent builder بسیار مرتبط است؛ ولی URL upstream را از روی اسکرین‌شات قطعی نمی‌کنم.

---

# 14. Project Management

### `Plane`

Project/Issue/Product management.

برای:

```text
Project
Cycle
Module
Issue
Task
State
```

UI و Domain Model آن خیلی ارزش دارد.

---

### `OpenProject`

Project، Portfolio، Task، Agile، roadmap و team collaboration را پوشش می‌دهد. ([GitHub][30])

برای Enterprise Project Domain.

---

### `Taiga`

Agile:

```text
Epic
Sprint
Story
Task
Issue
Kanban
```

---

### `Focalboard`

Board/Kanban ساده.

برای Task View.

---

# 15. ERP / Business

### `ERPNext`

بسیار مهم‌تر از چیزی است که در نگاه اول به نظر می‌آید.

به تو نشان می‌دهد شرکت واقعی فقط Project + Agent نیست.

داریم:

```text
HR
CRM
Sales
Accounting
Payroll
Assets
Procurement
Inventory
Support
...
```

برای Organization Domain R&D بسیار مهم.

---

### `Frappe`

Framework زیر ERPNext.

برای Metadata-driven Business Objectها و extensible application architecture.

---

### `Odoo`

یکی از بزرگ‌ترین R&D Referenceهای Business Platform.

برای:

```text
CRM
HR
Accounting
Sales
Inventory
Project
Manufacturing
...
```

هدف این نیست Odoo را داخل محصول بگذاری؛ هدف فهم **Business Module Architecture** آن است.

---

# 16. Source Code / Repository

### `Gitea`

Git Hosting سبک.

برای اینکه Organization بتواند Repository داخلی داشته باشد.

---

### `Gitness`

Developer platform/source hosting.

برای R&D CI/repository/project integration.

---

# 17. Identity / Permissions

این بخش تقریباً در ریپوهای اولیه‌ات کم بود.

### `Keycloak` — جدید

Identity/IAM با federation، authentication، users و fine-grained authorization. ([GitHub][31])

برای:

```text
Human Identity
Organization Identity
SSO
OIDC
OAuth
```

---

### `OpenFGA` — جدید

Fine-grained Authorization مبتنی بر relationship؛ الهام‌گرفته از Zanzibar. ([GitHub][32])

برای پروژه ما خیلی مهم است:

```text
Alice
CAN
use Agent X
IN
Project A

Agent X
CAN
read Dataset B
BUT NOT
Finance Dataset
```

---

### `Casbin` — جدید

Authorization Engine با مدل‌های مختلف access control. ([GitHub][33])

برای Policy/Permission Engine Reference.

---

# 18. Communication

### `Mattermost` — جدید

Self-hosted collaboration با chat/workflows/calling و AI integration. ([GitHub][34])

برای Communication Layer:

```text
Channel
DM
Thread
Team
Bot
AI
Human
```

---

### `Mattermost Agents` — جدید

Agentها را مستقیماً وارد Collaboration محیط Mattermost می‌کند. ([GitHub][35])

**این را حتماً ببین چون دقیقاً Human ↔ AI Collaboration است.**

---

### `LiveKit` — جدید

Realtime Voice/Video/Data بر پایه WebRTC. ([GitHub][36])

برای Meeting/Voice/Realtime Communication.

---

### `LiveKit Agents` — جدید

Realtime voice/multimodal agents. ([GitHub][37])

برای:

```text
Human speaks
↓
AI Worker
↓
Voice response
```

---

# 19. Event / Message Bus

### `NATS` — جدید

Messaging System سریع برای services/devices و distributed systems. ([GitHub][38])

برای easyES:

```text
TaskCreated
AgentStarted
MessageSent
ToolCalled
TaskFailed
EvaluationCompleted
```

این Eventها می‌توانند از Event Backbone عبور کنند.

---

# 20. Platform Runtime

### `Dapr` — جدید

Distributed application runtime با state management، workflow، messaging و service communication. ([GitHub][39])

برای ما:

```text
Actor Runtime
State
PubSub
Workflow
Service Invocation
Secrets
```

خیلی مهم است.

---

# مهم‌ترین نتیجه این R&D

اگر این همه Repository را یکجا ببینی، تقریباً معماری محصولت خودش نمایان می‌شود:

```text
                    easyES
                        │
 ┌──────────────────────┼──────────────────────┐
 │                      │                      │
Organization         Execution             Intelligence
 │                      │                      │
ERPNext             Temporal              LangGraph
Odoo                Hatchet               CrewAI
Plane               Conductor             AutoGen
OpenProject         n8n                   PydanticAI
                                         Mastra
                        │
                    AI Runtime
                        │
              OpenHands / OpenFang
              Dapr Agents / SwarmClaw
                        │
             ┌──────────┼──────────┐
             │          │          │
          Memory     Knowledge    Tools
             │          │          │
           Mem0      LlamaIndex    MCP
          Graphiti     Qdrant      Nango
                                  Browser-use
                        │
                    Sandbox
                        │
                       E2B
                        │
                   Model Layer
                        │
             LiteLLM / Portkey
                        │
                  Observability
                        │
           Langfuse / Phoenix
           OpenLIT / AgentOps
                        │
                   Governance
                        │
             Keycloak / OpenFGA
                  / Casbin
                        │
                 Communication
                        │
           Mattermost / LiveKit
                        │
                    Event Bus
                        │
                       NATS
```

از بین همه این‌ها، **۱۰ ریپویی که من قبل از طراحی Core حتماً سورسشان را عمیق می‌خواندم** این‌ها هستند: `Temporal`, `LangGraph`, `OpenFang`, `Dapr Agents`, `OpenHands`, `Nango`, `MCP Servers/SDK`, `E2B`, `Mem0/Graphiti` و `OpenFGA`. چون کنار هم تقریباً همان Primitiveهایی را پوشش می‌دهند که برای easyES لازم داری: Durable Workflow، Agent Runtime، Tool Contract، Integration، Sandbox، Memory و Governance. ([GitHub][1])

[1]: https://github.com/temporalio/temporal?utm_source=chatgpt.com "temporalio/temporal: Temporal service"
[2]: https://github.com/pydantic/pydantic-ai?utm_source=chatgpt.com "AI Agent Framework, the Pydantic way"
[3]: https://github.com/pydantic/pydantic-ai-harness?utm_source=chatgpt.com "Pydantic AI Harness"
[4]: https://github.com/mastra-ai/mastra?utm_source=chatgpt.com "Mastra is the modern TypeScript framework for AI-powered ..."
[5]: https://github.com/huggingface/smolagents?utm_source=chatgpt.com "smolagents: a barebones library for agents that think in code."
[6]: https://github.com/rightnow-ai/openfang?utm_source=chatgpt.com "RightNow-AI/openfang: Open-source Agent Operating ..."
[7]: https://github.com/swarmclawai/swarmclaw?utm_source=chatgpt.com "swarmclawai/swarmclaw: Open-source self-hosted AI ..."
[8]: https://github.com/dapr/dapr-agents?utm_source=chatgpt.com "Dapr Agents: A Framework for Agentic AI Systems"
[9]: https://github.com/hatchet-dev/hatchet?utm_source=chatgpt.com "hatchet-dev/hatchet: 🪓 An orchestration engine for ..."
[10]: https://github.com/conductor-oss/conductor?utm_source=chatgpt.com "Conductor is an event driven agentic workflow engine ..."
[11]: https://github.com/PrefectHQ/prefect?utm_source=chatgpt.com "Prefect is a workflow orchestration framework for building ..."
[12]: https://github.com/browser-use/workflow-use?utm_source=chatgpt.com "browser-use/workflow-use: ⚙️ Create and run ..."
[13]: https://github.com/e2b-dev/e2b?utm_source=chatgpt.com "GitHub - e2b-dev/E2B: Open-source, secure environment with real ..."
[14]: https://github.com/e2b-dev/code-interpreter?utm_source=chatgpt.com "GitHub - e2b-dev/code-interpreter: Python & JS/TS SDK for running ..."
[15]: https://github.com/browser-use/browser-use?utm_source=chatgpt.com "browser-use/browser-use: 🌐 Make websites accessible for ..."
[16]: https://github.com/browser-use/qa-use?utm_source=chatgpt.com "browser-use/qa-use"
[17]: https://github.com/modelcontextprotocol/servers?utm_source=chatgpt.com "Model Context Protocol Servers"
[18]: https://github.com/modelcontextprotocol/python-sdk?utm_source=chatgpt.com "The official Python SDK for Model Context Protocol servers ..."
[19]: https://github.com/punkpeye/awesome-mcp-servers?utm_source=chatgpt.com "GitHub - punkpeye/awesome-mcp-servers: A collection of ..."
[20]: https://github.com/nangohq/nango?utm_source=chatgpt.com "NangoHQ/nango: Build product integrations with AI."
[21]: https://github.com/NangoHQ/integration-templates?utm_source=chatgpt.com "GitHub - NangoHQ/integration-templates"
[22]: https://github.com/portkey-ai/gateway?utm_source=chatgpt.com "GitHub - Portkey-AI/gateway"
[23]: https://github.com/mem0ai/mem0?utm_source=chatgpt.com "mem0ai/mem0: Universal memory layer for AI Agents"
[24]: https://github.com/getzep/graphiti?utm_source=chatgpt.com "getzep/graphiti: Build Real-Time Knowledge Graphs for AI ..."
[25]: https://github.com/run-llama/llama_index?utm_source=chatgpt.com "run-llama/llama_index: LlamaIndex is the leading ..."
[26]: https://github.com/qdrant/qdrant?utm_source=chatgpt.com "GitHub - qdrant/qdrant: Qdrant - High-performance ..."
[27]: https://github.com/langfuse/langfuse?utm_source=chatgpt.com "langfuse/langfuse: Open source AI engineering platform: LLM evals ..."
[28]: https://github.com/arize-ai/phoenix?utm_source=chatgpt.com "GitHub - Arize-ai/phoenix: AI Observability & Evaluation"
[29]: https://github.com/openlit/openlit?utm_source=chatgpt.com "GitHub - openlit/openlit: Open source platform for AI Engineering ..."
[30]: https://github.com/opf/openproject?utm_source=chatgpt.com "OpenProject is the leading open source project ..."
[31]: https://github.com/keycloak/keycloak?utm_source=chatgpt.com "keycloak/keycloak: Open Source Identity and Access Management ..."
[32]: https://github.com/openfga/openfga?utm_source=chatgpt.com "OpenFGA - GitHub"
[33]: https://github.com/apache/casbin?utm_source=chatgpt.com "Apache Casbin: an authorization library that supports ... - GitHub"
[34]: https://github.com/mattermost/mattermost?utm_source=chatgpt.com "Mattermost is an open source platform for secure collaboration ..."
[35]: https://github.com/mattermost/mattermost-plugin-agents?utm_source=chatgpt.com "Mattermost Agents plugin supporting multiple LLMs - GitHub"
[36]: https://github.com/livekit/livekit?utm_source=chatgpt.com "LiveKit: Real-time video, audio and data for developers - GitHub"
[37]: https://github.com/livekit/agents?utm_source=chatgpt.com "GitHub - livekit/agents: A framework for building realtime voice AI ..."
[38]: https://github.com/nats-io/nats-server?utm_source=chatgpt.com "GitHub - nats-io/nats-server: High-Performance server for NATS.io ..."
[39]: https://github.com/dapr/dapr?utm_source=chatgpt.com "Dapr is a portable runtime for building distributed ..."
