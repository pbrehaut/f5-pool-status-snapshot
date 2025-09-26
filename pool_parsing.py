#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import glob
import re
import sys


def parse_pool_file(file_path):
    """Parse a pool snapshot file and return a dictionary of pool data."""
    pools = {}

    with open(file_path, 'r') as infile:
        content = infile.read()
        # Split by record separator "\n}\n"
        records = content.split('\n}\n')

        for record in records:
            if 'ltm pool ' in record:
                pool_data = parse_pool_record(record)
                if pool_data:
                    pool_name = pool_data['name']
                    pools[pool_name] = pool_data

    return pools


def parse_pool_record(record):
    """Parse a single pool record and return a dictionary of its attributes."""
    # Extract pool name from the ltm pool line
    pool_match = re.search(r'ltm pool ([^ ]+)', record)
    if not pool_match:
        return None

    pool_name = pool_match.group(1)
    pool_data = {'name': pool_name}

    # Parse each line in the record
    lines = record.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('ltm pool') and not line == '{':
            # Split on first space to get key-value pairs
            parts = line.split(' ', 1)
            if len(parts) == 2:
                key = parts[0]
                value = parts[1]

                # Convert numeric values to appropriate types
                if value.isdigit():
                    value = int(value)
                elif re.match(r'^\d+\.\d+$', value):
                    value = float(value)

                pool_data[key] = value

    return pool_data


def parse_all_snapshot_files():
    """Parse all pool snapshot files and return a dictionary mapping filenames to pool data."""
    snapshot_files = glob.glob('pool_snapshot_*.txt')
    all_data = {}

    for file_path in snapshot_files:
        if os.path.isfile(file_path):
            print('Parsing {}...'.format(file_path))
            pools = parse_pool_file(file_path)
            all_data[file_path] = pools
            print('Found {} pools in {}'.format(len(pools), file_path))

    return all_data


def filter_pools_by_condition(pool_data, filter_key, filter_value):
    """Filter pools that have a specific key-value pair.

    Args:
        pool_data: Dictionary of pool data
        filter_key: Key to check for
        filter_value: Value that the key should have

    Returns:
        Dictionary containing only pools that match the condition
    """
    filtered_pools = {}

    for pool_name, pool_info in pool_data.items():
        if pool_info.get(filter_key) == filter_value:
            filtered_pools[pool_name] = pool_info

    return filtered_pools


def check_unchanged_values(data1, data2, filename1, filename2, filter_key=None, filter_value=None, keys_to_check=None):
    """Check for unchanged values between two pool datasets, with optional filtering.

    Args:
        data1: First pool data dictionary
        data2: Second pool data dictionary
        filename1: Name of first file
        filename2: Name of second file
        filter_key: Key to filter pools by (optional)
        filter_value: Value to filter pools by (optional)
        keys_to_check: List of specific keys to compare. If None, compares all keys.

    Returns:
        Dictionary of pools with unchanged values
    """
    # Apply filtering if specified
    if filter_key is not None and filter_value is not None:
        print('Filtering pools where {} = {}'.format(filter_key, filter_value))
        data1_filtered = filter_pools_by_condition(data1, filter_key, filter_value)
        data2_filtered = filter_pools_by_condition(data2, filter_key, filter_value)
        print('Found {} pools in {} and {} pools in {} matching the filter'.format(
            len(data1_filtered), os.path.basename(filename1),
            len(data2_filtered), os.path.basename(filename2)))
    else:
        data1_filtered = data1
        data2_filtered = data2

    unchanged_values = {}

    # Get pools that exist in both filtered datasets
    common_pools = set(data1_filtered.keys()) & set(data2_filtered.keys())

    for pool_name in common_pools:
        pool1_data = data1_filtered[pool_name]
        pool2_data = data2_filtered[pool_name]

        # Determine which keys to check
        if keys_to_check is None:
            # Get all unique keys from both pool records
            keys_to_compare = set(pool1_data.keys()) | set(pool2_data.keys())
        else:
            # Only check specified keys
            keys_to_compare = set(keys_to_check)

        unchanged_attrs = {}

        for key in keys_to_compare:
            value1 = pool1_data.get(key, '<missing>')
            value2 = pool2_data.get(key, '<missing>')

            # Check if values are the same and both exist
            if value1 == value2 and value1 != '<missing>':
                unchanged_attrs[key] = value1

        if unchanged_attrs:
            unchanged_values[pool_name] = unchanged_attrs

    return unchanged_values


