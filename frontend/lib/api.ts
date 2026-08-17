// Single typed fetch client for the whole app.
//
// - Base URL comes from NEXT_PUBLIC_API_BASE (same-origin by default).
// - Every request carries the JWT access token as `Authorization: Bearer <token>`.
// - A 401 clears the stored session and bounces the user to /login.
//
// All resource helpers live at the bottom so pages import one thing.
import { getAccess, getActiveOrganization, clearSession, saveSession } from "./auth";
import type {
  Paginated,
  LoginResponse,
  User,
  Organization,
  OrgUnit,
  Capability,
  Role,
  Actor,
  Agent,
  KnowledgeSource,
  ModelInfo,
  ModelProvider,
  Credential,
  ProviderCatalog,
  ProviderCatalogEntry,
  Workflow,
  WorkflowGraph,
  Project,
  ProjectDetail,
  WorkspaceRepository,
  Execution,
  ExecutionDetail,
  EventItem,
  Artifact,
  ArtifactDetail,
  Evaluation,
  Intervention,
  Task,
  Conversation,
  Scenario,
  WorkflowValidation,
  WorkflowTestResult,
  AgentRuntimeTestResult,
  Arena,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  // Skip the auth header (only the login call needs this).
  anonymous?: boolean;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, anonymous = false, signal } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (!anonymous) {
    const token = getAccess();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const organization = getActiveOrganization();
    if (organization) headers["X-Organization"] = organization;
  }

  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
    cache: "no-store",
  });

  if (res.status === 401 && !anonymous) {
    // Token expired or invalid — drop the session and redirect.
    clearSession();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "unauthorized", null);
  }

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const message =
      (data && typeof data === "object" && "detail" in data
        ? String((data as Record<string, unknown>).detail)
        : `request failed (${res.status})`) || `request failed (${res.status})`;
    throw new ApiError(res.status, message, data);
  }

  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// Some list endpoints paginate, some (small seed tables) may return a bare array.
// Normalise both to a plain array so callers don't branch.
function asList<T>(payload: Paginated<T> | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await request<LoginResponse>("/auth/login/", {
    method: "POST",
    body: { username, password },
    anonymous: true,
  });
  saveSession(res.access, res.refresh, res.user);
  return res;
}

export function me(): Promise<User> {
  return request<User>("/auth/me/");
}

// ---------------------------------------------------------------------------
// Resource helpers
// ---------------------------------------------------------------------------

async function list<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const payload = await request<Paginated<T> | T[]>(path, { signal });
  return asList<T>(payload);
}

export function paginated<T>(path: string, signal?: AbortSignal): Promise<Paginated<T>> {
  return request<Paginated<T>>(path, { signal });
}

export const listOrganizations = (s?: AbortSignal) =>
  list<Organization>("/organizations/", s);
export function createOrganization(input: { name: string; type?: string; description?: string }): Promise<Organization> {
  return request<Organization>("/organizations/", { method: "POST", body: input });
}
export const listUnits = (s?: AbortSignal) => list<OrgUnit>("/units/?page_size=200", s);
export const listCapabilities = (s?: AbortSignal) =>
  list<Capability>("/capabilities/", s);
export const listRoles = (s?: AbortSignal) => list<Role>("/roles/?page_size=200", s);
export const listActors = (s?: AbortSignal) => list<Actor>("/actors/", s);
export function createActor(input: { name: string; kind: "human" | "hybrid"; role_ids?: number[]; user?: number | null }): Promise<Actor> {
  return request<Actor>("/actors/", { method: "POST", body: input });
}
export const listAgents = (s?: AbortSignal) => list<Agent>("/agents/?page_size=200", s);
export const listModels = (s?: AbortSignal) => list<ModelInfo>("/models/?page_size=200", s);
export const listProviders = (s?: AbortSignal) =>
  list<ModelProvider>("/providers/?page_size=200", s);
export const listCredentials = (s?: AbortSignal) =>
  list<Credential>("/credentials/?page_size=200", s);

export function searchAgents(params: { search?: string; unit?: string; status?: string; page?: number; pageSize?: number }, signal?: AbortSignal) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.unit) query.set("unit", params.unit);
  if (params.status) query.set("status", params.status);
  query.set("page", String(params.page || 1));
  query.set("page_size", String(params.pageSize || 24));
  return paginated<Agent>(`/agents/?${query}`, signal);
}

