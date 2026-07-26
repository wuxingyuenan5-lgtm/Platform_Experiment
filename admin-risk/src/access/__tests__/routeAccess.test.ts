import { describe, expect, it } from 'vitest';
import {
  canAccessMatchedRoute,
  canAccessRouteMeta,
  filterPermissionTree,
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

  it('filters inaccessible menu and route branches without mutating the source', () => {
    const source = [
      {
        path: '/account',
        meta: { permissions: 'profile.read_self' },
        children: [
          {
            path: 'index',
            meta: { permissions: 'profile.read_self' },
          },
        ],
      },
      {
        path: '/risk',
        children: [
          {
            path: 'users',
            meta: { permissions: 'user.read' },
          },
          {
            path: 'detail',
          },
        ],
      },
    ];

    const filtered = filterPermissionTree(source, ['profile.read_self']);
    expect(filtered).toEqual([
      {
        path: '/account',
        meta: { permissions: 'profile.read_self' },
        children: [
          {
            path: 'index',
            meta: { permissions: 'profile.read_self' },
            children: [],
          },
        ],
      },
      {
        path: '/risk',
        children: [
          {
            path: 'detail',
            children: [],
          },
        ],
      },
    ]);
    expect(source[1].children).toHaveLength(2);
  });

  it('removes an empty parent whose protected children are all denied', () => {
    const source = [
      {
        path: '/users',
        children: [
          {
            path: 'index',
            meta: { permissions: 'user.read' },
          },
        ],
      },
    ];
    expect(filterPermissionTree(source, [])).toEqual([]);
  });
});
