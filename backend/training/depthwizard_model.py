"""Shared DepthWizard multiscale model used by Kaggle training and inference.

The model deliberately keeps the pretrained Depth Anything V2 encoder intact,
but replaces its generic relative-depth head with a DPT-like multiscale decoder
whose outputs are trained on GAMUS nDSM, semantic labels, and building edges.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from app.semantic_contract import CLASS_COUNT
except ModuleNotFoundError:  # Allows this file to run beside the Kaggle script.
    CLASS_COUNT = 7


def _tokens_to_map(values: torch.Tensor) -> torch.Tensor:
    """Convert a ViT token sequence to BCHW, removing a class token if present."""
    if values.ndim == 4:
        return values
    if values.ndim != 3:
        raise ValueError(f"Expected a token tensor or feature map, got {tuple(values.shape)}")
    tokens = values
    count = tokens.shape[1]
    side = int(math.sqrt(count))
    if side * side != count:
        side = int(math.sqrt(count - 1))
        if side * side != count - 1:
            raise ValueError(f"Cannot infer a square token grid from {count} tokens")
        tokens = tokens[:, 1:]
    tokens = tokens[:, : side * side]
    return tokens.transpose(1, 2).reshape(tokens.shape[0], tokens.shape[2], side, side)


class ConvNormAct(nn.Sequential):
    def __init__(self, input_channels: int, output_channels: int, kernel_size: int = 3) -> None:
        groups = 8 if output_channels >= 8 else 1
        super().__init__(
            nn.Conv2d(input_channels, output_channels, kernel_size, padding=kernel_size // 2, bias=False),
            nn.GroupNorm(groups, output_channels),
            nn.GELU(),
        )


class DPTFeatureFusion(nn.Module):
    """Fuse four encoder levels and decode them to a dense quarter-resolution map."""

    def __init__(self, input_channels: int, feature_count: int = 4, decoder_channels: int = 128) -> None:
        super().__init__()
        self.projections = nn.ModuleList(
            [ConvNormAct(input_channels, decoder_channels, kernel_size=1) for _ in range(feature_count)]
        )
        self.fusion = nn.Sequential(
            ConvNormAct(decoder_channels * feature_count, decoder_channels),
            ConvNormAct(decoder_channels, decoder_channels),
        )
        self.refine = nn.Sequential(
            ConvNormAct(decoder_channels, decoder_channels),
            ConvNormAct(decoder_channels, decoder_channels),
        )

    def forward(self, features: list[torch.Tensor], output_size: tuple[int, int]) -> torch.Tensor:
        if len(features) != len(self.projections):
            raise ValueError(f"Expected {len(self.projections)} feature levels, got {len(features)}")
        maps = [_tokens_to_map(feature) for feature in features]
        target_size = maps[-1].shape[-2:]
        projected = []
        for projection, feature in zip(self.projections, maps):
            value = projection(feature)
            if value.shape[-2:] != target_size:
                value = F.interpolate(value, size=target_size, mode="bilinear", align_corners=False)
            projected.append(value)
        fused = self.fusion(torch.cat(projected, dim=1))
        fused = F.interpolate(fused, size=(max(1, output_size[0] // 4), max(1, output_size[1] // 4)), mode="bilinear", align_corners=False)
        return self.refine(fused)


class DepthWizardMultitask(nn.Module):
    """Depth Anything V2 encoder with nDSM, semantic, and boundary heads."""

    checkpoint_format = "depthwizard_dpt_multiscale_v2"

    def __init__(self, base_model: nn.Module, class_count: int = CLASS_COUNT, decoder_channels: int = 128) -> None:
        super().__init__()
        self.base = base_model
        hidden_size = getattr(base_model.config, "hidden_size", None)
        backbone_config = getattr(base_model.config, "backbone_config", None)
        if hidden_size is None and isinstance(backbone_config, dict):
            hidden_size = backbone_config.get("hidden_size")
        if hidden_size is None and backbone_config is not None:
            hidden_size = getattr(backbone_config, "hidden_size", None)
        # Depth Anything V2 Base uses a 768-wide ViT backbone. The explicit
        # fallback is only for older Transformers configurations that do not
        # expose backbone_config as an object.
        hidden_size = int(hidden_size or (getattr(base_model.config, "reassemble_hidden_size", None) or 768))
        self.decoder = DPTFeatureFusion(hidden_size, feature_count=4, decoder_channels=decoder_channels)
        self.height_head = nn.Sequential(
            ConvNormAct(decoder_channels, decoder_channels),
            nn.Conv2d(decoder_channels, 1, kernel_size=1),
        )
        self.semantic_head = nn.Sequential(
            ConvNormAct(decoder_channels, decoder_channels),
            nn.Conv2d(decoder_channels, class_count, kernel_size=1),
        )
        self.boundary_head = nn.Sequential(
            ConvNormAct(decoder_channels, decoder_channels // 2),
            nn.Conv2d(decoder_channels // 2, 1, kernel_size=1),
        )

    def _feature_levels(self, outputs: object) -> list[torch.Tensor]:
        hidden_states = getattr(outputs, "hidden_states", None)
        if hidden_states is None:
            hidden_states = getattr(outputs, "backbone_hidden_states", None)
        if hidden_states is None or len(hidden_states) < 4:
            raise ValueError("Depth Anything output did not include at least four hidden-state levels")
        return list(hidden_states[-4:])

    def forward(self, pixel_values: torch.Tensor) -> dict[str, torch.Tensor]:
        outputs = self.base(pixel_values=pixel_values, output_hidden_states=True, return_dict=True)
        features = self._feature_levels(outputs)
        fused = self.decoder(features, pixel_values.shape[-2:])
        height = F.interpolate(self.height_head(fused), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
        semantic = F.interpolate(self.semantic_head(fused), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
        boundary = F.interpolate(self.boundary_head(fused), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
        return {
            "height": F.softplus(height),
            "semantic": semantic,
            "boundary": boundary,
        }


def build_depthwizard_model(model_id: str) -> DepthWizardMultitask:
    from transformers import AutoModelForDepthEstimation

    base = AutoModelForDepthEstimation.from_pretrained(model_id)
    return DepthWizardMultitask(base)
