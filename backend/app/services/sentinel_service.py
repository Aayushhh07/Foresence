"""
Sentinel-2 data fetcher.
Primary source: Copernicus Data Space OData API (L2A products).
Fallback: Element84 STAC (earth-search.aws.element84.com/v1).
"""
import logging
import os
import tempfile
import zipfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import httpx
import numpy as np
import rasterio
from rasterio.warp import transform_geom
from rasterio.mask import mask as rasterio_mask
from fastapi.concurrency import run_in_threadpool
from pystac_client import Client as StacClient

from app.core.config import settings

logger = logging.getLogger(__name__)

COPERNICUS_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
COPERNICUS_ODATA_URL = (
    "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
)
COPERNICUS_DOWNLOAD_URL = (
    "https://zipper.dataspace.copernicus.eu/odata/v1/Products"
)
ELEMENT84_STAC_URL = "https://earth-search.aws.element84.com/v1"

_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0}


async def _get_copernicus_token() -> str:
    """Fetch or refresh Copernicus OAuth2 token."""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            COPERNICUS_TOKEN_URL,
            data={
                "grant_type": "password",
                "username": settings.copernicus_username,
                "password": settings.copernicus_password,
                "client_id": "cdse-public",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 600)
        logger.info("Copernicus token refreshed.")
        return _token_cache["token"]


def _geojson_to_wkt(geojson_coords: list) -> str:
    """Convert GeoJSON polygon coordinates to WKT POLYGON string."""
    ring = geojson_coords[0]
    pairs = ", ".join(f"{lon} {lat}" for lon, lat in ring)
    return f"POLYGON(({pairs}))"


async def search_copernicus(
    geojson_coords: list, start_date: datetime, end_date: datetime
) -> Optional[Dict]:
    """
    Search Copernicus Data Space for Sentinel-2 L2A products.
    Returns the product metadata dict or None if not found.
    """
    wkt = _geojson_to_wkt(geojson_coords)
    date_from = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    date_to = end_date.strftime("%Y-%m-%dT%H:%M:%S.999Z")

    filter_str = (
        f"Collection/Name eq 'SENTINEL-2' and "
        f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        f"and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and "
        f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
        f"and att/OData.CSC.DoubleAttribute/Value lt 30.00) and "
        f"ContentDate/Start gt {date_from} and "
        f"ContentDate/Start lt {date_to} and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            COPERNICUS_ODATA_URL,
            params={
                "$filter": filter_str,
                "$orderby": "ContentDate/Start desc",
                "$top": 1,
                "$expand": "Attributes",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    products = data.get("value", [])
    if not products:
        logger.info("No Copernicus products found for the given parameters.")
        return None

    product = products[0]
    logger.info(f"Found Copernicus product: {product.get('Name')}")
    return product


async def download_sentinel_bands(
    product_id: str, output_dir: Path
) -> Optional[Dict[str, Path]]:
    """
    Download Sentinel-2 product and extract Band 2 (Blue), Band 4 (Red), Band 8 (NIR).
    Returns dict with band paths: {B02: Path, B04: Path, B08: Path}
    """
    token = await _get_copernicus_token()
    download_url = f"{COPERNICUS_DOWNLOAD_URL}({product_id})/$value"

    zip_path = output_dir / f"{product_id}.zip"
    logger.info(f"Downloading product {product_id}...")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(600.0, connect=30.0),
        follow_redirects=True,
    ) as client:
        async with client.stream(
            "GET", download_url,
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)

    logger.info(f"Downloaded {zip_path.stat().st_size / 1e6:.1f} MB")
    return _extract_bands(zip_path, output_dir)


def _extract_bands(zip_path: Path, output_dir: Path) -> Optional[Dict[str, Path]]:
    """Extract B02, B04, B08 jp2 files from a Sentinel-2 zip archive."""
    bands = {"B02": None, "B04": None, "B08": None}

    with zipfile.ZipFile(zip_path, "r") as z:
        all_files = z.namelist()
        for fname in all_files:
            for band_key in bands:
                # Match 10m resolution bands
                if f"_{band_key}_10m.jp2" in fname or f"_{band_key}.jp2" in fname:
                    if bands[band_key] is None:
                        dest = output_dir / Path(fname).name
                        with z.open(fname) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        bands[band_key] = dest
                        logger.info(f"Extracted {band_key}: {dest.name}")

    # Verify all bands extracted
    missing = [k for k, v in bands.items() if v is None]
    if missing:
        logger.warning(f"Missing bands: {missing}")
        return None

    return bands


def _download_cropped_cog(href: str, geojson_polygon: dict, dest: Path) -> Path:
    """
    Open a remote Cloud Optimized GeoTIFF (COG), crop it to the zone polygon,
    and save the small cropped result locally.
    """
    logger.info(f"Streaming and cropping remote COG: {href}")
    try:
        with rasterio.open(href) as src:
            # Reproject WGS84 GeoJSON geometry (EPSG:4326) to the raster's CRS
            geom_projected = transform_geom("EPSG:4326", src.crs, geojson_polygon)

            # Mask/crop the remote dataset to the polygon
            nodata_val = src.nodata if src.nodata is not None else 0
            clipped, transform = rasterio_mask(
                src,
                [geom_projected],
                crop=True,
                nodata=nodata_val,
                all_touched=True,
                filled=True,
            )

            # Prepare metadata for the output file
            out_meta = src.profile.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": clipped.shape[1],
                "width": clipped.shape[2],
                "transform": transform,
                "nodata": nodata_val,
                "dtype": src.profile["dtype"]
            })

            # Write only the clipped image to the local destination
            dest.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(dest, "w", **out_meta) as dst:
                dst.write(clipped)

        logger.info(f"Saved cropped band locally: {dest} ({dest.stat().st_size} bytes)")
        return dest
    except Exception as e:
        logger.error(f"Failed to stream/crop remote COG from {href}: {e}", exc_info=True)
        raise


