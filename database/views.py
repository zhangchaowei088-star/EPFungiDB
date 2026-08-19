import csv
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Count, Max, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.shortcuts import render
from rest_framework import decorators, response, viewsets

from . import models, serializers


KEGG_PATHWAY_DIR = settings.PROJECT_ROOT / '02_annotation-protein-data' / '07_ko_pathway'
BIGSCAPE_DIR = settings.PROJECT_ROOT / '04_antismash-bigscape'


@lru_cache(maxsize=1)
def get_kegg_pathway_names():
    path = KEGG_PATHWAY_DIR / 'annotated_map_pathway_names.csv'
    names = {}
    if not path.exists():
        return names
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            names[row.get('pathway_id', '')] = {
                'pathway_id': row.get('pathway_id', ''),
                'pathway_name': row.get('pathway_name', ''),
                'n_samples': int(row.get('n_samples') or 0),
                'total_protein_ko_hits': int(row.get('total_protein_ko_hits') or 0),
            }
    return names


@lru_cache(maxsize=1)
def get_sample_pathway_counts():
    path = KEGG_PATHWAY_DIR / 'sample_pathway_counts.csv'
    by_sample = {}
    if not path.exists():
        return by_sample
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            sample = row.get('sample', '')
            if not sample:
                continue
            by_sample.setdefault(sample, []).append({
                'pathway_id': row.get('pathway_id', ''),
                'pathway_name': row.get('pathway_name', ''),
                'n_protein_ko_hits': int(row.get('n_protein_ko_hits') or 0),
            })
    for rows in by_sample.values():
        rows.sort(key=lambda item: (-item['n_protein_ko_hits'], item['pathway_id']))
    return by_sample


def kegg_pathway_name(pathway_id):
    if not pathway_id:
        return ''
    if pathway_id.startswith('ko') and len(pathway_id) > 2:
        pathway_id = f'map{pathway_id[2:]}'
    return get_kegg_pathway_names().get(pathway_id, {}).get('pathway_name', '')


def parse_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def parse_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


