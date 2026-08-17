دقیقاً. این Prompt را بده به Agent. سه فایل، مخصوصاً `Idea.md`، معماری را به‌عنوان یک **Universal Human + AI Execution Platform** تعریف می‌کنند و تأکید دارند که Agent، Project و Workflow نباید به هم hard-code شوند.  همچنین در R&D تو، n8n برای Node/Trigger/Condition/Loop و Temporal/SWE-agent/OpenHands برای اجرای durable، retry و حلقه توسعه مرجع در نظر گرفته شده‌اند.  

````md
# MASTER IMPLEMENTATION PROMPT
# easyES — Foundation + Software Company Demo

تو مسئول طراحی و پیاده‌سازی نسخه Foundation/Demo یک پلتفرم بزرگ و قابل توسعه برای مدیریت و اجرای سازمان‌های Human + AI هستی.

این پروژه یک Agent Builder ساده، Chatbot، Workflow Automation ساده یا کپی n8n نیست.

هدف بلندمدت:

> Universal Human + AI Organization & Execution Platform

یعنی بستری که در آینده هزاران Organization با هزاران Project، Workflow، Human، AI Agent، Tool، Model، Knowledge Source و Runtime متفاوت بتوانند داخل آن فعالیت کنند.

اما در این مرحله قرار نیست کل محصول نهایی ساخته شود.

هدف این مرحله:

1. Core Architecture صحیح و قابل توسعه ساخته شود.
2. Domain Model از ابتدا درست طراحی شود.
3. یک Company نمونه به نام `amin` Seed شود.
4. یک Software Development Workflow واقعی به‌عنوان Demo ساخته شود.
5. چند AI Agent تخصصی داخل Company کار کنند.
6. Agentها با یکدیگر تعامل داشته باشند.
7. کاربر بتواند کل اتفاقات را Live مشاهده و کنترل کند.
8. چرخه Idea → Research → Planning → Development → Testing → Review → Improvement → Completion/Archive واقعاً اجرا شود.
9. سیستم از همان ابتدا برای اضافه شدن Organizationها، Projectها، Workflowها، Agentها و Use Caseهای کاملاً متفاوت آماده باشد.

---

# 0. قوانین حیاتی درباره فایل‌ها و Source Repositoryها

دو مسیر اصلی داریم:

```text
D:\AgentPlayground
D:\easyES
````

## D:\AgentPlayground

این مسیر فقط و فقط:

```text
READ-ONLY R&D REFERENCE
```

است.

تمام Repositoryها، Sampleها و فایل‌های تحقیقاتی موجود در:

```text
D:\AgentPlayground
```

را بررسی کن.

اما تحت هیچ شرایطی:

* فایل‌های آن را Edit نکن.
* Delete نکن.
* Rename نکن.
* Move نکن.
* Format نکن.
* Commit نکن.
* Config آنها را تغییر نده.
* Dependency داخل آنها نصب نکن مگر برای بررسی کاملاً ضروری و بدون تغییر Source.
* Build artifact داخل آنها تولید نکن.
* پروژه اصلی را داخل آنها نساز.

اگر بخشی از Source برای Reference لازم است:

```text
READ
ANALYZE
UNDERSTAND
```

اگر واقعاً استفاده مستقیم از قسمتی لازم شد، فقط با رعایت License آن را به پروژه خودمان COPY کن و Source/License attribution لازم را مستند کن.

هرگز Source اصلی را تغییر نده.

---

# 1. فایل‌های الزامی R&D

قبل از هرگونه Implementation ابتدا این سه فایل را کامل بخوان:

```text
Idea.md
SourceProjectsHelp.md
SoftwareEngineerCompanySamples.html
```

ممکن است داخل:

```text
D:\AgentPlayground
```

یا یکی از زیرمسیرهای آن باشند.

آنها را پیدا و کامل مطالعه کن.

این سه فایل Source of Truth مفهومی پروژه هستند.

مخصوصاً:

```text
Idea.md
```

تعریف Product Vision و Domain Architecture است.

```text
SourceProjectsHelp.md
```

مشخص می‌کند Repositoryهای مختلف برای کدام قسمت پروژه Reference هستند.

```text
SoftwareEngineerCompanySamples.html
```

ساختار گسترده Company / Department / Team / Role را برای R&D نشان می‌دهد.

ساختار کامل آن فایل را در Demo پیاده نکن.

از آن فقط برای Domain Modeling و انتخاب Roleهای اصلی Software Company استفاده کن.

---

# 2. Repository Research

تمام Folderهای:

```text
D:\AgentPlayground
```

را Inventory کن.

Repositoryهایی که مرتبط هستند را بررسی کن.

به‌خصوص اگر موجود بودند:

```text
n8n
Activepieces

LangGraph
LangGraphJS
CrewAI
AutoGen
AG2
CAMEL
PydanticAI
Mastra

MetaGPT
ChatDev

Temporal
Hatchet
Conductor
Prefect

OpenHands
SWE-agent
Aider
Continue

Dify
Flowise
Langflow
Sim

Langfuse
Phoenix
AgentOps
Helicone
OpenTelemetry

LiteLLM
Portkey

