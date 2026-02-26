import { useState } from "react";

import { DrawerPanel } from "./DrawerPanel";

type UploadWizardDrawerProps = {
  open: boolean;
  onClose: () => void;
  busy: boolean;
  onPreviewUpload: (payload: {
    target: string;
    recursive: boolean;
    albumName: string;
  }) => Promise<void>;
};

export function UploadWizardDrawer({ open, onClose, busy, onPreviewUpload }: UploadWizardDrawerProps) {
  const [target, setTarget] = useState(".");
  const [albumName, setAlbumName] = useState("");
  const [recursive, setRecursive] = useState(false);

  return (
    <DrawerPanel title="Upload Wizard" open={open} onClose={onClose}>
      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          void onPreviewUpload({ target, recursive, albumName });
        }}
      >
        <label className="lm-field">
          <span>Target path</span>
          <input value={target} onChange={(event) => setTarget(event.target.value)} placeholder="File/folder path" required />
        </label>

        <label className="lm-field">
          <span>Album (optional)</span>
          <input value={albumName} onChange={(event) => setAlbumName(event.target.value)} placeholder="Album name" />
        </label>

        <label className="lm-toggle">
          <input type="checkbox" checked={recursive} onChange={(event) => setRecursive(event.target.checked)} />
          Recursive scan
        </label>

        <button disabled={busy || !target.trim()}>Preview upload</button>
      </form>
    </DrawerPanel>
  );
}
