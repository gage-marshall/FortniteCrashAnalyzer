"""NVIDIA driver download URL resolver using NVIDIA's public API."""
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import json
from typing import Optional, Tuple, Dict, Any
from difflib import SequenceMatcher


class NvidiaDriverResolver:
    """Resolves NVIDIA GPU names to driver download URLs."""

    # NVIDIA API endpoints
    LOOKUP_API = "https://www.nvidia.com/Download/API/lookupValueSearch.aspx"
    DRIVER_API = "https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/services/AjaxDriverService.php"

    # Driver page URL pattern (using driver ID from API)
    DRIVER_PAGE_URL = "https://www.nvidia.com/download/driverResults.aspx/{driver_id}/en-us"

    # Windows 10/11 64-bit OS ID
    WINDOWS_10_11_64BIT_OSID = 57

    # API Structure:
    # TypeID=1: Product Type (e.g., "GeForce" has Value=1)
    # TypeID=2: Product Series (e.g., "GeForce RTX 40 Series") with ParentID=1 (GeForce)
    # TypeID=3: Specific Products (e.g., "NVIDIA GeForce RTX 4060") with ParentID=psid

    @staticmethod
    def get_driver_url(gpu_brand: str) -> Optional[str]:
        """Get NVIDIA driver download URL for a given GPU.

        Args:
            gpu_brand: GPU brand string from crash data (e.g., "NVIDIA GeForce RTX 4060")

        Returns:
            Driver download page URL or None if unable to resolve.
        """
        # Check if NVIDIA GPU
        if not NvidiaDriverResolver._is_nvidia_gpu(gpu_brand):
            return None

        # Extract model from GPU brand string
        model = NvidiaDriverResolver._extract_model(gpu_brand)
        if not model:
            return None

        # Find matching product series and product
        psid, pfid = NvidiaDriverResolver._find_product_ids(model)
        if not psid or not pfid:
            return None

        # Fetch latest driver info from API
        driver_info = NvidiaDriverResolver._fetch_latest_driver_info(psid, pfid)
        if driver_info and driver_info.get('driver_id'):
            return NvidiaDriverResolver.DRIVER_PAGE_URL.format(driver_id=driver_info['driver_id'])

        return None

    @staticmethod
    def get_driver_info(gpu_brand: str) -> Optional[Dict[str, Any]]:
        """Get NVIDIA driver information for a given GPU.

        Args:
            gpu_brand: GPU brand string from crash data (e.g., "NVIDIA GeForce RTX 4060")

        Returns:
            Dict with 'driver_id', 'version', and 'url' or None if unable to resolve.
        """
        # Check if NVIDIA GPU
        if not NvidiaDriverResolver._is_nvidia_gpu(gpu_brand):
            print(f"[DEBUG] Not NVIDIA GPU: {gpu_brand}")
            return None

        # Extract model from GPU brand string
        model = NvidiaDriverResolver._extract_model(gpu_brand)
        print(f"[DEBUG] Extracted model: '{model}' from '{gpu_brand}'")
        if not model:
            print("[DEBUG] Failed to extract model")
            return None

        # Find matching product series and product
        psid, pfid = NvidiaDriverResolver._find_product_ids(model)
        print(f"[DEBUG] Found IDs: psid={psid}, pfid={pfid}")
        if not psid or not pfid:
            print("[DEBUG] Failed to find psid/pfid")
            return None

        # Fetch latest driver info from API
        driver_info = NvidiaDriverResolver._fetch_latest_driver_info(psid, pfid)
        print(f"[DEBUG] Driver info from API: {driver_info}")
        if driver_info and driver_info.get('driver_id'):
            driver_info['url'] = NvidiaDriverResolver.DRIVER_PAGE_URL.format(driver_id=driver_info['driver_id'])
            print(f"[DEBUG] Final URL: {driver_info['url']}")
            return driver_info

        print("[DEBUG] Failed to get driver info from API")
        return None

    @staticmethod
    def _is_nvidia_gpu(gpu_brand: str) -> bool:
        """Check if GPU is NVIDIA.

        Args:
            gpu_brand: GPU brand string.

        Returns:
            True if NVIDIA GPU.
        """
        gpu_lower = gpu_brand.lower()
        return any(keyword in gpu_lower for keyword in ['nvidia', 'geforce', 'rtx', 'gtx', 'quadro'])

    @staticmethod
    def _extract_model(gpu_brand: str) -> str:
        """Extract GPU model from brand string.

        Args:
            gpu_brand: GPU brand string (e.g., "NVIDIA GeForce RTX 4060")

        Returns:
            Extracted model (e.g., "RTX 4060")
        """
        # Remove common prefixes
        model = gpu_brand
        for prefix in ['NVIDIA', 'GeForce', 'NVIDIA GeForce']:
            model = model.replace(prefix, '').strip()

        return model

    @staticmethod
    def _find_product_ids(model: str) -> Tuple[Optional[int], Optional[int]]:
        """Find NVIDIA product series ID (psid) and product family ID (pfid).

        Args:
            model: GPU model string (e.g., "RTX 4060")

        Returns:
            Tuple of (psid, pfid) or (None, None) if not found.
        """
        try:
            # Fetch product series list (TypeID=2, ParentID=1 for GeForce)
            series_list = NvidiaDriverResolver._fetch_series_list()
            if not series_list:
                return None, None

            # Find best matching series
            best_series = NvidiaDriverResolver._find_best_series_match(model, series_list)
            if not best_series:
                return None, None

            psid = best_series['psid']

            # Fetch products in this series (TypeID=3, ParentID=psid)
            product_list = NvidiaDriverResolver._fetch_product_list(psid)
            if not product_list:
                return None, None

            # Find exact matching product
            best_product = NvidiaDriverResolver._find_best_product_match(model, product_list)
            if not best_product:
                return None, None

            pfid = best_product['pfid']

            return psid, pfid

        except Exception as e:
            print(f"Error finding NVIDIA product IDs: {e}")
            return None, None

    @staticmethod
    def _fetch_latest_driver_info(psid: int, pfid: int) -> Optional[Dict[str, Any]]:
        """Fetch latest driver information from NVIDIA API.

        Args:
            psid: Product series ID.
            pfid: Product family ID.

        Returns:
            Dict with 'driver_id' and 'version' or None if not found.
        """
        try:
            # Build API URL with parameters
            params = {
                'func': 'DriverManualLookup',
                'psid': psid,
                'pfid': pfid,
                'osID': NvidiaDriverResolver.WINDOWS_10_11_64BIT_OSID,
                'languageCode': 1033,  # English
                'beta': 0,
                'isWHQL': 1,
                'dltype': -1,
                'dch': 1,
                'upCRD': 0,
                'qnf': 0,
                'sort1': 0,
                'numberOfResults': 1
            }

            # Build query string
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{NvidiaDriverResolver.DRIVER_API}?{query_string}"

            # Fetch driver info
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read()

            # Parse JSON response
            result = json.loads(data)

            # Extract driver info from response
            if result.get('Success') and result.get('IDS'):
                drivers = result['IDS']
                if len(drivers) > 0 and 'downloadInfo' in drivers[0]:
                    driver_info = drivers[0]['downloadInfo']  # It's a dict, not array
                    return {
                        'driver_id': driver_info.get('ID'),
                        'version': driver_info.get('Version', 'Unknown')
                    }

            return None

        except Exception as e:
            print(f"Error fetching driver info from NVIDIA API: {e}")
            return None

    @staticmethod
    def _fetch_series_list() -> list:
        """Fetch list of NVIDIA GeForce product series from API.

        Uses TypeID=2 with ParentID=1 (GeForce).

        Returns:
            List of dicts with 'name' and 'psid' keys.
        """
        try:
            # TypeID=2 (Product Series), ParentID=1 (GeForce)
            url = f"{NvidiaDriverResolver.LOOKUP_API}?TypeID=2&ParentID=1"
            with urllib.request.urlopen(url, timeout=5) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            series_list = []

            # Parse XML structure: <LookupValueSearch><LookupValues><LookupValue>
            for lookup_value in root.findall('.//LookupValue'):
                name_elem = lookup_value.find('Name')
                value_elem = lookup_value.find('Value')

                if name_elem is not None and value_elem is not None:
                    name = name_elem.text
                    psid = int(value_elem.text)

                    # Filter to relevant series (RTX, GTX 9/10/16)
                    if name and ('RTX' in name or 'GTX 1' in name or 'GTX 9' in name):
                        series_list.append({'name': name, 'psid': psid})

            return series_list

        except Exception as e:
            print(f"Error fetching NVIDIA series list: {e}")
            return []

    @staticmethod
    def _fetch_product_list(psid: int) -> list:
        """Fetch list of specific products in a series from API.

        Uses TypeID=3 with ParentID=psid.

        Args:
            psid: Product series ID.

        Returns:
            List of dicts with 'name' and 'pfid' keys.
        """
        try:
            # TypeID=3 (Specific Products), ParentID=psid (series)
            url = f"{NvidiaDriverResolver.LOOKUP_API}?TypeID=3&ParentID={psid}"
            with urllib.request.urlopen(url, timeout=5) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            product_list = []

            for lookup_value in root.findall('.//LookupValue'):
                name_elem = lookup_value.find('Name')
                value_elem = lookup_value.find('Value')

                if name_elem is not None and value_elem is not None:
                    name = name_elem.text
                    pfid = int(value_elem.text)

                    if name:
                        product_list.append({'name': name, 'pfid': pfid})

            return product_list

        except Exception as e:
            print(f"Error fetching NVIDIA product list for psid {psid}: {e}")
            return []

    @staticmethod
    def _find_best_series_match(model: str, series_list: list) -> Optional[dict]:
        """Find best matching product series.

        Args:
            model: GPU model string (e.g., "RTX 4060")
            series_list: List of series dicts from API.

        Returns:
            Best matching series dict or None.
        """
        model_lower = model.lower()

        # Extract series number (e.g., "40" from "RTX 4060")
        series_num = None
        if 'rtx' in model_lower:
            # RTX 20, 30, 40, 50 series
            for num in ['50', '40', '30', '20', '16']:
                if num in model_lower:
                    series_num = num
                    break
        elif 'gtx' in model_lower:
            # GTX 16, 10, 900, 700, 600 series
            for num in ['16', '10', '900', '700', '600']:
                if num in model_lower:
                    series_num = num
                    break

        if not series_num:
            return None

        # Find series containing this number
        best_match = None
        best_score = 0

        for series in series_list:
            series_name_lower = series['name'].lower()

            # Check if series number appears in series name
            # For "RTX 4060" → match "GeForce RTX 40 Series"
            if series_num in series_name_lower:
                # Prefer desktop over notebook if no "notebook" keyword in model
                is_notebook = 'notebook' in series_name_lower or 'laptop' in series_name_lower
                is_model_notebook = 'notebook' in model_lower or 'laptop' in model_lower

                # Calculate match score
                score = SequenceMatcher(None, model_lower, series_name_lower).ratio()

                # Bonus for matching notebook/desktop type
                if is_notebook == is_model_notebook:
                    score += 0.3

                if score > best_score:
                    best_score = score
                    best_match = series

        return best_match

    @staticmethod
    def _find_best_product_match(model: str, product_list: list) -> Optional[dict]:
        """Find best matching product in a series.

        Args:
            model: GPU model string (e.g., "RTX 4060")
            product_list: List of product dicts from API.

        Returns:
            Best matching product dict or None.
        """
        # Normalize model name for comparison
        # "RTX 4060" → "nvidia geforce rtx 4060"
        model_normalized = f"nvidia geforce {model}".lower().strip()

        best_match = None
        best_score = 0

        for product in product_list:
            product_name = product['name']
            product_name_lower = product_name.lower().strip()

            # Normalize product name (already has "NVIDIA GeForce" prefix from API)
            # e.g., "NVIDIA GeForce RTX 4060" from API

            # Calculate similarity score
            score = SequenceMatcher(None, model_normalized, product_name_lower).ratio()

            # Exact match gets huge bonus
            if model_normalized == product_name_lower:
                score += 1.0

            # Substring match gets bonus
            if model.lower() in product_name_lower or product_name_lower in model.lower():
                score += 0.4

            # Extract model number and compare (e.g., "4060" from "RTX 4060")
            model_num = ''.join(filter(str.isdigit, model))
            product_num = ''.join(filter(str.isdigit, product_name))

            # Exact number match is critical
            if model_num and product_num and model_num == product_num:
                score += 0.6

            if score > best_score:
                best_score = score
                best_match = product

        # Only return if we have a strong match (> 0.7)
        return best_match if best_score > 0.7 else None