Mem0
Graphiti
LlamaIndex
Qdrant
Weaviate

Nango
MCP

OpenFGA
Keycloak
Casbin

Plane
OpenProject
Taiga

Mattermost
LiveKit

E2B
browser-use
```

هیچ‌کدام را کورکورانه Fork یا کپی نکن.

هدف:

> استخراج Pattern و Design Decision خوب.

برای هر بخش بررسی کن که بهترین Pattern چیست و سپس Implementation مستقل، تمیز و ساده خودمان را بساز.

---

# 3. محل پروژه جدید

تمام پروژه جدید فقط در:

```text
D:\easyES
```

ساخته شود.

اگر Directory وجود ندارد:

```text
D:\easyES
```

را ایجاد کن.

هیچ Source اصلی پروژه در:

```text
D:\AgentPlayground
```

نباشد.

---

# 4. Technology Stack

Backend:

```text
Python
Django
Django REST Framework
```

Frontend:

```text
Next.js
TypeScript
React
```

Database:

```text
PostgreSQL
```

Infrastructure:

```text
Docker
Docker Compose
```

برای Background Execution / realtime در صورت نیاز:

```text
Redis
Celery
Django Channels
```

مجاز است.

اما PostgreSQL دیتابیس اصلی سیستم باشد.

Architecture باید طوری باشد که بعداً Execution Engine بتواند با چیزهایی مانند:

```text
Temporal
Hatchet
Dapr
```

جایگزین یا Integrate شود.

Core Domain را مستقیماً به Celery یا Temporal وابسته نکن.

---

# 5. Architecture Principle

این Domain Separation را از ابتدا حفظ کن:

```text
Organization != Project

Project != Workflow

Workflow != Execution

Task != Execution

Role != Actor

Role != Agent

Agent != Model

Actor != Agent

Capability != Role

Tool != Connector

Knowledge != Memory

Evaluation != Execution
```

هیچ‌کدام را فقط به دلیل ساده‌تر شدن Demo با هم Merge نکن.

---

# 6. معماری کلان

Foundation باید حداقل برای این Domainها آماده باشد:

```text
Platform
│
├── Organizations
├── Spaces
├── Organizational Structure
├── Actors
├── Roles
├── Capabilities
├── Agents
├── Models
├── Prompts
├── Tools
├── Connectors
├── Projects
├── Goals
├── Workflows
├── Tasks
├── Assignments
├── Executions
├── Runs
├── Communication
├── Events
├── Artifacts
├── Evaluations
├── Policies
├── Logs
└── Analytics
```

همه اینها لازم نیست در Demo Feature کامل داشته باشند.

اما Domain Model نباید مسیر آینده را مسدود کند.

---

# 7. Multi-Tenant Design

سیستم از ابتدا Multi-Organization باشد.

یعنی:

```text
Platform
│
├── Organization A
│   ├── Projects
│   ├── Agents
│   ├── Humans
│   └── ...
│
├── Organization B
│
└── Organization N
```

Demo فقط یک Organization دارد.

اما Schema و Service Layer نباید Single Company فرض کنند.

---

# 8. Demo User

یک User برای Demo ایجاد کن:

```text
username: amin
password: 123456
```

این Credential فقط Development Seed است.

Password داخل Database به شکل Plaintext ذخیره نشود.

از Password Hash استاندارد Django استفاده شود.

در Production configuration این credential نباید خودکار ساخته شود.

---

# 9. Demo Organization

بعد از Login کاربر باید Company زیر را ببیند:

```text
Company Name:
amin
```

Type:

```text
Software Company
```

این Company فقط Sample Data است.

---

# 10. Demo Organization Structure

فعلاً Organization را بیش از حد بزرگ نکن.

فقط Roleهای اصلی لازم برای Software Product Lifecycle را Seed کن.

مثلاً:

```text
amin
│
├── Executive / Direction
│   └── Project Director / Orchestrator
│
├── Product
│   ├── Idea Analyst
│   ├── Market Researcher
│   ├── Product Manager
│   └── Product Analyst
│
├── Architecture
│   ├── Software Architect
│   └── Technical Lead
│
├── Engineering
│   ├── Backend Engineer
│   ├── Frontend Engineer
│   └── Full-Stack Engineer
│
├── Quality
│   ├── QA Engineer
│   ├── Test Engineer
│   └── Code Reviewer
│
└── Release
    └── DevOps / Release Engineer
```

Roleها قابل ایجاد، حذف و تغییر باشند.

این لیست Hard-coded Core نباشد.

فقط Seed Data باشد.

---

# 11. AI Agent System

برای Demo، بیشتر Roleها توسط AI Agent قابل اجرا باشند.

هر Agent Entity مستقل داشته باشد.

حداقل Agent Configuration:

```text
Agent
├── Name
├── Description
├── Role
├── Persona
├── System Prompt
├── Prompt Version
├── Model Provider
├── Model
├── API Credential / Token
├── Temperature
├── Max Tokens
├── Context Limit
├── Token Budget
├── Cost Budget
├── Capabilities
├── Tools
├── Permissions
├── Knowledge Access
├── Status
├── Enabled / Disabled
└── Metadata
```

مهم:

هر Agent بتواند:

```text
Provider متفاوت
Model متفاوت
API Token متفاوت
Prompt متفاوت
Token Budget متفاوت
Tool متفاوت
Permission متفاوت
```

داشته باشد.

مثلاً:

```text
Market Research Agent
→ Model A
→ API Credential A

