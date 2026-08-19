from django.db import models


class Sample(models.Model):
    sample_id = models.CharField(max_length=80, primary_key=True)
    sample_id_source = models.CharField(max_length=120, blank=True)
    full_name = models.CharField(max_length=255, unique=True)
    file_prefix = models.CharField(max_length=255, blank=True)
    order_group = models.CharField(max_length=80, blank=True, db_index=True)
    abbreviation_source = models.CharField(max_length=120, blank=True)
    family = models.CharField(max_length=160, blank=True, db_index=True)
    genus = models.CharField(max_length=160, blank=True, db_index=True)
    species = models.CharField(max_length=255, blank=True, db_index=True)
    species_status = models.CharField(max_length=120, blank=True)
    genus_from_name = models.CharField(max_length=160, blank=True)
    species_epithet_from_name = models.CharField(max_length=160, blank=True)
    species_binomial_from_name = models.CharField(max_length=255, blank=True)
    strain_from_name = models.CharField(max_length=160, blank=True)
    genome_size = models.BigIntegerField(null=True, blank=True)
    gc_content = models.FloatField(null=True, blank=True)
    scaffold_count = models.IntegerField(null=True, blank=True)
    n50 = models.BigIntegerField(null=True, blank=True)
    gene_count = models.IntegerField(null=True, blank=True)
    protein_count = models.IntegerField(null=True, blank=True)
    functional_any_annotation_ratio = models.FloatField(null=True, blank=True)
    functional_unannotated_ratio = models.FloatField(null=True, blank=True)
    busco_complete_pct = models.FloatField(null=True, blank=True)
    busco_missing_pct = models.FloatField(null=True, blank=True)
    bgc_count = models.IntegerField(null=True, blank=True)
    effector_candidate_count = models.IntegerField(null=True, blank=True)
    cazyme_protein_count = models.IntegerField(null=True, blank=True)
    merops_protein_count = models.IntegerField(null=True, blank=True)
    signalp_total_proteins = models.IntegerField(null=True, blank=True)
    signalp_sp_count = models.IntegerField(null=True, blank=True)
    signalp_other_count = models.IntegerField(null=True, blank=True)
    signalp_sp_fraction = models.FloatField(null=True, blank=True)
    signalp_high_confidence_sp_count = models.IntegerField(null=True, blank=True)
    has_genome_core = models.BooleanField(default=False)
    has_functional_core = models.BooleanField(default=False)
    has_busco = models.BooleanField(default=False)
    has_antismash = models.BooleanField(default=False)
    has_signalp = models.BooleanField(default=False)
    ready_basic_db = models.BooleanField(default=False)
    ready_full_analysis = models.BooleanField(default=False)
    genome_dir = models.TextField(blank=True)
    genome_fasta_path = models.TextField(blank=True)
    cds_fasta_path = models.TextField(blank=True)
    gff3_path = models.TextField(blank=True)
    genbank_path = models.TextField(blank=True)
    protein_fasta_path = models.TextField(blank=True)
    busco_dir = models.TextField(blank=True)
    busco_summary_json_path = models.TextField(blank=True)
    antismash_dir = models.TextField(blank=True)
    antismash_json_path = models.TextField(blank=True)
    signalp_dir = models.TextField(blank=True)
    signalp_prediction_path = models.TextField(blank=True)

    class Meta:
        db_table = 'samples'
        indexes = [
            models.Index(fields=['order_group', 'family']),
            models.Index(fields=['genus', 'species']),
            models.Index(fields=['ready_basic_db', 'ready_full_analysis']),
        ]
        ordering = ['order_group', 'genus', 'species', 'sample_id']

    def __str__(self):
        return f'{self.sample_id} ({self.full_name})'


class GenomeMetric(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='genome_metric')
    full_name = models.CharField(max_length=255)
    order_group = models.CharField(max_length=80, blank=True, db_index=True)
    genome_size = models.BigIntegerField(null=True, blank=True)
    gc_content = models.FloatField(null=True, blank=True)
    n_content = models.FloatField(null=True, blank=True)
    scaffold_count = models.IntegerField(null=True, blank=True)
    n50 = models.BigIntegerField(null=True, blank=True)
    l50 = models.IntegerField(null=True, blank=True)
    max_scaffold_length = models.BigIntegerField(null=True, blank=True)
    mean_scaffold_length = models.FloatField(null=True, blank=True)
    gene_count = models.IntegerField(null=True, blank=True)
    protein_coding_count = models.IntegerField(null=True, blank=True)
    trna_count = models.IntegerField(null=True, blank=True)
    rrna_count = models.IntegerField(null=True, blank=True)
    ncrna_count = models.IntegerField(null=True, blank=True)
    protein_count = models.IntegerField(null=True, blank=True)
    mean_protein_length = models.FloatField(null=True, blank=True)
    parse_errors = models.TextField(blank=True)

    class Meta:
        db_table = 'genome_metrics'


