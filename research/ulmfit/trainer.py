from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
import torch
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm

from research.ulmfit.config import (
    ExperimentConfig,
    LmTrainConfig,
)
from research.ulmfit.data import (
    PreparedData,
    TextClassificationDataset,
    lm_iter_batches,
    prepare_data,
    save_vocab,
)
from research.ulmfit.modeling import ConcatPoolingClassifier, LanguageModel


def _detach_hidden(
    hidden: list[tuple[torch.Tensor, torch.Tensor]] | None,
) -> list[tuple[torch.Tensor, torch.Tensor]] | None:
    if hidden is None:
        return None
    return [(h.detach(), c.detach()) for h, c in hidden]


@dataclass
class SlantedTriangularScheduler:
    optimizer: torch.optim.Optimizer
    total_steps: int
    cut_frac: float
    ratio: float
    max_lrs: list[float]

    def __post_init__(self) -> None:
        self.cut = max(1, int(self.total_steps * self.cut_frac))
        self.step_count = 0

    def _compute_p(self) -> float:
        if self.step_count < self.cut:
            return self.step_count / self.cut
        return 1 - (self.step_count - self.cut) / max(1, self.total_steps - self.cut)

    def step(self) -> None:
        self.step_count += 1
        p = max(0.0, self._compute_p())
        lr_scale = (1 + p * (self.ratio - 1)) / self.ratio
        for group, max_lr in zip(
            self.optimizer.param_groups, self.max_lrs, strict=True
        ):
            group["lr"] = max_lr * lr_scale


def _lm_loss_and_tokens(
    logits: torch.Tensor, target: torch.Tensor
) -> tuple[torch.Tensor, int]:
    vocab_size = logits.size(-1)
    loss = nn.functional.cross_entropy(
        logits.reshape(-1, vocab_size),
        target.reshape(-1),
    )
    return loss, int(target.numel())