@lru_cache(maxsize=1)
def get_bigscape_overview():
    comparison_dir = BIGSCAPE_DIR / '12_bigscape_cutoff_comparison_c030_c050'
    core_dir = BIGSCAPE_DIR / '18_full_dataset_core_bgc_c030'
    knowncluster_dir = BIGSCAPE_DIR / '21_mibig_knowncluster_annotation'
    priority_dir = BIGSCAPE_DIR / '22_priority_gcf_novelty_analysis_20260716'

    overview = {
        'global': [],
        'class_summary': [],
        'top_gcf': [],
        'knowncluster': {},
        'priority_gcf_count': None,
        'source_paths': {
            'global': '04_antismash-bigscape/12_bigscape_cutoff_comparison_c030_c050/global_summary.tsv',
            'class_summary': '04_antismash-bigscape/12_bigscape_cutoff_comparison_c030_c050/class_summary_c0.30.tsv',
            'top_gcf': '04_antismash-bigscape/18_full_dataset_core_bgc_c030/full_gcf_presence_rank_c030.tsv',
        },
    }

    global_path = comparison_dir / 'global_summary.tsv'
    if global_path.exists():
        with global_path.open(newline='', encoding='utf-8') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                overview['global'].append({
                    'cutoff': row.get('cutoff', ''),
                    'assigned_bgc': parse_int(row.get('assigned_bgc')),
                    'gcf_count': parse_int(row.get('gcf_count')),
                    'genome_count': parse_int(row.get('genome_count')),
                    'family_count': parse_int(row.get('family_count')),
                    'genus_count': parse_int(row.get('genus_count')),
                    'species_count': parse_int(row.get('species_count')),
                    'singleton_gcf_count': parse_int(row.get('singleton_gcf_count')),
                })

    class_path = comparison_dir / 'class_summary_c0.30.tsv'
    if class_path.exists():
        with class_path.open(newline='', encoding='utf-8') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                overview['class_summary'].append({
                    'class_name': row.get('BiGSCAPE_Class', ''),
                    'gcf_count': parse_int(row.get('GCF_count')),
                    'bgc_count': parse_int(row.get('BGC_count')),
                    'genome_count_sum': parse_int(row.get('Genome_count_sum')),
                    'singleton_gcf_count': parse_int(row.get('singleton_GCF_count')),
                })
        overview['class_summary'].sort(key=lambda item: (-item['bgc_count'], item['class_name']))

    top_gcf_path = core_dir / 'full_gcf_presence_rank_c030.tsv'
    if top_gcf_path.exists():
        with top_gcf_path.open(newline='', encoding='utf-8') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                overview['top_gcf'].append({
                    'gcf_id': row.get('GCF_ID', ''),
                    'class_name': row.get('BiGSCAPE_Class', ''),
                    'bgc_count': parse_int(row.get('BGC_count')),
                    'genome_count': parse_int(row.get('Genome_count')),
                    'presence_frequency': parse_float(row.get('Presence_frequency')),
                    'family_count': parse_int(row.get('Family_count')),
                    'genus_count': parse_int(row.get('Genus_count')),
                    'species_count': parse_int(row.get('Species_count')),
                    'families': row.get('Families', ''),
                    'genera': row.get('Genera', ''),
                    'top_products': row.get('Top_products', ''),
                    'representative_bgc': row.get('Representative_BGC', ''),
                    'representative_path': row.get('Representative_path', ''),
                })
                if len(overview['top_gcf']) >= 8:
                    break

    knowncluster_path = knowncluster_dir / 'knowncluster_global_summary.tsv'
    if knowncluster_path.exists():
        with knowncluster_path.open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle, delimiter='\t'))
            if rows:
                overview['knowncluster'] = rows[0]

    priority_path = priority_dir / 'priority_gcf_summary.tsv'
    if priority_path.exists():
        with priority_path.open(newline='', encoding='utf-8') as handle:
            overview['priority_gcf_count'] = max(sum(1 for _ in handle) - 1, 0)

    return overview


def dashboard(request):
    return render(request, 'database/dashboard.html')


def genomes(request):
    return render(request, 'database/genomes.html')


def genome_detail(request, sample_id):
    return render(request, 'database/genome_detail.html', {'sample_id': sample_id})


def antismash_report(request, sample_id, asset_path='index.html'):
    try:
        sample = models.Sample.objects.select_related('antismash_summary').get(sample_id=sample_id)
    except models.Sample.DoesNotExist as exc:
        raise Http404('Sample not found') from exc
    antismash = getattr(sample, 'antismash_summary', None)
    if not antismash or not antismash.antismash_dir:
        raise Http404('antiSMASH report not found')

    antismash_dir = (settings.PROJECT_ROOT / antismash.antismash_dir).resolve()
    requested = (antismash_dir / asset_path).resolve()
    try:
        requested.relative_to(antismash_dir)
    except ValueError as exc:
        raise Http404('Invalid antiSMASH asset path') from exc
    if not requested.exists() or not requested.is_file():
        raise Http404('antiSMASH asset not found')
    return FileResponse(requested.open('rb'))


def species(request):
    return render(request, 'database/species.html')


def genes(request):
    return render(request, 'database/genes.html')


def kegg(request):
    return render(request, 'database/kegg.html')


def gene_families(request):
    return render(request, 'database/gene_families.html')


def bioassays(request):
    return render(request, 'database/bioassays.html')


def literature(request):
    return render(request, 'database/literature.html')


def gene_detail(request, protein_uid):
    return render(request, 'database/gene_detail.html', {'protein_uid': protein_uid})


