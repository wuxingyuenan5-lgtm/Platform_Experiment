// Utility to format or mask company/menu display names.
// Temporarily implemented to restore previous behavior and prevent import errors.
export function maskCompanyDisplay(name?: string | null, options?: { forceLang?: 'en' | 'zh' }): string {
    if (!name) return '';

    // Force language if provided
    if (options?.forceLang === 'en') return 'Variable Global';
    if (options?.forceLang === 'zh') return '全球变量';

    // If the name contains any CJK character, treat as Chinese
    const hasCJK = /[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]/.test(name);
    return hasCJK ? '全球变量' : 'Variable Global';
}

export default maskCompanyDisplay;
