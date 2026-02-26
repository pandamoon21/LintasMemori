import { useEffect, useMemo, useState } from "react";

import { DrawerPanel } from "./DrawerPanel";
import type { OperationCatalogEntry } from "../types";

type AdvancedDrawerProps = {
  open: boolean;
  onClose: () => void;
  busy: boolean;
  operations: OperationCatalogEntry[];
  onPreviewAdvanced: (payload: {
    provider: "gptk" | "gpmc" | "gp_disguise";
    operation: string;
    params: Record<string, unknown>;
  }) => Promise<void>;
};

export function AdvancedDrawer({ open, onClose, busy, operations, onPreviewAdvanced }: AdvancedDrawerProps) {
  const [provider, setProvider] = useState<"gptk" | "gpmc" | "gp_disguise">("gptk");
  const providerOperations = useMemo(
    () => operations.filter((item) => item.provider === provider),
    [operations, provider]
  );

  const [operation, setOperation] = useState("");
  const [paramsText, setParamsText] = useState("{}");
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    if (!providerOperations.length) {
      setOperation("");
      setParamsText("{}");
      return;
    }
    if (!providerOperations.some((item) => item.operation === operation)) {
      setOperation(providerOperations[0].operation);
      setParamsText(JSON.stringify(providerOperations[0].params_template, null, 2));
    }
  }, [providerOperations, operation]);

  return (
    <DrawerPanel title="Advanced Drawer" open={open} onClose={onClose}>
      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          try {
            const parsed = JSON.parse(paramsText) as Record<string, unknown>;
            setParseError(null);
            void onPreviewAdvanced({ provider, operation, params: parsed });
          } catch {
            setParseError("Invalid JSON in params.");
          }
        }}
      >
        <label className="lm-field">
          <span>Provider</span>
          <select value={provider} onChange={(event) => setProvider(event.target.value as "gptk" | "gpmc" | "gp_disguise")}> 
            <option value="gptk">gptk</option>
            <option value="gpmc">gpmc</option>
            <option value="gp_disguise">gp_disguise</option>
          </select>
        </label>

        <label className="lm-field">
          <span>Operation</span>
          <select value={operation} onChange={(event) => setOperation(event.target.value)}>
            {providerOperations.map((item) => (
              <option key={item.operation} value={item.operation}>
                {item.operation}
              </option>
            ))}
          </select>
        </label>

        <textarea value={paramsText} onChange={(event) => setParamsText(event.target.value)} rows={7} />
        {parseError ? <div className="lm-inline-error">{parseError}</div> : null}

        <button disabled={busy || !operation}>Preview advanced operation</button>
      </form>
    </DrawerPanel>
  );
}
