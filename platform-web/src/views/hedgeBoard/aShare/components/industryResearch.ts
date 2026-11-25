import type { EquityObservatory, EquityTheme, EquityThemes } from '@/api/equityObservatory';

export type IndustryObservation = NonNullable<EquityObservatory['structure']>['industries'][number];

/** The two existing sources use the same SW level-one code, with/without .SI. */
export function industryCode(value?: string | null): string {
  return value && /^\d{6}(\.SI)?$/i.test(value) ? value.slice(0, 6) : '';
}

export function industryThemes(themes: EquityThemes | null | undefined, code: string) {
  const key = industryCode(code);
  if (!key) return [];
  return (themes?.items || []).flatMap((theme) => {
    const members = [
      ...new Map(
        theme.members
          .filter((member) => industryCode(member.industryCode) === key)
          .map((member) => [member.code, member]),
      ).values(),
    ];
    return members.length ? [{ theme, members }] : [];
  });
}

export function themeIndustries(theme: EquityTheme | undefined, industries: IndustryObservation[]) {
  const members = new Map<string, Set<string>>();
  for (const member of theme?.members || []) {
    const code = industryCode(member.industryCode);
    if (!code) continue;
    if (!members.has(code)) members.set(code, new Set());
    members.get(code)!.add(member.code);
  }
  return industries
    .filter((row) => members.has(industryCode(row.code)))
    .map((row) => ({
      ...row,
      themeMemberCount: members.get(industryCode(row.code))!.size,
    }));
}
