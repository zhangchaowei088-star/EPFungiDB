from django.contrib import admin

from . import models


@admin.register(models.Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = (
        'sample_id',
        'full_name',
        'order_group',
        'family',
        'genus',
        'species',
        'protein_count',
        'busco_complete_pct',
        'bgc_count',
        'ready_full_analysis',
    )
    list_filter = ('order_group', 'family', 'ready_basic_db', 'ready_full_analysis')
    search_fields = ('sample_id', 'full_name', 'genus', 'species', 'strain_from_name')


@admin.register(models.Protein)
class ProteinAdmin(admin.ModelAdmin):
    list_display = ('protein_uid', 'sample', 'gene_id', 'protein_id', 'seqid', 'start', 'end', 'protein_length')
    list_filter = ('has_general_functional_annotation', 'has_pathogenicity_associated_feature')
    search_fields = ('protein_uid', 'gene_id', 'protein_id', 'product')
    raw_id_fields = ('sample',)


@admin.register(models.KeggPathwayMember)
class KeggPathwayMemberAdmin(admin.ModelAdmin):
    list_display = ('sample', 'kegg_pathway_id', 'protein', 'gene_id', 'kegg_ko', 'preferred_name')
    list_filter = ('kegg_pathway_id', 'kegg_ko')
    search_fields = ('kegg_pathway_id', 'protein_id', 'gene_id', 'kegg_ko', 'description')
    raw_id_fields = ('sample', 'protein')


@admin.register(models.ProteinPathogenicityFeature)
class ProteinPathogenicityFeatureAdmin(admin.ModelAdmin):
    list_display = ('sample', 'protein', 'feature_type', 'source_key', 'feature_id', 'evidence_strength')
    list_filter = ('feature_type', 'source_key', 'evidence_strength')
    search_fields = ('protein_id', 'feature_id', 'feature_label', 'prediction')
    raw_id_fields = ('sample', 'protein')


@admin.register(models.BasicMetadataRecord)
class BasicMetadataRecordAdmin(admin.ModelAdmin):
    list_display = ('table_name', 'record_key', 'sample_id', 'strain_id', 'source_id')
    list_filter = ('table_name',)
    search_fields = ('record_key', 'sample_id', 'strain_id', 'source_id')


for model in (
    models.GenomeMetric,
    models.AnnotationSource,
    models.GeneralFunctionalAnnotationSummary,
    models.PathogenicityAssociatedSummary,
    models.BuscoSummary,
    models.AntismashGenomeSummary,
    models.SignalpSummary,
    models.AnalysisStatus,
    models.SampleFile,
    models.ProteinGeneralAnnotation,
    models.ProteinPathogenicitySummary,
):
    admin.site.register(model)