Backend Agent
→ Model B
→ API Credential B

QA Agent
→ Model C
→ API Credential C
```

Agent را به Model خاص Hard-code نکن.

---

# 12. Model Provider Abstraction

یک Model Gateway abstraction بساز.

مثلاً:

```text
ModelProvider

call()
stream()
estimate_cost()
health_check()
```

و Provider Adapter:

```text
OpenAICompatibleProvider
OpenAIProvider
AnthropicProvider
GeminiProvider
LocalProvider
```

برای Demo لازم نیست همه Providerها کامل شوند.

حداقل architecture و یک OpenAI-Compatible Provider آماده باشد.

بعداً باید بتوان LiteLLM یا Gateway خارجی را بدون تغییر Agent Domain جایگزین کرد.

Credentials encrypted / protected نگهداری شوند و هیچ API Key در Log نمایش داده نشود.

---

# 13. Prompt Management

Prompt نباید فقط یک Text Field ساده و بی‌تاریخچه باشد.

حداقل:

```text
Prompt
PromptVersion
AgentPromptAssignment
```

داشته باش.

کاربر بتواند Prompt هر Agent را جدا Edit کند.

Version history حفظ شود.

Execution باید مشخص کند با کدام Prompt Version انجام شده است.

---

# 14. Global Company Rules

یک بخش بسیار مهم:

```text
Company Rules
```

کاربر بتواند Rule عمومی برای کل Company تعریف کند.

مثلاً:

```text
Never deploy without QA approval.

All generated code must have tests.

Never expose secrets.

Maximum 3 automatic retry loops.

Security failures are blocking.

All important decisions must be logged.
```

Hierarchy اولیه:

```text
Platform Rules
    ↓
Organization Rules
    ↓
Project Rules
    ↓
Workflow Rules
    ↓
Agent Rules
    ↓
Task Constraints
```

Rule Resolution ساده ولی تمیز پیاده شود.

---

# 15. Project System

Company بتواند چندین Project داشته باشد.

Demo امکان:

```text
Create Project
List Projects
Open Project
Archive Project
```

را داشته باشد.

Project Fields:

```text
Name
Description
Objective
Status
Owner
Organization
Start Date
Budget
Workflow
Created At
Updated At
Archived At
```

Statusها حداقل:

```text
Draft
Planning
Running
Blocked
Review
Completed
Failed
Archived
```

---

# 16. Demo Goal

User باید بتواند چیزی مثل این وارد کند:

```text
یک SaaS برای مدیریت هزینه‌های شخصی بساز.
```

یا:

```text
یک سیستم مدیریت Task برای تیم‌های کوچک بساز.
```

این Input تبدیل به Project شود.

---

# 17. Demo Software Development Workflow

Workflow نمونه:

```text
Idea Submitted
      ↓
Idea Analysis
      ↓
Market Research
      ↓
Feature Discovery
      ↓
Product Specification
      ↓
Architecture Design
      ↓
Implementation Planning
      ↓
┌─────────────────────────┐
│                         │
▼                         ▼
Backend Implementation   Frontend Implementation
│                         │
└────────────┬────────────┘
             ↓
         Integration
             ↓
          QA / Test
             ↓
        Evaluation
             ↓
       Quality Gate
        /         \
      PASS        FAIL
       │            │
       │            ▼
       │      Failure Analysis
       │            ↓
       │        Fix Planning
       │            ↓
       │      Relevant Developer
       │            ↓
       │          Re-Test
       │            │
       │            └──────────↺
       │
       ▼
    Review
       ↓
Product Analysis
       ↓
Final Evaluation
       ↓
┌───────────────┬────────────────┐
│               │                │
Complete      Improve          Reject
│               │                │
▼               └──────↺         ▼
Done                          Archive
```

---

# 18. Loop باید واقعی باشد

Loop فقط Graphic نباشد.

Execution Engine باید واقعاً Condition و Loop را اجرا کند.

مثلاً:

```text
IF test_score < threshold
    → create feedback
    → assign fix task
    → execute developer
    → execute tests again
