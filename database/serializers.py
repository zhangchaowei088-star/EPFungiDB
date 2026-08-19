from rest_framework import serializers

from . import models


class GenomeMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GenomeMetric
        exclude = ['sample']


class BuscoSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BuscoSummary
        exclude = ['sample']


class AntismashGenomeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AntismashGenomeSummary
        exclude = ['sample']


class SignalpSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SignalpSummary
        exclude = ['sample']


class GeneralFunctionalAnnotationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeneralFunctionalAnnotationSummary
        exclude = ['sample']


class PathogenicityAssociatedSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PathogenicityAssociatedSummary
        exclude = ['sample']


class AnalysisStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AnalysisStatus
        exclude = ['sample']


class BasicMetadataRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BasicMetadataRecord
        fields = '__all__'


def basic_metadata_for_sample(sample_id):
    records = models.BasicMetadataRecord.objects.filter(sample_id=sample_id)
    metadata_summary = records.filter(table_name='metadata_summary').values_list('payload', flat=True).first()
    identity_summary = records.filter(table_name='strain_identity_summary').values_list('payload', flat=True).first()
    sample_map = records.filter(table_name='sample_strain_map').values_list('payload', flat=True).first()
    strain_id = ''
    if sample_map:
        strain_id = sample_map.get('strain_id', '')
    if not strain_id and metadata_summary:
        strain_id = metadata_summary.get('strain_id', '')
    if not strain_id and identity_summary:
        strain_id = identity_summary.get('strain_id', '')

    strain_records = models.BasicMetadataRecord.objects.filter(strain_id=strain_id) if strain_id else models.BasicMetadataRecord.objects.none()

    def payloads(queryset, limit=20):
        return list(queryset.values_list('payload', flat=True)[:limit])

    return {
        'metadata_summary': metadata_summary or {},
        'strain_identity_summary': identity_summary or {},
        'sample_strain_map': sample_map or {},
        'external_accessions': payloads(records.filter(table_name='external_accessions').order_by('record_key'), 30),
        'strain_entity': strain_records.filter(table_name='strain_entities').values_list('payload', flat=True).first() or {},
        'identifiers': payloads(strain_records.filter(table_name='strain_identifiers').order_by('record_key')),
        'taxonomy_assertions': payloads(strain_records.filter(table_name='strain_taxonomy_assertions').order_by('record_key'), 30),
        'host_associations': payloads(strain_records.filter(table_name='strain_host_associations').order_by('record_key')),
        'isolation_events': payloads(strain_records.filter(table_name='strain_isolation_events').order_by('record_key')),
        'locations': payloads(strain_records.filter(table_name='strain_locations').order_by('record_key')),
        'literature_retrievals': payloads(records.filter(table_name='strain_literature_retrievals').order_by('record_key')),
        'literature_evidence': payloads(records.filter(table_name='strain_literature_evidence').order_by('record_key'), 30),
        'virulence_assays': payloads(strain_records.filter(table_name='strain_virulence_assays').order_by('record_key')),
    }


class SampleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Sample
        fields = [
            'sample_id',
            'full_name',
            'order_group',
            'family',
            'genus',
            'species',
            'strain_from_name',
            'genome_size',
            'gc_content',
            'n50',
            'gene_count',
            'protein_count',
            'busco_complete_pct',
            'bgc_count',
            'effector_candidate_count',
            'cazyme_protein_count',
            'merops_protein_count',
            'signalp_sp_count',
            'ready_basic_db',
            'ready_full_analysis',
        ]


class SampleDetailSerializer(serializers.ModelSerializer):
    genome_metric = GenomeMetricSerializer(read_only=True)
    functional_summary = GeneralFunctionalAnnotationSummarySerializer(read_only=True)
    pathogenicity_summary = PathogenicityAssociatedSummarySerializer(read_only=True)
    busco_summary = BuscoSummarySerializer(read_only=True)
    antismash_summary = AntismashGenomeSummarySerializer(read_only=True)
    signalp_summary = SignalpSummarySerializer(read_only=True)
    analysis_status = AnalysisStatusSerializer(read_only=True)
    basic_metadata = serializers.SerializerMethodField()

    def get_basic_metadata(self, obj):
        return basic_metadata_for_sample(obj.sample_id)

    class Meta:
        model = models.Sample
        fields = '__all__'


class AnnotationSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AnnotationSource
        fields = '__all__'


