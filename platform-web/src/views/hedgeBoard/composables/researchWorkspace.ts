import { inject, provide, ref, type InjectionKey, type Ref } from 'vue';

interface Workspace {
  states: Map<string, Ref>;
  snapshots: Map<string, { expires: number; value: unknown }>;
  page: () => string;
}
const key: InjectionKey<Workspace> = Symbol('research-workspace');

// Only the current board owns these values; no chart instances or DOM are retained.
export function provideResearchWorkspace(page: () => string) {
  const workspace: Workspace = { states: new Map(), snapshots: new Map(), page };
  provide(key, workspace);
  return workspace;
}

export function useResearchViewState<T>(name: string, initial: T): Ref<T> {
  const workspace = inject(key, null);
  const id = `${workspace?.page()}:${name}`;
  if (!workspace) return ref(initial) as Ref<T>;
  if (!workspace.states.has(id)) workspace.states.set(id, ref(initial));
  return workspace.states.get(id) as Ref<T>;
}

export function useResearchSnapshots() {
  const workspace = inject(key, null);
  return {
    get<T>(id: string): T | undefined {
      const entry = workspace?.snapshots.get(id);
      return entry && entry.expires > Date.now() ? (entry.value as T) : undefined;
    },
    set<T>(id: string, value: T) {
      if (!workspace) return;
      if (workspace.snapshots.get(id)?.value === value) return;
      // ETF navigation may visit many funds; bound retained payloads.
      if (workspace.snapshots.size >= 16) {
        workspace.snapshots.delete(workspace.snapshots.keys().next().value!);
      }
      workspace.snapshots.set(id, { expires: Date.now() + 60_000, value });
    },
  };
}