class SummaryViewSet(viewsets.ViewSet):
    def list(self, request):
        sample_qs = models.Sample.objects.all()
        summary = sample_qs.aggregate(
            sample_count=Count('sample_id'),
            genus_count=Count('genus', distinct=True, filter=Q(genus__gt='')),
            species_count=Count('species', distinct=True, filter=Q(species__gt='')),
            family_count=Count('family', distinct=True, filter=Q(family__gt='')),
            order_group_count=Count('order_group', distinct=True, filter=Q(order_group__gt='')),
            total_genes=Sum('gene_count'),
            total_proteins=Sum('protein_count'),
            avg_busco_complete_pct=Avg('busco_complete_pct'),
            max_bgc_count=Max('bgc_count'),
            ready_basic_db=Count('sample_id', filter=Q(ready_basic_db=True)),
            ready_full_analysis=Count('sample_id', filter=Q(ready_full_analysis=True)),
        )
        summary['order_groups'] = list(
            sample_qs.values('order_group')
            .annotate(sample_count=Count('sample_id'))
            .order_by('order_group')
        )
        summary['families'] = list(
            sample_qs.values('family')
            .annotate(sample_count=Count('sample_id'))
            .order_by('-sample_count', 'family')[:20]
        )
        summary['annotation_sources'] = list(
            models.AnnotationSource.objects.values('category')
            .annotate(source_count=Count('source_key'))
            .order_by('category')
        )
        return response.Response(summary)


class KeggPathwayIndexViewSet(viewsets.ViewSet):
    def list(self, request):
        sample_id = request.query_params.get('sample_id', '').strip()
        query = request.query_params.get('q', '').strip().lower()
        if sample_id:
            sample = models.Sample.objects.filter(sample_id=sample_id).first()
            sample_key = sample.full_name if sample else sample_id
            rows = get_sample_pathway_counts().get(sample_key, [])
            records = [
                {
                    **row,
                    'sample_id': sample_id,
                    'kegg_url': f'https://www.kegg.jp/pathway/{row["pathway_id"]}',
                }
                for row in rows
            ]
        else:
            records = [
                {
                    **row,
                    'n_protein_ko_hits': row.get('total_protein_ko_hits', 0),
                    'kegg_url': f'https://www.kegg.jp/pathway/{pathway_id}',
                }
                for pathway_id, row in get_kegg_pathway_names().items()
            ]
        if query:
            records = [
                row for row in records
                if query in row.get('pathway_id', '').lower()
                or query in row.get('pathway_name', '').lower()
            ]
        records.sort(key=lambda item: (-int(item.get('n_protein_ko_hits') or item.get('total_protein_ko_hits') or 0), item.get('pathway_id', '')))
        return response.Response({
            'count': len(records),
            'results': records[:500],
            'source': '02_annotation-protein-data/07_ko_pathway',
        })


