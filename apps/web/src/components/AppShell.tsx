import type { ReactNode } from "react";

type AppShellProps = {
  topBar: ReactNode;
  notices?: ReactNode;
  sidebar: ReactNode;
  explorer: ReactNode;
  taskCenter: ReactNode;
  drawers?: ReactNode;
  modal?: ReactNode;
};

export function AppShell({ topBar, notices, sidebar, explorer, taskCenter, drawers, modal }: AppShellProps) {
  return (
    <div className="lm-app">
      {topBar}
      {notices}
      <div className="lm-layout">
        {sidebar}
        {explorer}
        {taskCenter}
      </div>
      {drawers}
      {modal}
    </div>
  );
}