class AnnotationSource(models.Model):
    source_key = models.CharField(max_length=80, primary_key=True)
    display_name = models.CharField(max_length=160)
    category = models.CharField(max_length=120, db_index=True)
    sub_category = models.CharField(max_length=160, blank=True)
    evidence_type = models.CharField(max_length=160, blank=True)
    evidence_strength = models.CharField(max_length=80, blank=True)
    result_level = models.CharField(max_length=80, blank=True)
    primary_output_table = models.CharField(max_length=160, blank=True)
    interpretation_note = models.TextField(blank=True)

    class Meta:
        db_table = 'annotation_sources'
        ordering = ['category', 'source_key']

    def __str__(self):
        return self.display_name


class GeneralFunctionalAnnotationSummary(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='functional_summary')
    full_name = models.CharField(max_length=255)
    annotation_category = models.CharField(max_length=120, blank=True)
    species = models.CharField(max_length=255, blank=True)
    funannotate_species_name = models.CharField(max_length=255, blank=True)
    total_genes = models.IntegerField(null=True, blank=True)
    funannotate_annotated_genes = models.IntegerField(null=True, blank=True)
    eggnog_matched_genes = models.IntegerField(null=True, blank=True)
    eggnog_annotated_genes = models.IntegerField(null=True, blank=True)
    any_functionally_annotated_genes = models.IntegerField(null=True, blank=True)
    unannotated_genes = models.IntegerField(null=True, blank=True)
    funannotate_annotation_ratio = models.FloatField(null=True, blank=True)
    eggnog_match_ratio = models.FloatField(null=True, blank=True)
    eggnog_annotation_ratio = models.FloatField(null=True, blank=True)
    any_annotation_ratio = models.FloatField(null=True, blank=True)
    unannotated_ratio = models.FloatField(null=True, blank=True)
    eggnog_only_records = models.IntegerField(null=True, blank=True)
    complete_02_annotation = models.BooleanField(default=False)
    complete_funannotate_and_02 = models.BooleanField(default=False)
    output = models.TextField(blank=True)

    class Meta:
        db_table = 'general_functional_annotation_summary'


class PathogenicityAssociatedSummary(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='pathogenicity_summary')
    full_name = models.CharField(max_length=255)
    annotation_category = models.CharField(max_length=120, blank=True)
    has_signalp = models.BooleanField(default=False)
    has_effectorp = models.BooleanField(default=False)
    has_cazyme = models.BooleanField(default=False)
    has_merops = models.BooleanField(default=False)
    has_antismash = models.BooleanField(default=False)
    complete_pathogenicity_associated_features = models.BooleanField(default=False)
    signalp_total_proteins = models.IntegerField(null=True, blank=True)
    signalp_sp_count = models.IntegerField(null=True, blank=True)
    signalp_other_count = models.IntegerField(null=True, blank=True)
    signalp_sp_fraction = models.FloatField(null=True, blank=True)
    signalp_high_confidence_sp_count = models.IntegerField(null=True, blank=True)
    effectorp_total_proteins = models.IntegerField(null=True, blank=True)
    effector_candidate_count = models.IntegerField(null=True, blank=True)
    cytoplasmic_effector_count = models.IntegerField(null=True, blank=True)
    apoplastic_effector_count = models.IntegerField(null=True, blank=True)
    dual_localization_effector_count = models.IntegerField(null=True, blank=True)
    non_effector_count = models.IntegerField(null=True, blank=True)
    effector_candidate_fraction = models.FloatField(null=True, blank=True)
    effectors_fasta_count = models.IntegerField(null=True, blank=True)
    noneffectors_fasta_count = models.IntegerField(null=True, blank=True)
    cazyme_hit_count = models.IntegerField(null=True, blank=True)
    cazyme_protein_count = models.IntegerField(null=True, blank=True)
    merops_hit_count = models.IntegerField(null=True, blank=True)
    merops_protein_count = models.IntegerField(null=True, blank=True)
    bgc_count = models.IntegerField(null=True, blank=True)
    antismash_top_products = models.TextField(blank=True)
    signalp_prediction_path = models.TextField(blank=True)
    effectorp_path = models.TextField(blank=True)
    cazyme_tsv_path = models.TextField(blank=True)
    merops_tsv_path = models.TextField(blank=True)
    antismash_json_path = models.TextField(blank=True)

    class Meta:
        db_table = 'pathogenicity_associated_summary'


