import requests
import zipfile
import io
import os

# Downloads USDA RMA crop insurance loss data (1989-2025) and extracts zip archives locally.
BASE_URL = 'https://www.rma.usda.gov/sites/default/files/'
FOLDERS = ['information-tools/', '2024-09/']
OUTPUT_DIR = 'crop_loss_data'
START_YEAR = 1989
END_YEAR = 2025

FILE_TYPES = {
    'type_practice_usage': 'sobtpu_',
    'state_county_crop': 'sobcov_',
    'cost_of_loss': 'colsom_',
}


def download_zip(url, timeout=60, retries=2):
    """Return a ZipFile for a valid zip response, or None."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            content = response.content
            if content[:2] != b'PK':
                return None
            return zipfile.ZipFile(io.BytesIO(content))
        except requests.RequestException:
            if attempt + 1 == retries:
                return None
    return None


os.makedirs(OUTPUT_DIR, exist_ok=True)

for name_of_data, file_prefix in FILE_TYPES.items():
    output_directory_year = os.path.join(OUTPUT_DIR, name_of_data)
    os.makedirs(output_directory_year, exist_ok=True)

    for year_use in range(START_YEAR, END_YEAR + 1):
        print(f'Reading {name_of_data} from year {year_use}')

        z = None
        for folder in FOLDERS:
            url = f'{BASE_URL}{folder}{file_prefix}{year_use}.zip'
            z = download_zip(url)
            if z is not None:
                break

        if z is None:
            # Some data types don't start until 1999; missing years print 'Read Fail'.
            print(f'Read Fail {name_of_data} {year_use}')
            continue

        try:
            z.extractall(output_directory_year)
        finally:
            z.close()
