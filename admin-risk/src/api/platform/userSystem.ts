import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

export type HumanRole = 'ceo' | 'tech_lead' | 'employee' | 'member';
export type PublicRegistrationRole = 'employee' | 'member';
export type UserLifecycleStatus = 'pending' | 'active' | 'disabled' | 'rejected';
export type ManagedLifecycleStatus = 'active' | 'disabled';
export type UserSortField = 'username' | 'registered_at' | 'last_login_at' | 'updated_at';
export type SortDirection = 'asc' | 'desc';

export interface UserSelf {
  userId: string;
  username: string;
  displayName?: string;
  realName?: string;
  avatarKey?: string;
  phone?: string;
  email?: string;
  role: HumanRole;
  department?: string;
  memberType?: string;
  status: UserLifecycleStatus;
  registeredAt: string;
  lastLoginAt?: string;
  rowVersion: number;
}

export interface CurrentSession {
  sessionId: string;
  expiresAt: string;
  lastReauthenticatedAt?: string;
}

export interface AuthenticationState {
  user: UserSelf;
  permissions: string[];
  session: CurrentSession;
  csrfToken: string;
}

export interface RegistrationPayload {
  username: string;
  realName: string;
  email?: string;
  phone?: string;
  requestedRole: PublicRegistrationRole;
  department?: string;
  memberType?: string;
  applicationNote?: string;
  password: string;
  passwordConfirmation: string;
  privacyAccepted: boolean;
}

export interface RegistrationResult {
  applicationId: string;
  status: 'pending';
  message: string;
}

export interface UpdateSelfPayload {
  displayName?: string;
  email?: string;
  phone?: string;
  expectedVersion: number;
}

export interface SessionSummary {
  sessionId: string;
  current: boolean;
  createdAt: string;
  expiresAt: string;
  idleExpiresAt: string;
  lastSeenAt: string;
  lastReauthenticatedAt?: string;
  ipSummary?: string;
  userAgentSummary?: string;
}

export interface ActionResult {
  status: 'ok';
  revokedSessionCount?: number;
}

export interface AvatarMutationResult {
  avatarKey?: string;
  rowVersion: number;
}

export interface AdminUserSummary {
  userId: string;
  username: string;
  displayName?: string;
  realName?: string;
  avatarKey?: string;
  phone?: string;
  email?: string;
  contactMasked: boolean;
  role?: HumanRole;
  requestedRole?: PublicRegistrationRole;
  department?: string;
  memberType?: string;
  status: UserLifecycleStatus;
  registeredAt: string;
  lastLoginAt?: string;
  activeSessionCount: number;
  rowVersion: number;
}

export interface AdminUserDetail extends AdminUserSummary {
  applicationNote?: string;
  rejectionReason?: string;
  permissions: string[];
  createdAt: string;
  updatedAt: string;
}

export interface AdminUserPage {
  items: AdminUserSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface AdminUserListParams {
  search?: string;
  role?: HumanRole;
  status?: UserLifecycleStatus;
  createdFrom?: string;
  createdTo?: string;
  sortBy?: UserSortField;
  sortDirection?: SortDirection;
  page?: number;
  pageSize?: number;
}

export interface CreateAdminUserPayload {
  username: string;
  displayName?: string;
  realName: string;
  email?: string;
  phone?: string;
  role: HumanRole;
  department?: string;
  memberType?: string;
}

export interface CreateAdminUserResult {
  user: AdminUserDetail;
  resetTicket: string;
  resetTicketExpiresAt: string;
}

export interface UpdateAdminUserPayload {
  displayName?: string;
  realName?: string;
  email?: string;
  phone?: string;
  department?: string;
  memberType?: string;
  expectedVersion: number;
}

export interface PasswordResetTicketResult {
  resetTicket: string;
  expiresAt: string;
  revokedSessionCount: number;
}

export interface UserAuditEvent {
  eventId: string;
  eventType: string;
  actorUserId?: string;
  result?: string;
  authMethod?: string;
  requestId?: string;
  details: Record<string, unknown>;
  createdAt: string;
}

export interface UserSystemErrorBody {
  code?: string;
  message?: string;
}

export class UserSystemApiError extends Error {
  readonly status?: number;
  readonly code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = 'UserSystemApiError';
    this.status = status;
    this.code = code;
  }
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);
const client: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

let csrfToken = '';

export function setUserSystemCsrfToken(value?: string): void {
  csrfToken = value || '';
}

export function clearUserSystemSessionMemory(): void {
  csrfToken = '';
}

export function getUserSystemCsrfToken(): string {
  return csrfToken;
}

client.interceptors.request.use((config) => {
  const method = String(config.method || 'GET').toUpperCase();
  if (!SAFE_METHODS.has(method) && csrfToken) {
    config.headers.set('X-CSRF-Token', csrfToken);
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const payload = error.response?.data as
      | { detail?: UserSystemErrorBody | string; message?: string }
      | undefined;
    const detail = payload?.detail;
    const body = typeof detail === 'object' && detail ? detail : undefined;
    const message =
      body?.message ||
      (typeof detail === 'string' ? detail : undefined) ||
      payload?.message ||
      error.message ||
      '用户系统请求失败';
    return Promise.reject(
      new UserSystemApiError(message, error.response?.status, body?.code),
    );
  },
);

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await client.request<T>(config);
  return response.data;
}

function acceptAuthenticationState(state: AuthenticationState): AuthenticationState {
  setUserSystemCsrfToken(state.csrfToken);
  return state;
}

export async function registerUser(payload: RegistrationPayload): Promise<RegistrationResult> {
  return request({ method: 'POST', url: '/auth/register', data: payload });
}

