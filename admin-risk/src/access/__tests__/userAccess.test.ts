import { describe, expect, it } from 'vitest';
import { canAccessRoute, hasAnyPermission, hasEveryPermission, hasPermission } from '../userAccess';

describe('userAccess', () => {
  it('matches browser permission points exactly', () => {
    expect(hasPermission(['user.read'], 'user.read')).toBe(true);
    expect(hasPermission(['*'], 'user.read')).toBe(false);
  });

  it('supports all-of and any-of requirements without wildcard expansion', () => {
    const granted = ['profile.read_self', 'member.holding.read_self'];
    expect(hasEveryPermission(granted, ['profile.read_self', 'member.holding.read_self'])).toBe(
      true,
    );
    expect(hasEveryPermission(granted, ['profile.read_self', 'user.read'])).toBe(false);
    expect(hasAnyPermission(granted, ['user.read', 'profile.read_self'])).toBe(true);
    expect(hasAnyPermission(['*'], ['user.read', 'profile.read_self'])).toBe(false);
  });

  it('evaluates route all-of and any-of metadata consistently', () => {
    expect(
      canAccessRoute(['profile.read_self', 'member.holding.read_self'], {
        permissions: 'profile.read_self',
        anyPermissions: ['member.holding.read_self', 'user.read'],
      }),
    ).toBe(true);
    expect(
      canAccessRoute(['profile.read_self'], {
        permissions: 'profile.read_self',
        anyPermissions: ['member.holding.read_self', 'user.read'],
      }),
    ).toBe(false);
  });
});