export function searchRoles(search = "", pageSize = 50, signal?: AbortSignal) {
  const query = new URLSearchParams({ search, page_size: String(pageSize) });
  return paginated<Role>(`/roles/?${query}`, signal);
}
export const listWorkflows = (s?: AbortSignal) => list<Workflow>("/workflows/", s);
export const listWorkspaceWorkflows = (workspaceUuid: string, s?: AbortSignal) => list<Workflow>(`/workflows/?workspace=${workspaceUuid}`, s);
export const listProjects = (s?: AbortSignal) => list<Project>("/projects/", s);
export const listExecutions = (s?: AbortSignal) =>
  list<Execution>("/executions/", s);
export const listConversations = (s?: AbortSignal) =>
  list<Conversation>("/conversations/", s);

export const getWorkflow = (uuid: string, s?: AbortSignal) =>
  request<WorkflowGraph>(`/workflows/${uuid}/`, { signal: s });

export const getProject = (uuid: string, s?: AbortSignal) =>
  request<ProjectDetail>(`/projects/${uuid}/`, { signal: s });
export const getWorkspaceRepository = (uuid: string, s?: AbortSignal) => request<WorkspaceRepository>(`/projects/${uuid}/repository/`, { signal: s });
export const getWorkspaceRevision = (uuid: string, revision = "HEAD", s?: AbortSignal) => request<{ diff: string }>(`/projects/${uuid}/repository-diff/?revision=${encodeURIComponent(revision)}`, { signal: s });

export const getExecution = (uuid: string, s?: AbortSignal) =>
  request<ExecutionDetail>(`/executions/${uuid}/`, { signal: s });

export const getConversation = (uuid: string, s?: AbortSignal) =>
  request<Conversation>(`/conversations/${uuid}/`, { signal: s });

export const listEvents = (executionUuid: string, s?: AbortSignal) =>
  list<EventItem>(`/events/?execution=${executionUuid}`, s);

export const listArtifacts = (projectUuid: string, s?: AbortSignal) =>
  list<Artifact>(`/artifacts/?project=${projectUuid}`, s);

export const getArtifact = (uuid: string, s?: AbortSignal) =>
  request<ArtifactDetail>(`/artifacts/${uuid}/`, { signal: s });

export const listEvaluations = (projectUuid: string, s?: AbortSignal) =>
  list<Evaluation>(`/evaluations/?project=${projectUuid}`, s);

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function updateAgent(uuid: string, patch: Partial<Agent>): Promise<Agent> {
  return request<Agent>(`/agents/${uuid}/`, { method: "PATCH", body: patch });
}

export interface CreateAgentInput {
  name: string;
  title?: string;
  key?: string;
  description?: string;
  role?: number | null;
  model?: number | null;
  credential?: number | null;
  temperature?: number;
  max_output_tokens?: number;
  context_limit?: number;
  token_budget?: number;
  cost_budget?: number;
  status?: string;
  is_enabled?: boolean;
  initial_prompt?: string;
}

export function createAgent(input: CreateAgentInput): Promise<Agent> {
  return request<Agent>("/agents/", { method: "POST", body: input });
}

export const listKnowledgeSources = (agentUuid: string, s?: AbortSignal) => list<KnowledgeSource>(`/knowledge-sources/?agent=${agentUuid}`, s);
export function createKnowledgeSource(input: { agent: string; name: string; kind: string; content?: string; url?: string }): Promise<KnowledgeSource> {
  return request<KnowledgeSource>("/knowledge-sources/", { method: "POST", body: input });
}
export function deleteKnowledgeSource(uuid: string): Promise<void> {
  return request<void>(`/knowledge-sources/${uuid}/`, { method: "DELETE" });
}

export function testAgentRuntime(input: {
  model: number | null;
  credential: number | null;
  prompt?: string;
  input?: string;
  temperature?: number;
  max_tokens?: number;
}): Promise<AgentRuntimeTestResult> {
  return request<AgentRuntimeTestResult>("/agents/test-runtime/", { method: "POST", body: input });
}

export function getProviderCatalog(search = "", category = "", signal?: AbortSignal): Promise<ProviderCatalog> {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (category) query.set("category", category);
  return request<ProviderCatalog>(`/providers/catalog/?${query}`, { signal });
}

export interface ConnectProviderInput {
  catalog_key: string;
  key?: string;
  name?: string;
  adapter?: string;
  base_url?: string;
  credentials?: Record<string, string>;
  config?: Record<string, unknown>;
  model_id?: string;
  model_name?: string;
  context_window?: number;
  max_output_tokens?: number;
}

