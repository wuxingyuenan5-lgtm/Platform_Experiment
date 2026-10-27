import { setStrategyQuerySession } from '@/api/platform/strategyQueries';
import type { UserInfo } from '#/store';
import type { ErrorMessageMode } from '#/axios';
import { defineStore } from 'pinia';
import { store } from '@/store';
import { PageEnum } from '@/enums/pageEnum';
import { clearAuthCache } from '@/utils/auth';
import type { LoginParams } from '@/api/sys/model/userModel';
import {
  clearUserSystemSessionMemory,
  getCurrentAuthentication,
  getUserSystemCsrfToken,
  isUserSystemServiceUnavailable,
  loginUser,
  logoutUser,
  selfAvatarUrl,
  type AuthenticationState,
} from '@/api/platform/userSystem';
import { useI18n } from '@/hooks/web/useI18n';
import { useMessage } from '@/hooks/web/useMessage';
import { router } from '@/router';
import { usePermissionStore } from '@/store/modules/permission';
import { h } from 'vue';
import { message } from 'ant-design-vue';

interface LegacyAccountOption {
  id?: string | number;
  value?: string | number;
  label?: string;
  checkCode?: string;
  platform?: string;
}

interface LegacyProductOption {
  id?: string | number;
  value?: string | number;
  label?: string;
  children?: LegacyAccountOption[];
}

interface UserState {
  userInfo: Nullable<UserInfo>;
  roleList: string[];
  sessionTimeout: boolean;
  lastUpdateTime: number;
  hydrationAttempted: boolean;
  authenticated: boolean;
  sessionUnavailable: boolean;
  authentication: AuthenticationState | null;
  optionsMap?: Record<string, unknown> | null;
  account?: unknown;
}

function toLegacyUserInfo(authentication: AuthenticationState): UserInfo {
  const { user, permissions } = authentication;
  const displayName = user.displayName || user.realName || user.username;
  const homePath = user.role === 'member' ? '/account' : '/home/index';
  return {
    roles: [{ roleName: user.role, value: user.role }],
    userId: user.userId,
    username: user.username,
    realName: displayName,
    avatar: selfAvatarUrl(user.avatarKey),
    desc: '',
    role: user.role,
    name: displayName,
    homePath,
    permissions,
    data: {
      userInfo: {
        userId: user.userId,
        username: user.username,
        name: displayName,
        role: user.role,
        avatarKey: user.avatarKey,
        status: user.status,
      },
      path: [],
      product: [],
    },
  } as UserInfo;
}

