import { describe, expect, it } from 'vitest';
import {
  canAccessMatchedRoute,
  canAccessRouteMeta,
  matchedRoutePermissions,
  normalizeRoutePermissions,
} from '../routeAccess';

describe('routeAccess', () => {
  it('normalizes one or many permission points', () => {
    expect(normalizeRoutePermissions(' user.read ')).toEqual(['user.read']);
    expect(normalizeRoutePermissions(['user.read', ' ', 'user.audit.read'])).toEqual([
      'user.read',
      'user.audit.read',
    ]);
    expect(normalizeRoutePermissions(undefined)).toEqual([]);
  });

  it('requires every permission declared by matched parent and child records', () => {
    const matched = [
      { meta: { permissions: 'profile.read_self' } },
      { meta: { permissions: ['member.holding.read_self', 'profile.read_self'] } },
    ];
    expect(matchedRoutePermissions(matched)).toEqual([
      'profile.read_self',
      'member.holding.read_self',
    ]);
    expect(
      canAccessMatchedRoute(matched, ['profile.read_self', 'member.holding.read_self']),
    ).toBe(true);
    expect(canAccessMatchedRoute(matched, ['profile.read_self'])).toBe(false);
  });

  it('allows routes without a permission declaration', () => {
    expect(canAccessRouteMeta(undefined, [])).toBe(true);
    expect(canAccessRouteMeta({}, [])).toBe(true);
  });

  it('does not treat API-key wildcard syntax as a browser route permission', () => {
    expect(canAccessRouteMeta({ permissions: 'user.read' }, ['*'])).toBe(false);
    expect(canAccessRouteMeta({ permissions: 'user.read' }, ['user.read'])).toBe(true);
  });
});
