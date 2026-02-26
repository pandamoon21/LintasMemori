import type { PreviewDialogState } from "../hooks/useActionPreviewCommit";

type PreviewConfirmModalProps = {
  preview: PreviewDialogState | null;
  busy: boolean;
  onConfirm: () => void;
  onClose: () => void;
};

export function PreviewConfirmModal({ preview, busy, onConfirm, onClose }: PreviewConfirmModalProps) {
  if (!preview) {
    return null;
  }

  return (
    <section className="lm-modal-wrap" role="dialog" aria-label="Preview confirmation">
      <div className="lm-modal lm-surface">
        <h2>{preview.title}</h2>
        <p className="lm-muted">Matched items: {preview.matchCount}</p>

        {preview.warnings.map((warning) => (
          <p className="lm-warn" key={warning}>
            {warning}
          </p>
        ))}

        <div className="lm-sample-box">
          {preview.sampleItems.slice(0, 12).map((item) => (
            <div key={item}>{item}</div>
          ))}
        </div>

        <div className="lm-modal-actions">
          <button onClick={onConfirm} disabled={busy}>
            Confirm Commit
          </button>
          <button className="lm-btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
        </div>
      </div>
    </section>
  );
}
