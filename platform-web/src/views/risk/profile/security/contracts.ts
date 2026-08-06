export type SecurityBindingType = 0 | 1;
export type SecurityBindingOperation = 'bind' | 'change';
export type SecurityBindingAction = 'phone' | 'email' | 'feishu';

export interface PasswordFormValues {
  oldPw: string;
  newPw1: string;
  newPw2: string;
  code: string;
}

export interface PhoneFormValues {
  newPhone: string;
  code: string;
}

export interface EmailFormValues {
  newEmail: string;
  code: string;
}

export interface FeishuFormValues {
  url: string;
  code: string;
}

export interface SecurityBindingDiscriminator {
  action: SecurityBindingAction;
  operation: SecurityBindingOperation;
}

export type PhoneSubmitPayload = PhoneFormValues &
  SecurityBindingDiscriminator & {
    action: 'phone';
  };

export type EmailSubmitPayload = EmailFormValues &
  SecurityBindingDiscriminator & {
    action: 'email';
  };

export type FeishuSubmitPayload = FeishuFormValues &
  SecurityBindingDiscriminator & {
    action: 'feishu';
  };

export type SecurityBindingPayload = PhoneSubmitPayload | EmailSubmitPayload | FeishuSubmitPayload;

export function operationFromBindingType(type: SecurityBindingType): SecurityBindingOperation {
  return type === 1 ? 'change' : 'bind';
}

export function buildPasswordPayload(values: PasswordFormValues): PasswordFormValues {
  return {
    oldPw: values.oldPw,
    newPw1: values.newPw1,
    newPw2: values.newPw2,
    code: values.code,
  };
}

export function buildPhonePayload(
  type: SecurityBindingType,
  values: PhoneFormValues,
): PhoneSubmitPayload {
  return {
    ...values,
    action: 'phone',
    operation: operationFromBindingType(type),
  };
}

export function buildEmailPayload(
  type: SecurityBindingType,
  values: EmailFormValues,
): EmailSubmitPayload {
  return {
    ...values,
    action: 'email',
    operation: operationFromBindingType(type),
  };
}

export function buildFeishuPayload(
  type: SecurityBindingType,
  values: FeishuFormValues,
): FeishuSubmitPayload {
  return {
    ...values,
    action: 'feishu',
    operation: operationFromBindingType(type),
  };
}

export async function executeWithLoading<T>(
  setLoading: (loading: boolean) => void,
  task: () => Promise<T> | T,
): Promise<T> {
  setLoading(true);
  try {
    return await task();
  } finally {
    setLoading(false);
  }
}

export function resetFormWhenClosed(open: boolean, resetFields: () => void): void {
  if (!open) resetFields();
}
