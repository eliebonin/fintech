import type {CSSProperties} from 'react';

/** Presentation only: status colours and financial display semantics remain feature-owned. */
export const workspacePresentation={
 primary:'#1f5eff',ink:'#172238',muted:'#52627a',border:'#dbe3ef',background:'#f3f6fb',
 controlRadius:8,actionHeight:40,compactActionHeight:32,
} as const;

export const workspaceCssVariables={
 '--workspace-primary':workspacePresentation.primary,
 '--workspace-ink':workspacePresentation.ink,
 '--workspace-muted':workspacePresentation.muted,
 '--workspace-border':workspacePresentation.border,
 '--workspace-background':workspacePresentation.background,
 '--workspace-control-radius':`${workspacePresentation.controlRadius}px`,
 '--workspace-action-height':`${workspacePresentation.actionHeight}px`,
} as CSSProperties;