```

و Stop Conditions:

```text
PASS
MAX_ITERATIONS
MAX_COST
MAX_TIME
MANUAL_STOP
FATAL_ERROR
REJECTED
```

---

# 19. Loop Safety

برای جلوگیری از Infinite Loop:

هر Loop باید حداقل داشته باشد:

```text
max_iterations
max_duration
max_cost
failure_threshold
```

اگر Loop محدودیت را رد کرد:

```text
Needs Human Review
```

یا:

```text
Failed
```

شود.

---

# 20. Failed Project / Archive

اگر Project ناموفق بود، پاک نشود.

Status:

```text
Failed
```

و سپس قابل:

```text
Archive
```

باشد.

Archive باید:

* Project
* Workflow
* Tasks
* Executions
* Agent Conversations
* Logs
* Artifacts
* Evaluations
* Failure Reasons
* Metrics

را حفظ کند.

بعداً امکان Restore فراهم باشد.

فعلاً اگر Restore کامل سنگین است، Domain و API برای آینده آماده باشد.

---

# 21. Workflow Engine

Workflow را به شکل Graph مدل کن.

Primitiveهای اولیه:

```text
Start
Task
Agent Task
Human Task
Tool
Condition
Decision
Parallel
Join
Loop
Review
Approval
Evaluation
Wait
Event
Subworkflow
End
Archive
```

هر Node:

```text
id
type
name
configuration
inputs
outputs
position
metadata
```

هر Edge:

```text
source
target
condition
priority
metadata
```

باشد.

---

# 22. Workflow UI

برای Workflow Studio از UX پروژه‌هایی مثل:

```text
n8n
Dify
Flowise
Langflow
```

الهام بگیر.

اما UI را کپی Pixel-by-Pixel نکن.

برای Demo یک Canvas مدرن شبیه n8n بساز.

ترجیحاً:

```text
React Flow
```

یا abstraction مناسب مشابه.

کاربر باید بتواند:

```text
Zoom
Pan
Select Node
Inspect Node
See Edge
See Current Running Node
See Failed Node
See Completed Node
See Loop
```

را انجام دهد.

Editor کامل Drag/Drop برای Version اول ضروری نیست اگر زمان را زیاد کند.

اما Architecture باید برای Visual Workflow Editor آماده باشد.

حداقل Workflow Demo به‌صورت Graph Interactive نمایش داده شود.

---

# 23. مهم‌ترین UI: Live Project Control Room

وقتی Project اجرا می‌شود، User باید حس کند مدیر یک Company AI است.

یک صفحه:

```text
Project Control Room
```

بساز.

مثلاً Layout:

```text
┌─────────────────────────────────────────────────────────────┐
│ Project / Status / Cost / Duration / Controls              │
├──────────────────────┬──────────────────────────────────────┤
│                      │                                      │
│ Workflow Graph       │ Current Execution                   │
│                      │                                      │
│ ● Idea               │ Agent: Backend Engineer             │
│ ● Research           │ Status: Working                     │
│ ● Product            │ Model: ...                          │
│ ● Backend            │ Tokens: ...                         │
│ ● Frontend           │ Cost: ...                           │
│ ● QA                 │ Current Task: ...                   │
│                      │                                      │
├──────────────────────┼──────────────────────────────────────┤
│ Agent Conversations  │ Live Logs                           │
│                      │                                      │
│ PM → Architect       │ Tool called...                      │
│ Architect → Backend  │ Model response...                   │
│ QA → Backend         │ Test failed...                      │
│                      │ Retrying...                         │
├──────────────────────┴──────────────────────────────────────┤
│ Artifacts / Evaluation / Decisions / Metrics               │
└─────────────────────────────────────────────────────────────┘
```

---

# 24. User Control

User باید بتواند Execution را:

```text
Start
Pause
Resume
Stop
Cancel
Retry
Approve
Reject
Archive
```

کند.

همچنین بتواند:

```text
Send Instruction
```

به Project یا Agent بدهد.

مثلاً وسط اجرا:

```text
از PostgreSQL استفاده کن نه SQLite.
```

این Intervention باید Log شود.

---

# 25. Agent Communication

Agentها نباید فقط پشت صحنه Call شوند.

Communication باید First-Class باشد.

حداقل:

```text
Conversation
Message
Sender Actor
Receiver Actor
Project
Task
Execution
Timestamp
Message Type
```

انواع Message:

```text
Request
Response
Feedback
Review
Question
Answer
Delegation
Report
Decision
System
```

UI باید Conversation را نشان دهد.

مثلاً:

```text
Product Manager
→ Architect:
Feature list finalized...

Architect
→ Backend:
Implement API contract...

Backend
→ QA:
Build ready for test...

QA
→ Backend:
3 tests failed...

Backend
→ QA:
Fix completed, please retest.
```

---

# 26. Internal Reasoning

Chain-of-thought خصوصی مدل را ذخیره یا نمایش نده.

به‌جای آن ذخیره کن:

```text
Decision Summary
Action Summary
Evidence
Tool Calls
Inputs
Outputs
Result
```

یعنی User بتواند بفهمد:

```text
چه اتفاقی افتاد؟
چه تصمیمی گرفته شد؟
چه Toolی استفاده شد؟
خروجی چه بود؟
```

بدون ذخیره private chain-of-thought.

---

# 27. Execution Logging

تمام Executionها Traceable باشند.

حداقل Eventها:

```text
PROJECT_CREATED
PROJECT_STARTED

WORKFLOW_STARTED
NODE_STARTED
NODE_COMPLETED
NODE_FAILED

TASK_CREATED
TASK_ASSIGNED
TASK_STARTED
TASK_COMPLETED
TASK_FAILED

AGENT_STARTED
AGENT_MESSAGE

MODEL_CALL_STARTED
MODEL_CALL_COMPLETED
MODEL_CALL_FAILED

TOOL_CALL_STARTED
TOOL_CALL_COMPLETED
TOOL_CALL_FAILED

ARTIFACT_CREATED

EVALUATION_STARTED
EVALUATION_COMPLETED

