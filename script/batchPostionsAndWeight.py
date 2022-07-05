#!/usr/bin/env python
# Script to batch create positions.json and weight.json files, and adjust the
# manifest.json file for already imported books that did not have the positions
# and weight pre-calculated during their import

import argparse
import json
import math
import os

from pathlib import Path


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s UPLOAD_FOLDER",
        description='Create positions and weight for imported books that lack same.'
    )
    parser.add_argument("folder", help="Root folder containing all of the uploaded books")
    return parser


def uploads_folder_loop(uploads, uploads_full_path) -> None:
    print(f"Using {uploads} as the root of the uploaded books")
    print(f"uploads_folder_loop({uploads_full_path})")
    manifests = list(uploads_full_path.glob('**/manifest.json'))
    for manifest in manifests:
        # Check for existing positions and weight.  If present, skip
        positions = manifest.joinpath(manifest.parent, 'positions.json')
        if positions.exists():
            print(f"{positions} already calculated, skipping...")
            continue
        else:
            print(f"NO POSITIONS: calc_position_and_weight({manifest})")
            with open(manifest, 'r', encoding='utf-8') as f:
                manifest_json = json.load(f)
                position_list, weight = make_positions_and_weight(manifest_json, manifest.parent)
                

def make_positions_and_weight(manifest: dict, manifest_folder: Path):
    """
    Calculate the positions within and weight of "chapters" in the
    `readingOrder` section of the `manifest`.  This relies on the EPUB having
    been unpacked, and located in an "EPUB" directory as a sub-folder of
    `manifest_folder`.  The files listed in the `manifest` are sought for their
    size.
    :param manifest: JSON (dict) created by Clusive's make_manifest().
    :return: a tuple of position_list and weight JSON objects.
    """
    POSITION_LENGTH = 1024
    start_position = 0
    total_content_length = 0
    positions = []
    weight = {}

    # Loop through the link structs in the manifest's `readingOrder`, adding
    # 1. a `contentLength` property to each,
    # 2. track the `total_content_length`,
    # 3. build up the `positions` array containing `locator` structs
    for link in manifest['readingOrder']:
        try:
            entry_file = manifest_folder.joinpath(link['href'])
            entry_length = entry_file.stat().st_size
            link['contentLength'] = entry_length
            total_content_length += entry_length
            position_count = max(1, math.ceil(entry_length / POSITION_LENGTH))

            # Load the `positions` array `positions_count` locator structs
            for position in range(position_count):
                locator = {
                    'href': link['href'],
                    'locations': {
                        'progression': position / position_count,
                        'position': start_position + (position + 1)
                    },
                    'type': link['type']
                }
                positions.append(locator)
            start_position += position_count
        except KeyError:
            logger.debug('No entry in %s for %s, ignoring', zip_file.filename, link['href'])

    # Loop through the reading order again, using the just calculated `positions`
    # to calculate the weight of each linked item
    total_content_percent = 100 / total_content_length
    for link in manifest['readingOrder']:
        content_length = link.get('contentLength')
        if content_length:
            weight[link['href']] = total_content_percent * content_length

    # Loop through the `positions` to update its locators with progress and
    # position info.
    num_positions = len(positions)
    for locator in positions:
        resources = [loc for loc in positions if loc['href'] == locator['href']]
        num_resources = len(resources)
        locations = locator['locations']
        progression = locations['progression']
        position = locations['position']
        position_index = math.ceil(progression * (num_resources - 1))
        locations.update({
            'totalProgression': (position - 1) / num_positions,
            'remainingPositions': abs(position_index - (num_resources - 1)),
            'totalRemainingPositions': abs(position - 1 - (num_positions - 1))
        })

    position_list = {
        'total': num_positions,
        'positions': positions
    }
    return position_list, weight


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    if not args.folder:
        print('No folder listed, nothing to do.')

    uploads = args.folder
    uploads_full_path = Path(os.path.abspath(uploads))
    if os.path.exists(uploads_full_path):
        uploads_folder_loop(uploads, uploads_full_path)
    else:
        print(f"No such folder: {uploads}")

if __name__ == "__main__":
    main()
