"""
NDVI and EVI computation service.
Clips raster to zone polygon, computes vegetation indices,
renders a color-mapped PNG, and uploads to R2.
"""
import logging
import io
import uuid
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.enums import Resampling
from rasterio.warp import reproject, Resampling as WarpResampling, transform_geom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from PIL import Image

from app.services.storage_service import upload_bytes_to_r2

logger = logging.getLogger(__name__)


def _load_band(path: Path) -> Tuple[np.ndarray, dict]:
    """Load a single raster band, returning float32 array and profile."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        profile = src.profile.copy()
        nodata = src.nodata
        if nodata is not None:
            data = np.where(data == nodata, np.nan, data)
        return data, profile


def _clip_band_to_polygon(
    band_path: Path, geojson_polygon: dict
) -> Tuple[Optional[np.ndarray], Optional[dict]]:
    """
    Clip a raster band to the zone polygon.
    Handles the case where the raster doesn't fully cover the polygon.
    Returns (clipped_array, profile) or (None, None).
    """
    try:
        with rasterio.open(band_path) as src:
            # Reproject WGS84 GeoJSON geometry (EPSG:4326) to the raster's CRS (e.g. UTM)
            geom_projected = transform_geom("EPSG:4326", src.crs, geojson_polygon)
            shapes = [geom_projected]
            nodata_val = src.nodata if src.nodata is not None else 0
            try:
                clipped, transform = rasterio_mask(
                    src,
                    shapes,
                    crop=True,
                    nodata=nodata_val,
                    all_touched=True,
                    filled=True,
                )
            except ValueError as e:
                # Polygon does not intersect raster
                logger.warning(f"Polygon does not intersect raster {band_path.name}: {e}")
                return None, None

            data = clipped[0].astype(np.float32)
            if nodata_val is not None:
                data = np.where(data == nodata_val, np.nan, data)

            profile = src.profile.copy()
            profile.update(
                height=clipped.shape[1],
                width=clipped.shape[2],
                transform=transform,
                dtype=rasterio.float32,
                nodata=np.nan,
            )
            return data, profile
    except Exception as e:
        logger.error(f"Error clipping band {band_path}: {e}", exc_info=True)
        return None, None


def _align_arrays(*arrays: np.ndarray) -> Tuple[np.ndarray, ...]:
    """Ensure all arrays have the same shape by cropping to minimum dimensions."""
    min_rows = min(a.shape[0] for a in arrays)
    min_cols = min(a.shape[1] for a in arrays)
    return tuple(a[:min_rows, :min_cols] for a in arrays)


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Compute NDVI = (NIR - Red) / (NIR + Red), clipped to [-1, 1].
    Handles division by zero with nodata masking.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(
            (nir + red) != 0,
            (nir - red) / (nir + red),
            np.nan,
        )
    return np.clip(ndvi, -1.0, 1.0)


def compute_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """
    Compute EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    Values are in reflectance (0-1 range expected).
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = nir + 6.0 * red - 7.5 * blue + 1.0
        evi = np.where(
            denom != 0,
            2.5 * (nir - red) / denom,
            np.nan,
        )
    return np.clip(evi, -1.0, 2.0)


def render_ndvi_png(ndvi_array: np.ndarray) -> bytes:
    """
    Render NDVI array as a color-mapped PNG using RdYlGn colormap.
    green = healthy, yellow = stressed, red = vegetation loss.
    Returns PNG bytes.
    """
    fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
    ax.axis("off")

    cmap = plt.get_cmap("RdYlGn")
    # Normalize to [-0.2, 0.8] for better vegetation visualization
    norm = matplotlib.colors.Normalize(vmin=-0.2, vmax=0.8)

    masked = np.ma.masked_invalid(ndvi_array)
    img = ax.imshow(masked, cmap=cmap, norm=norm, interpolation="bilinear")
    plt.colorbar(img, ax=ax, fraction=0.046, pad=0.04, label="NDVI")

    fig.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


async def compute_ndvi_for_zone(
    band_paths: Dict[str, Path],
    geojson_polygon: dict,
    zone_id: str,
    scan_id: str,
) -> Optional[Dict]:
    """
    Full NDVI/EVI computation pipeline for a zone.
    Returns dict with ndvi_mean, ndvi_min, ndvi_max, evi_mean,
    cloud_cover_pct, image_url, ndvi_array (for change detection).
    """
    try:
        # Clip each band to the zone polygon
        blue_arr, blue_prof = _clip_band_to_polygon(band_paths["B02"], geojson_polygon)
        red_arr, red_prof = _clip_band_to_polygon(band_paths["B04"], geojson_polygon)
        nir_arr, nir_prof = _clip_band_to_polygon(band_paths["B08"], geojson_polygon)

        if any(arr is None for arr in [blue_arr, red_arr, nir_arr]):
            logger.error(f"Band clipping failed for zone {zone_id}")
            return None

        # Normalize Sentinel-2 reflectance (DN to [0,1])
        # L2A BOA reflectance is scaled by 10000
        blue_arr = blue_arr / 10000.0
        red_arr = red_arr / 10000.0
        nir_arr = nir_arr / 10000.0

        # Align arrays (handle slight size differences from jp2 rounding)
        blue_arr, red_arr, nir_arr = _align_arrays(blue_arr, red_arr, nir_arr)

        # Clip reflectance to valid range
        blue_arr = np.clip(blue_arr, 0, 1)
        red_arr = np.clip(red_arr, 0, 1)
        nir_arr = np.clip(nir_arr, 0, 1)

        # Compute NDVI and EVI
        ndvi = compute_ndvi(nir_arr, red_arr)
        evi = compute_evi(nir_arr, red_arr, blue_arr)

        # Estimate cloud cover: pixels with very high blue reflectance
        cloud_mask = blue_arr > 0.3
        valid_pixels = ~np.isnan(blue_arr)
        cloud_cover_pct = (
            np.sum(cloud_mask & valid_pixels) / max(np.sum(valid_pixels), 1) * 100
        )

        # Compute statistics (ignoring NaN)
        valid_ndvi = ndvi[~np.isnan(ndvi)]
        if valid_ndvi.size == 0:
            logger.warning(f"No valid NDVI pixels for zone {zone_id}")
            return None

        ndvi_mean = float(np.nanmean(ndvi))
        ndvi_min = float(np.nanmin(ndvi))
        ndvi_max = float(np.nanmax(ndvi))
        evi_mean = float(np.nanmean(evi))

        # Render and upload NDVI PNG
        png_bytes = render_ndvi_png(ndvi)
        image_key = f"ndvi/{zone_id}/{scan_id}.png"
        image_url = await upload_bytes_to_r2(png_bytes, image_key, "image/png")

        logger.info(
            f"NDVI computed for zone {zone_id}: mean={ndvi_mean:.3f}, "
            f"min={ndvi_min:.3f}, max={ndvi_max:.3f}, cloud={cloud_cover_pct:.1f}%"
        )

        return {
            "ndvi_mean": ndvi_mean,
            "ndvi_min": ndvi_min,
            "ndvi_max": ndvi_max,
            "evi_mean": evi_mean,
            "cloud_cover_pct": float(cloud_cover_pct),
            "image_url": image_url,
            "ndvi_array": ndvi,  # Raw array for change detection
            "profile": nir_prof,
        }

    except Exception as e:
        logger.error(f"NDVI computation failed for zone {zone_id}: {e}", exc_info=True)
        return None
