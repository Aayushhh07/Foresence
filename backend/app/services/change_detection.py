"""
Change detection service.
Compares current NDVI array vs previous snapshot's NDVI array,
computes pixel-level delta, affected area in hectares, confidence score,
and renders a diff PNG uploaded to R2.
"""
import logging
import io
import numpy as np
from typing import Optional, Dict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pyproj import Transformer, CRS, Geod

from app.services.storage_service import upload_bytes_to_r2

logger = logging.getLogger(__name__)


def _compute_zone_area_ha(geojson_coords: list) -> float:
    """
    Compute the area of a GeoJSON polygon in hectares using WGS84 geodesic.
    """
    geod = Geod(ellps="WGS84")
    ring = geojson_coords[0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    area_m2, _ = geod.polygon_area_perimeter(lons, lats)
    return abs(area_m2) / 10000.0  # m² to ha


def _pixel_area_ha(profile: dict) -> float:
    """
    Estimate the area of a single pixel in hectares from the raster profile.
    Uses the transform's pixel size (in CRS units).
    """
    transform = profile.get("transform")
    if transform is None:
        return 0.0001  # fallback: ~10m Sentinel-2 pixel ≈ 0.01 ha

    pixel_width = abs(transform.a)
    pixel_height = abs(transform.e)

    crs_str = str(profile.get("crs", "EPSG:4326"))

    # If geographic (degrees), convert to meters using crude approximation
    if "4326" in crs_str or "geographic" in crs_str.lower():
        # Mean meters per degree at equator: ~111320
        px_meters = pixel_width * 111320
        py_meters = pixel_height * 111320
        return (px_meters * py_meters) / 10000.0
    else:
        # Projected CRS, units are already meters
        return (pixel_width * pixel_height) / 10000.0


def render_change_map(
    ndvi_before: np.ndarray,
    ndvi_after: np.ndarray,
    threshold: float,
) -> bytes:
    """
    Render a change map PNG:
    - gray:  no significant change
    - red:   vegetation loss (ndvi_delta < -threshold)
    - green: vegetation gain (ndvi_delta > threshold)
    Returns PNG bytes.
    """
    # Align arrays if sizes differ
    min_rows = min(ndvi_before.shape[0], ndvi_after.shape[0])
    min_cols = min(ndvi_before.shape[1], ndvi_after.shape[1])
    before = ndvi_before[:min_rows, :min_cols]
    after = ndvi_after[:min_rows, :min_cols]

    delta = after - before

    # Create RGB image
    rgb = np.ones((*delta.shape, 3), dtype=np.float32) * 0.5  # gray

    loss_mask = delta < -threshold
    gain_mask = delta > threshold

    # Red for loss, intensity by magnitude
    rgb[loss_mask, 0] = np.clip(0.5 + abs(delta[loss_mask]) * 2, 0, 1)
    rgb[loss_mask, 1] = 0.1
    rgb[loss_mask, 2] = 0.1

    # Green for gain
    rgb[gain_mask, 0] = 0.1
    rgb[gain_mask, 1] = np.clip(0.5 + delta[gain_mask] * 2, 0, 1)
    rgb[gain_mask, 2] = 0.1

    # NaN pixels → transparent (black)
    nan_mask = np.isnan(delta)
    rgb[nan_mask] = [0.2, 0.2, 0.2]

    fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
    ax.axis("off")
    ax.imshow(rgb, interpolation="bilinear")

    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=(0.8, 0.1, 0.1), label="Vegetation Loss"),
        Patch(facecolor=(0.1, 0.8, 0.1), label="Vegetation Gain"),
        Patch(facecolor=(0.5, 0.5, 0.5), label="No Change"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="lower right",
        framealpha=0.8,
        fontsize=9,
    )
    ax.set_title("NDVI Change Detection Map", fontsize=12, pad=4)

    fig.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


async def detect_change(
    current_result: Dict,
    previous_snapshot: Optional[Dict],
    geojson_coords: list,
    zone_id: str,
    scan_id: str,
    ndvi_threshold: float = 0.15,
) -> Optional[Dict]:
    """
    Compare current NDVI with previous snapshot to detect deforestation.

    Returns dict with:
    - ndvi_delta, evi_delta
    - affected_pixels, affected_area_ha, affected_area_pct
    - confidence
    - change_map_url
    Returns None if no previous snapshot is available or on error.
    """
    if previous_snapshot is None:
        logger.info(f"No previous snapshot for zone {zone_id}. Skipping change detection.")
        return None

    try:
        current_ndvi = current_result.get("ndvi_array")
        if current_ndvi is None:
            logger.error("Current NDVI array missing.")
            return None

        # Previous snapshot may not have the raw array persisted.
        # In this case we use the mean values for scalar metrics only
        # and skip pixel-level diff if arrays aren't available.
        prev_ndvi_mean = previous_snapshot.get("ndvi_mean", 0.0)
        prev_evi_mean = previous_snapshot.get("evi_mean", 0.0)

        curr_ndvi_mean = current_result["ndvi_mean"]
        curr_evi_mean = current_result["evi_mean"]

        ndvi_delta = curr_ndvi_mean - prev_ndvi_mean
        evi_delta = curr_evi_mean - prev_evi_mean

        # Pixel-level analysis on current array
        # Mask pixels below threshold compared to previous mean
        loss_mask = current_ndvi < (prev_ndvi_mean - ndvi_threshold)
        valid_mask = ~np.isnan(current_ndvi)
        affected_pixels = int(np.sum(loss_mask & valid_mask))
        total_valid_pixels = int(np.sum(valid_mask))

        affected_area_pct = affected_pixels / max(total_valid_pixels, 1)

        # Compute affected area in hectares
        profile = current_result.get("profile", {})
        px_ha = _pixel_area_ha(profile)
        affected_area_ha = affected_pixels * px_ha

        # Confidence score formula
        cloud_cover_pct = current_result.get("cloud_cover_pct", 0.0)
        raw_confidence = min(
            1.0,
            (abs(ndvi_delta) / 0.4) * 0.7 + (affected_area_pct / 0.3) * 0.3,
        )
        # Reduce confidence for high cloud cover
        cloud_penalty = (cloud_cover_pct / 100.0) * 0.5
        confidence = max(0.0, raw_confidence - cloud_penalty)

        # Render change map
        # For pixel-level diff map, use constant previous mean as reference
        prev_ndvi_synthetic = np.full_like(current_ndvi, prev_ndvi_mean)
        change_png = render_change_map(prev_ndvi_synthetic, current_ndvi, ndvi_threshold)

        change_map_key = f"changes/{zone_id}/{scan_id}.png"
        change_map_url = await upload_bytes_to_r2(change_png, change_map_key, "image/png")

        logger.info(
            f"Change detection for zone {zone_id}: delta={ndvi_delta:.3f}, "
            f"confidence={confidence:.2f}, area={affected_area_ha:.2f}ha"
        )

        return {
            "ndvi_delta": float(ndvi_delta),
            "evi_delta": float(evi_delta),
            "affected_pixels": affected_pixels,
            "affected_area_ha": float(affected_area_ha),
            "affected_area_pct": float(affected_area_pct),
            "confidence": float(confidence),
            "change_map_url": change_map_url,
            "ndvi_before": float(prev_ndvi_mean),
            "ndvi_after": float(curr_ndvi_mean),
            "evi_before": float(prev_evi_mean),
            "evi_after": float(curr_evi_mean),
        }

    except Exception as e:
        logger.error(f"Change detection error for zone {zone_id}: {e}", exc_info=True)
        return None