export async function loginUser(username: string, password: string): Promise<AuthenticationState> {
  const state = await request<AuthenticationState>({
    method: 'POST',
    url: '/auth/login',
    data: { username, password },
  });
  return acceptAuthenticationState(state);
}

export async function getCurrentAuthentication(): Promise<AuthenticationState> {
  const state = await request<AuthenticationState>({ method: 'GET', url: '/auth/me' });
  return acceptAuthenticationState(state);
}

export async function logoutUser(): Promise<void> {
  try {
    await request<ActionResult>({ method: 'POST', url: '/auth/logout' });
  } finally {
    clearUserSystemSessionMemory();
  }
}

export async function reauthenticateUser(password: string): Promise<void> {
  await request<ActionResult>({ method: 'POST', url: '/auth/reauth', data: { password } });
}

export async function resetPasswordWithTicket(payload: {
  username: string;
  resetTicket: string;
  newPassword: string;
  newPasswordConfirmation: string;
}): Promise<ActionResult> {
  try {
    return await request({ method: 'POST', url: '/auth/reset-password', data: payload });
  } finally {
    clearUserSystemSessionMemory();
  }
}

export async function getSelfProfile(): Promise<UserSelf> {
  return request({ method: 'GET', url: '/me' });
}

export async function updateSelfProfile(payload: UpdateSelfPayload): Promise<UserSelf> {
  return request({ method: 'PATCH', url: '/me', data: payload });
}

export async function changeSelfPassword(
  currentPassword: string,
  newPassword: string,
  newPasswordConfirmation: string,
): Promise<ActionResult> {
  try {
    return await request({
      method: 'POST',
      url: '/me/password',
      data: { currentPassword, newPassword, newPasswordConfirmation },
    });
  } finally {
    clearUserSystemSessionMemory();
  }
}

export async function listSelfSessions(): Promise<SessionSummary[]> {
  const result = await request<{ items: SessionSummary[] }>({
    method: 'GET',
    url: '/me/sessions',
  });
  return result.items;
}

export async function revokeSelfSession(sessionId: string): Promise<void> {
  await request<ActionResult>({
    method: 'DELETE',
    url: `/me/sessions/${encodeURIComponent(sessionId)}`,
  });
}

export async function revokeOtherSelfSessions(): Promise<number> {
  const result = await request<ActionResult>({
    method: 'POST',
    url: '/me/sessions/revoke-others',
  });
  return result.revokedSessionCount || 0;
}

export async function uploadSelfAvatar(
  file: File,
  expectedVersion: number,
): Promise<AvatarMutationResult> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('expectedVersion', String(expectedVersion));
  return request({
    method: 'POST',
    url: '/me/avatar',
    data: form,
  });
}

export async function deleteSelfAvatar(expectedVersion: number): Promise<AvatarMutationResult> {
  return request({
    method: 'DELETE',
    url: '/me/avatar',
    params: { expectedVersion },
  });
}

export function selfAvatarUrl(avatarKey?: string): string {
  return avatarKey ? '/api/v1/me/avatar' : '/logo.png';
}

export async function listAdminUsers(params: AdminUserListParams = {}): Promise<AdminUserPage> {
  return request({ method: 'GET', url: '/users', params });
}

export async function getAdminUser(userId: string): Promise<AdminUserDetail> {
  return request({ method: 'GET', url: `/users/${encodeURIComponent(userId)}` });
}

export async function createAdminUser(
  payload: CreateAdminUserPayload,
): Promise<CreateAdminUserResult> {
  return request({ method: 'POST', url: '/users', data: payload });
}

export async function updateAdminUser(
  userId: string,
  payload: UpdateAdminUserPayload,
): Promise<AdminUserDetail> {
  return request({
    method: 'PATCH',
    url: `/users/${encodeURIComponent(userId)}`,
    data: payload,
  });
}

export async function approveAdminUser(
  userId: string,
  finalRole: PublicRegistrationRole,
  expectedVersion: number,
): Promise<AdminUserDetail> {
  return request({
    method: 'POST',
    url: `/users/${encodeURIComponent(userId)}/approve`,
    data: { finalRole, expectedVersion },
  });
}

export async function rejectAdminUser(
  userId: string,
  reason: string,
  expectedVersion: number,
): Promise<AdminUserDetail> {
  return request({
    method: 'POST',
    url: `/users/${encodeURIComponent(userId)}/reject`,
    data: { reason, expectedVersion },
  });
}

export async function changeAdminUserRole(
  userId: string,
  role: HumanRole,
  expectedVersion: number,
): Promise<AdminUserDetail> {
  return request({
    method: 'POST',
    url: `/users/${encodeURIComponent(userId)}/role`,
    data: { role, expectedVersion },
  });
}

export async function changeAdminUserStatus(
  userId: string,
  status: ManagedLifecycleStatus,
  reason: string,
  expectedVersion: number,
): Promise<AdminUserDetail> {
  return request({
    method: 'POST',
    url: `/users/${encodeURIComponent(userId)}/status`,
    data: { status, reason, expectedVersion },
  });
}

export async function issueAdminPasswordResetTicket(
  userId: string,
): Promise<PasswordResetTicketResult> {
  return request({
    method: 'POST',
    url: `/users/${encodeURIComponent(userId)}/password-reset-tickets`,
  });
}

export async function revokeAdminUserSessions(userId: string): Promise<number> {
  const result = await request<ActionResult>({
    method: 'POST',
    url: `/users/${encodeURIComponent(userId)}/sessions/revoke`,
  });
  return result.revokedSessionCount || 0;
}

export async function getAdminUserAudit(
  userId: string,
  limit = 50,
): Promise<UserAuditEvent[]> {
  const result = await request<{ items: UserAuditEvent[] }>({
    method: 'GET',
    url: `/users/${encodeURIComponent(userId)}/audit`,
    params: { limit },
  });
  return result.items;
}