export const useUserStore = defineStore({
  id: 'app-user',
  state: (): UserState => ({
    userInfo: null,
    roleList: [],
    sessionTimeout: false,
    lastUpdateTime: 0,
    hydrationAttempted: false,
    authenticated: false,
    sessionUnavailable: false,
    authentication: null,
    optionsMap: null,
    account: null,
  }),
  getters: {
    getUserInfoInfo(state): Record<string, unknown> {
      return ((state.userInfo as any)?.data?.userInfo || {}) as Record<string, unknown>;
    },
    getUserInfoAccount(state): LegacyProductOption[] {
      return ((state.userInfo as any)?.data?.product || []) as LegacyProductOption[];
    },
    getOptionsMap(state): Record<string, unknown> {
      return state.optionsMap || {};
    },
    getUserInfo(state): UserInfo {
      return (state.userInfo || {}) as UserInfo;
    },
    // Kept only for legacy callers while the route guard migrates to getIsAuthenticated.
    // It is an in-memory marker, never a credential and never persisted.
    getToken(state): string {
      return state.authenticated && getUserSystemCsrfToken() ? 'browser-session' : '';
    },
    getRoleList(state): string[] {
      return state.roleList;
    },
    getIsAuthenticated(state): boolean {
      return state.authenticated && Boolean(getUserSystemCsrfToken());
    },
    getHydrationAttempted(state): boolean {
      return state.hydrationAttempted;
    },
    getSessionUnavailable(state): boolean {
      return state.sessionUnavailable;
    },
    getAuthentication(state): AuthenticationState | null {
      return state.authentication;
    },
    getSessionTimeout(state): boolean {
      return state.sessionTimeout;
    },
    getLastUpdateTime(state): number {
      return state.lastUpdateTime;
    },
  },
  actions: {
    setOptionsMap(optionsMap?: Record<string, unknown> | null) {
      this.optionsMap = optionsMap || {};
    },
    setRoleList(roleList: string[]) {
      this.roleList = roleList;
    },
    setUserInfo(info: UserInfo | null) {
      this.userInfo = info;
      this.lastUpdateTime = info ? Date.now() : 0;
    },
    setSessionTimeout(flag: boolean) {
      this.sessionTimeout = flag;
    },
    setToken(token?: string) {
      if (token) return;
      this.resetState();
      this.hydrationAttempted = true;
    },
    applyAuthentication(authentication: AuthenticationState) {
      setStrategyQuerySession(
        authentication.user.userId,
        JSON.stringify([
          authentication.user.role,
          authentication.permissions,
          getUserSystemCsrfToken(),
        ]),
      );
      if (!this.authenticated) clearAuthCache();
      if (JSON.stringify(this.authentication) !== JSON.stringify(authentication)) {
        this.authentication = authentication;
      }
      this.authenticated = true;
      this.sessionUnavailable = false;
      this.hydrationAttempted = true;
      this.sessionTimeout = false;
      if (this.roleList.length !== 1 || this.roleList[0] !== authentication.user.role) {
        this.setRoleList([authentication.user.role]);
      }
      const info = toLegacyUserInfo(authentication);
      // Verification still runs on every navigation. Keep unchanged UI projections
      // stable so a renewed session does not invalidate the whole application.
      if (JSON.stringify(this.userInfo) !== JSON.stringify(info)) this.setUserInfo(info);
      const permissionStore = usePermissionStore();
      if (
        JSON.stringify(permissionStore.getPermCodeList) !==
        JSON.stringify(authentication.permissions)
      ) {
        permissionStore.setPermCodeList(authentication.permissions);
      }
    },
    resetState() {
      setStrategyQuerySession();
      this.userInfo = null;
      this.account = null;
      this.roleList = [];
      this.sessionTimeout = false;
      this.optionsMap = null;
      this.authentication = null;
      this.authenticated = false;
      this.sessionUnavailable = false;
      this.lastUpdateTime = 0;
      clearUserSystemSessionMemory();
      clearAuthCache();
      const permissionStore = usePermissionStore();
      permissionStore.resetState();
    },
    async login(
      params: LoginParams & {
        goHome?: boolean;
        mode?: ErrorMessageMode;
      },
    ): Promise<UserInfo | null> {
      const { goHome = true, ...loginParams } = params;
      const username = loginParams.username || loginParams.name || '';
      const authentication = await loginUser(username, loginParams.password);
      this.applyAuthentication(authentication);
      return this.afterLoginAction(goHome, false);
    },
    async afterLoginAction(goHome = true, hydrate = true): Promise<UserInfo | null> {
      if (hydrate && !this.getIsAuthenticated) {
        await this.getUserInfoAction();
      }
      if (!this.getIsAuthenticated || !this.userInfo) return null;

      if (goHome) {
        await router.replace((this.userInfo as any).homePath || PageEnum.BASE_HOME);
      }
      return this.userInfo;
    },
    async getUserInfoAction(): Promise<UserInfo | null> {
      try {
        const authentication = await getCurrentAuthentication();
        this.applyAuthentication(authentication);
        return this.userInfo;
      } catch (error) {
        const serviceUnavailable = isUserSystemServiceUnavailable(error);
        // A loaded browser session remains usable while the auth service is
        // temporarily unreachable. Only a definitive auth failure may clear it.
        if (!serviceUnavailable || !this.authenticated) this.resetState();
        // An unreachable API has not decided whether the cookie is valid.
        // Preserve an already verified page, while refusing new protected navigation.
        this.sessionUnavailable = serviceUnavailable;
        this.hydrationAttempted = !serviceUnavailable;
        throw error;
      }
    },
    async hydrateSession(forceVerify = false): Promise<boolean> {
      if (!forceVerify && this.authenticated && getUserSystemCsrfToken()) return true;
      if (forceVerify && this.authenticated && getUserSystemCsrfToken()) {
        try {
          await this.getUserInfoAction();
          return this.getIsAuthenticated;
        } catch {
          return false;
        }
      }
      if (this.authenticated) {
        this.resetState();
        this.hydrationAttempted = false;
      }
      if (this.hydrationAttempted) return false;
      try {
        await this.getUserInfoAction();
        return this.getIsAuthenticated;
      } catch {
        return false;
      }
    },
    async logout(goLogin = false) {
      if (this.authenticated) {
        try {
          await logoutUser();
        } catch {
          // Local state must still clear when a server Session is already invalid.
        }
      }
      this.resetState();
      this.hydrationAttempted = true;
      message.destroy();
      if (goLogin) await router.push(PageEnum.BASE_LOGIN);
    },
    confirmLoginOut() {
      const { createConfirm } = useMessage();
      const { t } = useI18n();
      createConfirm({
        iconType: 'warning',
        title: () => h('span', t('sys.app.logoutTip')),
        content: () => h('span', t('sys.app.logoutMessage')),
        onOk: async () => {
          await this.logout(true);
        },
      });
    },
  },
});

export function useUserStoreWithOut() {
  return useUserStore(store);
}
