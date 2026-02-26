import { useState } from "react";

import { DrawerPanel } from "./DrawerPanel";

type SetupDrawerProps = {
  open: boolean;
  onClose: () => void;
  accountLabel: string;
  busy: boolean;
  hasAccount: boolean;
  onCreateAccount: (label: string, emailHint: string) => Promise<void>;
  onSaveGpmcAuth: (authData: string) => Promise<void>;
  onPasteCookies: (cookieText: string) => Promise<void>;
  onImportCookieFile: (file: File) => Promise<void>;
  onRefreshSession: () => Promise<void>;
};

export function SetupDrawer({
  open,
  onClose,
  accountLabel,
  busy,
  hasAccount,
  onCreateAccount,
  onSaveGpmcAuth,
  onPasteCookies,
  onImportCookieFile,
  onRefreshSession,
}: SetupDrawerProps) {
  const [newLabel, setNewLabel] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [gpmcAuth, setGpmcAuth] = useState("");
  const [cookieText, setCookieText] = useState("");
  const [cookieFile, setCookieFile] = useState<File | null>(null);

  return (
    <DrawerPanel title="Setup Account" open={open} onClose={onClose}>
      <p className="lm-muted">Selected account: {accountLabel || "-"}</p>

      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          void onCreateAccount(newLabel, newEmail).then(() => {
            setNewLabel("");
            setNewEmail("");
          });
        }}
      >
        <h3>Create account</h3>
        <input value={newLabel} onChange={(event) => setNewLabel(event.target.value)} placeholder="Account label" required />
        <input value={newEmail} onChange={(event) => setNewEmail(event.target.value)} placeholder="Email hint (optional)" />
        <button disabled={busy || !newLabel.trim()}>Create</button>
      </form>

      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          void onSaveGpmcAuth(gpmcAuth).then(() => setGpmcAuth(""));
        }}
      >
        <h3>gpmc auth_data</h3>
        <textarea value={gpmcAuth} onChange={(event) => setGpmcAuth(event.target.value)} rows={3} placeholder="androidId=...&app=..." required />
        <button disabled={busy || !hasAccount || !gpmcAuth.trim()}>Save gpmc</button>
      </form>

      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          void onPasteCookies(cookieText).then(() => setCookieText(""));
        }}
      >
        <h3>Paste cookies</h3>
        <textarea value={cookieText} onChange={(event) => setCookieText(event.target.value)} rows={3} placeholder="SAPISID=...; HSID=...;" required />
        <button disabled={busy || !hasAccount || !cookieText.trim()}>Import cookies</button>
      </form>

      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          if (!cookieFile) return;
          void onImportCookieFile(cookieFile).then(() => setCookieFile(null));
        }}
      >
        <h3>Import cookie file</h3>
        <input type="file" accept=".txt" onChange={(event) => setCookieFile(event.target.files?.[0] ?? null)} required />
        <button disabled={busy || !hasAccount || !cookieFile}>Import file</button>
      </form>

      <button onClick={() => void onRefreshSession()} disabled={busy || !hasAccount}>
        Refresh GPTK session
      </button>
    </DrawerPanel>
  );
}