class BuscoSummary(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='busco_summary')
    source_group = models.CharField(max_length=80, blank=True)
    full_name = models.CharField(max_length=255)
    lineage = models.CharField(max_length=120, blank=True)
    busco_version = models.CharField(max_length=80, blank=True)
    complete_pct = models.FloatField(null=True, blank=True)
    complete_buscos = models.IntegerField(null=True, blank=True)
    single_copy_pct = models.FloatField(null=True, blank=True)
    single_copy_buscos = models.IntegerField(null=True, blank=True)
    duplicated_pct = models.FloatField(null=True, blank=True)
    duplicated_buscos = models.IntegerField(null=True, blank=True)
    fragmented_pct = models.FloatField(null=True, blank=True)
    fragmented_buscos = models.IntegerField(null=True, blank=True)
    missing_pct = models.FloatField(null=True, blank=True)
    missing_buscos = models.IntegerField(null=True, blank=True)
    n_markers = models.IntegerField(null=True, blank=True)
    avg_identity = models.FloatField(null=True, blank=True)
    internal_stop_codon_pct = models.FloatField(null=True, blank=True)
    one_line_summary = models.CharField(max_length=255, blank=True)
    busco_dir = models.TextField(blank=True)
    summary_json_path = models.TextField(blank=True)
    summary_txt_path = models.TextField(blank=True)
    has_summary_json = models.BooleanField(default=False)
    has_summary_txt = models.BooleanField(default=False)
    parse_error = models.TextField(blank=True)

    class Meta:
        db_table = 'busco_summary'
        indexes = [models.Index(fields=['complete_pct', 'missing_pct'])]


class AntismashGenomeSummary(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='antismash_summary')
    full_name = models.CharField(max_length=255)
    genome = models.CharField(max_length=255, blank=True)
    family = models.CharField(max_length=160, blank=True)
    genus = models.CharField(max_length=160, blank=True)
    species = models.CharField(max_length=255, blank=True)
    species_status = models.CharField(max_length=120, blank=True)
    bgc_count = models.IntegerField(null=True, blank=True)
    json_records = models.IntegerField(null=True, blank=True)
    json_present = models.BooleanField(default=False)
    html_present = models.BooleanField(default=False)
    zip_present = models.BooleanField(default=False)
    full_gbk_present = models.BooleanField(default=False)
    antismash_version = models.CharField(max_length=80, blank=True)
    taxonomy_empty_in_json = models.BooleanField(default=False)
    contig_edge_bgcs = models.IntegerField(null=True, blank=True)
    contig_edge_fraction = models.FloatField(null=True, blank=True)
    no_biosynthetic_cds_bgcs = models.IntegerField(null=True, blank=True)
    cds_zero_bgcs = models.IntegerField(null=True, blank=True)
    median_bgc_size_kb = models.FloatField(null=True, blank=True)
    top_products = models.TextField(blank=True)
    antismash_dir = models.TextField(blank=True)

    class Meta:
        db_table = 'antismash_genome_summary'
        indexes = [models.Index(fields=['bgc_count'])]


class SignalpSummary(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='signalp_summary')
    full_name = models.CharField(max_length=255)
    signalp_total_proteins = models.IntegerField(null=True, blank=True)
    signalp_sp_count = models.IntegerField(null=True, blank=True)
    signalp_other_count = models.IntegerField(null=True, blank=True)
    signalp_sp_fraction = models.FloatField(null=True, blank=True)
    signalp_high_confidence_sp_count = models.IntegerField(null=True, blank=True)
    signalp_dir = models.TextField(blank=True)
    prediction_results_path = models.TextField(blank=True)
    output_gff3_path = models.TextField(blank=True)

    class Meta:
        db_table = 'signalp_summary'
        indexes = [models.Index(fields=['signalp_sp_count'])]


