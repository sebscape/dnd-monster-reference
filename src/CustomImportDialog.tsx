import { useEffect, useRef, useState } from "react";
import type { Monster } from "./models/monster";
import type { Duplicate, DuplicateChoice, ImportMode } from "./models/customImport";
import { findDuplicates } from "./models/customImport";

interface Props {
  fileName: string;
  incoming: Monster[];
  existing: Monster[];
  onAdd: (choices: Record<string, DuplicateChoice>) => void;
  onReplace: () => void;
  onCancel: () => void;
}

const CHOICES: { value: DuplicateChoice; label: string; hint: string }[] = [
  { value: "keep_original", label: "Keep original", hint: "Skip the one in the file" },
  { value: "overwrite", label: "Overwrite with new", hint: "Replace yours with the file's version (keeps its UUID and artwork)" },
  { value: "keep_both", label: "Keep both", hint: "Add the file's version as a numbered copy" },
];

const describe = (m: Monster) => m.type + " · CR " + m.challenge_rating + " · HP " + m.hit_points + " · AC " + m.armor_class;
const modified = (m: Monster) => { const d = new Date(m.timestamp_modified); return Number.isNaN(d.getTime()) ? "" : "modified " + d.toLocaleDateString(); };
const PREVIEW_LIMIT = 12;

/** Step 1: preview the file and choose Add or Replace. Step 2 (Add with duplicates): decide each duplicate. */
export default function CustomImportDialog({ fileName, incoming, existing, onAdd, onReplace, onCancel }: Props) {
  const [mode, setMode] = useState<ImportMode>("add");
  const [duplicates, setDuplicates] = useState<Duplicate[] | null>(null);
  const [choices, setChoices] = useState<Record<string, DuplicateChoice>>({});
  const focus = useRef<HTMLButtonElement | null>(null);
  useEffect(() => { focus.current?.focus(); }, [duplicates]);

  function go() {
    if (mode === "replace") { onReplace(); return; }
    const found = findDuplicates(existing, incoming);
    if (!found.length) { onAdd({}); return; }
    setChoices(Object.fromEntries(found.map(d => [d.incoming.id, "keep_original" as DuplicateChoice])));
    setDuplicates(found);
  }
  const setAll = (choice: DuplicateChoice) => setChoices(Object.fromEntries((duplicates ?? []).map(d => [d.incoming.id, choice])));
  const count = (choice: DuplicateChoice) => Object.values(choices).filter(c => c === choice).length;

  return <div className="modal-backdrop" onClick={onCancel}>
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="import-title" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === "Escape") onCancel(); }}>
      {!duplicates ? <>
        <h2 id="import-title">Import custom monsters</h2>
        <p className="muted"><b>{fileName}</b> contains {incoming.length} custom monster{incoming.length === 1 ? "" : "s"}. You have {existing.length} now.</p>
        <ul className="import-list">
          {incoming.slice(0, PREVIEW_LIMIT).map(m => <li key={m.id}><strong>{m.name}</strong><small>{describe(m)}</small></li>)}
          {incoming.length > PREVIEW_LIMIT && <li className="muted">…and {incoming.length - PREVIEW_LIMIT} more</li>}
        </ul>
        <fieldset className="choice-group">
          <legend>What should happen?</legend>
          <label className="radio"><input type="radio" name="import-mode" checked={mode === "add"} onChange={() => setMode("add")} />
            <span><b>Add to my custom monsters</b><small>Keeps your {existing.length} and adds these. If any are already in your library, you'll choose what to do with each.</small></span></label>
          <label className="radio"><input type="radio" name="import-mode" checked={mode === "replace"} onChange={() => setMode("replace")} />
            <span><b>Replace my custom monsters</b><small>{existing.length ? "Removes your " + existing.length + " custom monster" + (existing.length === 1 ? "" : "s") + " and keeps only the ones in this file." : "You have none yet, so this is the same as adding."}</small></span></label>
        </fieldset>
        {mode === "replace" && existing.length > 0 && <p className="warning-text">Your current custom monsters will be gone. Export a backup first if you might want them back.</p>}
        <div className="dialog-actions">
          <button type="button" onClick={onCancel}>Cancel</button>
          <button ref={focus} type="button" className={mode === "replace" && existing.length ? "danger" : "primary"} onClick={go}>Go</button>
        </div>
      </> : <>
        <h2 id="import-title">{duplicates.length} duplicate{duplicates.length === 1 ? "" : "s"} found</h2>
        <p className="muted">{duplicates.length} of the {incoming.length} monsters in the file {duplicates.length === 1 ? "is" : "are"} already in your library. The other {incoming.length - duplicates.length} will be added.</p>
        <div className="apply-all" role="group" aria-label="Apply to all duplicates">
          <span className="muted">Apply to all:</span>
          {CHOICES.map(c => <button key={c.value} type="button" className="small-button" title={c.hint} onClick={() => setAll(c.value)}>{c.label}</button>)}
        </div>
        <ul className="duplicate-list">
          {duplicates.map(d => <li key={d.incoming.id}>
            <div className="duplicate-compare">
              <div><span className="tag">Yours</span><strong>{d.existing.name}</strong><small>{describe(d.existing)}</small><small>{modified(d.existing)}</small></div>
              <div><span className="tag new">In the file</span><strong>{d.incoming.name}</strong><small>{describe(d.incoming)}</small><small>{modified(d.incoming)}</small></div>
            </div>
            <small className="muted">{d.match === "id" ? "Same monster (same UUID)." : "Different monster with the same name."}</small>
            <div className="duplicate-choices" role="radiogroup" aria-label={"What to do with " + d.incoming.name}>
              {CHOICES.map(c => <label key={c.value} className="radio inline" title={c.hint}>
                <input type="radio" name={"dup-" + d.incoming.id} checked={choices[d.incoming.id] === c.value} onChange={() => setChoices(x => ({ ...x, [d.incoming.id]: c.value }))} /> {c.label}
              </label>)}
            </div>
          </li>)}
        </ul>
        <p className="muted small-text">{count("keep_original")} kept as they are · {count("overwrite")} overwritten · {count("keep_both")} added as copies</p>
        <div className="dialog-actions">
          <button type="button" onClick={() => setDuplicates(null)}>Back</button>
          <button type="button" onClick={onCancel}>Cancel</button>
          <button ref={focus} type="button" className="primary" onClick={() => onAdd(choices)}>Import</button>
        </div>
      </>}
    </div>
  </div>;
}

