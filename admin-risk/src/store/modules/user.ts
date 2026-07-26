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

interface UserState {
  userInfo: Nullable<UserInfo>;
  roleList: string[];
  sessionTimeout: boolean;
  lastUpdateTime: number;
  hydrationAttempted: boolean;
  authenticated: boolean;
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
    authentication: null,
    optionsMap: null,
    account: null,
  }),
  getters: {
    getUserInfoInfo(state): Record<string, unknown> {
      return ((state.userInfo as any)?.data?.userInfo || {}) as Record<string, unknown>;
    },
    getUserInfoAccount(state): unknown[] {
      return ((state.userInfo as any)?.data?.product || []) as unknown[];
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
      return state.authenticated ? 'browser-session' : '';
    },
    getRoleList(state): string[] {
      return state.roleList;
    },
    getIsAuthenticated(state): boolean {
      return state.authenticated;
    },
    getHydrationAttempted(state): boolean {
      return state.hydrationAttempted;
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
    applyAuthentication(authentication: AuthenticationState) {
      clearAuthCache();
      this.authentication = authentication;
      this.authenticated = true;
      this.hydrationAttempted = true;
      this.sessionTimeout = false;
      this.setRoleList([authentication.user.role]);
      this.setUserInfo(toLegacyUserInfo(authentication));
      const permissionStore = usePermissionStore();
      permissionStore.setPermCodeList(authentication.permissions);
    },
    resetState() {
      this.userInfo = null;
      this.account = null;
      this.roleList = [];
      this.sessionTimeout = false;
      this.optionsMap = null;
      this.authentication = null;
      this.authenticated = false;
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
      if (hydrate && !this.authenticated) {
        await this.getUserInfoAction();
      }
      if (!this.authenticated || !this.userInfo) return null;

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
        this.hydrationAttempted = true;
        this.resetState();
        throw error;
      }
    },
    async hydrateSession(): Promise<boolean> {
      if (this.authenticated) return true;
      if (this.hydrationAttempted) return false;
      try {
        await this.getUserInfoAction();
        return this.authenticated;
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