async def fetch_via_stac_fallback(
    geojson_coords: list, start_date: datetime, end_date: datetime
) -> Optional[Dict[str, Path]]:
    """
    Use Element84 STAC API as fallback to download Sentinel-2 L2A tiles.
    Returns band paths or None.
    """
    logger.info("Trying Element84 STAC fallback...")
    try:
        catalog = StacClient.open(ELEMENT84_STAC_URL)

        # Build bounding box from polygon coordinates
        ring = geojson_coords[0]
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]
        bbox = [min(lons), min(lats), max(lons), max(lats)]

        search = catalog.search(
            collections=["sentinel-2-c1-l2a", "sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
        )

        items = list(search.items())
        if not items:
            logger.warning("No STAC items found via Element84 fallback.")
            return None

        # Filter items with < 80% cloud cover to avoid completely cloudy scenes if possible
        clean_items = [i for i in items if i.properties.get("eo:cloud_cover", 100) < 80]
        if clean_items:
            items = clean_items

        # Sort items locally by datetime descending to get the most recent one
        items = sorted(
            items,
            key=lambda x: x.datetime if x.datetime else datetime.min,
            reverse=True
        )
        item = items[0]

        logger.info(f"STAC item found: {item.id}")

        output_dir = Path(tempfile.mkdtemp(prefix="foresence_stac_"))
        band_map = {}
        geojson_polygon = {"type": "Polygon", "coordinates": geojson_coords}

        for band_key, asset_key in [("B02", "blue"), ("B04", "red"), ("B08", "nir")]:
            if asset_key not in item.assets:
                # Try alternate asset keys
                alt_keys = {
                    "blue": ["B02", "b02"],
                    "red": ["B04", "b04"],
                    "nir": ["B08", "b08"],
                }
                found = False
                for ak in alt_keys.get(asset_key, []):
                    if ak in item.assets:
                        asset_key = ak
                        found = True
                        break
                if not found:
                    logger.error(f"Asset {asset_key} not found in STAC item.")
                    return None

            href = item.assets[asset_key].href
            dest = output_dir / f"{band_key}.tif"

            # Stream and crop the COG in a thread pool to avoid blocking the event loop
            await run_in_threadpool(_download_cropped_cog, href, geojson_polygon, dest)
            band_map[band_key] = dest

        return band_map

    except Exception as e:
        logger.error(f"STAC fallback failed: {e}", exc_info=True)
        return None


async def fetch_sentinel_bands(
    geojson_coords: list,
    zone_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Optional[Dict[str, Path]]:
    """
    Main entry point: try STAC first (since it supports windowed downloads and doesn't require credentials),
    then Copernicus as fallback.
    Returns {B02: Path, B04: Path, B08: Path} or None.
    """
    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Primary: Element84 STAC (fast, public, windowed downloads)
    try:
        bands = await fetch_via_stac_fallback(geojson_coords, start_date, end_date)
        if bands:
            logger.info(f"Successfully retrieved bands from STAC for zone {zone_id}")
            return bands
    except Exception as e:
        logger.warning(f"STAC primary search failed, trying Copernicus fallback: {e}")

    # Fallback: Copernicus OData (requires credentials, downloads full zip file)
    output_dir = Path(tempfile.mkdtemp(prefix=f"foresence_{zone_id}_"))
    try:
        product = await search_copernicus(geojson_coords, start_date, end_date)
        if product:
            product_id = product["Id"]
            bands = await download_sentinel_bands(product_id, output_dir)
            if bands:
                logger.info(f"Successfully retrieved bands from Copernicus fallback for zone {zone_id}")
                return bands
    except Exception as e:
        logger.error(f"Copernicus fallback failed for zone {zone_id}: {e}", exc_info=True)

    return None


async def check_satellite_availability(
    geojson_coords: list,
    lookback_days: int = 30,
    require_copernicus_auth: bool = False,
) -> Dict[str, Any]:
    """
    Check live satellite API availability for a polygon.
    Returns source connectivity and latest scene metadata when available.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=lookback_days)

    result: Dict[str, Any] = {
        "window": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "lookback_days": lookback_days,
        },
        "stac": {"reachable": False, "latest_scene": None, "error": None},
        "copernicus": {
            "auth_ok": False,
            "latest_scene": None,
            "error": None,
            "checked": require_copernicus_auth,
        },
    }

    # STAC check (public, primary)
    try:
        catalog = StacClient.open(ELEMENT84_STAC_URL)
        ring = geojson_coords[0]
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]
        bbox = [min(lons), min(lats), max(lons), max(lats)]

        search = catalog.search(
            collections=["sentinel-2-c1-l2a", "sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
            limit=1,
            sortby=[{"field": "properties.datetime", "direction": "desc"}],
        )
        items = list(search.items())
        result["stac"]["reachable"] = True

        if items:
            item = items[0]
            result["stac"]["latest_scene"] = {
                "id": item.id,
                "datetime": (
                    item.datetime.isoformat()
                    if item.datetime is not None
                    else item.properties.get("datetime")
                ),
                "cloud_cover": item.properties.get("eo:cloud_cover"),
                "collection": item.collection_id,
            }
    except Exception as e:
        result["stac"]["error"] = str(e)

    # Optional Copernicus auth + latest product check
    if require_copernicus_auth:
        try:
            await _get_copernicus_token()
            result["copernicus"]["auth_ok"] = True
            product = await search_copernicus(geojson_coords, start_date, end_date)
            if product:
                result["copernicus"]["latest_scene"] = {
                    "id": product.get("Id"),
                    "name": product.get("Name"),
                    "datetime": (product.get("ContentDate", {}) or {}).get("Start"),
                }
        except Exception as e:
            result["copernicus"]["error"] = str(e)

    return result

