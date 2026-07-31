export function validatePassword(password: string) {
  // 正确的正则表达式：
  // ^                 - 字符串开始
  // (?=.*[\dA-Za-z])  - 必须包含数字或字母
  // |                 - 或
  // (?=.*[\W_])       - 必须包含特殊字符
  // [\da-zA-Z\W_]{8,16}$ - 允许的字符范围，长度8-16
  const regex = /^(?:(?=.*\d)(?=.*[a-zA-Z])|(?=.*\d)(?=.*[\W_]))[\da-zA-Z\W_]{8,16}$/;
  return regex.test(password);
}

// 验证手机号
export function validatePhone(phone: string) {
  const regex = /^1[3456789]\d{9}$/;
  return regex.test(phone);
}

// 验证邮箱
export function validateEmail(email: string) {
  const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return regex.test(email);
}
