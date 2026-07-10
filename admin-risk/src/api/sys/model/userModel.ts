/**
 * @description: Login interface parameters
 */
export interface LoginParams {
  username?: string;
  name?: string;
  password: string;
  action?: string;
}

export interface RegisterParams {
  username: string;
  password: string;
  email?: string;
  requested_role: 'guest' | 'employee' | 'admin';
  department?: string;
}

export interface RegistrationRequest {
  id: number;
  username: string;
  email?: string;
  role: string;
  requested_role: string;
  approval_status: 'pending' | 'approved' | 'rejected';
  department?: string;
  rejected_reason?: string;
  created_at: string;
}

export interface RoleInfo {
  roleName: string;
  value: string;
}

/**
 * @description: Login interface return value
 */
export interface LoginResultModel {
  userId: string | number;
  token: string;
  roles: RoleInfo[];
}

/**
 * @description: Get user information return value
 */
export interface GetUserInfoModel {
  roles: RoleInfo[];
  // 用户id
  userId: string | number;
  // 用户名
  username: string;
  // 真实名字
  realName: string;
  // 头像
  avatar: string;
  // 介绍
  desc?: string;
}
