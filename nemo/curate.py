"""Curate the synthetic spec-writer data with NVIDIA NeMo Curator (CPU only).

Pipeline (NeMo Curator 1.x stages, XennaExecutor, CUDA hidden):
  JsonlReader(raw.jsonl)
  -> ScoreFilter(WordCountFilter 6..120 words)                 Curator heuristic filter
  -> ScoreFilter(LabelApplicable on "label")                   our DocumentFilter: the label must be JSON with a known base
                                                               and parameters that scenarios.gen.generate accepts
  -> NormalizedExactDedup                                      our ProcessingStage (CPU): Curator's exact/fuzzy dedup
                                                               stages need cuDF on a GPU, and this server's GPUs are off-limits
  -> JsonlWriter(nemo/data/curated/)
Then a deterministic split by hash of the text: 80 % train / 10 % val / 10 % test,
written as chat-format JSONL for SFT (nemo/data/sft_{train,val,test}.jsonl).

  CUDA_VISIBLE_DEVICES= .venv/bin/python -m nemo.curate
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass

os.environ["CUDA_VISIBLE_DEVICES"] = ""          # never touch this server's GPUs
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nemo_curator.pipeline import Pipeline  # noqa: E402
from nemo_curator.stages.base import ProcessingStage  # noqa: E402
from nemo_curator.stages.text.filters.doc_filter import DocumentFilter  # noqa: E402
from nemo_curator.stages.text.filters.heuristic.string import WordCountFilter  # noqa: E402
from nemo_curator.stages.text.filters.score_filter import ScoreFilter  # noqa: E402
from nemo_curator.stages.text.io.reader.jsonl import JsonlReader  # noqa: E402
from nemo_curator.stages.text.io.writer.jsonl import JsonlWriter  # noqa: E402
from nemo_curator.tasks import DocumentBatch  # noqa: E402

DATA = os.path.join(ROOT, "nemo", "data")


class LabelApplicable(DocumentFilter):
    """Score 1 if the label is a JSON {"base", "params"} that the scenario generator accepts, else 0."""

    def __init__(self):
        super().__init__()
        self._name = "label_applicable"
        self._bases = {b: json.load(open(os.path.join(ROOT, "scenarios", "examples", f"{b}.json"))) for b in ("s1_base", "s2_base")}

    def score_document(self, text: str) -> float:
        from scenarios.gen import generate
        try:
            d = json.loads(text)
            generate(self._bases[d["base"]], d["params"], 0)
            return 1.0
        except Exception:  # noqa: BLE001 — any failure means the label is unusable
            return 0.0

    def keep_document(self, score: float) -> bool:
        return score >= 1.0


@dataclass
class NormalizedExactDedup(ProcessingStage[DocumentBatch, DocumentBatch]):
    """Drop rows whose (normalised text, label) was already seen. CPU, in-batch.
    Normalisation: lower case, collapse whitespace, digits kept (numbers carry the meaning)."""
    text_field: str = "text"
    name: str = "normalized_exact_dedup"

    def inputs(self):
        return ["data"], [self.text_field, "label"]

    def outputs(self):
        return ["data"], [self.text_field, "label"]

    def process(self, batch: DocumentBatch) -> DocumentBatch:
        df = batch.to_pandas()
        key = df[self.text_field].str.lower().str.replace(r"\s+", " ", regex=True).str.strip() + "||" + df["label"]
        df = df[~key.duplicated(keep="first")]
        return DocumentBatch(dataset_name=batch.dataset_name, data=df, _metadata=batch._metadata, _stage_perf=batch._stage_perf)


def main() -> int:
    raw = os.path.join(DATA, "raw.jsonl")
    out_dir = os.path.join(DATA, "curated")
    for f in glob.glob(os.path.join(out_dir, "*")):
        os.remove(f)
    p = Pipeline(name="spec_writer_curation", description="synthetic goal->spec data")
    p.add_stage(JsonlReader(file_paths=raw, fields=["id", "text", "label", "base"]))
    p.add_stage(ScoreFilter(WordCountFilter(min_words=6, max_words=120), text_field="text", score_field="word_count"))
    p.add_stage(ScoreFilter(LabelApplicable(), text_field="label", score_field="label_ok"))
    p.add_stage(NormalizedExactDedup())
    p.add_stage(JsonlWriter(path=out_dir))
    p.run()
    rows = [json.loads(l) for f in sorted(glob.glob(os.path.join(out_dir, "*.jsonl"))) for l in open(f, encoding="utf-8")]
    n_raw = sum(1 for _ in open(raw, encoding="utf-8"))
    from nemo.make_sft_data import SYSTEM
    splits = {"train": [], "val": [], "test": []}
    for r in rows:
        h = int(hashlib.sha256(r["text"].encode()).hexdigest(), 16) % 10
        k = "test" if h == 0 else "val" if h == 1 else "train"
        splits[k].append({"id": r["id"], "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["text"]},
                                                      {"role": "assistant", "content": r["label"]}]})
    for k, v in splits.items():
        with open(os.path.join(DATA, f"sft_{k}.jsonl"), "w", encoding="utf-8") as f:
            for x in v:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    stats = {"raw": n_raw, "curated": len(rows), "removed": n_raw - len(rows), **{k: len(v) for k, v in splits.items()},
             "unique_labels_curated": len({r["label"] for r in rows})}
    json.dump(stats, open(os.path.join(DATA, "curation_stats.json"), "w"), indent=1)
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