class AnalysisStatus(models.Model):
    sample = models.OneToOneField(Sample, to_field='sample_id', db_column='sample_id', primary_key=True, on_delete=models.CASCADE, related_name='analysis_status')
    full_name = models.CharField(max_length=255)
    has_genome_core = models.BooleanField(default=False)
    has_protein_fasta = models.BooleanField(default=False)
    has_eggnog = models.BooleanField(default=False)
    has_effectorp = models.BooleanField(default=False)
    has_cazy = models.BooleanField(default=False)
    has_merops = models.BooleanField(default=False)
    has_functional_core = models.BooleanField(default=False)
    has_busco = models.BooleanField(default=False)
    has_antismash = models.BooleanField(default=False)
    has_signalp = models.BooleanField(default=False)
    ready_basic_db = models.BooleanField(default=False)
    ready_full_analysis = models.BooleanField(default=False)

    class Meta:
        db_table = 'analysis_status'


class SampleFile(models.Model):
    sample = models.ForeignKey(Sample, to_field='sample_id', db_column='sample_id', on_delete=models.CASCADE, related_name='files')
    full_name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=120, db_index=True)
    object_type = models.CharField(max_length=80, blank=True)
    path = models.TextField()
    exists = models.BooleanField(default=False)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    mtime = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = 'sample_files'
        indexes = [
            models.Index(fields=['sample', 'data_type']),
            models.Index(fields=['exists']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['sample', 'data_type', 'path'], name='uniq_sample_file_path'),
        ]


class Protein(models.Model):
    protein_uid = models.CharField(max_length=180, primary_key=True)
    sample = models.ForeignKey(Sample, to_field='sample_id', db_column='sample_id', on_delete=models.CASCADE, related_name='proteins')
    full_name = models.CharField(max_length=255)
    gene_id = models.CharField(max_length=120, blank=True)
    transcript_id = models.CharField(max_length=120, blank=True)
    protein_id = models.CharField(max_length=120)
    seqid = models.CharField(max_length=160, blank=True)
    start = models.BigIntegerField(null=True, blank=True)
    end = models.BigIntegerField(null=True, blank=True)
    strand = models.CharField(max_length=8, blank=True)
    protein_length = models.IntegerField(null=True, blank=True)
    product = models.TextField(blank=True)
    has_general_functional_annotation = models.BooleanField(default=False)
    has_pathogenicity_associated_feature = models.BooleanField(default=False)

    class Meta:
        db_table = 'proteins'
        indexes = [
            models.Index(fields=['sample', 'protein_id']),
            models.Index(fields=['sample', 'gene_id']),
            models.Index(fields=['sample', 'seqid', 'start']),
            models.Index(fields=['has_pathogenicity_associated_feature']),
        ]

    def __str__(self):
        return self.protein_uid


class ProteinGeneralAnnotation(models.Model):
    protein = models.OneToOneField(Protein, to_field='protein_uid', db_column='protein_uid', primary_key=True, on_delete=models.CASCADE, related_name='general_annotation')
    sample = models.ForeignKey(Sample, to_field='sample_id', db_column='sample_id', on_delete=models.CASCADE, related_name='protein_general_annotations')
    full_name = models.CharField(max_length=255)
    gene_id = models.CharField(max_length=120, blank=True)
    source_protein_id = models.CharField(max_length=120, db_column='protein_id')
    funannotate_product = models.TextField(blank=True)
    funannotate_dbxref = models.TextField(blank=True)
    funannotate_note = models.TextField(blank=True)
    eggnog_seed_ortholog = models.CharField(max_length=255, blank=True)
    eggnog_evalue = models.FloatField(null=True, blank=True)
    eggnog_score = models.FloatField(null=True, blank=True)
    eggnog_cog_category = models.CharField(max_length=80, blank=True)
    eggnog_description = models.TextField(blank=True)
    eggnog_preferred_name = models.CharField(max_length=255, blank=True)
    go_terms = models.TextField(blank=True)
    ec_numbers = models.TextField(blank=True)
    kegg_ko = models.TextField(blank=True, db_index=True)
    kegg_pathways = models.TextField(blank=True)
    kegg_modules = models.TextField(blank=True)
    kegg_reactions = models.TextField(blank=True)
    brite_terms = models.TextField(blank=True)
    pfam_domains = models.TextField(blank=True)

    class Meta:
        db_table = 'protein_general_annotation_summary'
        indexes = [
            models.Index(fields=['sample', 'source_protein_id']),
            models.Index(fields=['sample', 'kegg_ko']),
        ]


