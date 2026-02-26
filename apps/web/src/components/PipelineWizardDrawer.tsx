import { useState } from "react";

import { DrawerPanel } from "./DrawerPanel";

type PipelineWizardDrawerProps = {
  open: boolean;
  onClose: () => void;
  busy: boolean;
  onPreviewPipeline: (payload: {
    inputLines: string;
    disguiseType: "image" | "video";
    separator: string;
    outputDir: string;
    keepArtifacts: boolean;
    albumName: string;
  }) => Promise<void>;
};

export function PipelineWizardDrawer({ open, onClose, busy, onPreviewPipeline }: PipelineWizardDrawerProps) {
  const [inputLines, setInputLines] = useState("");
  const [disguiseType, setDisguiseType] = useState<"image" | "video">("image");
  const [separator, setSeparator] = useState("FILE_DATA_BEGIN");
  const [outputDir, setOutputDir] = useState("");
  const [keepArtifacts, setKeepArtifacts] = useState(false);
  const [albumName, setAlbumName] = useState("");

  return (
    <DrawerPanel title="Pipeline Wizard" open={open} onClose={onClose}>
      <ol className="lm-step-list">
        <li>Select files/folders/patterns (one per line).</li>
        <li>Choose disguise mode and separator.</li>
        <li>Set upload target album and artifact policy.</li>
        <li>Preview before commit.</li>
      </ol>

      <form
        className="lm-stack"
        onSubmit={(event) => {
          event.preventDefault();
          void onPreviewPipeline({
            inputLines,
            disguiseType,
            separator,
            outputDir,
            keepArtifacts,
            albumName,
          });
        }}
      >
        <textarea
          value={inputLines}
          onChange={(event) => setInputLines(event.target.value)}
          rows={5}
          placeholder="One file/folder/pattern per line"
          required
        />

        <label className="lm-field">
          <span>Disguise type</span>
          <select value={disguiseType} onChange={(event) => setDisguiseType(event.target.value as "image" | "video")}> 
            <option value="image">image</option>
            <option value="video">video</option>
          </select>
        </label>

        <label className="lm-field">
          <span>Separator</span>
          <input value={separator} onChange={(event) => setSeparator(event.target.value)} />
        </label>

        <label className="lm-field">
          <span>Output dir (optional)</span>
          <input value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
        </label>

        <label className="lm-field">
          <span>Upload album (optional)</span>
          <input value={albumName} onChange={(event) => setAlbumName(event.target.value)} />
        </label>

        <label className="lm-toggle">
          <input type="checkbox" checked={keepArtifacts} onChange={(event) => setKeepArtifacts(event.target.checked)} />
          Keep artifacts after upload
        </label>

        <button disabled={busy || !inputLines.trim()}>Preview pipeline</button>
      </form>
    </DrawerPanel>
  );
}
