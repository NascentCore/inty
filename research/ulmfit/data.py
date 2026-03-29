from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import random
import re

from loguru import logger
import torch
from torch.utils.data import Dataset

from research.ulmfit.config import ExperimentConfig

TOKENIZER_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def simple_tokenize(text: str) -> list[str]:
    return TOKENIZER_RE.findall(text.lower())


@dataclass
class Vocab:
    stoi: dict[str, int]
    itos: list[str]
    pad_idx: int
    unk_idx: int
    eos_idx: int

    def encode(self, tokens: list[str]) -> list[int]:
        return [self.stoi.get(token, self.unk_idx) for token in tokens]

    def decode(self, ids: list[int]) -> list[str]:
        return [self.itos[idx] for idx in ids]


def build_vocab(
    tokenized_texts: list[list[str]],
    max_size: int,
    min_freq: int,
    pad_token: str,
    unk_token: str,
    eos_token: str,
) -> Vocab:
    counter = Counter(token for tokens in tokenized_texts for token in tokens)
    kept = [
        token
        for token, freq in counter.most_common()
        if freq >= min_freq and token not in {pad_token, unk_token, eos_token}
    ]
    kept = kept[: max(0, max_size - 3)]
    itos = [pad_token, unk_token, eos_token, *kept]
    stoi = {token: idx for idx, token in enumerate(itos)}
    return Vocab(
        stoi=stoi,
        itos=itos,
        pad_idx=stoi[pad_token],
        unk_idx=stoi[unk_token],
        eos_idx=stoi[eos_token],
    )


def generate_toy_lm_corpus(size: int) -> list[str]:
    topics = [
        "cinema storytelling pacing visual emotion dialogue arc performance",
        "football match tactics pressing passing midfield defense attack strategy",
        "technology innovation machine learning model training data quality metrics",
        "cooking recipe seasoning texture balance aroma kitchen preparation",
        "travel culture history architecture city landscape local life",
    ]
    lines: list[str] = []
    for index in range(size):
        topic = topics[index % len(topics)]
        lines.append(f"sample {index} discusses {topic} with detailed context.")
    return lines


def generate_toy_classification_dataset(
    train_size: int,
    valid_size: int,
    test_size: int,
) -> tuple[list[tuple[str, int]], list[tuple[str, int]], list[tuple[str, int]]]:
    positive_templates = [
        "This movie was excellent with strong acting and a touching story.",
        "A wonderful film that felt engaging, warm and memorable.",
        "I liked this drama; it was emotional and beautifully directed.",
        "Great screenplay and satisfying ending made it a good watch.",
    ]
    negative_templates = [
        "This movie was terrible with weak acting and dull scenes.",
        "A boring film that felt slow, flat and forgettable.",
        "I disliked this drama; it was noisy and badly directed.",
        "Poor screenplay and frustrating ending made it hard to watch.",
    ]

    def build_split(size: int, seed: int) -> list[tuple[str, int]]:
        rng = random.Random(seed)
        rows: list[tuple[str, int]] = []
        for idx in range(size):
            label = idx % 2
            template = (
                rng.choice(positive_templates) if label == 1 else rng.choice(negative_templates)
            )
            rows.append((f"{template} Instance {idx}.", label))
        rng.shuffle(rows)
        return rows

    return (
        build_split(train_size, 100),
        build_split(valid_size, 200),
        build_split(test_size, 300),
    )