class KeggPathwayMember(models.Model):
    sample = models.ForeignKey(Sample, to_field='sample_id', db_column='sample_id', on_delete=models.CASCADE, related_name='kegg_pathway_members')
    full_name = models.CharField(max_length=255)
    kegg_pathway_id = models.CharField(max_length=40, db_index=True)
    protein = models.ForeignKey(Protein, to_field='protein_uid', db_column='protein_uid', on_delete=models.CASCADE, related_name='kegg_pathways')
    source_protein_id = models.CharField(max_length=120, db_column='protein_id')
    gene_id = models.CharField(max_length=120, blank=True)
    seqid = models.CharField(max_length=160, blank=True)
    start = models.BigIntegerField(null=True, blank=True)
    end = models.BigIntegerField(null=True, blank=True)
    strand = models.CharField(max_length=8, blank=True)
    kegg_ko = models.CharField(max_length=80, blank=True, db_index=True)
    preferred_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    evalue = models.FloatField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'kegg_pathway_members'
        indexes = [
            models.Index(fields=['sample', 'kegg_pathway_id']),
            models.Index(fields=['sample', 'kegg_ko']),
            models.Index(fields=['protein']),
        ]


class ProteinPathogenicitySummary(models.Model):
    protein = models.OneToOneField(Protein, to_field='protein_uid', db_column='protein_uid', primary_key=True, on_delete=models.CASCADE, related_name='pathogenicity_summary')
    sample = models.ForeignKey(Sample, to_field='sample_id', db_column='sample_id', on_delete=models.CASCADE, related_name='protein_pathogenicity_summaries')
    full_name = models.CharField(max_length=255)
    gene_id = models.CharField(max_length=120, blank=True)
    source_protein_id = models.CharField(max_length=120, db_column='protein_id')
    is_secreted = models.BooleanField(default=False)
    signalp_prediction = models.CharField(max_length=80, blank=True)
    signalp_sp_score = models.FloatField(null=True, blank=True)
    signalp_cs_position = models.CharField(max_length=80, blank=True)
    is_effector_candidate = models.BooleanField(default=False)
    effectorp_prediction = models.CharField(max_length=120, blank=True)
    effectorp_score = models.FloatField(null=True, blank=True)
    has_cazyme = models.BooleanField(default=False)
    cazyme_families = models.TextField(blank=True)
    has_merops = models.BooleanField(default=False)
    merops_families = models.TextField(blank=True)
    pathogenicity_feature_count = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'protein_pathogenicity_summary'
        indexes = [
            models.Index(fields=['sample', 'is_secreted']),
            models.Index(fields=['sample', 'is_effector_candidate']),
            models.Index(fields=['sample', 'has_cazyme']),
            models.Index(fields=['sample', 'has_merops']),
        ]


class ProteinPathogenicityFeature(models.Model):
    protein = models.ForeignKey(Protein, to_field='protein_uid', db_column='protein_uid', on_delete=models.CASCADE, related_name='pathogenicity_features')
    sample = models.ForeignKey(Sample, to_field='sample_id', db_column='sample_id', on_delete=models.CASCADE, related_name='protein_pathogenicity_features')
    full_name = models.CharField(max_length=255)
    source_protein_id = models.CharField(max_length=120, db_column='protein_id')
    feature_type = models.CharField(max_length=120, db_index=True)
    source_key = models.CharField(max_length=80, db_index=True)
    feature_id = models.CharField(max_length=160, blank=True)
    feature_label = models.CharField(max_length=255, blank=True)
    prediction = models.CharField(max_length=160, blank=True)
    score = models.TextField(blank=True, null=True)
    start = models.IntegerField(null=True, blank=True)
    end = models.IntegerField(null=True, blank=True)
    evalue = models.FloatField(null=True, blank=True)
    coverage = models.FloatField(null=True, blank=True)
    evidence_strength = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'protein_pathogenicity_features'
        indexes = [
            models.Index(fields=['sample', 'feature_type']),
            models.Index(fields=['sample', 'source_key']),
            models.Index(fields=['protein']),
            models.Index(fields=['feature_id']),
        ]


class BasicMetadataRecord(models.Model):
    table_name = models.CharField(max_length=120, db_index=True)
    record_key = models.CharField(max_length=255)
    sample_id = models.CharField(max_length=80, blank=True, db_index=True)
    strain_id = models.CharField(max_length=80, blank=True, db_index=True)
    source_id = models.CharField(max_length=80, blank=True, db_index=True)
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = 'basic_metadata_records'
        constraints = [
            models.UniqueConstraint(fields=['table_name', 'record_key'], name='uniq_basic_metadata_record'),
        ]
        indexes = [
            models.Index(fields=['table_name', 'sample_id']),
            models.Index(fields=['table_name', 'strain_id']),
        ]
        ordering = ['table_name', 'record_key']

    def __str__(self):
        return f'{self.table_name}:{self.record_key}'
