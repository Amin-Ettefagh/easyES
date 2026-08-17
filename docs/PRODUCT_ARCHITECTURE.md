# easyES product hierarchy

```text
User
└── Company (Organization + Membership)
    ├── Human / Hybrid Actors
    ├── AI Agents
    │   ├── Provider → Model → encrypted Credential
    │   ├── immutable system-prompt versions
    │   ├── Knowledge Sources
    │   └── Persistent Memory
    └── Workspace (Project)
        ├── Git repository and artifacts
        ├── Jira-style Tasks
        └── Workflows (one or many)
            ├── Arenas (team lanes)
            ├── Nodes and Edges
            ├── Agent / Human assignments
            ├── related Workflow links
            └── Executions
                ├── NodeRuns / Events / Evaluations
                ├── loop safety and budgets
                └── Approval / Human / Operator interventions
```

Every API request is membership-scoped. The browser sends the selected company
UUID in `X-Organization`; writes validate all referenced objects against that
same tenant. Workspaces retain the existing `/projects/` API path for backward
compatibility while the UI presents the product concept as **Workspace**.