def load_hf_imdb_dataset(
    train_limit: int | None,
    valid_limit: int | None,
    test_limit: int | None,
) -> tuple[list[tuple[str, int]], list[tuple[str, int]], list[tuple[str, int]]]:
    from datasets import load_dataset

    dataset = load_dataset("imdb")
    train = [(item["text"], int(item["label"])) for item in dataset["train"]]
    test = [(item["text"], int(item["label"])) for item in dataset["test"]]
    valid_size = min(2500, len(train) // 10)
    valid = train[:valid_size]
    train_main = train[valid_size:]

    if train_limit is not None:
        train_main = train_main[:train_limit]
    if valid_limit is not None:
        valid = valid[:valid_limit]
    if test_limit is not None:
        test = test[:test_limit]

    return train_main, valid, test


def load_wikitext2_corpus(
    train_limit: int | None,
    valid_limit: int | None,
) -> tuple[list[str], list[str]]:
    from datasets import load_dataset

    dataset = load_dataset("wikitext", "wikitext-2-raw-v1")
    train = [row["text"] for row in dataset["train"] if row["text"].strip()]
    valid = [row["text"] for row in dataset["validation"] if row["text"].strip()]
    if train_limit is not None:
        train = train[:train_limit]
    if valid_limit is not None:
        valid = valid[:valid_limit]
    return train, valid


def batchify_token_ids(
    flat_ids: list[int],
    batch_size: int,
    device: torch.device,
) -> torch.Tensor:
    n_batch_tokens = (len(flat_ids) // batch_size) * batch_size
    ids = torch.tensor(flat_ids[:n_batch_tokens], dtype=torch.long, device=device)
    return ids.view(batch_size, -1).t().contiguous()


def lm_iter_batches(
    source: torch.Tensor,
    bptt: int,
) -> list[tuple[torch.Tensor, torch.Tensor]]:
    batches: list[tuple[torch.Tensor, torch.Tensor]] = []
    for start in range(0, source.size(0) - 1, bptt):
        seq_len = min(bptt, source.size(0) - 1 - start)
        x = source[start : start + seq_len]
        y = source[start + 1 : start + 1 + seq_len]
        batches.append((x, y.reshape(-1)))
    return batches


class TextClassificationDataset(Dataset[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]):
    def __init__(
        self,
        rows: list[tuple[str, int]],
        vocab: Vocab,
        max_seq_len: int,
    ) -> None:
        self.rows = rows
        self.vocab = vocab
        self.max_seq_len = max_seq_len

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        text, label = self.rows[index]
        tokens = simple_tokenize(text)[: self.max_seq_len - 1]
        token_ids = self.vocab.encode(tokens) + [self.vocab.eos_idx]
        length = len(token_ids)
        if length < self.max_seq_len:
            token_ids = token_ids + [self.vocab.pad_idx] * (self.max_seq_len - length)
        else:
            token_ids = token_ids[: self.max_seq_len]
            length = self.max_seq_len
        return (
            torch.tensor(token_ids, dtype=torch.long),
            torch.tensor(length, dtype=torch.long),
            torch.tensor(label, dtype=torch.long),
        )


@dataclass
class PreparedData:
    vocab: Vocab
    lm_pretrain_train_ids: torch.Tensor
    lm_pretrain_valid_ids: torch.Tensor
    lm_finetune_train_ids: torch.Tensor
    lm_finetune_valid_ids: torch.Tensor
    classifier_train: list[tuple[str, int]]
    classifier_valid: list[tuple[str, int]]
    classifier_test: list[tuple[str, int]]


def _flatten_for_lm(
    texts: list[str],
    vocab: Vocab,
    min_tokens_per_sample: int = 2,
) -> list[int]:
    all_ids: list[int] = []
    for text in texts:
        tokens = simple_tokenize(text)
        if len(tokens) < min_tokens_per_sample:
            continue
        all_ids.extend(vocab.encode(tokens))
        all_ids.append(vocab.eos_idx)
    return all_ids


def _load_task_splits(cfg: ExperimentConfig) -> tuple[list[tuple[str, int]], list[tuple[str, int]], list[tuple[str, int]]]:
    if cfg.dataset.provider == "toy":
        return generate_toy_classification_dataset(
            train_size=cfg.dataset.toy_train_size,
            valid_size=cfg.dataset.toy_valid_size,
            test_size=cfg.dataset.toy_test_size,
        )
    return load_hf_imdb_dataset(
        train_limit=cfg.dataset.imdb_train_limit,
        valid_limit=cfg.dataset.imdb_valid_limit,
        test_limit=cfg.dataset.imdb_test_limit,
    )


def _load_lm_corpus(cfg: ExperimentConfig) -> tuple[list[str], list[str]]:
    if cfg.dataset.lm_corpus_provider == "toy":
        train_size = max(cfg.dataset.toy_train_size * 2, 512)
        valid_size = max(cfg.dataset.toy_valid_size, 64)
        return generate_toy_lm_corpus(train_size), generate_toy_lm_corpus(valid_size)
    return load_wikitext2_corpus(
        train_limit=cfg.dataset.lm_train_limit,
        valid_limit=cfg.dataset.lm_valid_limit,
    )


def prepare_data(cfg: ExperimentConfig, device: torch.device) -> PreparedData:
    lm_train_texts, lm_valid_texts = _load_lm_corpus(cfg)
    cls_train, cls_valid, cls_test = _load_task_splits(cfg)
    tokenized_for_vocab = [
        simple_tokenize(text)
        for text in (
            lm_train_texts
            + lm_valid_texts
            + [row[0] for row in cls_train[: min(len(cls_train), 20000)]]
        )
    ]

    vocab = build_vocab(
        tokenized_texts=tokenized_for_vocab,
        max_size=cfg.vocab.max_size,
        min_freq=cfg.vocab.min_freq,
        pad_token=cfg.vocab.pad_token,
        unk_token=cfg.vocab.unk_token,
        eos_token=cfg.vocab.eos_token,
    )
    logger.info("Built vocab size: {}", len(vocab.itos))

    lm_pretrain_train = _flatten_for_lm(lm_train_texts, vocab)
    lm_pretrain_valid = _flatten_for_lm(lm_valid_texts, vocab)
    lm_finetune_train = _flatten_for_lm([item[0] for item in cls_train], vocab)
    lm_finetune_valid = _flatten_for_lm([item[0] for item in cls_valid], vocab)

    pretrain_train_ids = batchify_token_ids(
        lm_pretrain_train,
        cfg.lm_train.batch_size,
        device,
    )
    pretrain_valid_ids = batchify_token_ids(
        lm_pretrain_valid,
        cfg.lm_train.batch_size,
        device,
    )
    finetune_train_ids = batchify_token_ids(
        lm_finetune_train,
        cfg.lm_train.batch_size,
        device,
    )
    finetune_valid_ids = batchify_token_ids(
        lm_finetune_valid,
        cfg.lm_train.batch_size,
        device,
    )
    logger.info(
        "LM token tensors pretrain train/valid: {}/{}",
        tuple(pretrain_train_ids.shape),
        tuple(pretrain_valid_ids.shape),
    )
    return PreparedData(
        vocab=vocab,
        lm_pretrain_train_ids=pretrain_train_ids,
        lm_pretrain_valid_ids=pretrain_valid_ids,
        lm_finetune_train_ids=finetune_train_ids,
        lm_finetune_valid_ids=finetune_valid_ids,
        classifier_train=cls_train,
        classifier_valid=cls_valid,
        classifier_test=cls_test,
    )


def save_vocab(vocab: Vocab, output_dir: Path) -> None:
    vocab_path = output_dir / "vocab.txt"
    vocab_path.write_text("\n".join(vocab.itos) + "\n", encoding="utf-8")
    logger.info("Saved vocab to {}", vocab_path)
