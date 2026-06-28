import { describe, expect, it } from 'vitest';

import { isTerminal, type TaskStatus } from '@/types';

describe('isTerminal', () => {
  it('is true for terminal statuses', () => {
    expect(isTerminal('completed')).toBe(true);
    expect(isTerminal('failed')).toBe(true);
  });

  it('is false for in-flight statuses', () => {
    expect(isTerminal('pending')).toBe(false);
    expect(isTerminal('running')).toBe(false);
  });

  it('selects exactly the terminal statuses', () => {
    const all: TaskStatus[] = ['pending', 'running', 'completed', 'failed'];
    expect(all.filter(isTerminal)).toEqual(['completed', 'failed']);
  });
});