def _evaluate_lm(
    model: LanguageModel,
    token_ids: torch.Tensor,
    bptt: int,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    hidden: list[tuple[torch.Tensor, torch.Tensor]] | None = None
    with torch.no_grad():
        for x_batch, y_batch in lm_iter_batches(token_ids, bptt):
            x = x_batch.t().contiguous()
            y = y_batch.view(x_batch.size(0), x_batch.size(1)).t().contiguous()
            out = model(x, hidden)
            hidden = _detach_hidden(out.hidden)
            loss, n_tokens = _lm_loss_and_tokens(out.logits, y)
            total_loss += float(loss.item()) * n_tokens
            total_tokens += n_tokens
    avg_loss = total_loss / max(1, total_tokens)
    ppl = float(math.exp(min(avg_loss, 20)))
    return avg_loss, ppl


def train_language_model_stage(
    model: LanguageModel,
    cfg: LmTrainConfig,
    train_ids: torch.Tensor,
    valid_ids: torch.Tensor,
    epochs: int,
    output_path: Path,
) -> dict[str, float]:
    optimizer = AdamW(
        model.parameters(),
        lr=cfg.lr_max / cfg.stlr_ratio,
        weight_decay=cfg.weight_decay,
    )
    train_batches = lm_iter_batches(train_ids, cfg.bptt)
    total_steps = max(1, epochs * len(train_batches))
    scheduler = SlantedTriangularScheduler(
        optimizer=optimizer,
        total_steps=total_steps,
        cut_frac=cfg.stlr_cut_frac,
        ratio=cfg.stlr_ratio,
        max_lrs=[cfg.lr_max],
    )

    model.train()
    for epoch in range(epochs):
        hidden: list[tuple[torch.Tensor, torch.Tensor]] | None = None
        progress = tqdm(train_batches, desc=f"lm-epoch-{epoch + 1}", leave=False)
        for x_batch, y_batch in progress:
            x = x_batch.t().contiguous()
            y = y_batch.view(x_batch.size(0), x_batch.size(1)).t().contiguous()
            optimizer.zero_grad(set_to_none=True)
            out = model(x, hidden)
            hidden = _detach_hidden(out.hidden)
            loss, _ = _lm_loss_and_tokens(out.logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.gradient_clip)
            optimizer.step()
            scheduler.step()
            progress.set_postfix(loss=f"{loss.item():.4f}")

    valid_loss, valid_ppl = _evaluate_lm(model, valid_ids, cfg.bptt)
    torch.save(model.state_dict(), output_path)
    logger.info("Saved LM checkpoint to {}", output_path)
    return {
        "valid_loss": valid_loss,
        "valid_ppl": valid_ppl,
    }


def _set_encoder_trainable_blocks(
    classifier: ConcatPoolingClassifier,
    unfreeze_blocks: int,
) -> None:
    for param in classifier.encoder.parameters():
        param.requires_grad = False
    total_blocks = len(classifier.encoder.rnns)
    blocks = max(0, min(unfreeze_blocks, total_blocks))
    for offset in range(blocks):
        layer_index = total_blocks - 1 - offset
        for param in classifier.encoder.rnns[layer_index].parameters():
            param.requires_grad = True
    if blocks >= total_blocks:
        for param in classifier.encoder.embedding.parameters():
            param.requires_grad = True
    for param in classifier.classifier.parameters():
        param.requires_grad = True


def _build_discriminative_lrs(
    classifier: ConcatPoolingClassifier,
    cfg: ClassifierTrainConfig,
) -> tuple[list[dict], list[float]]:
    groups: list[dict] = []
    max_lrs: list[float] = []
    lr = cfg.lr_max
    groups.append(
        {"params": list(classifier.classifier.parameters()), "lr": lr / cfg.stlr_ratio}
    )
    max_lrs.append(lr)
    for rnn in reversed(classifier.encoder.rnns):
        lr = lr / cfg.layer_lr_decay
        groups.append({"params": list(rnn.parameters()), "lr": lr / cfg.stlr_ratio})
        max_lrs.append(lr)
    lr = lr / cfg.layer_lr_decay
    groups.append(
        {
            "params": list(classifier.encoder.embedding.parameters()),
            "lr": lr / cfg.stlr_ratio,
        }
    )
    max_lrs.append(lr)
    return groups, max_lrs


def _evaluate_classifier(
    classifier: ConcatPoolingClassifier,
    dataloader: DataLoader,
    device: torch.device,
) -> tuple[float, float]:
    classifier.eval()
    total = 0
    correct = 0
    total_loss = 0.0
    with torch.no_grad():
        for token_ids, lengths, labels in dataloader:
            token_ids = token_ids.to(device)
            lengths = lengths.to(device)
            labels = labels.to(device)
            attention_mask = (
                torch.arange(token_ids.size(1), device=device)[None, :]
                < lengths[:, None]
            ).long()
            logits = classifier(token_ids, attention_mask)
            loss = nn.functional.cross_entropy(logits, labels)
            total_loss += float(loss.item()) * int(labels.size(0))
            preds = logits.argmax(dim=1)
            correct += int((preds == labels).sum().item())
            total += int(labels.size(0))
    return total_loss / max(total, 1), correct / max(total, 1)


def train_classifier_with_ulmfit(
    lm_model: LanguageModel,
    data: PreparedData,
    cfg: ExperimentConfig,
    device: torch.device,
    output_dir: Path,
) -> dict[str, float]:
    cls_cfg = cfg.classifier_train
    classifier = ConcatPoolingClassifier(lm_model.encoder, cls_cfg).to(device)
    train_set = TextClassificationDataset(
        data.classifier_train, data.vocab, cls_cfg.max_seq_len
    )
    valid_set = TextClassificationDataset(
        data.classifier_valid, data.vocab, cls_cfg.max_seq_len
    )
    test_set = TextClassificationDataset(
        data.classifier_test, data.vocab, cls_cfg.max_seq_len
    )
    train_loader = DataLoader(train_set, batch_size=cls_cfg.batch_size, shuffle=True)
    valid_loader = DataLoader(valid_set, batch_size=cls_cfg.batch_size, shuffle=False)
    test_loader = DataLoader(test_set, batch_size=cls_cfg.batch_size, shuffle=False)

    stage_metrics: list[dict[str, float]] = []
    for stage_index, (unfreeze_blocks, epochs) in enumerate(
        zip(cls_cfg.unfreeze_blocks, cls_cfg.stage_epochs, strict=True),
        start=1,
    ):
        _set_encoder_trainable_blocks(classifier, unfreeze_blocks)
        param_groups, max_lrs = _build_discriminative_lrs(classifier, cls_cfg)
        optimizer = AdamW(param_groups, weight_decay=cls_cfg.weight_decay)
        total_steps = max(1, epochs * len(train_loader))
        scheduler = SlantedTriangularScheduler(
            optimizer=optimizer,
            total_steps=total_steps,
            cut_frac=cls_cfg.stlr_cut_frac,
            ratio=cls_cfg.stlr_ratio,
            max_lrs=max_lrs,
        )
        for epoch in range(epochs):
            classifier.train()
            progress = tqdm(
                train_loader,
                desc=f"cls-stage-{stage_index}-epoch-{epoch + 1}",
                leave=False,
            )
            for token_ids, lengths, labels in progress:
                token_ids = token_ids.to(device)
                lengths = lengths.to(device)
                labels = labels.to(device)
                attention_mask = (
                    torch.arange(token_ids.size(1), device=device)[None, :]
                    < lengths[:, None]
                ).long()
                optimizer.zero_grad(set_to_none=True)
                logits = classifier(token_ids, attention_mask)
                loss = nn.functional.cross_entropy(logits, labels)
                loss.backward()
                trainable_parameters = [
                    p for p in classifier.parameters() if p.requires_grad
                ]
                torch.nn.utils.clip_grad_norm_(
                    trainable_parameters, cls_cfg.gradient_clip
                )
                optimizer.step()
                scheduler.step()
                progress.set_postfix(loss=f"{loss.item():.4f}")

        valid_loss, valid_acc = _evaluate_classifier(classifier, valid_loader, device)
        stage_metrics.append(
            {
                "stage": float(stage_index),
                "unfreeze_blocks": float(unfreeze_blocks),
                "valid_loss": valid_loss,
                "valid_acc": valid_acc,
            }
        )

    test_loss, test_acc = _evaluate_classifier(classifier, test_loader, device)
    best_valid = max(stage_metrics, key=lambda item: item["valid_acc"])
    ckpt_path = output_dir / "classifier.pt"
    torch.save(classifier.state_dict(), ckpt_path)
    logger.info("Saved classifier checkpoint to {}", ckpt_path)
    return {
        "best_valid_acc": float(best_valid["valid_acc"]),
        "best_valid_loss": float(best_valid["valid_loss"]),
        "test_acc": test_acc,
        "test_loss": test_loss,
    }


def save_metrics(metrics: dict, output_dir: Path) -> Path:
    output_path = output_dir / "metrics_summary.json"
    output_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Saved metrics to {}", output_path)
    return output_path


def run_ulmfit_pipeline(
    cfg: ExperimentConfig, device: torch.device
) -> dict[str, float | dict]:
    data = prepare_data(cfg, device)
    save_vocab(data.vocab, cfg.output_dir)

    lm_model = LanguageModel(cfg.model, vocab_size=len(data.vocab.itos)).to(device)

    pretrain_path = cfg.output_dir / "lm_pretrained.pt"
    pretrain_metrics = train_language_model_stage(
        model=lm_model,
        cfg=cfg.lm_train,
        train_ids=data.lm_pretrain_train_ids,
        valid_ids=data.lm_pretrain_valid_ids,
        epochs=cfg.lm_train.pretrain_epochs,
        output_path=pretrain_path,
    )
    logger.info(
        "LM pretrain valid_loss={:.4f} valid_ppl={:.4f}",
        pretrain_metrics["valid_loss"],
        pretrain_metrics["valid_ppl"],
    )

    finetune_path = cfg.output_dir / "lm_finetuned.pt"
    finetune_metrics = train_language_model_stage(
        model=lm_model,
        cfg=cfg.lm_train,
        train_ids=data.lm_finetune_train_ids,
        valid_ids=data.lm_finetune_valid_ids,
        epochs=cfg.lm_train.finetune_epochs,
        output_path=finetune_path,
    )
    logger.info(
        "LM finetune valid_loss={:.4f} valid_ppl={:.4f}",
        finetune_metrics["valid_loss"],
        finetune_metrics["valid_ppl"],
    )

    cls_metrics = train_classifier_with_ulmfit(
        lm_model=lm_model,
        data=data,
        cfg=cfg,
        device=device,
        output_dir=cfg.output_dir,
    )
    logger.info(
        "Classifier best_valid_acc={:.4f} test_acc={:.4f}",
        cls_metrics["best_valid_acc"],
        cls_metrics["test_acc"],
    )

    metrics: dict[str, float | dict] = {
        "experiment_name": cfg.experiment_name,
        "vocab_size": float(len(data.vocab.itos)),
        "pretrain_lm": pretrain_metrics,
        "finetune_lm": finetune_metrics,
        "classifier": cls_metrics,
    }
    save_metrics(metrics, cfg.output_dir)
    return metrics