LOOP_STARTED
LOOP_ITERATION
LOOP_EXITED

USER_INTERVENTION

PROJECT_COMPLETED
PROJECT_FAILED
PROJECT_ARCHIVED
```

---

# 28. Execution Trace

هر Run باید Trace داشته باشد.

مثلاً:

```text
Project Run #12

10:00 Project Started
10:01 Idea Analyst Started
10:03 Idea Analysis Completed
10:04 Market Research Started
10:09 Market Research Completed
10:10 PM Started
...
11:02 QA Failed
11:02 Loop Iteration #1
11:03 Backend Fix Started
11:14 Fix Completed
11:15 QA Started
11:20 QA Passed
...
12:00 Project Completed
```

---

# 29. Agent Execution Detail

برای هر Agent Run نمایش بده:

```text
Agent
Role
Prompt Version
Provider
Model
Task
Input
Output
Tokens Input
Tokens Output
Estimated Cost
Duration
Tools Used
Status
Error
Created Artifacts
Evaluation
```

---

# 30. Artifacts

Agentها باید بتوانند Artifact تولید کنند.

مثلاً:

```text
Market Research Report
Product Requirements
Feature List
Architecture Document
API Specification
Database Design
Backend Code
Frontend Code
Test Report
Review Report
Final Report
```

Artifact Entity مستقل باشد.

حداقل:

```text
Artifact
├── Project
├── Task
├── Execution
├── Created By
├── Type
├── Name
├── Content / File Reference
├── Version
└── Metadata
```

---

# 31. Demo Outputs

برای Demo لازم نیست AI واقعاً یک SaaS بزرگ Production-ready بسازد.

اما Workflow باید End-to-End واقعی باشد.

یعنی Input Idea حداقل منجر شود به:

```text
Idea Analysis
Market Analysis
Feature List
Product Specification
Architecture
Implementation Plan
Backend Artifact
Frontend Artifact
Test Result
Evaluation
Final Report
```

Backend/Frontend Agent بتوانند در Workspace پروژه فایل ایجاد کنند.

---

# 32. Project Workspace Isolation

هر Project یک Workspace مستقل داشته باشد.

مثلاً:

```text
D:\easyES\data\workspaces\<project-id>\
```

یا Volume داخلی Docker معادل آن.

Agent نباید آزادانه کل Disk را تغییر دهد.

Filesystem Access abstraction ایجاد کن.

---

# 33. Agent Tools

برای Demo حداقل Tool abstraction داشته باش.

نمونه:

```text
FileReadTool
FileWriteTool
CodeTool
ShellTool
TestRunnerTool
GitTool
SearchTool
HTTPTool
```

همه Tool Callها Log شوند.

Tool Permission برای هر Agent مستقل باشد.

مثلاً Market Researcher نباید Shell Production داشته باشد.

---

# 34. Future Connector Architecture

Core Tool را به Provider خاص وابسته نکن.

برای آینده در نظر بگیر:

```text
MCP
REST
Webhook
OAuth
Nango
Custom Connector
```

اما Demo لازم نیست همه را پیاده کند.

Interface و Extension Point تمیز کافی است.

---

# 35. Agent Selection

در Demo می‌توان Agent مشخص به Node Assign کرد.

ولی Domain Model را برای آینده آماده کن که Node بتواند بگوید:

```text
Required Capability = Backend Development
```

و Resolver بهترین Actor را انتخاب کند.

فعلاً Resolver ساده باشد.

Hard-code معماری آینده نکن.

---

# 36. Evaluation

Evaluation یک Domain مستقل باشد.

QA صرفاً Pass/Fail نباشد.

حداقل Support:

```text
Evaluation
├── Target
├── Evaluator
├── Metrics
├── Score
├── Result
├── Feedback
└── Timestamp
```

برای Demo:

```text
Product Completeness
Code Quality
Test Result
Requirement Coverage
```

قابل اندازه‌گیری باشند.

---

# 37. Demo Quality Gate

مثلاً:

```text
tests_passed == true
AND
requirement_coverage >= threshold
AND
critical_errors == 0
```

اگر Pass:

```text
Continue
```

اگر Fail:

```text
Feedback
→ Fix
→ Retest
```

---

# 38. Project Completion

Project فقط وقتی Completed شود که:

```text
Required Workflow Nodes Completed
Quality Gate Passed
Required Artifacts Produced
Final Evaluation Passed
```

در غیر این صورت Completed نشود.

---

# 39. Human-in-the-loop

از ابتدا Human Approval را در Domain داشته باش.

مثلاً:

```text
AI Work
↓
Human Approval Required?
├── No → Continue
└── Yes → WAITING_FOR_APPROVAL
```

Demo حداقل یک Approval Node قابل استفاده داشته باشد.

---

# 40. Dashboard

بعد از Login:

```text
Dashboard
```

حداقل نمایش دهد:

```text
Organization: amin

Projects
Active Runs
Agents
Running Agents
Completed Tasks
Failed Tasks
Total Executions
Recent Activity
```

---

# 41. Navigation

پیشنهاد اولیه:

```text
Dashboard

Company
├── Structure
├── Roles
├── People
└── Rules

Projects
├── All Projects
└── New Project

