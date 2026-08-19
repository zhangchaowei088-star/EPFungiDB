import csv
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from database.models import BasicMetadataRecord


@dataclass(frozen=True)
class BasicTableSpec:
    name: str
    path: str
    key_columns: tuple[str, ...]


BASIC_TABLE_SPECS = [
    BasicTableSpec('sample_strain_map', 'curated/sample_strain_map.tsv', ('sample_id',)),
    BasicTableSpec('strain_entities', 'curated/strain_entities.tsv', ('strain_id',)),
    BasicTableSpec('strain_identifiers', 'curated/strain_identifiers.tsv', ('identifier_id',)),
    BasicTableSpec('strain_taxonomy_assertions', 'curated/strain_taxonomy_assertions.tsv', ('taxonomy_assertion_id',)),
    BasicTableSpec('strain_identity_evidence', 'curated/strain_identity_evidence.tsv', ('identity_evidence_id',)),
    BasicTableSpec('external_accessions', 'curated/external_accessions.tsv', ('external_accession_id',)),
    BasicTableSpec('source_registry', 'curated/source_registry.tsv', ('source_id',)),
    BasicTableSpec('strain_isolation_events', 'curated/strain_isolation_events.tsv', ('isolation_event_id',)),
    BasicTableSpec('strain_locations', 'curated/strain_locations.tsv', ('location_id',)),
    BasicTableSpec('strain_host_associations', 'curated/strain_host_associations.tsv', ('association_id',)),
    BasicTableSpec('taxon_ecology_profiles', 'curated/taxon_ecology_profiles.tsv', ('profile_id',)),
    BasicTableSpec('strain_literature_retrievals', 'curated/strain_literature_retrievals.tsv', ('literature_retrieval_id',)),
    BasicTableSpec('strain_literature_evidence', 'curated/strain_literature_evidence.tsv', ('literature_evidence_id',)),
    BasicTableSpec('strain_virulence_assays', 'curated/strain_virulence_assays.tsv', ('assay_id',)),
    BasicTableSpec('supplemental_assemblies', 'curated/supplemental_assemblies.tsv', ('supplemental_assembly_id',)),
    BasicTableSpec('assay_measurements', 'curated/assay_measurements.tsv', ('measurement_id',)),
    BasicTableSpec('strain_identity_summary', 'derived/strain_identity_summary.tsv', ('sample_id',)),
    BasicTableSpec('metadata_summary', 'derived/metadata_summary.tsv', ('sample_id',)),
    BasicTableSpec('release_manifest', 'derived/release_manifest.tsv', ('release_id', 'artifact_path')),
]


class Command(BaseCommand):
    help = 'Import 11_basic-data curated and derived metadata into generic JSON-backed records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--basic-dir',
            default=str(settings.BASIC_METADATA_DIR),
            help='Directory containing 11_basic-data metadata tables.',
        )
        parser.add_argument(
            '--tables',
            nargs='+',
            choices=[spec.name for spec in BASIC_TABLE_SPECS],
            help='Only import selected logical tables.',
        )
        parser.add_argument(
            '--truncate',
            action='store_true',
            help='Delete selected basic metadata records before importing.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Rows per bulk_create batch.',
        )

    def handle(self, *args, **options):
        basic_dir = Path(options['basic_dir']).resolve()
        if not basic_dir.exists():
            raise CommandError(f'Basic metadata directory not found: {basic_dir}')

        selected = set(options['tables'] or [spec.name for spec in BASIC_TABLE_SPECS])
        specs = [spec for spec in BASIC_TABLE_SPECS if spec.name in selected]

        if options['truncate']:
            deleted, _ = BasicMetadataRecord.objects.filter(table_name__in=selected).delete()
            self.stdout.write(f'truncated basic metadata records: {deleted:,}')

        total = 0
        for spec in specs:
            path = basic_dir / spec.path
            if not path.exists():
                raise CommandError(f'Missing metadata table for {spec.name}: {path}')
            imported = self.import_table(spec, path, options['batch_size'])
            total += imported
            self.stdout.write(self.style.SUCCESS(f'{spec.name}: imported {imported:,} rows'))

        self.stdout.write(self.style.SUCCESS(f'Done. Imported {total:,} basic metadata rows.'))

    @transaction.atomic
    def import_table(self, spec, path, batch_size):
        batch = []
        count = 0
        seen = set()
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            if not reader.fieldnames:
                return 0
            for row in reader:
                record_key = self.record_key(spec, row, count + 1)
                if record_key in seen:
                    record_key = f'{record_key}#{count + 1}'
                seen.add(record_key)
                batch.append(BasicMetadataRecord(
                    table_name=spec.name,
                    record_key=record_key,
                    sample_id=(row.get('sample_id') or '').strip(),
                    strain_id=(row.get('strain_id') or '').strip(),
                    source_id=(row.get('source_id') or '').strip(),
                    payload={key: value for key, value in row.items()},
                ))
                count += 1
                if len(batch) >= batch_size:
                    BasicMetadataRecord.objects.bulk_create(batch, batch_size=batch_size)
                    batch.clear()
        if batch:
            BasicMetadataRecord.objects.bulk_create(batch, batch_size=batch_size)
        return count

    def record_key(self, spec, row, index):
        values = [(row.get(column) or '').strip() for column in spec.key_columns]
        values = [value for value in values if value]
        if values:
            return '|'.join(values)
        return f'{spec.name}:{index}'
