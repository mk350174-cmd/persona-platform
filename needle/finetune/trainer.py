"""
PersonaNeedleTrainer — fine-tune orchestrator (requires torch).

Distils the hybrid-teacher dataset (``needle/training/data/``) into the SAN's three heads
with a combined objective ``0.4·ceid + 0.3·drift + 0.3·voice`` (terms re-normalise if a
dataset is absent). Supports LoRA (attention-only) or full fine-tune, warmup + gradient
accumulation, per-epoch validation (CEID MAE, drift F1, perplexity), checkpointing, and
early stopping. ``evaluate`` flips the model's ``untrained`` flag to ``False``; ``save``
merges LoRA and writes the full weights + ``config.json``.

Not executed in this repo environment (no torch / no GPU); run where torch+GPU exist:

    python -m needle.finetune.trainer --train needle/training/data/train.jsonl \
        --val needle/training/data/val.jsonl --lora --epochs 3 --device cuda
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from .lora.adapter import LoRAAdapter
from .lora.config import LoRAConfig
from .losses.ceid_loss import CEIDLoss
from .losses.drift_loss import DriftLoss
from .losses.voice_loss import VoiceLoss

_CEID_AXES = ("C", "E", "I", "D")
LOSS_WEIGHTS = {"ceid": 0.4, "drift": 0.3, "voice": 0.3}


def _read_jsonl(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _auto_device(device: str) -> str:
    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _pad(ids, length: int, pad_value: int = 0) -> list[int]:
    ids = list(ids)[:length]
    return ids + [pad_value] * (length - len(ids))


class PersonaFinetuneDataset(Dataset):
    """CEID split (train/val.jsonl) joined with the sibling drift/voice datasets by persona.

    Each item is a fixed-shape tensor dict (padded), so the default collate stacks them.
    Drift/voice availability is a dataset-level flag (``has_drift``/``has_voice``); when a
    sibling file is missing those loss terms are dropped and the weights re-normalise.
    """

    def __init__(self, ceid_path: str, tokenizer, max_len: int = 128, voice_len: int = 64,
                 data_dir: Optional[str] = None):
        self.rows = _read_jsonl(ceid_path)
        self.tok = tokenizer
        self.max_len = max_len
        self.voice_len = voice_len
        d = Path(data_dir) if data_dir else Path(ceid_path).parent
        drift = _read_jsonl(str(d / "drift_dataset.jsonl"))
        voice = _read_jsonl(str(d / "voice_dataset.jsonl"))
        self.has_drift = bool(drift)
        self.has_voice = bool(voice)
        self._drift_by_pid = self._group(drift, "persona_id")
        self._voice_by_pid = self._group(voice, "persona_id")

    @staticmethod
    def _group(rows, key):
        out: dict = {}
        for r in rows:
            out.setdefault(r.get(key), []).append(r)
        return out

    def __len__(self):
        return len(self.rows)

    def _pick(self, pool: dict, pid: str, i: int):
        items = pool.get(pid) or (next(iter(pool.values())) if pool else None)
        return items[i % len(items)] if items else None

    def __getitem__(self, i):
        r = self.rows[i]
        pid = r.get("persona_id")
        kv = np.asarray(r.get("k_layer_vector") or [0.0] * 100, dtype=np.float32)
        labels = r.get("ceid_labels", {})
        ceid = np.array([float(labels.get(a, 0.0)) for a in _CEID_AXES], dtype=np.float32)
        ids = _pad(self.tok.encode(r.get("conversation", ""), max_len=self.max_len), self.max_len)

        item = {
            "persona_vector": torch.tensor(kv),
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "ceid_target": torch.tensor(ceid),
            "confidence": torch.tensor(float(r.get("confidence", 1.0)), dtype=torch.float32),
        }

        d = self._pick(self._drift_by_pid, pid, i)
        item["drift_target"] = torch.tensor(float(bool(d["drift"])) if d else 0.0, dtype=torch.float32)

        v = self._pick(self._voice_by_pid, pid, i)
        vtoks = self.tok.encode(v["voice"], max_len=self.voice_len + 1) if v else [self.tok.bos]
        dec_in = _pad(vtoks[:-1] or [self.tok.bos], self.voice_len, 0)
        tgt = _pad(vtoks[1:], self.voice_len, -100)            # -100 = ignored by VoiceLoss
        item["voice_input_ids"] = torch.tensor(dec_in, dtype=torch.long)
        item["voice_target_ids"] = torch.tensor(tgt, dtype=torch.long)
        return item


class PersonaNeedleTrainer:
    def __init__(self, model, lora_config: Optional[LoRAConfig] = None,
                 learning_rate: float = 2e-4, batch_size: int = 16, epochs: int = 3,
                 warmup_steps: int = 100, gradient_accumulation: int = 4,
                 device: str = "auto", checkpoint_dir: str = "needle/finetune/checkpoints/"):
        self.pn = model                                   # PersonaNeedle wrapper
        self.device = _auto_device(device)
        self.lora_config = lora_config
        self.lr = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.warmup_steps = warmup_steps
        self.grad_accum = gradient_accumulation
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.adapter = None
        if lora_config is not None:
            self.adapter = LoRAAdapter(self.pn, lora_config)
            self.adapter.apply()

        self.san = getattr(self.pn, "model", self.pn).to(self.device)
        self.ceid_loss = CEIDLoss().to(self.device)
        self.drift_loss = DriftLoss().to(self.device)
        self.voice_loss = VoiceLoss().to(self.device)

    # ── one combined forward/loss for a batch ────────────────────────────────────
    def _step_losses(self, batch, has_drift: bool, has_voice: bool) -> dict:
        pv = batch["persona_vector"].to(self.device)
        ids = batch["input_ids"].to(self.device)
        conf = batch["confidence"].to(self.device)
        dec = batch["voice_input_ids"].to(self.device) if has_voice else None
        out = self.san(pv, ids, decoder_input_ids=dec)

        terms, weights = {}, {}
        terms["ceid"] = self.ceid_loss(out["ceid"], batch["ceid_target"].to(self.device), conf)
        weights["ceid"] = LOSS_WEIGHTS["ceid"]
        if has_drift:
            drift_logit = out["drift_logits"][:, 1] - out["drift_logits"][:, 0]
            terms["drift"] = self.drift_loss(drift_logit, batch["drift_target"].to(self.device), conf)
            weights["drift"] = LOSS_WEIGHTS["drift"]
        if has_voice:
            vout = self.voice_loss(out["voice_logits"], batch["voice_target_ids"].to(self.device))
            terms["voice"] = vout["loss"]
            weights["voice"] = LOSS_WEIGHTS["voice"]
            terms["_perplexity"] = vout["perplexity"]

        wsum = sum(weights.values())
        total = sum(weights[k] * terms[k] for k in weights) / wsum
        terms["total"] = total
        return terms

    def train(self, train_path: str, val_path: str) -> dict:
        train_ds = PersonaFinetuneDataset(train_path, self.pn.tokenizer, self.san.cfg.max_context)
        val_ds = PersonaFinetuneDataset(val_path, self.pn.tokenizer, self.san.cfg.max_context)
        train_dl = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        has_drift, has_voice = train_ds.has_drift, train_ds.has_voice

        params = [p for p in self.san.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=self.lr)
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda s: min(1.0, (s + 1) / max(1, self.warmup_steps)))

        history, best_val, patience, bad = [], float("inf"), 3, 0
        for epoch in range(self.epochs):
            self.san.train()
            run = 0.0
            opt.zero_grad()
            for i, batch in enumerate(train_dl):
                loss = self._step_losses(batch, has_drift, has_voice)["total"] / self.grad_accum
                loss.backward()
                if (i + 1) % self.grad_accum == 0:
                    opt.step()
                    sched.step()
                    opt.zero_grad()
                run += float(loss) * self.grad_accum
            train_loss = run / max(1, len(train_dl))

            val = self._validate(DataLoader(val_ds, batch_size=self.batch_size),
                                 has_drift, has_voice)
            stats = {"epoch": epoch, "train_loss": round(train_loss, 4), **val}
            history.append(stats)
            self._save_checkpoint(self.checkpoint_dir / f"epoch_{epoch}.pt")

            if val["val_loss"] < best_val - 1e-4:
                best_val, bad = val["val_loss"], 0
                self._save_checkpoint(self.checkpoint_dir / "best_model.pt")
            else:
                bad += 1
                if bad >= patience:
                    stats["early_stopped"] = True
                    history[-1] = stats
                    break
        return {"history": history, "best_val_loss": round(best_val, 4),
                "losses_used": ["ceid"] + (["drift"] if has_drift else []) + (["voice"] if has_voice else [])}

    @torch.no_grad()
    def _validate(self, dl, has_drift, has_voice) -> dict:
        from sklearn.metrics import f1_score
        self.san.eval()
        losses, mae, ppl = [], [], []
        dy, dp = [], []
        for batch in dl:
            terms = self._step_losses(batch, has_drift, has_voice)
            losses.append(float(terms["total"]))
            if "_perplexity" in terms:
                ppl.append(terms["_perplexity"])
            pv = batch["persona_vector"].to(self.device)
            ids = batch["input_ids"].to(self.device)
            out = self.san(pv, ids)
            mae.append(float(torch.mean(torch.abs(out["ceid"].cpu() - batch["ceid_target"]))))
            if has_drift:
                pred = (torch.softmax(out["drift_logits"], dim=-1)[:, 1] > 0.5).long().cpu().tolist()
                dp += pred
                dy += batch["drift_target"].long().tolist()
        res = {"val_loss": round(float(np.mean(losses)) if losses else 0.0, 4),
               "ceid_mae": round(float(np.mean(mae)) if mae else 0.0, 4)}
        res["drift_f1"] = round(float(f1_score(dy, dp, zero_division=0)), 4) if dy else None
        res["perplexity"] = round(float(np.mean(ppl)), 4) if ppl else None
        return res

    def evaluate(self, test_path: str) -> dict:
        test_ds = PersonaFinetuneDataset(test_path, self.pn.tokenizer, self.san.cfg.max_context)
        dl = DataLoader(test_ds, batch_size=self.batch_size)
        res = self._validate(dl, test_ds.has_drift, test_ds.has_voice)
        self.pn.untrained = False          # the SAN has now been trained
        res["untrained"] = False
        return res

    def _save_checkpoint(self, path):
        torch.save(self.san.state_dict(), path)

    def save(self, output_dir: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        if self.adapter is not None:
            self.adapter.merge_and_unload()            # fold LoRA → full weights
        torch.save(self.san.state_dict(), out / "pytorch_model.bin")
        (out / "config.json").write_text(json.dumps(self.san.cfg.to_dict(), indent=2))
        return str(out)


def main(argv=None) -> int:
    from needle import PersonaNeedle
    from needle.architecture.config import PersonaNeedleConfig

    ap = argparse.ArgumentParser(description="PersonaNeedle fine-tune")
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--test", default=None)
    ap.add_argument("--persona-id", default="generic")
    ap.add_argument("--lora", action="store_true", help="LoRA fine-tune (else full)")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--gradient-accumulation", type=int, default=4)
    ap.add_argument("--warmup-steps", type=int, default=100)
    ap.add_argument("--checkpoint-dir", default="needle/finetune/checkpoints/")
    ap.add_argument("--output-dir", default=None,
                    help="where save() writes the merged model (default <checkpoint-dir>/best_model)")
    args = ap.parse_args(argv)

    pn = PersonaNeedle(PersonaNeedleConfig(persona_id=args.persona_id))
    trainer = PersonaNeedleTrainer(pn, lora_config=LoRAConfig() if args.lora else None,
                                   learning_rate=args.lr, batch_size=args.batch_size,
                                   epochs=args.epochs, warmup_steps=args.warmup_steps,
                                   gradient_accumulation=args.gradient_accumulation,
                                   device=args.device, checkpoint_dir=args.checkpoint_dir)
    stats = trainer.train(args.train, args.val)
    if args.test:
        stats["test"] = trainer.evaluate(args.test)
    out_dir = args.output_dir or str(Path(args.checkpoint_dir) / "best_model")
    trainer.save(out_dir)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
