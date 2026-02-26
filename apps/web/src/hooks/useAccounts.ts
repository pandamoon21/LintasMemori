import { useCallback, useMemo, useState } from "react";

import { postForm, postJson, getJson } from "../api";
import type { Account } from "../types";

export function useAccounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [activeAccountId, setActiveAccountId] = useState("");
  const [loading, setLoading] = useState(false);

  const activeAccount = useMemo(
    () => accounts.find((item) => item.id === activeAccountId) ?? null,
    [accounts, activeAccountId]
  );

  const refreshAccounts = useCallback(async () => {
    const rows = await getJson<Account[]>("/api/v2/accounts");
    setAccounts(rows);
    if (!activeAccountId && rows[0]) {
      setActiveAccountId(rows[0].id);
    }
    if (activeAccountId && rows.every((item) => item.id !== activeAccountId)) {
      setActiveAccountId(rows[0]?.id || "");
    }
    return rows;
  }, [activeAccountId]);

  const createAccount = useCallback(async (label: string, emailHint: string) => {
    const created = await postJson<Account>("/api/v2/accounts", {
      label: label.trim(),
      email_hint: emailHint.trim() || null,
    });
    await refreshAccounts();
    setActiveAccountId(created.id);
    return created;
  }, [refreshAccounts]);

  const saveGpmcAuth = useCallback(async (authData: string) => {
    if (!activeAccountId) {
      throw new Error("No account selected");
    }
    await postJson(`/api/v2/accounts/${activeAccountId}/credentials/gpmc`, {
      auth_data: authData.trim(),
    });
    await refreshAccounts();
  }, [activeAccountId, refreshAccounts]);

  const pasteCookies = useCallback(async (cookieText: string) => {
    if (!activeAccountId) {
      throw new Error("No account selected");
    }
    await postJson(`/api/v2/accounts/${activeAccountId}/credentials/cookies/paste`, {
      cookie_string: cookieText.trim(),
    });
    await refreshAccounts();
  }, [activeAccountId, refreshAccounts]);

  const importCookieFile = useCallback(async (file: File) => {
    if (!activeAccountId) {
      throw new Error("No account selected");
    }
    const form = new FormData();
    form.set("file", file);
    await postForm(`/api/v2/accounts/${activeAccountId}/credentials/cookies/import`, form);
    await refreshAccounts();
  }, [activeAccountId, refreshAccounts]);

  const refreshSession = useCallback(async () => {
    if (!activeAccountId) {
      throw new Error("No account selected");
    }
    await postJson(`/api/v2/accounts/${activeAccountId}/session/refresh`, { source_path: "/" });
  }, [activeAccountId]);

  const withLoading = useCallback(async <T,>(fn: () => Promise<T>) => {
    setLoading(true);
    try {
      return await fn();
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    accounts,
    activeAccountId,
    setActiveAccountId,
    activeAccount,
    loading,
    refreshAccounts,
    createAccount: (label: string, emailHint: string) => withLoading(() => createAccount(label, emailHint)),
    saveGpmcAuth: (authData: string) => withLoading(() => saveGpmcAuth(authData)),
    pasteCookies: (cookieText: string) => withLoading(() => pasteCookies(cookieText)),
    importCookieFile: (file: File) => withLoading(() => importCookieFile(file)),
    refreshSession: () => withLoading(() => refreshSession()),
  };
}