Agents
├── All Agents
├── Agent Detail
└── Prompts

Workflows
├── Templates
└── Workflow Studio

Models
├── Providers
└── Models

Tools

Activity
├── Conversations
├── Executions
└── Logs

Analytics

Settings
```

---

# 42. Agent UI

Agent Detail Page حداقل:

```text
Overview
Role
Prompt
Model
Credential
Capabilities
Tools
Permissions
Runs
Messages
Metrics
```

Prompt و Model قابل Edit باشند.

Secretها Mask شوند.

---

# 43. Company Structure UI

Company `amin` را به شکل Organization Tree نشان بده.

مثلاً:

```text
amin
│
├── Product
│   ├── Product Manager
│   └── Market Researcher
│
├── Engineering
│   ├── Architect
│   ├── Backend
│   └── Frontend
│
└── Quality
    ├── QA
    └── Reviewer
```

روی هر Role بتوان Actor مربوط را دید.

---

# 44. Visual Language

UI:

```text
Modern
Clean
Dense but understandable
Professional
Dark/Light capable
Responsive
```

نباید شبیه Admin Panel قدیمی Django باشد.

Workflow Canvas از n8n الهام بگیرد.

Project Management از Plane/Linear.

Execution Monitoring از Langfuse/Temporal.

Agent config از Dify/Langflow/OpenHands.

اما Design System واحد خودمان داشته باش.

---

# 45. Backend Code Architecture

Django را Modular Monolith پیاده کن.

Microservice فعلاً نساز.

مثلاً:

```text
backend/
├── config/
├── apps/
│   ├── accounts/
│   ├── organizations/
│   ├── structure/
│   ├── actors/
│   ├── agents/
│   ├── models_registry/
│   ├── prompts/
│   ├── tools/
│   ├── projects/
│   ├── workflows/
│   ├── executions/
│   ├── communications/
│   ├── artifacts/
│   ├── evaluations/
│   ├── policies/
│   └── audit/
├── core/
├── integrations/
└── tests/
```

Boundaries را رعایت کن.

Business Logic داخل Viewها نریز.

از:

```text
Service Layer
Domain Services
Repositories where useful
Selectors / Queries
DTO / Schemas
```

به شکل منطقی استفاده کن.

Overengineering هم نکن.

---

# 46. Frontend Architecture

مثلاً:

```text
frontend/
├── app/
├── components/
├── features/
│   ├── organizations/
│   ├── projects/
│   ├── workflows/
│   ├── agents/
│   ├── executions/
│   └── activity/
├── lib/
├── hooks/
├── services/
└── types/
```

Feature-based architecture ترجیح دارد.

---

# 47. API

REST API تمیز ایجاد کن.

Versioned:

```text
/api/v1/
```

OpenAPI/Swagger فعال باشد.

API Contracts مستند شوند.

---

# 48. Realtime

Project Control Room باید Update زنده بگیرد.

می‌توانی از:

```text
WebSocket
```

یا:

```text
SSE
```

استفاده کنی.

انتخاب را Document کن.

Polling سنگین ایجاد نکن.

---

# 49. Authentication

برای Demo Authentication واقعی Django داشته باش.

JWT یا Session architecture مناسب انتخاب کن.

Security basics رعایت شود.

Demo account:

```text
amin / 123456
```

Seed شود.

---

# 50. PostgreSQL

تمام Domain State اصلی در PostgreSQL ذخیره شود.

Migrationها کامل باشند.

Seed Data reproducible باشد.

---

# 51. Docker

کل پروژه با یک Command بالا بیاید.

ترجیحاً:

```bash
docker compose up --build
```

Services حداقل:

```text
frontend
backend
postgres
```

در صورت استفاده:

```text
redis
worker
```

نیز اضافه شوند.

Healthcheck مناسب تعریف کن.

---

# 52. Configuration

تمام Configها از Environment Variables.

فایل:

```text
.env.example
```

بساز.

Secret واقعی Commit نکن.

---

# 53. Testing

Backend:

```text
Unit Tests
Domain Tests
API Tests
Workflow Tests
Loop Tests
Permission Tests
```

Frontend:

```text
Component Tests
Critical Flow Tests
```

حداقل یک Integration/E2E برای Flow اصلی:

```text
Login
→ Create Project
→ Start Workflow
→ Run Agents
→ Fail QA
→ Loop
→ Pass QA
→ Complete
```

وجود داشته باشد.

برای AI Calls در Automated Testها Mock/Fake Provider داشته باش.

---

# 54. Fake AI Provider

این بسیار مهم است.

Demo نباید برای Development کاملاً به API خارجی وابسته باشد.

یک:

```text
FakeModelProvider
```

بساز.

که پاسخ‌های deterministic برای Software Demo بدهد.

با آن بتوان:

```text
Success Scenario
Failure Scenario
Retry Scenario
```

را تست کرد.

سپس User بتواند Provider واقعی خودش را Configure کند.

---

# 55. Demo Scenario

یک Demo Project آماده Seed کن:

```text
Project:
Build a Simple Task Management SaaS
```

Flow:

```text
Idea Analyst
↓
Market Research
↓
Product Manager
↓
Architect
↓
Backend Engineer ─┐
                  ├→ Integration