class SampleFileSerializer(serializers.ModelSerializer):
    sample_id = serializers.CharField(read_only=True)

    class Meta:
        model = models.SampleFile
        fields = '__all__'


class ProteinSerializer(serializers.ModelSerializer):
    sample_id = serializers.CharField(read_only=True)
    gene_name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    kegg_info = serializers.SerializerMethodField()

    def get_gene_name(self, obj):
        annotation = getattr(obj, 'general_annotation', None)
        if annotation and annotation.eggnog_preferred_name and annotation.eggnog_preferred_name != '-':
            return annotation.eggnog_preferred_name
        return obj.gene_id

    def get_description(self, obj):
        annotation = getattr(obj, 'general_annotation', None)
        if annotation and annotation.eggnog_description and annotation.eggnog_description != '-':
            return annotation.eggnog_description
        return obj.product

    def get_kegg_info(self, obj):
        annotation = getattr(obj, 'general_annotation', None)
        if not annotation:
            return ''
        parts = [annotation.kegg_ko, annotation.kegg_pathways]
        return '; '.join(part for part in parts if part)

    class Meta:
        model = models.Protein
        fields = [
            'protein_uid',
            'sample_id',
            'full_name',
            'gene_id',
            'transcript_id',
            'protein_id',
            'seqid',
            'start',
            'end',
            'strand',
            'protein_length',
            'product',
            'gene_name',
            'description',
            'kegg_info',
            'has_general_functional_annotation',
            'has_pathogenicity_associated_feature',
            'sample',
        ]


class ProteinGeneralAnnotationSerializer(serializers.ModelSerializer):
    protein_uid = serializers.CharField(source='protein_id', read_only=True)
    sample_id = serializers.CharField(read_only=True)

    class Meta:
        model = models.ProteinGeneralAnnotation
        fields = '__all__'


class ProteinPathogenicitySummarySerializer(serializers.ModelSerializer):
    protein_uid = serializers.CharField(source='protein_id', read_only=True)
    sample_id = serializers.CharField(read_only=True)

    class Meta:
        model = models.ProteinPathogenicitySummary
        fields = '__all__'


class ProteinDetailSerializer(serializers.ModelSerializer):
    sample_id = serializers.CharField(read_only=True)
    general_annotation = ProteinGeneralAnnotationSerializer(read_only=True)
    pathogenicity_summary = ProteinPathogenicitySummarySerializer(read_only=True)

    class Meta:
        model = models.Protein
        fields = '__all__'


class KeggPathwayMemberSerializer(serializers.ModelSerializer):
    sample_id = serializers.CharField(read_only=True)
    protein_uid = serializers.CharField(source='protein_id', read_only=True)
    pathway_name = serializers.SerializerMethodField()
    kegg_pathway_url = serializers.SerializerMethodField()
    kegg_ko_url = serializers.SerializerMethodField()

    def get_pathway_name(self, obj):
        from .views import kegg_pathway_name
        return kegg_pathway_name(obj.kegg_pathway_id)

    def get_kegg_pathway_url(self, obj):
        pathway_id = obj.kegg_pathway_id
        if pathway_id.startswith('ko') and len(pathway_id) > 2:
            pathway_id = f'map{pathway_id[2:]}'
        return f'https://www.kegg.jp/pathway/{pathway_id}' if pathway_id else ''

    def get_kegg_ko_url(self, obj):
        return f'https://www.kegg.jp/entry/{obj.kegg_ko}' if obj.kegg_ko else ''

    class Meta:
        model = models.KeggPathwayMember
        fields = '__all__'


class ProteinPathogenicityFeatureSerializer(serializers.ModelSerializer):
    sample_id = serializers.CharField(read_only=True)
    protein_uid = serializers.CharField(source='protein_id', read_only=True)
    gene_id = serializers.CharField(source='protein.gene_id', read_only=True)
    protein_id = serializers.CharField(source='protein.protein_id', read_only=True)
    product = serializers.CharField(source='protein.product', read_only=True)
    seqid = serializers.CharField(source='protein.seqid', read_only=True)
    gene_start = serializers.IntegerField(source='protein.start', read_only=True)
    gene_end = serializers.IntegerField(source='protein.end', read_only=True)
    strand = serializers.CharField(source='protein.strand', read_only=True)

    class Meta:
        model = models.ProteinPathogenicityFeature
        fields = '__all__'