class PathogenicityOverviewViewSet(viewsets.ViewSet):
    def list(self, request):
        summary = models.PathogenicityAssociatedSummary.objects.aggregate(
            sample_count=Count('sample_id'),
            complete_count=Count('sample_id', filter=Q(complete_pathogenicity_associated_features=True)),
            signalp_sample_count=Count('sample_id', filter=Q(has_signalp=True)),
            effectorp_sample_count=Count('sample_id', filter=Q(has_effectorp=True)),
            cazyme_sample_count=Count('sample_id', filter=Q(has_cazyme=True)),
            merops_sample_count=Count('sample_id', filter=Q(has_merops=True)),
            antismash_sample_count=Count('sample_id', filter=Q(has_antismash=True)),
            signalp_total_proteins=Sum('signalp_total_proteins'),
            signalp_sp_total=Sum('signalp_sp_count'),
            signalp_high_confidence_sp_total=Sum('signalp_high_confidence_sp_count'),
            effector_candidate_total=Sum('effector_candidate_count'),
            cytoplasmic_effector_total=Sum('cytoplasmic_effector_count'),
            apoplastic_effector_total=Sum('apoplastic_effector_count'),
            dual_localization_effector_total=Sum('dual_localization_effector_count'),
            cazyme_hit_total=Sum('cazyme_hit_count'),
            cazyme_protein_total=Sum('cazyme_protein_count'),
            merops_hit_total=Sum('merops_hit_count'),
            merops_protein_total=Sum('merops_protein_count'),
            bgc_total=Sum('bgc_count'),
        )
        summary = {key: (value or 0) for key, value in summary.items()}
        feature_distribution = list(
            models.ProteinPathogenicityFeature.objects.values('feature_type', 'source_key')
            .annotate(record_count=Count('id'), protein_count=Count('protein_id', distinct=True))
            .order_by('feature_type', 'source_key')
        )
        source_notes = list(
            models.AnnotationSource.objects
            .filter(category='pathogenicity_associated_annotation')
            .values('source_key', 'display_name', 'sub_category', 'evidence_type', 'evidence_strength', 'result_level', 'interpretation_note')
            .order_by('source_key')
        )
        bigscape = get_bigscape_overview()
        c030 = next((row for row in bigscape['global'] if row.get('cutoff') == 'c0.30'), None) or {}

        modules = [
            {
                'key': 'secretome',
                'title': 'Secretome signal',
                'source': 'SignalP6',
                'level': 'protein',
                'primary_count': summary['signalp_sp_total'],
                'secondary_count': summary['signalp_high_confidence_sp_total'],
                'secondary_label': 'high-confidence SP proteins',
                'sample_count': summary['signalp_sample_count'],
                'interpretation': 'Secreted proteins define the searchable entry point for host-interface candidates.',
            },
            {
                'key': 'effectors',
                'title': 'Effector candidates',
                'source': 'EffectorP',
                'level': 'protein',
                'primary_count': summary['effector_candidate_total'],
                'secondary_count': summary['cytoplasmic_effector_total'] + summary['apoplastic_effector_total'] + summary['dual_localization_effector_total'],
                'secondary_label': 'localized effector calls',
                'sample_count': summary['effectorp_sample_count'],
                'interpretation': 'Predicted effectors are candidate host-modulating proteins for follow-up screening.',
            },
            {
                'key': 'cazymes',
                'title': 'CAZyme repertoire',
                'source': 'run_dbCAN',
                'level': 'protein',
                'primary_count': summary['cazyme_protein_total'],
                'secondary_count': summary['cazyme_hit_total'],
                'secondary_label': 'domain hits',
                'sample_count': summary['cazyme_sample_count'],
                'interpretation': 'CAZyme calls capture enzymes tied to cuticle, cell-wall, and nutrient substrate processing.',
            },
            {
                'key': 'proteases',
                'title': 'Protease repertoire',
                'source': 'MEROPS',
                'level': 'protein',
                'primary_count': summary['merops_protein_total'],
                'secondary_count': summary['merops_hit_total'],
                'secondary_label': 'MEROPS hits',
                'sample_count': summary['merops_sample_count'],
                'interpretation': 'Protease annotations support invasion and host tissue degradation hypotheses.',
            },
            {
                'key': 'bgc',
                'title': 'Secondary metabolite BGCs',
                'source': 'antiSMASH',
                'level': 'genome region',
                'primary_count': summary['bgc_total'],
                'secondary_count': summary['antismash_sample_count'],
                'secondary_label': 'genomes with antiSMASH',
                'sample_count': summary['antismash_sample_count'],
                'interpretation': 'BGC regions summarize secondary metabolite potential per genome.',
            },
            {
                'key': 'gcf',
                'title': 'BGC families',
                'source': 'BiG-SCAPE',
                'level': 'GCF',
                'primary_count': c030.get('gcf_count', 0),
                'secondary_count': c030.get('assigned_bgc', 0),
                'secondary_label': 'assigned BGCs at c0.30',
                'sample_count': c030.get('genome_count', 0),
                'interpretation': 'GCFs connect antiSMASH regions across genomes for conserved and lineage-skewed metabolite families.',
            },
        ]

        return response.Response({
            'summary': summary,
            'modules': modules,
            'feature_distribution': feature_distribution,
            'annotation_sources': source_notes,
            'bigscape': bigscape,
            'protein_feature_records_loaded': models.ProteinPathogenicityFeature.objects.count(),
            'candidate_scope_note': 'Computational annotations are candidate pathogenicity-associated evidence. They should be interpreted with genomic context and experimental validation.',
        })


class SampleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Sample.objects.all()
    lookup_field = 'sample_id'
    filterset_fields = {
        'order_group': ['exact'],
        'family': ['exact', 'icontains'],
        'genus': ['exact', 'icontains'],
        'species': ['exact', 'icontains'],
        'ready_basic_db': ['exact'],
        'ready_full_analysis': ['exact'],
        'has_busco': ['exact'],
        'has_antismash': ['exact'],
        'has_signalp': ['exact'],
    }
    search_fields = ['sample_id', 'full_name', 'family', 'genus', 'species', 'strain_from_name']
    ordering_fields = [
        'sample_id',
        'genome_size',
        'gc_content',
        'n50',
        'gene_count',
        'protein_count',
        'busco_complete_pct',
        'bgc_count',
        'signalp_sp_count',
        'effector_candidate_count',
    ]
    ordering = ['order_group', 'genus', 'sample_id']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.SampleDetailSerializer
        return serializers.SampleListSerializer

    def retrieve(self, request, *args, **kwargs):
        accept = request.headers.get('Accept', '')
        wants_json = 'application/json' in accept or request.query_params.get('format') == 'json'
        if not wants_json:
            sample_id = kwargs.get(self.lookup_field)
            return redirect('genome_detail', sample_id=sample_id)
        return super().retrieve(request, *args, **kwargs)

    @decorators.action(detail=True, methods=['get'])
    def proteins(self, request, sample_id=None):
        queryset = self.get_object().proteins.all().order_by('seqid', 'start', 'protein_id')
        page = self.paginate_queryset(queryset)
        serializer = serializers.ProteinSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @decorators.action(detail=True, methods=['get'], url_path='kegg-pathways')
    def kegg_pathways(self, request, sample_id=None):
        sample = self.get_object()
        rows = get_sample_pathway_counts().get(sample.full_name, [])
        if rows:
            return response.Response(rows)
        queryset = (
            sample.kegg_pathway_members.values('kegg_pathway_id')
            .annotate(protein_count=Count('protein_id'))
            .order_by('kegg_pathway_id')
        )
        return response.Response([
            {
                'pathway_id': row['kegg_pathway_id'],
                'pathway_name': kegg_pathway_name(row['kegg_pathway_id']),
                'n_protein_ko_hits': row['protein_count'],
            }
            for row in queryset
        ])

    @decorators.action(detail=True, methods=['get'], url_path='antismash-regions')
    def antismash_regions(self, request, sample_id=None):
        sample = self.get_object()
        antismash = getattr(sample, 'antismash_summary', None)
        json_path = sample.antismash_json_path or getattr(antismash, 'antismash_dir', '')
        if json_path and not json_path.endswith('.json'):
            json_path = f'{json_path.rstrip("/")}/{sample.full_name}.json'

        resolved_json = self.resolve_project_path(json_path)
        if not resolved_json or not resolved_json.exists():
            return response.Response({
                'sample_id': sample.sample_id,
                'json_present': False,
                'regions': [],
                'product_counts': [],
                'error': 'antiSMASH JSON was not found for this sample.',
            }, status=404)

        with resolved_json.open(encoding='utf-8') as handle:
            data = json.load(handle)

        regions = []
        product_counter = Counter()
        region_sizes = []
        edge_count = 0
        protocluster_count = 0
        candidate_count = 0

        for record in data.get('records', []):
            seqid = record.get('id') or record.get('name') or ''
            seq_len = len(record.get('seq', {}).get('data', '')) or None
            for index, area in enumerate(record.get('areas') or [], start=1):
                start = int(area.get('start') or 0)
                end = int(area.get('end') or 0)
                size = max(0, end - start)
                products = area.get('products') or []
                protoclusters = area.get('protoclusters') or {}
                candidates = area.get('candidates') or []
                is_contig_edge = start <= 0 or bool(seq_len and end >= seq_len)

                product_counter.update(products)
                region_sizes.append(size)
                edge_count += 1 if is_contig_edge else 0
                protocluster_count += len(protoclusters)
                candidate_count += len(candidates)

                regions.append({
                    'region_id': f'{seqid}.region{index:03d}',
                    'seqid': seqid,
                    'start': start + 1,
                    'end': end,
                    'size_bp': size,
                    'size_kb': round(size / 1000, 1),
                    'products': products,
                    'protocluster_count': len(protoclusters),
                    'candidate_count': len(candidates),
                    'subregion_count': len(area.get('subregions') or []),
                    'contig_edge': is_contig_edge,
                    'gbk_path': self.find_antismash_region_gbk(sample, seqid, index),
                })

        region_sizes.sort()
        median_size_kb = round((region_sizes[len(region_sizes) // 2] / 1000), 1) if region_sizes else None
        index_path = self.resolve_project_path(f'{getattr(antismash, "antismash_dir", "")}/index.html')

        return response.Response({
            'sample_id': sample.sample_id,
            'full_name': sample.full_name,
            'version': data.get('version') or getattr(antismash, 'antismash_version', ''),
            'taxon': data.get('taxon', ''),
            'json_present': True,
            'report_url': f'/genomes/{sample.sample_id}/antismash/',
            'json_path': json_path,
            'index_html_path': self.relative_project_path(index_path) if index_path and index_path.exists() else '',
            'region_count': len(regions),
            'protocluster_count': protocluster_count,
            'candidate_count': candidate_count,
            'contig_edge_count': edge_count,
            'median_region_size_kb': median_size_kb,
            'product_counts': [
                {'product': product, 'count': count}
                for product, count in product_counter.most_common()
            ],
            'regions': regions,
        })

    def resolve_project_path(self, relative_path):
        if not relative_path:
            return None
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return settings.PROJECT_ROOT / path

    def relative_project_path(self, path):
        try:
            return str(path.relative_to(settings.PROJECT_ROOT))
        except ValueError:
            return str(path)

    def find_antismash_region_gbk(self, sample, seqid, index):
        antismash = getattr(sample, 'antismash_summary', None)
        antismash_dir = self.resolve_project_path(getattr(antismash, 'antismash_dir', ''))
        if not antismash_dir:
            return ''
        path = antismash_dir / f'{seqid}.region{index:03d}.gbk'
        return self.relative_project_path(path) if path.exists() else ''

    @decorators.action(detail=True, methods=['get'])
    def files(self, request, sample_id=None):
        queryset = self.get_object().files.all().order_by('data_type', 'path')
        serializer = serializers.SampleFileSerializer(queryset, many=True)
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=['get'], url_path='basic-metadata')
    def basic_metadata(self, request, sample_id=None):
        sample = self.get_object()
        return response.Response(serializers.basic_metadata_for_sample(sample.sample_id))


class BasicMetadataRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.BasicMetadataRecord.objects.all()
    serializer_class = serializers.BasicMetadataRecordSerializer
    filterset_fields = {
        'table_name': ['exact'],
        'record_key': ['exact', 'icontains'],
        'sample_id': ['exact'],
        'strain_id': ['exact'],
        'source_id': ['exact'],
    }
    search_fields = ['table_name', 'record_key', 'sample_id', 'strain_id', 'source_id']
    ordering_fields = ['table_name', 'record_key', 'sample_id', 'strain_id', 'source_id']
    ordering = ['table_name', 'record_key']


class ProteinViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Protein.objects.select_related('sample', 'general_annotation', 'pathogenicity_summary').all()
    lookup_field = 'protein_uid'
    filterset_fields = {
        'sample_id': ['exact'],
        'gene_id': ['exact', 'icontains'],
        'protein_id': ['exact', 'icontains'],
        'product': ['icontains'],
        'seqid': ['exact'],
        'has_general_functional_annotation': ['exact'],
        'has_pathogenicity_associated_feature': ['exact'],
        'general_annotation__kegg_ko': ['icontains'],
        'general_annotation__kegg_pathways': ['icontains'],
        'general_annotation__eggnog_preferred_name': ['icontains'],
        'general_annotation__eggnog_description': ['icontains'],
    }
    search_fields = [
        'protein_uid',
        'gene_id',
        'protein_id',
        'product',
        'general_annotation__eggnog_preferred_name',
        'general_annotation__eggnog_description',
        'general_annotation__kegg_ko',
        'general_annotation__kegg_pathways',
    ]
    ordering_fields = ['sample_id', 'seqid', 'start', 'end', 'protein_length']
    ordering = ['sample_id', 'seqid', 'start']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.ProteinDetailSerializer
        return serializers.ProteinSerializer

    @decorators.action(detail=True, methods=['get'])
    def features(self, request, protein_uid=None):
        queryset = self.get_object().pathogenicity_features.all().order_by('feature_type', 'source_key')
        serializer = serializers.ProteinPathogenicityFeatureSerializer(queryset, many=True)
        return response.Response(serializer.data)


class KeggPathwayMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.KeggPathwayMember.objects.select_related('sample', 'protein').all()
    serializer_class = serializers.KeggPathwayMemberSerializer
    filterset_fields = {
        'sample_id': ['exact'],
        'kegg_pathway_id': ['exact', 'icontains'],
        'kegg_ko': ['exact', 'icontains'],
        'gene_id': ['exact', 'icontains'],
        'source_protein_id': ['exact', 'icontains'],
    }
    search_fields = ['kegg_pathway_id', 'kegg_ko', 'gene_id', 'source_protein_id', 'preferred_name', 'description']
    ordering_fields = ['sample_id', 'kegg_pathway_id', 'seqid', 'start', 'score', 'evalue']
    ordering = ['sample_id', 'kegg_pathway_id', 'seqid', 'start']


class ProteinPathogenicityFeatureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ProteinPathogenicityFeature.objects.select_related('sample', 'protein').all()
    serializer_class = serializers.ProteinPathogenicityFeatureSerializer
    filterset_fields = {
        'sample_id': ['exact'],
        'feature_type': ['exact', 'icontains'],
        'source_key': ['exact'],
        'feature_id': ['exact', 'icontains'],
        'feature_label': ['icontains'],
        'prediction': ['exact', 'icontains'],
        'source_protein_id': ['exact', 'icontains'],
        'protein__gene_id': ['exact', 'icontains'],
        'protein__product': ['icontains'],
        'evidence_strength': ['exact'],
    }
    search_fields = [
        'feature_type',
        'source_key',
        'feature_id',
        'feature_label',
        'prediction',
        'notes',
        'source_protein_id',
        'protein__gene_id',
        'protein__protein_id',
        'protein__product',
    ]
    ordering_fields = ['sample_id', 'feature_type', 'source_key', 'score', 'evalue', 'coverage']
    ordering = ['sample_id', 'feature_type', 'source_key']


class AnnotationSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.AnnotationSource.objects.all()
    serializer_class = serializers.AnnotationSourceSerializer
    lookup_field = 'source_key'
    filterset_fields = ['category', 'sub_category', 'evidence_strength', 'result_level']
    search_fields = ['source_key', 'display_name', 'interpretation_note']
    ordering = ['category', 'source_key']