/** "Are you sure?" before deleting every custom monster. */
export function PurgeDialog({ count, onExport, onConfirm, onCancel }: { count: number; onExport: () => void; onConfirm: () => void; onCancel: () => void }) {
  const cancel = useRef<HTMLButtonElement | null>(null);
  useEffect(() => { cancel.current?.focus(); }, []);
  return <div className="modal-backdrop" onClick={onCancel}>
    <div className="modal" role="alertdialog" aria-modal="true" aria-labelledby="purge-title" aria-describedby="purge-text" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === "Escape") onCancel(); }}>
      <h2 id="purge-title">Delete all custom monsters?</h2>
      <p id="purge-text">Are you sure? This permanently deletes {count === 1 ? <>your <b>1</b> custom monster</> : <>all <b>{count}</b> custom monsters</>} from this browser. It can't be undone. Published monsters aren't affected.</p>
      <p className="muted">Export a backup first if you might want them back.</p>
      <div className="dialog-actions">
        <button type="button" onClick={onExport}>Export backup</button>
        <button ref={cancel} type="button" onClick={onCancel}>Cancel</button>
        <button type="button" className="danger" onClick={onConfirm}>{count === 1 ? "Yes, delete it" : "Yes, delete all " + count}</button>
      </div>
    </div>
  </div>;
}