Frontend Engineer ┘
↓
QA
↓
FAIL intentionally on first run
↓
Backend/Frontend Feedback
↓
Fix
↓
QA Again
↓
PASS
↓
Reviewer
↓
Final Analysis
↓
Completed
```

این Scenario باید بدون API Key واقعی با Fake Provider قابل اجرا باشد.

---

# 56. User باید Loop را ببیند

در UI به‌وضوح نمایش بده:

```text
QA
FAILED

Iteration 1/3

Reason:
API contract mismatch

Feedback sent to:
Backend Engineer

Backend Engineer:
Fixing...

QA:
Retesting...

PASS
```

این یکی از مهم‌ترین قسمت‌های Demo است.

---

# 57. Global Timeline

برای هر Project یک Timeline واحد داشته باش:

```text
Agent Messages
Task Changes
Workflow Events
Tool Calls
Evaluations
User Interventions
Artifacts
Errors
```

همه در ترتیب زمانی.

Filter نیز داشته باشد.

---

# 58. Auditability

هر Action مهم حداقل مشخص کند:

```text
WHO
WHAT
WHEN
PROJECT
TASK
EXECUTION
RESULT
```

در مورد AI:

```text
Agent
Model
Prompt Version
Tool
Cost
Tokens
```

نیز ثبت شود.

---

# 59. Error Handling

هیچ Exception مهمی Silent نباشد.

Execution Failure باید:

```text
Error Code
Error Message
Execution
Node
Retry Count
Timestamp
```

داشته باشد.

UI Error State واضح باشد.

---

# 60. Idempotency

Start/Retryهای حساس نباید باعث Duplicate Executionهای تصادفی شوند.

Execution operations تا حد منطقی idempotent طراحی شوند.

---

# 61. State Machine

Project و Execution Stateها را explicit طراحی کن.

مثلاً Execution:

```text
PENDING
QUEUED
RUNNING
WAITING
WAITING_FOR_APPROVAL
PAUSED
SUCCEEDED
FAILED
CANCELLED
```

Transitionها مشخص باشند.

---

# 62. Documentation

Documentation کامل بنویس.

حداقل:

```text
README.md

docs/
├── PRODUCT_VISION.md
├── ARCHITECTURE.md
├── DOMAIN_MODEL.md
├── DATABASE.md
├── API.md
├── WORKFLOW_ENGINE.md
├── AGENT_SYSTEM.md
├── MODEL_GATEWAY.md
├── REALTIME.md
├── SECURITY.md
├── DEVELOPMENT.md
├── DEPLOYMENT.md
├── TESTING.md
├── RND_REFERENCES.md
└── ROADMAP.md
```

در:

```text
RND_REFERENCES.md
```

بنویس از کدام Repository برای چه Patternی الهام گرفته شد.

---

# 63. ADR

برای تصمیم‌های معماری مهم ADR ایجاد کن.

مثلاً:

```text
docs/adr/

0001-modular-monolith.md
0002-workflow-graph-model.md
0003-provider-abstraction.md
0004-event-model.md
0005-realtime-transport.md
0006-background-execution.md
```

---

# 64. Database Design

قبل از Migrationهای زیاد، ERD تهیه کن.

حداقل Entityهای Core را مشخص کن.

از generic JSON field برای همه چیز استفاده نکن.

JSON فقط جایی استفاده شود که واقعاً extensibility لازم است.

Core Relationships relational و strongly modeled باشند.

---

# 65. Extensibility

هرجا Implementation Demo انجام می‌دهی از خودت بپرس:

> اگر فردا Company دیگری Workflow کاملاً متفاوت خواست، آیا Core باید تغییر کند؟

اگر جواب Yes است، Design را بازبینی کن.

مثلاً Trading Project نباید مجبور باشد Software Workflow داشته باشد.

Workflow Software فقط یک Template باشد.

---

# 66. عدم Hard-code کردن Demo

این موارد فقط Seed/Template هستند:

```text
Company amin

Software Roles

Software Workflow