def compare_pool_data(data1, data2, filename1, filename2, keys_to_check=None):
    """Compare two pool data dictionaries and return differences.

    Args:
        data1: First pool data dictionary
        data2: Second pool data dictionary
        filename1: Name of first file
        filename2: Name of second file
        keys_to_check: List of specific keys to compare. If None, compares all keys.
    """
    differences = {}

    # Get all unique pool names from both datasets
    all_pools = set(data1.keys()) | set(data2.keys())

    for pool_name in all_pools:
        pool_diffs = {}

        # Check if pool exists in both files
        if pool_name not in data1:
            pool_diffs['pool_status'] = 'Missing in {}'.format(filename1)
        elif pool_name not in data2:
            pool_diffs['pool_status'] = 'Missing in {}'.format(filename2)
        else:
            # Compare attributes for this pool
            pool1_data = data1[pool_name]
            pool2_data = data2[pool_name]

            # Determine which keys to check
            if keys_to_check is None:
                # Get all unique keys from both pool records
                keys_to_compare = set(pool1_data.keys()) | set(pool2_data.keys())
            else:
                # Only check specified keys
                keys_to_compare = set(keys_to_check)

            for key in keys_to_compare:
                value1 = pool1_data.get(key, '<missing>')
                value2 = pool2_data.get(key, '<missing>')

                if value1 != value2:
                    pool_diffs[key] = {
                        filename1: value1,
                        filename2: value2
                    }

        if pool_diffs:
            differences[pool_name] = pool_diffs

    return differences


def select_files_for_comparison(all_pool_data):
    """Allow user to select two files for comparison."""
    filenames = list(all_pool_data.keys())

    if len(filenames) < 2:
        print('Need at least 2 files to compare')
        return None, None

    print('\nAvailable files:')
    for i, filename in enumerate(filenames):
        print('{}. {}'.format(i + 1, os.path.basename(filename)))

    print()

    try:
        if sys.version_info[0] >= 3:
            choice1 = input('Select first file (1-{}): '.format(len(filenames)))
            choice2 = input('Select second file (1-{}): '.format(len(filenames)))
        else:
            choice1 = raw_input('Select first file (1-{}): '.format(len(filenames)))
            choice2 = raw_input('Select second file (1-{}): '.format(len(filenames)))

        choice1 = int(choice1) - 1
        choice2 = int(choice2) - 1

        if 0 <= choice1 < len(filenames) and 0 <= choice2 < len(filenames):
            return filenames[choice1], filenames[choice2]
        else:
            print('Invalid selection')
            return None, None

    except (ValueError, KeyboardInterrupt):
        print('Invalid input')
        return None, None


def display_differences(differences, filename1, filename2):
    """Display the differences in a readable format."""
    if not differences:
        print('No differences found between {} and {}'.format(
            os.path.basename(filename1), os.path.basename(filename2)))
        return

    print('\nDifferences between {} and {}:'.format(
        os.path.basename(filename1), os.path.basename(filename2)))
    print('=' * 60)

    for pool_name, pool_diffs in differences.items():
        print('\nPool: {}'.format(pool_name))
        print('-' * (len(pool_name) + 6))

        for key, value_info in pool_diffs.items():
            if key == 'pool_status':
                print('  {}'.format(value_info))
            else:
                print('  {}: {} -> {}'.format(
                    key,
                    value_info.get(filename1, '<missing>'),
                    value_info.get(filename2, '<missing>')
                ))


def display_unchanged_values(unchanged_values, filename1, filename2):
    """Display the unchanged values in a readable format."""
    if not unchanged_values:
        print('No unchanged values found between {} and {}'.format(
            os.path.basename(filename1), os.path.basename(filename2)))
        return

    print('\nUnchanged values between {} and {}:'.format(
        os.path.basename(filename1), os.path.basename(filename2)))
    print('=' * 60)

    for pool_name, unchanged_attrs in unchanged_values.items():
        print('\nPool: {}'.format(pool_name))
        print('-' * (len(pool_name) + 6))

        for key, value in unchanged_attrs.items():
            print('  {}: {}'.format(key, value))


def main():
    import sys

    # Parse all snapshot files
    all_pool_data = parse_all_snapshot_files()

    if not all_pool_data:
        print('No snapshot files found')
        return

    # Select two files for comparison
    file1, file2 = select_files_for_comparison(all_pool_data)
    if not file1 or not file2:
        return

    # Optional: specify which keys to check for differences
    # Example usage with specific keys:
    # keys_to_check = ['status.availability-state', 'serverside.tot-conns']

    # For now, check all keys (default behaviour)
    keys_to_check_changed = ['status.availability-state']
    keys_to_check_changed = None
    keys_to_check_unchanged = ['serverside.tot-conns']

    # Compare the selected files
    differences = compare_pool_data(
        all_pool_data[file1],
        all_pool_data[file2],
        file1,
        file2,
        keys_to_check_changed
    )

    # Display the results
    display_differences(differences, file1, file2)

    # Example: Check for unchanged values where status.availability-state is 'available'
    print('\n' + '=' * 60)
    unchanged = check_unchanged_values(
        all_pool_data[file1],
        all_pool_data[file2],
        file1,
        file2,
        filter_key='status.availability-state',
        filter_value='offline',
        keys_to_check=keys_to_check_unchanged
    )

    display_unchanged_values(unchanged, file1, file2)

    return all_pool_data


if __name__ == '__main__':
    main()