export type RunEventIdentity = {
  id: string;
  run_id: string;
  sequence: number;
};

export class RunEventCursor {
  private readonly lastSequenceByRun = new Map<string, number>();

  last(runId: string): number {
    return this.lastSequenceByRun.get(runId) ?? 0;
  }

  accept(runId: string, event: RunEventIdentity): boolean {
    if (!runId || event.run_id !== runId) return false;
    if (!event.id || !Number.isSafeInteger(event.sequence) || event.sequence <= 0) return false;
    const previous = this.last(runId);
    if (event.sequence <= previous) return false;
    this.lastSequenceByRun.set(runId, event.sequence);
    return true;
  }

  reset(runId: string): void {
    this.lastSequenceByRun.delete(runId);
  }
}