export function connectProvider(input: ConnectProviderInput): Promise<{ provider: ModelProvider; credential: Credential | null; model: ModelInfo | null }> {
  return request("/providers/connect/", { method: "POST", body: input });
}

export function testProvider(uuid: string, input: { mode?: "discovery" | "inference"; model_id?: string; prompt?: string } = {}): Promise<{ ok: boolean; mode: string; model_count?: number; models?: Array<{ id: string; name: string }>; text?: string; detail?: string }> {
  return request(`/providers/${uuid}/test/`, { method: "POST", body: input });
}

export function syncProviderModels(uuid: string, models: Array<{ id: string; name: string }>): Promise<{ count: number; models: ModelInfo[] }> {
  return request(`/providers/${uuid}/sync-models/`, { method: "POST", body: { models } });
}

export function updateAgentPrompt(
  uuid: string,
  content: string
): Promise<{ version: number; content: string }> {
  return request<{ version: number; content: string }>(`/agents/${uuid}/prompt/`, {
    method: "PATCH",
    body: { content },
  });
}

export interface CreateProjectInput {
  name: string;
  key: string;
  idea: string;
  requirements: string[];
  workflow?: number | null;
}

export function createProject(input: CreateProjectInput): Promise<Project> {
  return request<Project>("/projects/", { method: "POST", body: input });
}

export interface SaveWorkflowGraphInput {
  name: string;
  description: string;
  status: string;
  config: Record<string, unknown>;
  nodes: Array<{
    key: string;
    name: string;
    type: string;
    agent_key?: string;
    role_key?: string;
    arena_uuid?: string | null;
    config: Record<string, unknown>;
    position_x: number;
    position_y: number;
  }>;
  edges: Array<{
    source_key: string;
    target_key: string;
    label: string;
    condition: string;
    order: number;
  }>;
}

export function createWorkflow(input: { name: string; key?: string; description?: string; workspace?: string | null }): Promise<Workflow> {
  return request<Workflow>("/workflows/", { method: "POST", body: { ...input, status: "draft" } });
}

export function createArena(input: { workspace: string; workflow: string; name: string; description?: string; color?: string }): Promise<Arena> {
  return request<Arena>("/arenas/", { method: "POST", body: input });
}
export function createWorkflowLink(input: { workspace: string; source: string; target: string; kind: "related" | "depends_on" | "triggers" | "subworkflow" }): Promise<{ uuid: string }> {
  return request<{ uuid: string }>("/workflow-links/", { method: "POST", body: input });
}

export function saveWorkflowGraph(uuid: string, input: SaveWorkflowGraphInput): Promise<WorkflowGraph> {
  return request<WorkflowGraph>(`/workflows/${uuid}/graph/`, { method: "PUT", body: input });
}

export function validateWorkflowGraph(uuid: string, input: SaveWorkflowGraphInput): Promise<WorkflowValidation> {
  return request<WorkflowValidation>(`/workflows/${uuid}/validate/`, { method: "POST", body: input });
}

export function testWorkflow(uuid: string, scenario: Scenario = "success"): Promise<WorkflowTestResult> {
  return request<WorkflowTestResult>(`/workflows/${uuid}/test/`, { method: "POST", body: { scenario } });
}

export function startExecution(
  projectUuid: string,
  scenario: Scenario,
  workflowUuid?: string
): Promise<ExecutionDetail> {
  return request<ExecutionDetail>("/executions/start/", {
    method: "POST",
    body: { project: projectUuid, scenario, workflow: workflowUuid },
  });
}

export function pauseExecution(uuid: string, prompt: string): Promise<Intervention> {
  return request<Intervention>(`/executions/${uuid}/pause/`, { method: "POST", body: { prompt } });
}

export function resolveIntervention(uuid: string, decision: "approve" | "reject", response: string): Promise<Intervention> {
  return request<Intervention>(`/interventions/${uuid}/resolve/`, { method: "POST", body: { decision, response } });
}

export function createTask(input: { project: string; title: string; description?: string; issue_type?: string; priority?: string; status?: string; labels?: string[]; acceptance_criteria?: string; assigned_actor?: string | null }): Promise<Task> {
  return request<Task>("/tasks/", { method: "POST", body: input });
}

export function updateTask(uuid: string, patch: Partial<Task>): Promise<Task> {
  return request<Task>(`/tasks/${uuid}/`, { method: "PATCH", body: patch });
}