Demo Agents
```

Core نباید فرض کند همه Companyها اینها را دارند.

---

# 67. Performance

Demo است، اما Implementation شلخته نباشد.

رعایت کن:

```text
Database indexes
N+1 prevention
Pagination
Async/background execution where appropriate
Efficient realtime updates
No aggressive polling
Connection management
```

---

# 68. Security Basics

حداقل:

```text
Password hashing
JWT/session safety
Organization isolation
Authorization
Secret masking
Input validation
CSRF/CORS configuration
Secure defaults
No API key in logs
No arbitrary unrestricted shell access
```

Agent Tool Access باید محدود باشد.

---

# 69. Development Rules

کد:

```text
Readable
Typed where practical
Documented
Testable
Modular
Consistent
```

باشد.

از فایل‌های غول‌پیکر جلوگیری کن.

Business Logic را در Controller/View قرار نده.

Circular dependency ایجاد نکن.

---

# 70. قبل از Coding

قبل از Implementation:

1. هر سه فایل اصلی را بخوان.
2. `D:\AgentPlayground` را Inventory کن.
3. Repositoryهای مرتبط را شناسایی کن.
4. معماری پیشنهادی را بنویس.
5. Domain Model را طراحی کن.
6. ERD اولیه را ایجاد کن.
7. Folder Structure را مشخص کن.
8. Demo Workflow را تعریف کن.
9. سپس Implementation را شروع کن.

نیازی به توقف و گرفتن Confirmation برای هر قدم نیست.

اما تمام تصمیم‌ها را Documentation کن.

---

# 71. ترتیب Implementation

Implementation را Phase-based انجام بده.

## Phase 1 — Foundation

```text
Docker
Django
Next.js
PostgreSQL
Authentication
Organization
Demo Seed
```

## Phase 2 — Core Domain

```text
Role
Actor
Agent
Model Provider
Prompt
Project
Workflow
Task
Execution
```

## Phase 3 — Execution

```text
Workflow Runner
State
Condition
Loop
Retry
Events
Fake AI Provider
```

## Phase 4 — Observability

```text
Logs
Timeline
Agent Communication
Run Details
Metrics
```

## Phase 5 — UI

```text
Dashboard
Company
Projects
Agents
Workflow Canvas
Control Room
```

## Phase 6 — Demo Flow

```text
Idea
Research
Product
Architecture
Backend
Frontend
QA
Failure
Loop
Fix
Retest
Review
Complete
```

## Phase 7 — Hardening

```text
Tests
Permissions
Error handling
Docs
Cleanup
```

---

# 72. Definition of Done

نسخه اولیه زمانی Done است که من بتوانم:

1. پروژه را با Docker بالا بیاورم.

2. به UI وارد شوم.

3. با:

   amin
   123456

   Login کنم.

4. Company `amin` را ببینم.

5. Structure و Roleها را ببینم.

6. Agentها را ببینم.

7. Prompt هر Agent را جدا ببینم و تغییر دهم.

8. Model/Provider هر Agent را جدا تنظیم کنم.

9. Token/Budget هر Agent را جدا تنظیم کنم.

10. Company Rules تعریف کنم.

11. Project جدید بسازم.

12. Idea وارد کنم.

13. Workflow Software Development را Assign کنم.

14. Project را Start کنم.

15. Graph اجرای Workflow را ببینم.

16. ببینم کدام Agent الان در حال کار است.

17. Conversation Agentها را ببینم.

18. Event و Logها را Live ببینم.

19. Model Call و Tool Callها را ببینم.

20. Artifactهای هر مرحله را ببینم.

21. QA Failure را ببینم.

22. ببینم Failure Feedback به Developer برگشته است.

23. Loop Fix → Test را مشاهده کنم.

24. Iteration Count را ببینم.

25. در صورت Pass شدن Quality Gate پروژه Complete شود.

26. در صورت Failure نهایی پروژه Failed شود.

27. Failed Project را Archive کنم.

28. History پروژه بعد از Archive باقی بماند.

29. Executionها قابل بررسی باشند.

30. Fake Provider بدون API خارجی Demo کامل را اجرا کند.

---

# 73. مهم‌ترین اصل

برای سریع تمام کردن Demo معماری را خراب نکن.

اما در مقابل، برای Future Possibilityهایی که هنوز لازم نیستند نیز صدها abstraction بی‌استفاده نساز.

قاعده:

> Core درست + Demo کوچک + Extension Point مشخص.

نه:

> Demo سریع و Hard-coded.

و نه:

> معماری عظیم بدون محصول قابل اجرا.

---

# 74. خروجی نهایی کار

در پایان باید این موارد وجود داشته باشند:

```text
D:\easyES
│
├── backend
├── frontend
├── docs
├── docker-compose.yml
├── .env.example
├── README.md
└── ...
```

و:

```bash
docker compose up --build
```

باید سیستم را قابل اجرا کند.

همچنین در README دقیق بنویس:

```text
URL
Login
Docker commands
Seed commands
Test commands
How to configure AI provider
How to run fake demo
How to reset demo
```

---

# 75. محدودیت نهایی Source

دوباره تأکید:

```text
D:\AgentPlayground
```

فقط:

```text
READ
ANALYZE
REFERENCE
OPTIONALLY COPY WITH LICENSE COMPLIANCE
```

است.

هیچ تغییری روی آن انجام نده.

تمام تغییرات فقط داخل:

```text
D:\easyES
```

انجام شوند.

---

حالا کار را از بررسی کامل سه فایل اصلی و Inventory کردن `D:\AgentPlayground` شروع کن، سپس Architecture/ERD/Implementation Plan را ثبت کن و بعد بدون تخریب Foundation وارد Implementation شو.

```

این Prompt عمداً Demo را کوچک نگه می‌دارد ولی Core را به Agent یا Software Company قفل نمی‌کند؛ همان اصل جداسازی `Role ≠ Agent`، `Agent ≠ Model`، `Task ≠ Actor` و `Workflow ≠ Project` که در سند ایده آمده حفظ شده است. :contentReference[oaicite:3]{index=3} همچنین لاگ Run/Model/Tool/Prompt/Cost/Evaluation و UIهای Workflow/Project از R&D موجودت مستقیماً پوشش داده شده‌اند. :contentReference[oaicite:4]{index=4}
```
