#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Build a folder tree from a Preservica export CSV (preservica_path column).'
    )
    parser.add_argument(
        'input_csv',
        type=Path,
        help='Path to the full export CSV file',
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=None,
        help='Output tree file path (default: input stem + -folders-tree.txt in same directory)',
    )
    parser.add_argument(
        '-d', '--depth',
        type=int,
        default=None,
        metavar='N',
        help='Maximum depth (1 = root + top-level folders only, 2 = one more level, etc.; default: unlimited)',
    )
    parser.add_argument(
        '--show-ids',
        action='store_true',
        help='Append folder reference (assetId) after each folder name, e.g. AGM Papers [102b0c9c-3e6f-4e16-94d2-e2099646a7fd]',
    )
    parser.add_argument(
        '--include-assets',
        action='store_true',
        help='Include assets (EntityType.ASSET) in the tree; default is folders only (EntityType.FOLDER)',
    )
    args = parser.parse_args()

    inp = args.input_csv.resolve()
    if not inp.exists():
        parser.error(f'Input file not found: {inp}')
    out = args.output
    if out is None:
        out = inp.parent / f'{inp.stem}-folders-tree.txt'
    else:
        out = out.resolve()

    # Entity type column; only FOLDER by default, or FOLDER+ASSET with --include-assets
    ENTITY_TYPE_KEY = 'entity.entity_type'
    ALLOWED_TYPES = {'EntityType.FOLDER'}
    if args.include_assets:
        ALLOWED_TYPES.add('EntityType.ASSET')

    # Build trie from preservica_path; each node is {"_id": assetId or None, "children": {...}}
    root = {'_id': None, 'children': {}}

    with inp.open('r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entity_type = (row.get(ENTITY_TYPE_KEY) or '').strip()
            if entity_type not in ALLOWED_TYPES:
                continue
            p = (row.get('preservica_path') or '').strip().strip('/')
            if not p:
                continue
            asset_id = (row.get('assetId') or '').strip()
            parts = [x.strip() for x in p.split('/') if x.strip()]
            node = root
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                if part not in node['children']:
                    node['children'][part] = {'_id': asset_id if is_last else None, 'children': {}}
                else:
                    if is_last:
                        node['children'][part]['_id'] = asset_id
                node = node['children'][part]

    def walk(children, prefix='', depth=1):
        lines = []
        keys = sorted(children.keys(), key=str.casefold)
        for i, k in enumerate(keys):
            last = i == len(keys) - 1
            branch = '└── ' if last else '├── '
            node = children[k]
            label = k
            if args.show_ids and node.get('_id'):
                label = f"{k} [{node['_id']}]"
            lines.append(prefix + branch + label)
            if args.depth is None or depth < args.depth:
                child_prefix = prefix + ('    ' if last else '│   ')
                lines.extend(walk(node['children'], child_prefix, depth + 1))
        return lines

    lines = ['.'] + walk(root['children'])
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f"Wrote tree to: {out}")
    print(f"Total lines: {len(lines)}")


if __name__ == '__main__':
    main()
