// TypeScript interfaces mirroring the Django REST API (base /api/v1).
// Keep these in sync with the backend serializers under backend/apps/*/api.py.

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface OrgRef {
  uuid: string;
  name: string;
  slug: string;
  level: string;
}

export interface User {
  id: number;
  username: string;
  display_name: string;
  email: string;
  is_demo: boolean;
  is_staff: boolean;
  organizations: OrgRef[];
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface Organization {
  uuid: string;
  name: string;
  slug: string;
  type: string;
  description: string;
  is_active: boolean;
  role_count: number;
  agent_count: number;
  project_count: number;
  created_at: string;
}

export interface OrgUnit {
  uuid: string;
  name: string;
  kind: string;
  parent: string | null;
  order: number;
}

export interface Capability {
  uuid: string;
  key: string;
  name: string;
  description: string;
}

export interface Role {
  id: number;
  uuid: string;
  key: string;
  name: string;
  description: string;
  unit: string | null;
  unit_name: string;
  capability_keys: string[];
  is_seed: boolean;
}

export interface RoleAssignment {
  uuid: string;
  role: string | null;
  role_key: string;
  role_name: string;
  is_primary: boolean;
}

export type ActorKind = "human" | "ai_agent" | "hybrid" | "system";

export interface Actor {
  uuid: string;
  kind: ActorKind;
  name: string;
  presence: string;
  username: string;
  agent_key: string;
  role_assignments: RoleAssignment[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Agent {
  uuid: string;
  key: string;
  name: string;
  title: string;
  description: string;
  role: number | null;
  role_name: string;
  model: number | null;
  model_key: string;
  provider: string;
  provider_name: string;
  credential: number | null;
  credential_label: string;
  temperature: number;
  max_output_tokens: number;
  context_limit: number;
  token_budget: number;
  cost_budget: number;
  status: string;
  is_enabled: boolean;
  system_prompt: string;
  config: Record<string, unknown>;
  created_at: string;
}

export interface KnowledgeSource {
  uuid: string;
  agent: string;
  agent_name: string;
  name: string;
  kind: "text" | "url" | "file" | "memory";
  content: string;
  url: string;
  metadata: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelProvider {
  id: number;
  uuid: string;
  key: string;
  name: string;
  adapter: string;
  adapter_label: string;
  base_url: string;
  config: Record<string, unknown>;
  is_active: boolean;
  credential_count: number;
  model_count: number;
  created_at: string;
}

export interface Credential {
  id: number;
  uuid: string;
  provider: number;
  provider_name: string;
  label: string;
  secret_hint: string;
  configured_fields: Record<string, string>;
}

export interface ProviderCredentialField {
  key: string;
  label: string;
  secret: boolean;
  required: boolean;
  multiline?: boolean;
}

export interface ProviderCatalogEntry {
  index: number;
  key: string;
  name: string;
  category: string;
  capabilities: string[];
  adapter: string;
  base_url: string;
  website: string;
  docs_url: string;
  credential_fields: ProviderCredentialField[];
  configuration_required: boolean;
  local: boolean;
}

export interface ProviderCatalog {
  count: number;
  categories: string[];
  results: ProviderCatalogEntry[];
}

export interface ModelInfo {
  id: number;
  uuid: string;
  key: string;
  remote_id: string;
  name: string;
  provider: number;
  provider_key: string;
  provider_name: string;
  context_window: number;
  max_output_tokens: number;
  input_cost_per_1k: number | string;
  output_cost_per_1k: number | string;
  default_params: Record<string, unknown>;
  is_active: boolean;
}

export interface AgentRuntimeTestResult {
  ok: boolean;
  text?: string;
  detail?: string;
  provider: string;
  adapter: string;
  model: string;
  credential?: string | null;
  usage?: { input_tokens: number; output_tokens: number; total_tokens: number };
  cost?: number;
  latency_ms: number;
}

export type NodeType =
  | "start"
  | "end"
  | "task"
  | "agent"
  | "decision"
  | "loop"
  | "parallel"
  | "human"
  | string;

export interface WorkflowNode {
  uuid: string;
  key: string;
  name: string;
  type: NodeType;
  agent_key: string;
  role_key: string;
  arena_uuid: string | null;
  arena_name: string;
  config: Record<string, unknown>;
  position_x: number;
  position_y: number;
}

export interface WorkflowEdge {
  uuid: string;
  source_key: string;
  target_key: string;
  label: string;
  condition: string;
  order: number;
}

export interface Workflow {
  id: number;
  uuid: string;
  key: string;
  name: string;
  description: string;
  workspace: string | null;
  workspace_name: string;
  version: number;
  status: string;
  config: Record<string, unknown>;
  node_count: number;
  created_at: string;
}

export interface WorkflowGraph extends Workflow {
  arenas: Arena[];
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface Arena {
  uuid: string;
  workspace: string;
  workflow: string;
  name: string;
  description: string;
  color: string;
  order: number;
  config: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface WorkflowTestResult {
  execution: ExecutionDetail;
  project_uuid: string;
  warnings: string[];
}

export type ProjectStatus =
  | "draft"
  | "active"
  | "running"
  | "completed"
  | "archived"
  | string;

export interface Task {
  uuid: string;
  title: string;
  description: string;
  kind: string;
  issue_type: string;
  priority: string;
  status: string;
  labels: string[];
  acceptance_criteria: string;
  due_at: string | null;
  rank: number;
  assigned_actor: string | null;
  node_key: string;
  assigned_actor_name: string;
  iteration: number;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  created_at: string;
}

export interface Intervention {
  uuid: string;
  execution: number;
  node_key: string;
  task: number | null;
  kind: "approval" | "human_task" | "operator";
  status: "pending" | "approved" | "completed" | "rejected" | "cancelled";
  iteration: number;
  prompt: string;
  response: string;
  assigned_actor_name: string;
  resolved_by_name: string;
  metadata: Record<string, unknown>;
  resolved_at: string | null;
  created_at: string;
}

export interface Project {
  uuid: string;
  key: string;
  name: string;
  idea: string;
  requirements: string[];
  status: ProjectStatus;
  workflow: number | null;
  workflow_key: string;
  owner_name: string;
  workspace_key: string;
  context: Record<string, unknown>;
  task_count: number;
  execution_count: number;
  workflow_count: number;
  workflows: Array<{ uuid: string; key: string; name: string; status: string; node_count: number }>;
  created_at: string;
}

export interface ProjectDetail extends Project {
  tasks: Task[];
}

export interface WorkspaceRepository {
  initialized: boolean;
  branch: string;
  dirty: boolean;
  status: string[];
  files: string[];
  commits: Array<{ hash: string; short_hash: string; date: string; author: string; message: string }>;
}

export type ExecutionStatus =
  | "pending"
  | "queued"
  | "running"
  | "waiting"
  | "waiting_for_approval"
  | "paused"
  | "succeeded"
  | "failed"
  | "cancelled"
  | string;

export interface NodeRun {
  uuid: string;
  node_key: string;
  node_type: string;
  status: string;
  iteration: number;
  summary: string;
  outputs: Record<string, unknown>;
  model_key: string;
  input_tokens: number;
  output_tokens: number;
  cost: number | string;
  started_at: string | null;
  finished_at: string | null;
  error: string;
  created_at: string;
}

export interface LoopState {
  uuid: string;
  node_key: string;
  iteration: number;
  consecutive_failures: number;
  max_iterations: number;
  max_duration_seconds: number;
  max_cost: number | string;
  failure_threshold: number;
  is_active: boolean;
  stop_reason: string;
  started_at: string | null;
}

export interface Execution {
  uuid: string;
  project: number | null;
  project_key: string;
  workflow: number | null;
  workflow_key: string;
  status: ExecutionStatus;
  stop_reason: string;
  scenario: string;
  context: Record<string, unknown>;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number | string;
  started_at: string | null;
  finished_at: string | null;
  error: string;
  created_at: string;
}

export interface ExecutionDetail extends Execution {
  node_runs: NodeRun[];
  loop_states: LoopState[];
  interventions: Intervention[];
}

export interface EventItem {
  uuid: string;
  seq: number;
  type: string;
  level: string;
  message: string;
  data: Record<string, unknown>;
  node_key: string;
  created_at: string;
}

export interface Artifact {
  uuid: string;
  kind: string;
  name: string;
  path: string;
  content_type: string;
  iteration: number;
  project_key: string;
  produced_by_name: string;
  node_key: string;
  created_at: string;
}

export interface ArtifactDetail extends Artifact {
  content: string;
  project: number | null;
  metadata: Record<string, unknown>;
}

export interface Evaluation {
  uuid: string;
  project: number | null;
  project_key: string;
  node_key: string;
  iteration: number;
  verdict: string;
  passed: boolean;
  score: number | string;
  tests_passed: boolean;
  tests_total: number;
  tests_failed: number;
  requirement_coverage: number | string;
  critical_errors: number;
  coverage_threshold: number | string;
  summary: string;
  feedback: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Message {
  uuid: string;
  role: string;
  sender_name: string;
  node_key: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  uuid: string;
  title?: string;
  project_key?: string;
  messages: Message[];
}

export type Scenario = "success" | "fail_once" | "always_fail";
