from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn

from research.ulmfit.config import ClassifierTrainConfig, ModelConfig


@dataclass
class LMOutput:
    logits: Tensor
    hidden_states: list[Tensor]
    hidden: list[tuple[Tensor, Tensor]]


class AWDLikeLSTMEncoder(nn.Module):
    def __init__(self, cfg: ModelConfig, vocab_size: int) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, cfg.embedding_dim)
        self.embedding_dropout = nn.Dropout(cfg.embedding_dropout)
        self.rnns = nn.ModuleList()
        self.rnn_dropouts = nn.ModuleList()
        input_size = cfg.embedding_dim
        for layer_index in range(cfg.num_layers):
            layer_hidden_size = (
                cfg.embedding_dim if layer_index == cfg.num_layers - 1 else cfg.hidden_dim
            )
            self.rnns.append(
                nn.LSTM(
                    input_size=input_size,
                    hidden_size=layer_hidden_size,
                    num_layers=1,
                    batch_first=True,
                )
            )
            self.rnn_dropouts.append(nn.Dropout(cfg.hidden_dropout))
            input_size = layer_hidden_size
        self.output_dropout = nn.Dropout(cfg.output_dropout)
        self.output_dim = input_size

    def forward(
        self,
        input_ids: Tensor,
        hidden: list[tuple[Tensor, Tensor]] | None = None,
    ) -> tuple[Tensor, list[tuple[Tensor, Tensor]], list[Tensor]]:
        x = self.embedding(input_ids)
        x = self.embedding_dropout(x)
        new_hidden: list[tuple[Tensor, Tensor]] = []
        hidden_states: list[Tensor] = []
        layer_hidden = hidden or [None] * len(self.rnns)
        for idx, rnn in enumerate(self.rnns):
            out, layer_state = rnn(x, layer_hidden[idx])
            out = self.rnn_dropouts[idx](out)
            hidden_states.append(out)
            new_hidden.append(layer_state)
            x = out
        x = self.output_dropout(x)
        return x, new_hidden, hidden_states


class LanguageModel(nn.Module):
    def __init__(self, cfg: ModelConfig, vocab_size: int) -> None:
        super().__init__()
        self.encoder = AWDLikeLSTMEncoder(cfg, vocab_size)
        self.decoder = nn.Linear(self.encoder.output_dim, vocab_size)
        self.decoder.weight = self.encoder.embedding.weight

    def forward(
        self,
        input_ids: Tensor,
        hidden: list[tuple[Tensor, Tensor]] | None = None,
    ) -> LMOutput:
        encoded, hidden_out, hidden_states = self.encoder(input_ids, hidden)
        logits = self.decoder(encoded)
        return LMOutput(logits=logits, hidden_states=hidden_states, hidden=hidden_out)


class ConcatPoolingClassifier(nn.Module):
    def __init__(
        self,
        encoder: AWDLikeLSTMEncoder,
        cfg: ClassifierTrainConfig,
    ) -> None:
        super().__init__()
        self.encoder = encoder
        self.head_dropout = nn.Dropout(cfg.head_dropout)
        pooled_dim = encoder.output_dim * 3
        self.classifier = nn.Sequential(
            nn.Linear(pooled_dim, cfg.fc_hidden_dim),
            nn.ReLU(),
            nn.Dropout(cfg.head_dropout),
            nn.Linear(cfg.fc_hidden_dim, cfg.num_classes),
        )

    def _concat_pool(self, encoded: Tensor, attention_mask: Tensor) -> Tensor:
        mask = attention_mask.unsqueeze(-1).float()
        masked = encoded * mask
        sum_pool = masked.sum(dim=1)
        denom = mask.sum(dim=1).clamp(min=1.0)
        mean_pool = sum_pool / denom
        fill_value = torch.finfo(encoded.dtype).min
        max_pool = encoded.masked_fill(mask == 0.0, fill_value).max(dim=1).values
        last_index = attention_mask.long().sum(dim=1).clamp(min=1) - 1
        last_hidden = encoded[
            torch.arange(encoded.size(0), device=encoded.device),
            last_index,
        ]
        return torch.cat([last_hidden, max_pool, mean_pool], dim=1)

    def forward(self, input_ids: Tensor, attention_mask: Tensor) -> Tensor:
        encoded, _, _ = self.encoder(input_ids)
        pooled = self._concat_pool(encoded, attention_mask)
        pooled = self.head_dropout(pooled)
        return self.classifier(pooled)
