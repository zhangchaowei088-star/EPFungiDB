import csv
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models as django_models

from database import models


@dataclass(frozen=True)
class TableSpec:
    name: str
    filename: str
    model: type[django_models.Model]
    large: bool = False


TABLE_SPECS = [
    TableSpec('samples', 'master_sample_index.tsv', models.Sample),
    TableSpec('annotation_sources', 'annotation_sources.tsv', models.AnnotationSource),
    TableSpec('analysis_status', 'analysis_status_matrix.tsv', models.AnalysisStatus),
    TableSpec('genome_metrics', 'genome_summary.tsv', models.GenomeMetric),
    TableSpec('general_functional_annotation_summary', 'general_functional_annotation_summary.tsv', models.GeneralFunctionalAnnotationSummary),
    TableSpec('pathogenicity_associated_summary', 'pathogenicity_associated_summary.tsv', models.PathogenicityAssociatedSummary),
    TableSpec('busco_summary', 'busco_summary.tsv', models.BuscoSummary),
    TableSpec('antismash_genome_summary', 'antismash_genome_summary.tsv', models.AntismashGenomeSummary),
    TableSpec('signalp_summary', 'signalp_summary.tsv', models.SignalpSummary),
    TableSpec('sample_files', 'sample_file_paths.tsv', models.SampleFile),
    TableSpec('proteins', 'proteins.tsv', models.Protein, large=True),
    TableSpec('protein_general_annotation_summary', 'protein_general_annotation_summary.tsv', models.ProteinGeneralAnnotation, large=True),
    TableSpec('protein_pathogenicity_summary', 'protein_pathogenicity_summary.tsv', models.ProteinPathogenicitySummary, large=True),
    TableSpec('kegg_pathway_members', 'kegg_pathway_members.tsv', models.KeggPathwayMember, large=True),
    TableSpec('protein_pathogenicity_features', 'protein_pathogenicity_features.tsv', models.ProteinPathogenicityFeature, large=True),
]

COLUMN_ALIASES = {
    'antismash_genome_summary': {
        'antiSMASH_version': 'antismash_version',
        'Contig_edge_BGCs': 'contig_edge_bgcs',
        'No_biosynthetic_CDS_BGCs': 'no_biosynthetic_cds_bgcs',
        'CDS_zero_BGCs': 'cds_zero_bgcs',
    },
}

TRUNCATE_ORDER = [
    models.ProteinPathogenicityFeature,
    models.KeggPathwayMember,
    models.ProteinPathogenicitySummary,
    models.ProteinGeneralAnnotation,
    models.Protein,
    models.SampleFile,
    models.SignalpSummary,
    models.AntismashGenomeSummary,
    models.BuscoSummary,
    models.PathogenicityAssociatedSummary,
    models.GeneralFunctionalAnnotationSummary,
    models.GenomeMetric,
    models.AnalysisStatus,
    models.AnnotationSource,
    models.Sample,
]

NULL_NUMERIC = {'', 'NA', 'N/A', 'na', 'nan', 'NaN', 'None', 'none', 'null', 'NULL', '-'}
TRUE_VALUES = {'1', 'true', 'True', 'TRUE', 'yes', 'Yes', 'Y', 'y', 'T', 't'}
FALSE_VALUES = {'0', 'false', 'False', 'FALSE', 'no', 'No', 'N', 'n', 'F', 'f', ''}


class Command(BaseCommand):
    help = 'Import ready-for-database TSV tables into the Django database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--table-dir',
            default=str(settings.READY_TABLE_DIR),
            help='Directory containing tables/*.tsv files.',
        )
        parser.add_argument(
            '--tables',
            nargs='+',
            choices=[spec.name for spec in TABLE_SPECS],
            help='Only import the selected logical table names.',
        )
        parser.add_argument(
            '--skip-large',
            action='store_true',
            help='Skip protein-level million-row tables for quick development imports.',
        )
        parser.add_argument(
            '--truncate',
            action='store_true',
            help='Delete selected destination rows before importing.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5000,
            help='Rows per bulk_create batch.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Import only the first N rows from each selected table.',
        )

    def handle(self, *args, **options):
        table_dir = Path(options['table_dir']).resolve()
        if not table_dir.exists():
            raise CommandError(f'Table directory not found: {table_dir}')

        selected = set(options['tables'] or [spec.name for spec in TABLE_SPECS])
        specs = [spec for spec in TABLE_SPECS if spec.name in selected]
        if options['skip_large']:
            specs = [spec for spec in specs if not spec.large]

        if options['truncate']:
            self.truncate_selected(specs)

        total = 0
        for spec in specs:
            path = table_dir / spec.filename
            if not path.exists():
                raise CommandError(f'Missing table for {spec.name}: {path}')
            imported = self.import_table(spec, path, options['batch_size'], options.get('limit'))
            total += imported
            self.stdout.write(self.style.SUCCESS(f'{spec.name}: imported {imported:,} rows'))

        self.stdout.write(self.style.SUCCESS(f'Done. Imported {total:,} rows.'))

    def truncate_selected(self, specs):
        selected_models = {spec.model for spec in specs}
        for model in TRUNCATE_ORDER:
            if model in selected_models:
                deleted, _ = model.objects.all().delete()
                self.stdout.write(f'truncated {model._meta.db_table}: {deleted:,} rows')

    def import_table(self, spec, path, batch_size, limit):
        field_map = self.build_field_map(spec.model)
        fields_by_attname = {field.attname: field for field in spec.model._meta.concrete_fields}
        batch = []
        count = 0

        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            if not reader.fieldnames:
                return 0
            aliases = COLUMN_ALIASES.get(spec.name, {})
            column_map = {}
            for column in reader.fieldnames:
                lookup = self.normalize(aliases.get(column, column))
                if lookup in field_map:
                    column_map[column] = field_map[lookup]
            unmapped = [column for column in reader.fieldnames if column not in column_map]
            if unmapped:
                self.stdout.write(f'{spec.name}: ignored columns: {", ".join(unmapped)}')

            for row in reader:
                kwargs = {}
                for source_column, attname in column_map.items():
                    field = fields_by_attname[attname]
                    kwargs[attname] = self.convert(row.get(source_column, ''), field)
                batch.append(spec.model(**kwargs))
                count += 1
                if len(batch) >= batch_size:
                    spec.model.objects.bulk_create(batch, batch_size=batch_size)
                    batch.clear()
                if limit and count >= limit:
                    break

        if batch:
            spec.model.objects.bulk_create(batch, batch_size=batch_size)
        return count

    def build_field_map(self, model):
        mapping = {}
        for field in model._meta.concrete_fields:
            for name in {field.name, field.attname, field.db_column or ''}:
                if name:
                    mapping[self.normalize(name)] = field.attname
        return mapping

    def normalize(self, value):
        value = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', value)
        value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value)
        return value.strip().lower()

    def convert(self, value, field):
        if isinstance(field, django_models.BooleanField):
            if value in TRUE_VALUES:
                return True
            if value in FALSE_VALUES:
                return False
            return False

        if isinstance(field, (django_models.IntegerField, django_models.BigIntegerField)):
            if value in NULL_NUMERIC:
                return None
            return int(float(value))

        if isinstance(field, django_models.FloatField):
            if value in NULL_NUMERIC:
                return None
            return float(value)

        return value or ''
