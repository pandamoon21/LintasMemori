type SelectionActionBarProps = {
  selectedCount: number;
  loadedCount: number;
  selectedDateTime: string;
  onDateTimeChange: (value: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onTrash: () => void;
  onRestore: () => void;
  onArchive: () => void;
  onUnarchive: () => void;
  onFavorite: () => void;
  onUnfavorite: () => void;
  onAddAlbum: () => void;
  onRemoveAlbum: () => void;
  onSetDate: () => void;
  disabled: boolean;
};

export function SelectionActionBar({
  selectedCount,
  loadedCount,
  selectedDateTime,
  onDateTimeChange,
  onSelectAll,
  onClearSelection,
  onTrash,
  onRestore,
  onArchive,
  onUnarchive,
  onFavorite,
  onUnfavorite,
  onAddAlbum,
  onRemoveAlbum,
  onSetDate,
  disabled,
}: SelectionActionBarProps) {
  return (
    <section className="lm-surface lm-actionbar">
      <div className="lm-toolbar-row">
        <span className="lm-chip">Loaded: {loadedCount}</span>
        <span className="lm-chip">Selected: {selectedCount}</span>
        <span className="lm-shortcut-hint">Shortcuts: Ctrl/Cmd+A, Arrows, Shift+Arrows, Enter, Space, Esc</span>
        <button className="lm-btn-ghost" onClick={onSelectAll} type="button">Select All</button>
        <button className="lm-btn-ghost" onClick={onClearSelection} type="button">Clear</button>
      </div>

      <div className="lm-toolbar-row">
        <button onClick={onTrash} disabled={disabled} type="button">Trash</button>
        <button onClick={onRestore} disabled={disabled} type="button">Restore</button>
        <button onClick={onArchive} disabled={disabled} type="button">Archive</button>
        <button onClick={onUnarchive} disabled={disabled} type="button">Unarchive</button>
        <button onClick={onFavorite} disabled={disabled} type="button">Favorite</button>
        <button onClick={onUnfavorite} disabled={disabled} type="button">Unfavorite</button>
        <button onClick={onAddAlbum} disabled={disabled} type="button">Add Album</button>
        <button onClick={onRemoveAlbum} disabled={disabled} type="button">Remove Album</button>
        <input type="datetime-local" value={selectedDateTime} onChange={(event) => onDateTimeChange(event.target.value)} />
        <button onClick={onSetDate} disabled={disabled} type="button">Set Date</button>
      </div>
    </section>
  );
}
