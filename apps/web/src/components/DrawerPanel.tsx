import type { ReactNode } from "react";

type DrawerPanelProps = {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
};

export function DrawerPanel({ title, open, onClose, children }: DrawerPanelProps) {
  if (!open) return null;

  return (
    <section className="lm-drawer lm-surface lm-panel" role="dialog" aria-label={title}>
      <div className="lm-drawer-head">
        <h2>{title}</h2>
        <button className="lm-btn-ghost" onClick={onClose} type="button">
          Close
        </button>
      </div>
      {children}
    </section>
  );
}
